"""
M2 收费单元-OD(path)小时流量统计服务

核心流程：
CSV逐行读取 → intervalgroup+intervaltimegroup同步修复 → numPath映射
→ od_section_path_id查找/插入 → (section_id, stat_hour)去重计数 → 聚合upsert

支持三种运行模式：
1. 单进程月文件模式 (num_workers=1, data_dir=""): 原有逻辑
2. 多进程月文件模式 (num_workers>1, data_dir=""): CSV字节偏移分区并行
3. 日文件模式 (data_dir非空): 按日文件并行，输出日表
   - 单进程: _run_sequential_daily
   - 多进程: _run_parallel_daily，日文件Round-Robin分配给Worker
"""

import json
import multiprocessing
import os
import time
from collections import defaultdict
from typing import Optional

from tqdm import tqdm

from src.app.enums import TaskStatus
from src.app.logger import LoggerMixin, get_logger
from src.modules.m2_od_flow.csv_reader import (
    _detect_has_header,
    build_csv_offset_index,
    count_csv_lines,
    discover_daily_files,
    get_csv_path,
    iter_csv_batches,
    iter_csv_partition,
)
from src.modules.m2_od_flow.fix_failure_logger import FixFailureLogger
from src.modules.m2_od_flow.flow_stat_repository import FlowStatRepository
from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams, FlowStatResult, WorkerResult, WorkerStatus
from src.modules.m2_od_flow.interval_fixer import (
    TopologyChecker,
    fix_intervalgroup_batch,
    split_intervalgroup,
)
from src.modules.m6_od_section_path.repository import M6Repository
from src.modules.m2_od_flow.checkpoint import (
    load_checkpoint,
    save_checkpoint,
    clear_checkpoint,
    load_daily_checkpoint,
    save_daily_checkpoint,
    clear_daily_checkpoint,
)

logger = get_logger(__name__)

# Module-level shared data for fork-based multiprocessing.
# Populated by _run_parallel() / _run_parallel_daily() before forking, read by worker processes via CoW.
_shared_section_map: dict[str, int] = {}
_shared_od_path_lookup: dict[tuple, int] = {}
_shared_topo_checker: Optional[TopologyChecker] = None

# CSV columns to extract from the source file (logical names)
CSV_COLUMNS = [
    "enid", "exid", "intervalgroup", "intervaltimegroup",
    "envehicleid", "exvehicleid", "entime", "extime",
    "feevehicletype", "envehicletype",
]

# Actual column order in the CSV file (for headerless files, positional mapping)
# Header: exid,enid,intervalgroup,intervaltimegroup,envehicleid,exvehicleid,entime,extime,feevehicletype,exvehicleclass,envehicletype,envehicleclass
CSV_COLUMNS_IN_FILE_ORDER = [
    "exid", "enid", "intervalgroup", "intervaltimegroup",
    "envehicleid", "exvehicleid", "entime", "extime",
    "feevehicletype", "envehicletype",
]


def _resolve_vehicle_type(record: dict) -> str:
    """车型取值：feevehicletype 非空则用，否则 envehicletype，都空返回 '0'"""
    fee = record.get("feevehicletype", "").strip()
    if fee:
        return fee
    en = record.get("envehicletype", "").strip()
    if en:
        return en
    return "0"


def _adjacent_dedup(numbers: list) -> list:
    """移除列表中连续重复元素"""
    deduped = []
    prev = None
    for n in numbers:
        if n != prev:
            deduped.append(n)
            prev = n
    return deduped


def _extract_day_version(filepath: str) -> str:
    """从日文件路径提取日版字符串，如 data_20260301.csv -> 20260301"""
    basename = os.path.basename(filepath)
    return basename.replace("data_", "").replace(".csv", "")


class FlowStatService(LoggerMixin):
    """M2 收费单元-OD(path)小时流量统计服务"""

    def __init__(self):
        self.repository = FlowStatRepository()
        self.section_map: dict[str, int] = {}  # section_id -> section_number
        self.od_path_lookup: dict[tuple, int] = {}  # (enid,exid,numpath,version) -> id
        self.topo_checker: Optional[TopologyChecker] = None
        self.version = ""
        self._failure_logger: Optional[FixFailureLogger] = None
        # Aggregation: {(section_id, od_path_id, stat_hour): count}
        self._flow_agg: dict[tuple, int] = defaultdict(int)
        self._map_inserted = 0
        self._fix_failures = 0

    def _load_dependencies(self, section_version: str, topo_version: str, map_version: str) -> None:
        """Pre-load all dependencies into memory"""
        logger.info("Pre-loading dependencies...")

        # 1. section_number mapping (reuse M6 repository logic)
        m6_repo = M6Repository()
        self.section_map = m6_repo.load_section_number_map(section_version)
        logger.info(f"Loaded {len(self.section_map)} section_number mappings")

        # 2. od_path_map lookup
        self.od_path_lookup = self.repository.load_od_path_map_lookup(map_version)
        logger.info(f"Loaded {len(self.od_path_lookup)} od_path_map entries")

        # 3. Topology cache
        self.topo_checker = TopologyChecker(version=topo_version)
        self.topo_checker.load_topology_cache()
        logger.info("Topology cache loaded")

    def _map_and_dedupe(self, intervalgroup: str) -> Optional[str]:
        """
        Map intervalgroup to deduped numpath (three-step dedup logic).
        Only returns final_numpath, step1_numpath not needed here.
        """
        section_ids = split_intervalgroup(intervalgroup)
        if not section_ids:
            return None

        numbers = [self.section_map.get(sid) for sid in section_ids]

        # Step 1: adjacent dedup
        deduped = _adjacent_dedup([n for n in numbers if n is not None])
        if not deduped:
            return None

        # Step 2: pair dedup (try offset 0 and 1, pick shorter)
        best_result = None
        best_elem_count = float("inf")

        for offset in range(2):
            pairs = []
            i = offset
            if i > 0:
                pairs.append(("", deduped[0]))
            while i + 1 < len(deduped):
                pairs.append((deduped[i], deduped[i + 1]))
                i += 2
            if (i + 1) == len(deduped):
                pairs.append((deduped[i], ""))

            results_list = []
            k = 0
            while k < len(pairs):
                a, b = pairs[k]
                if a:
                    results_list.append(a)
                if b:
                    results_list.append(b)
                if k + 1 < len(pairs):
                    c, d = pairs[k + 1]
                    if (a, b) == (c, d):
                        k += 2
                        continue
                k += 1

            if offset == 0 and i < len(deduped):
                results_list.append(deduped[-1])
            if offset == 1:
                if deduped[0] not in results_list:
                    results_list.insert(0, deduped[0])
                if i >= len(deduped) and len(deduped) % 2 == 1:
                    results_list.append(deduped[-1])

            if len(results_list) < best_elem_count:
                best_elem_count = len(results_list)
                best_result = results_list

        if not best_result:
            return None

        # Step 3: adjacent dedup again (Step 2 may leave adjacent duplicates)
        best_result = _adjacent_dedup(best_result)

        return "|".join(str(x) for x in best_result)

    @staticmethod
    def _truncate_to_hour(time_str: str) -> Optional[str]:
        """Truncate time to hour: '2026-03-15 14:30:00' -> '2026-03-15 14:00:00'"""
        if not time_str or len(time_str) < 13:
            return None
        return time_str[:14] + "00:00"

    def _get_or_create_od_path_id(
        self, enid: str, exid: str, numpath: str, fixed_ig: str
    ) -> Optional[int]:
        """Lookup or insert od_section_path_id"""
        lookup_key = (enid, exid, numpath, self.version)
        od_path_id = self.od_path_lookup.get(lookup_key)
        if od_path_id is not None:
            return od_path_id

        # Not found — insert new record
        od_path_id = self.repository.upsert_od_path_map({
            "enid": enid,
            "exid": exid,
            "numpath": numpath,
            "version_yyyyMM": self.version,
            "fixed_intervalpath": fixed_ig,
            "intervalpath_cnt": 1,
            "total_trip_cnt": 1,
            "path_freq_ratio": 1.0,
            "source_flag": "computed",
        })

        if od_path_id > 0:
            self.od_path_lookup[lookup_key] = od_path_id
            self._map_inserted += 1

        return od_path_id if od_path_id > 0 else None

    def _process_batch(self, batch: list[dict]) -> int:
        """
        Process one batch of CSV records.

        Returns:
            Number of unique (section_id, od_path_id, stat_hour, vehicle_type) entries in this batch
        """
        # Step 1: Fix intervalgroup + intervaltimegroup
        fix_results = fix_intervalgroup_batch(batch, topology=self.topo_checker)

        # Step 2: Per-record processing
        local_agg: dict[tuple, int] = defaultdict(int)

        for record, fix_result in tqdm(zip(batch, fix_results)):
            enid = record.get("enid", "")
            exid = record.get("exid", "")
            if not enid or not exid:
                continue

            # Skip and log fix failures
            if fix_result.error:
                if self._failure_logger:
                    self._failure_logger.log_failure(record, fix_result.error)
                self._fix_failures += 1
                continue

            fixed_ig = fix_result.fixed
            fixed_itg = fix_result.fixed_timegroup
            if not fixed_ig:
                continue

            # Step 2a: Map to numpath
            numpath = self._map_and_dedupe(fixed_ig)
            if not numpath:
                continue

            # Step 2b: Get or create od_section_path_id
            od_path_id = self._get_or_create_od_path_id(enid, exid, numpath, fixed_ig)
            if od_path_id is None:
                continue

            # Step 2c: Resolve vehicle type
            vehicle_type = _resolve_vehicle_type(record)

            # Step 2d: Split sections and times (1:1 aligned)
            section_ids = split_intervalgroup(fixed_ig)
            time_strs = split_intervalgroup(fixed_itg) if fixed_itg else []

            # Step 2e: Dedup per record — same (section_id, stat_hour) only counts once
            seen: set[tuple[str, str]] = set()

            for idx, sid in enumerate(section_ids):
                stat_hour = None
                if idx < len(time_strs):
                    stat_hour = self._truncate_to_hour(time_strs[idx])
                if not stat_hour:
                    continue

                key = (sid, stat_hour)
                if key in seen:
                    continue  # Same section in same hour — skip duplicate
                seen.add(key)

                local_agg[(sid, od_path_id, stat_hour, vehicle_type)] += 1

        # Step 3: Merge into global aggregation
        for key, count in local_agg.items():
            self._flow_agg[key] += count

        return len(local_agg)

    def _flush_to_db(self, table_version: Optional[str] = None) -> int:
        """Flush aggregation results to database

        Args:
            table_version: 日文件模式下传入日版（如 "20260301"），
                           月文件模式下默认使用 self.version
        """
        version = table_version or self.version
        records = []
        for (section_id, od_path_id, stat_hour, vehicle_type), count in self._flow_agg.items():
            records.append({
                "section_id": section_id,
                "od_section_path_id": od_path_id,
                "stat_hour": stat_hour,
                "vehicle_type": vehicle_type,
                "flow_cnt": count,
                "source_flag": "computed",
            })
        if records:
            self.repository.upsert_flow_records(records, version)
            logger.info(f"Upserted {len(records)} flow records to dws_section_od_path_flow_hour_{version}")
        # Clear aggregation after flush
        written = len(self._flow_agg)
        self._flow_agg = defaultdict(int)
        return written

    # ========================================================================
    # Unified entry point
    # ========================================================================

    def run(self, params: FlowStatParams) -> FlowStatResult:
        """Main entry point — dispatches to the appropriate mode"""
        if params.data_dir:
            # 日文件模式（日表输出）
            if params.num_workers > 1:
                return self._run_parallel_daily(params)
            return self._run_sequential_daily(params)
        # 旧月文件模式（月表输出，保持向后兼容）
        if params.num_workers > 1:
            return self._run_parallel(params)
        return self._run_sequential(params)

    # ========================================================================
    # Sequential mode (original logic, preserved for backward compatibility)
    # ========================================================================

    def _run_sequential(self, params: FlowStatParams) -> FlowStatResult:
        """Original single-process logic"""
        self.version = params.version_yyyyMM
        start_time = time.time()

        # Reset state
        self._flow_agg = defaultdict(int)
        self._map_inserted = 0
        self._fix_failures = 0

        # Determine CSV path
        csv_path = params.csv_path or get_csv_path(params.version_yyyyMM)
        if not os.path.exists(csv_path):
            error_msg = f"CSV file not found: {csv_path}"
            logger.error(error_msg)
            return FlowStatResult(
                status=TaskStatus.FAILED,
                errors=[error_msg],
                execution_time=0,
            )

        # Load dependencies
        self._load_dependencies(params.section_version, params.topo_version, params.version_yyyyMM)

        # Initialize failure logger
        failure_log_dir = os.path.join(params.output_dir, "fix_failures")
        self._failure_logger = FixFailureLogger(failure_log_dir, params.version_yyyyMM)

        # Ensure target table exists
        self.repository.create_table(params.version_yyyyMM)
        self.repository.create_bridge_table()

        total_records = 0
        batch_count = 0
        total_flow_written = 0
        errors = []
        warnings = []

        logger.info("=" * 60)
        logger.info("M2 Flow Stat: section-OD(path)-hour flow statistics [SEQUENTIAL]")
        logger.info(f"Version: {params.version_yyyyMM}")
        logger.info(f"CSV: {csv_path}")
        logger.info(f"Batch size: {params.batch_size:,}")
        logger.info(f"Upsert interval: every {params.upsert_interval} batches")
        logger.info("=" * 60)

        # Count total records for progress bar
        if params.max_records > 0:
            total_csv_records = params.max_records
            logger.info(f"Processing up to {total_csv_records:,} records (max-records mode)")
        else:
            total_csv_records = count_csv_lines(csv_path)
            logger.info(f"Total CSV records: {total_csv_records:,}")

        try:
            pbar = tqdm(
                total=total_csv_records,
                desc=f"M2[{params.version_yyyyMM}]",
                unit="rec",
                unit_scale=True,
                dynamic_ncols=True,
            )

            for batch in iter_csv_batches(
                file_path=csv_path,
                batch_size=params.batch_size,
                columns=CSV_COLUMNS,
            ):
                batch_count += 1
                batch_start = time.time()

                entries = self._process_batch(batch)
                total_records += len(batch)
                pbar.update(len(batch))

                batch_time = time.time() - batch_start
                logger.info(
                    f"Batch {batch_count}: {len(batch):,} records, "
                    f"{entries:,} flow entries, {batch_time:.2f}s"
                )

                # Periodic upsert
                if batch_count % params.upsert_interval == 0:
                    written = self._flush_to_db()
                    total_flow_written += written

                # Max records limit (for testing)
                if params.max_records > 0 and total_records >= params.max_records:
                    logger.info(f"Reached max_records limit: {params.max_records}")
                    break

            # Final flush
            written = self._flush_to_db()
            total_flow_written += written

            # Validate
            logger.info("Validating output...")
            validation = self.repository.validate_output(params.version_yyyyMM)
            if not validation.get("valid", False):
                warnings.append(f"Validation warnings: {validation.get('errors', 'Unknown')}")

            # Summary
            summary = self.repository.get_summary(params.version_yyyyMM)
            logger.info("=" * 60)
            logger.info("M2 Flow Stat completed:")
            logger.info(f"  Records processed: {total_records:,}")
            logger.info(f"  Fix failures: {self._fix_failures:,}")
            logger.info(f"  Batches: {batch_count}")
            logger.info(f"  Map records inserted: {self._map_inserted}")
            logger.info(f"  Flow records written: {total_flow_written:,}")
            if summary:
                logger.info(f"  Total flow_cnt: {summary.get('total_flow', 'N/A')}")
                logger.info(f"  Unique sections: {summary.get('unique_sections', 'N/A')}")
                logger.info(f"  Unique OD paths: {summary.get('unique_od_paths', 'N/A')}")
            logger.info("=" * 60)

            # Test mode: save local JSON
            local_output_path = self._maybe_save_local(params, total_records, total_flow_written, summary)

            execution_time = time.time() - start_time
            return FlowStatResult(
                status=TaskStatus.SUCCESS,
                records_processed=total_records,
                flow_records_written=total_flow_written,
                map_records_inserted=self._map_inserted,
                fix_failures=self._fix_failures,
                batches=batch_count,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                local_output_path=local_output_path,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"M2 Flow Stat failed: {e}")
            errors.append(str(e))
            return FlowStatResult(
                status=TaskStatus.FAILED,
                records_processed=total_records,
                flow_records_written=0,
                map_records_inserted=self._map_inserted,
                fix_failures=self._fix_failures,
                batches=batch_count,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
            )

        finally:
            if 'pbar' in dir():
                pbar.close()
            if self._failure_logger:
                self._failure_logger.close()
            if self.topo_checker:
                self.topo_checker.close()

    # ========================================================================
    # Sequential daily mode
    # ========================================================================

    def _run_sequential_daily(self, params: FlowStatParams) -> FlowStatResult:
        """Sequential processing using daily CSV files, output to daily tables"""
        self.version = params.version_yyyyMM
        start_time = time.time()

        # Reset state
        self._flow_agg = defaultdict(int)
        self._map_inserted = 0
        self._fix_failures = 0

        # Discover daily files
        daily_files = discover_daily_files(params.version_yyyyMM, params.data_dir)
        if not daily_files:
            error_msg = f"No daily files found in {params.data_dir}/{params.version_yyyyMM}/"
            logger.error(error_msg)
            return FlowStatResult(
                status=TaskStatus.FAILED,
                errors=[error_msg],
                execution_time=0,
            )

        # Load dependencies
        self._load_dependencies(params.section_version, params.topo_version, params.version_yyyyMM)

        # Initialize failure logger
        failure_log_dir = os.path.join(params.output_dir, "fix_failures")
        self._failure_logger = FixFailureLogger(failure_log_dir, params.version_yyyyMM)

        total_records = 0
        batch_count = 0
        total_flow_written = 0
        errors = []
        warnings = []
        daily_summaries: dict[str, dict] = {}

        # Count total records across all daily files
        total_csv_records = 0
        for fp in daily_files:
            has_header = _detect_has_header(fp)
            total_csv_records += count_csv_lines(fp, has_header=has_header)

        logger.info("=" * 60)
        logger.info("M2 Flow Stat [SEQUENTIAL-DAILY]")
        logger.info(f"Version: {params.version_yyyyMM}")
        logger.info(f"Daily files: {len(daily_files)}")
        logger.info(f"Total records: {total_csv_records:,}")
        logger.info(f"Batch size: {params.batch_size:,}")
        logger.info(f"Upsert interval: every {params.upsert_interval} batches")
        logger.info("=" * 60)

        try:
            pbar = tqdm(
                total=total_csv_records,
                desc=f"M2[{params.version_yyyyMM}]",
                unit="rec",
                unit_scale=True,
                dynamic_ncols=True,
            )

            for file_idx, csv_path in enumerate(daily_files):
                day_version = _extract_day_version(csv_path)
                has_header = _detect_has_header(csv_path)
                logger.info(f"--- Day file {file_idx + 1}/{len(daily_files)}: {os.path.basename(csv_path)} -> table _{day_version} ---")

                # Create daily table
                self.repository.create_table(day_version)
                self.repository.create_bridge_table()

                for batch in iter_csv_batches(
                    file_path=csv_path,
                    batch_size=params.batch_size,
                    columns=CSV_COLUMNS if has_header else CSV_COLUMNS_IN_FILE_ORDER,
                    has_header=has_header,
                ):
                    batch_count += 1
                    batch_start = time.time()

                    entries = self._process_batch(batch)
                    total_records += len(batch)
                    pbar.update(len(batch))

                    batch_time = time.time() - batch_start
                    logger.info(
                        f"Batch {batch_count}: {len(batch):,} records, "
                        f"{entries:,} flow entries, {batch_time:.2f}s"
                    )

                    # Periodic upsert to daily table
                    if batch_count % params.upsert_interval == 0:
                        written = self._flush_to_db(table_version=day_version)
                        total_flow_written += written

                    if params.max_records > 0 and total_records >= params.max_records:
                        break

                # Flush remaining records for this day
                written = self._flush_to_db(table_version=day_version)
                total_flow_written += written

                # Per-day summary
                day_summary = self.repository.get_summary(day_version)
                daily_summaries[day_version] = day_summary
                if day_summary:
                    logger.info(
                        f"  Day {day_version}: flow_cnt={day_summary.get('total_flow', 'N/A')}, "
                        f"sections={day_summary.get('unique_sections', 'N/A')}, "
                        f"od_paths={day_summary.get('unique_od_paths', 'N/A')}"
                    )

                if params.max_records > 0 and total_records >= params.max_records:
                    logger.info(f"Reached max_records limit: {params.max_records}")
                    break

            # Overall summary
            logger.info("=" * 60)
            logger.info("M2 Flow Stat [SEQUENTIAL-DAILY] completed:")
            logger.info(f"  Records processed: {total_records:,}")
            logger.info(f"  Fix failures: {self._fix_failures:,}")
            logger.info(f"  Batches: {batch_count}")
            logger.info(f"  Map records inserted: {self._map_inserted}")
            logger.info(f"  Flow records written: {total_flow_written:,}")
            logger.info(f"  Daily tables created: {len(daily_summaries)}")
            logger.info("=" * 60)

            # Test mode: save local JSON
            local_output_path = self._maybe_save_local(
                params, total_records, total_flow_written,
                {"daily_summaries": daily_summaries},
            )

            execution_time = time.time() - start_time
            return FlowStatResult(
                status=TaskStatus.SUCCESS,
                records_processed=total_records,
                flow_records_written=total_flow_written,
                map_records_inserted=self._map_inserted,
                fix_failures=self._fix_failures,
                batches=batch_count,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                local_output_path=local_output_path,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"M2 Flow Stat [SEQUENTIAL-DAILY] failed: {e}")
            errors.append(str(e))
            return FlowStatResult(
                status=TaskStatus.FAILED,
                records_processed=total_records,
                flow_records_written=0,
                map_records_inserted=self._map_inserted,
                fix_failures=self._fix_failures,
                batches=batch_count,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
            )

        finally:
            if 'pbar' in dir():
                pbar.close()
            if self._failure_logger:
                self._failure_logger.close()
            if self.topo_checker:
                self.topo_checker.close()

    # ========================================================================
    # Parallel mode (original, preserved for backward compatibility)
    # ========================================================================

    def _run_parallel(self, params: FlowStatParams) -> FlowStatResult:
        """Parallel multi-process execution (original byte-offset mode)"""
        global _shared_section_map, _shared_od_path_lookup, _shared_topo_checker

        self.version = params.version_yyyyMM
        start_time = time.time()

        # Determine CSV path
        csv_path = params.csv_path or get_csv_path(params.version_yyyyMM)
        if not os.path.exists(csv_path):
            error_msg = f"CSV file not found: {csv_path}"
            logger.error(error_msg)
            return FlowStatResult(
                status=TaskStatus.FAILED,
                errors=[error_msg],
                execution_time=0,
            )

        # Pre-load shared data BEFORE forking (CoW optimization on Linux)
        logger.info("Pre-loading shared data for fork...")
        m6_repo = M6Repository()
        _shared_section_map = m6_repo.load_section_number_map(params.section_version)
        _shared_od_path_lookup = self.repository.load_od_path_map_lookup(params.version_yyyyMM)
        _shared_topo_checker = TopologyChecker(version=params.topo_version)
        _shared_topo_checker.load_topology_cache()
        # Reset PG connection so child processes create their own
        _shared_topo_checker._reset_pg_connection()
        logger.info(
            f"Shared data loaded: {len(_shared_section_map)} sections, "
            f"{len(_shared_od_path_lookup)} od_path entries, topology cache ready"
        )

        # Ensure target table exists (before forking)
        self.repository.create_table(params.version_yyyyMM)
        self.repository.create_bridge_table()

        # Build CSV offset index for partitioned reading
        logger.info("Building CSV offset index...")
        offsets, total_records_estimate = build_csv_offset_index(csv_path, step=params.mini_batch_size)
        logger.info(f"CSV: {len(offsets)} checkpoints, ~{total_records_estimate:,} total records")

        # Split offsets into partitions for each worker
        num_workers = params.num_workers
        partitions = _split_partitions(offsets, num_workers, csv_path, params)

        logger.info("=" * 60)
        logger.info("M2 Flow Stat: section-OD(path)-hour flow statistics [PARALLEL]")
        logger.info(f"Version: {params.version_yyyyMM}")
        logger.info(f"CSV: {csv_path}")
        logger.info(f"Workers: {num_workers}")
        logger.info(f"Mini-batch size: {params.mini_batch_size:,}")
        logger.info(f"Partitions: {len(partitions)}")
        logger.info("=" * 60)

        errors = []
        warnings = []

        try:
            # Use fork context on Linux for CoW sharing; fallback to spawn on Windows
            try:
                ctx = multiprocessing.get_context("fork")
            except ValueError:
                ctx = multiprocessing.get_context("spawn")
            with ctx.Pool(num_workers) as pool:
                worker_results = pool.map(_worker_process, partitions)

            # Aggregate worker results
            total_records = sum(r.records_processed for r in worker_results)
            total_flow_written = sum(r.flow_records_written for r in worker_results)
            total_map_inserted = sum(r.map_records_inserted for r in worker_results)
            total_fix_failures = sum(r.fix_failures for r in worker_results)
            total_batches = sum(r.batches for r in worker_results)

            # Check for worker errors
            for i, wr in enumerate(worker_results):
                if wr.errors:
                    errors.extend([f"W{i}: {e}" for e in wr.errors])

            # Validate (single query, after all workers finish)
            logger.info("Validating output...")
            validation = self.repository.validate_output(params.version_yyyyMM)
            if not validation.get("valid", False):
                warnings.append(f"Validation warnings: {validation.get('errors', 'Unknown')}")

            # Summary
            summary = self.repository.get_summary(params.version_yyyyMM)
            logger.info("=" * 60)
            logger.info("M2 Flow Stat [PARALLEL] completed:")
            logger.info(f"  Workers: {num_workers}")
            logger.info(f"  Records processed: {total_records:,}")
            logger.info(f"  Fix failures: {total_fix_failures:,}")
            logger.info(f"  Batches: {total_batches}")
            logger.info(f"  Map records inserted: {total_map_inserted}")
            logger.info(f"  Flow records written: {total_flow_written:,}")
            if summary:
                logger.info(f"  Total flow_cnt: {summary.get('total_flow', 'N/A')}")
                logger.info(f"  Unique sections: {summary.get('unique_sections', 'N/A')}")
                logger.info(f"  Unique OD paths: {summary.get('unique_od_paths', 'N/A')}")
            logger.info("=" * 60)

            # Test mode
            local_output_path = self._maybe_save_local(
                params, total_records, total_flow_written, summary
            )

            execution_time = time.time() - start_time
            return FlowStatResult(
                status=TaskStatus.SUCCESS,
                records_processed=total_records,
                flow_records_written=total_flow_written,
                map_records_inserted=total_map_inserted,
                fix_failures=total_fix_failures,
                batches=total_batches,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                local_output_path=local_output_path,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"M2 Flow Stat [PARALLEL] failed: {e}")
            errors.append(str(e))
            return FlowStatResult(
                status=TaskStatus.FAILED,
                errors=errors,
                execution_time=execution_time,
            )

        finally:
            # Clean up shared data
            _shared_section_map = {}
            _shared_od_path_lookup = {}
            if _shared_topo_checker:
                _shared_topo_checker.close()
                _shared_topo_checker = None

    # ========================================================================
    # Parallel daily mode
    # ========================================================================

    def _run_parallel_daily(self, params: FlowStatParams) -> FlowStatResult:
        """Parallel processing using daily CSV files, distributed round-robin"""
        global _shared_section_map, _shared_od_path_lookup, _shared_topo_checker

        self.version = params.version_yyyyMM
        start_time = time.time()

        # Discover daily files
        daily_files = discover_daily_files(params.version_yyyyMM, params.data_dir)
        if not daily_files:
            error_msg = f"No daily files found in {params.data_dir}/{params.version_yyyyMM}/"
            logger.error(error_msg)
            return FlowStatResult(
                status=TaskStatus.FAILED,
                errors=[error_msg],
                execution_time=0,
            )

        # Pre-load shared data BEFORE forking (CoW optimization on Linux)
        logger.info("Pre-loading shared data for fork...")
        m6_repo = M6Repository()
        _shared_section_map = m6_repo.load_section_number_map(params.section_version)
        _shared_od_path_lookup = self.repository.load_od_path_map_lookup(params.version_yyyyMM)
        _shared_topo_checker = TopologyChecker(version=params.topo_version)
        _shared_topo_checker.load_topology_cache()
        _shared_topo_checker._reset_pg_connection()
        logger.info(
            f"Shared data loaded: {len(_shared_section_map)} sections, "
            f"{len(_shared_od_path_lookup)} od_path entries, topology cache ready"
        )

        # Create daily tables in main process (avoid DDL in workers)
        for csv_path in daily_files:
            day_version = _extract_day_version(csv_path)
            self.repository.create_table(day_version)
        self.repository.create_bridge_table()

        # Distribute daily files across workers (round-robin)
        num_workers = params.num_workers
        worker_file_assignments = _assign_daily_files(daily_files, num_workers)

        logger.info("=" * 60)
        logger.info("M2 Flow Stat [PARALLEL-DAILY]")
        logger.info(f"Version: {params.version_yyyyMM}")
        logger.info(f"Daily files: {len(daily_files)}")
        logger.info(f"Workers: {num_workers}")
        logger.info(f"Mini-batch size: {params.mini_batch_size:,}")
        for i, files in enumerate(worker_file_assignments):
            logger.info(f"  W{i}: {len(files)} files")
        logger.info("=" * 60)

        # Build partition dicts for each worker
        partitions = []
        for i, assigned_files in enumerate(worker_file_assignments):
            if not assigned_files:
                continue
            partitions.append({
                "worker_id": i,
                "daily_files": assigned_files,
                "mini_batch_size": params.mini_batch_size,
                "version": params.version_yyyyMM,
                "section_version": params.section_version,
                "topo_version": params.topo_version,
            })

        errors = []
        warnings = []

        try:
            ctx = multiprocessing.get_context("fork")
            with ctx.Pool(len(partitions)) as pool:
                worker_results = pool.map(_worker_process_daily, partitions)

            # Aggregate worker results
            total_records = sum(r.records_processed for r in worker_results)
            total_flow_written = sum(r.flow_records_written for r in worker_results)
            total_map_inserted = sum(r.map_records_inserted for r in worker_results)
            total_fix_failures = sum(r.fix_failures for r in worker_results)
            total_batches = sum(r.batches for r in worker_results)

            # Check for worker errors
            for i, wr in enumerate(worker_results):
                if wr.errors:
                    errors.extend([f"W{i}: {e}" for e in wr.errors])

            # Per-day summaries
            daily_summaries = {}
            for csv_path in daily_files:
                day_version = _extract_day_version(csv_path)
                day_summary = self.repository.get_summary(day_version)
                daily_summaries[day_version] = day_summary

            # Overall summary
            logger.info("=" * 60)
            logger.info("M2 Flow Stat [PARALLEL-DAILY] completed:")
            logger.info(f"  Workers: {num_workers}")
            logger.info(f"  Records processed: {total_records:,}")
            logger.info(f"  Fix failures: {total_fix_failures:,}")
            logger.info(f"  Batches: {total_batches}")
            logger.info(f"  Map records inserted: {total_map_inserted}")
            logger.info(f"  Flow records written: {total_flow_written:,}")
            logger.info(f"  Daily tables created: {len(daily_summaries)}")
            logger.info("=" * 60)

            # Test mode
            local_output_path = self._maybe_save_local(
                params, total_records, total_flow_written,
                {"daily_summaries": daily_summaries},
            )

            execution_time = time.time() - start_time
            return FlowStatResult(
                status=TaskStatus.SUCCESS,
                records_processed=total_records,
                flow_records_written=total_flow_written,
                map_records_inserted=total_map_inserted,
                fix_failures=total_fix_failures,
                batches=total_batches,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                local_output_path=local_output_path,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"M2 Flow Stat [PARALLEL-DAILY] failed: {e}")
            errors.append(str(e))
            return FlowStatResult(
                status=TaskStatus.FAILED,
                errors=errors,
                execution_time=execution_time,
            )

        finally:
            _shared_section_map = {}
            _shared_od_path_lookup = {}
            if _shared_topo_checker:
                _shared_topo_checker.close()
                _shared_topo_checker = None

    def _maybe_save_local(
        self,
        params: FlowStatParams,
        total_records: int,
        total_flow_written: int,
        summary: dict,
    ) -> Optional[str]:
        """Save local JSON output if save_local is True"""
        if not params.save_local:
            return None

        os.makedirs(params.output_dir, exist_ok=True)
        output_file = os.path.join(
            params.output_dir,
            f"m2_flow_stat_v{params.version_yyyyMM}.json",
        )
        output_data = {
            "params": params.model_dump(),
            "summary": {
                "records_processed": total_records,
                "flow_written": total_flow_written,
                "db_summary": summary,
            },
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Test results saved to: {output_file}")
        return output_file


# ============================================================================
# Module-level Worker function — byte-offset mode (original, preserved)
# ============================================================================


def _worker_process(partition: dict) -> WorkerResult:
    """
    Independent worker process entry point (byte-offset mode).

    Each worker:
    1. Creates its own DB session + Repository
    2. Gets shared data via fork CoW (Linux) or loads independently (Windows/spawn)
    3. Reads its assigned CSV partition via iter_csv_partition()
    4. Processes each mini-batch: fix → map → batch od_path_map → aggregate → flush
    5. Returns WorkerResult with statistics

    Args:
        partition: dict with keys:
            - worker_id: int
            - csv_path: str
            - start_offset: int
            - end_offset: int
            - mini_batch_size: int
            - version: str
            - section_version: str
            - topo_version: str

    Returns:
        WorkerResult with processing statistics
    """
    worker_id = partition["worker_id"]
    csv_path = partition["csv_path"]
    start_offset = partition["start_offset"]
    end_offset = partition["end_offset"]
    mini_batch_size = partition["mini_batch_size"]
    version = partition["version"]

    start_time = time.time()
    records_processed = 0
    flow_records_written = 0
    map_records_inserted = 0
    fix_failures = 0
    batch_count = 0
    errors = []

    # Get shared data (fork CoW on Linux, or load fresh on spawn)
    section_map = _shared_section_map
    od_path_lookup = dict(_shared_od_path_lookup)  # shallow copy for local mutations
    topo_checker = _shared_topo_checker

    if not section_map or topo_checker is None:
        # Spawn mode — load data independently
        logger.info(f"W{worker_id}: Loading data independently (spawn mode)...")
        m6_repo = M6Repository()
        section_map = m6_repo.load_section_number_map(partition["section_version"])
        repo = FlowStatRepository()
        od_path_lookup = repo.load_od_path_map_lookup(version)
        topo_checker = TopologyChecker(version=partition["topo_version"])
        topo_checker.load_topology_cache()

    # Reset PG connection for this process (fork-safe)
    topo_checker._reset_pg_connection()

    # Reset SQLAlchemy engine to avoid fork-related connection issues
    import src.app.db as db_module
    if db_module._engine is not None:
        try:
            db_module._engine.dispose()
        except Exception:
            pass  # Fork-inherited connections are broken; just discard them
    db_module._engine = None
    db_module._SessionFactory = None

    # Create independent repository for this worker
    repository = FlowStatRepository()

    # Initialize failure logger for this worker
    failure_log_dir = os.path.join("outputs/m2_flow_stat", "fix_failures")
    failure_logger = FixFailureLogger(failure_log_dir, f"{version}_w{worker_id}")

    try:
        # Try to resume from checkpoint
        checkpoint = load_checkpoint(worker_id, version)
        current_offset = start_offset
        if checkpoint and not checkpoint.get("completed"):
            logger.info(f"W{worker_id}: Resuming from offset {checkpoint['last_offset']}")
            start_offset = checkpoint['last_offset']
            records_processed = checkpoint.get("records_processed", 0)
            flow_records_written = checkpoint.get("flow_records_written", 0)
            map_records_inserted = checkpoint.get("map_records_inserted", 0)
        else:
            logger.info(f"W{worker_id}: Starting partition [{start_offset}, {end_offset})")

        # Create progress bar for this worker (output to file to avoid terminal conflicts)
        progress_file = os.path.join("outputs/m2_flow_stat", f"w{worker_id}_progress.txt")
        pbar_file = open(progress_file, 'w')
        estimated_total = end_offset - start_offset if end_offset > 0 else 1000000
        pbar = tqdm(
            total=estimated_total,
            desc=f"W{worker_id}",
            unit="B",
            unit_scale=True,
            dynamic_ncols=True,
            file=pbar_file,
        )

        for mini_batch in iter_csv_partition(
            file_path=csv_path,
            start_offset=start_offset,
            end_offset=end_offset,
            batch_size=mini_batch_size,
            columns=CSV_COLUMNS,
        ):
            batch_count += 1
            batch_start = time.time()

            # ---- Step 1: Fix intervalgroup ----
            fix_results = fix_intervalgroup_batch(mini_batch, topology=topo_checker)

            # ---- Step 2: Per-record processing ----
            pending_od_path_maps: list[dict] = []  # collect cache misses for batch upsert
            local_agg: dict[tuple, int] = defaultdict(int)

            for record, fix_result in zip(mini_batch, fix_results):
                enid = record.get("enid", "")
                exid = record.get("exid", "")
                if not enid or not exid:
                    continue

                if fix_result.error:
                    failure_logger.log_failure(record, fix_result.error)
                    fix_failures += 1
                    continue

                fixed_ig = fix_result.fixed
                fixed_itg = fix_result.fixed_timegroup
                if not fixed_ig:
                    continue

                # Step 2a: Map to numpath
                numpath = _map_and_dedupe_static(section_map, fixed_ig)
                if not numpath:
                    continue

                # Step 2b: Lookup od_path_id (cache-first)
                lookup_key = (enid, exid, numpath, version)
                od_path_id = od_path_lookup.get(lookup_key)

                if od_path_id is None:
                    # Collect for batch upsert
                    vehicle_type = _resolve_vehicle_type(record)
                    pending_od_path_maps.append({
                        "enid": enid,
                        "exid": exid,
                        "numpath": numpath,
                        "fixed_intervalpath": fixed_ig,
                        "fixed_itg": fixed_itg or "",
                        "intervalpath_cnt": 1,
                        "total_trip_cnt": 1,
                        "path_freq_ratio": 1.0,
                        "source_flag": "computed",
                        "vehicle_type": vehicle_type,
                    })
                    # Placeholder — will be resolved after batch upsert
                    continue

                # Step 2c: Resolve vehicle type
                vehicle_type = _resolve_vehicle_type(record)

                # Step 2d: Split sections and times, aggregate
                _aggregate_record(
                    fixed_ig, fixed_itg, od_path_id, vehicle_type, local_agg
                )

            # ---- Step 3: Batch upsert pending od_path_maps ----
            if pending_od_path_maps:
                try:
                    new_ids = repository.batch_upsert_od_path_map(
                        pending_od_path_maps, version
                    )
                    for (enid, exid, numpath), new_id in new_ids.items():
                        lookup_key = (enid, exid, numpath, version)
                        od_path_lookup[lookup_key] = new_id
                        map_records_inserted += 1

                    # Re-process records that were waiting for od_path_id
                    for pm in pending_od_path_maps:
                        lookup_key = (pm["enid"], pm["exid"], pm["numpath"], version)
                        od_path_id = od_path_lookup.get(lookup_key)
                        if od_path_id is None:
                            continue
                        fixed_ig = pm["fixed_intervalpath"]
                        fixed_itg = pm.get("fixed_itg", "")
                        _aggregate_record(
                            fixed_ig, fixed_itg, od_path_id, pm["vehicle_type"], local_agg
                        )
                except Exception as e:
                    logger.warning(f"W{worker_id}: batch_upsert_od_path_map failed: {e}")
                    errors.append(f"batch_upsert_od_path_map: {e}")

            # ---- Step 4: Flush local_agg to DB ----
            if local_agg:
                records = []
                for (section_id, od_path_id, stat_hour, vehicle_type), count in local_agg.items():
                    records.append({
                        "section_id": section_id,
                        "od_section_path_id": od_path_id,
                        "stat_hour": stat_hour,
                        "vehicle_type": vehicle_type,
                        "flow_cnt": count,
                        "source_flag": "computed",
                    })
                try:
                    repository.upsert_flow_records(records, version)
                    flow_records_written += len(records)
                except Exception as e:
                    logger.warning(f"W{worker_id}: upsert_flow_records failed: {e}")
                    errors.append(f"upsert_flow_records: {e}")

            records_processed += len(mini_batch)
            current_offset += mini_batch_size  # Approximate byte offset
            batch_time = time.time() - batch_start

            # Update progress bar
            pbar.update(mini_batch_size)

            # Save checkpoint every 5 batches
            if batch_count % 5 == 0:
                save_checkpoint(
                    worker_id=worker_id,
                    version=version,
                    last_offset=current_offset,
                    records_processed=records_processed,
                    flow_records_written=flow_records_written,
                    map_records_inserted=map_records_inserted,
                    completed=False,
                )

            if batch_count % 10 == 0:
                logger.info(
                    f"W{worker_id}: batch {batch_count}, "
                    f"{len(mini_batch):,} recs, "
                    f"{len(local_agg):,} flow entries, "
                    f"{batch_time:.2f}s"
                )

        execution_time = time.time() - start_time
        logger.info(
            f"W{worker_id}: Done. {records_processed:,} records in {execution_time:.1f}s"
        )

        # Determine status based on errors
        if errors:
            status = WorkerStatus.PARTIAL
        else:
            status = WorkerStatus.SUCCESS

        return WorkerResult(
            worker_id=worker_id,
            status=status,
            last_batch_offset=current_offset,
            records_processed=records_processed,
            flow_records_written=flow_records_written,
            map_records_inserted=map_records_inserted,
            fix_failures=fix_failures,
            batches=batch_count,
            errors=errors,
            execution_time=execution_time,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.exception(f"W{worker_id}: FAILED: {e}")
        return WorkerResult(
            worker_id=worker_id,
            status=WorkerStatus.FAILED,
            last_batch_offset=current_offset,
            records_processed=records_processed,
            flow_records_written=flow_records_written,
            map_records_inserted=map_records_inserted,
            fix_failures=fix_failures,
            batches=batch_count,
            errors=[str(e)],
            execution_time=execution_time,
        )

    finally:
        pbar.close()
        pbar_file.close()
        failure_logger.close()
        # Remove progress file on completion
        if 'progress_file' in dir():
            try:
                os.remove(progress_file)
            except OSError:
                pass
        clear_checkpoint(worker_id, version)
        if topo_checker:
            topo_checker.close()


# ============================================================================
# Module-level Worker function — daily-file mode
# ============================================================================


def _worker_process_daily(partition: dict) -> WorkerResult:
    """
    Worker process for daily-file mode.

    Each worker:
    1. Creates its own DB session + Repository
    2. Gets shared data via fork CoW (Linux) or loads independently (Windows/spawn)
    3. Iterates over its assigned daily files using iter_csv_batches()
    4. Processes each mini-batch: fix → map → batch od_path_map → aggregate → flush
    5. Returns WorkerResult with statistics

    Args:
        partition: dict with keys:
            - worker_id: int
            - daily_files: list[str] — assigned daily file paths
            - mini_batch_size: int
            - version: str (month version, e.g. "202603")
            - section_version: str
            - topo_version: str

    Returns:
        WorkerResult with processing statistics
    """
    worker_id = partition["worker_id"]
    daily_files = partition["daily_files"]
    mini_batch_size = partition["mini_batch_size"]
    version = partition["version"]

    start_time = time.time()
    records_processed = 0
    flow_records_written = 0
    map_records_inserted = 0
    fix_failures = 0
    batch_count = 0
    completed_files: list[str] = []
    errors = []

    # Get shared data (fork CoW on Linux, or load fresh on spawn)
    section_map = _shared_section_map
    od_path_lookup = dict(_shared_od_path_lookup)  # shallow copy for local mutations
    topo_checker = _shared_topo_checker

    if not section_map or topo_checker is None:
        # Spawn mode — load data independently
        logger.info(f"W{worker_id}: Loading data independently (spawn mode)...")
        m6_repo = M6Repository()
        section_map = m6_repo.load_section_number_map(partition["section_version"])
        repo = FlowStatRepository()
        od_path_lookup = repo.load_od_path_map_lookup(version)
        topo_checker = TopologyChecker(version=partition["topo_version"])
        topo_checker.load_topology_cache()

    # Reset PG connection for this process (fork-safe)
    topo_checker._reset_pg_connection()

    # Reset SQLAlchemy engine to avoid fork-related connection issues
    import src.app.db as db_module
    if db_module._engine is not None:
        try:
            db_module._engine.dispose()
        except Exception:
            pass  # Fork-inherited connections are broken; just discard them
    db_module._engine = None
    db_module._SessionFactory = None

    # Create independent repository for this worker
    repository = FlowStatRepository()

    # Initialize failure logger for this worker
    failure_log_dir = os.path.join("outputs/m2_flow_stat", "fix_failures")
    failure_logger = FixFailureLogger(failure_log_dir, f"{version}_w{worker_id}")

    # Try to resume from checkpoint
    checkpoint = load_daily_checkpoint(worker_id, version)
    if checkpoint and not checkpoint.get("completed"):
        completed_files = checkpoint.get("completed_files", [])
        records_processed = checkpoint.get("records_processed", 0)
        flow_records_written = checkpoint.get("flow_records_written", 0)
        map_records_inserted = checkpoint.get("map_records_inserted", 0)
        # Filter out already-completed files
        completed_set = set(completed_files)
        daily_files = [f for f in daily_files if f not in completed_set]
        logger.info(
            f"W{worker_id}: Resuming, {len(completed_files)} files already done, "
            f"{len(daily_files)} remaining"
        )
    else:
        logger.info(f"W{worker_id}: Starting with {len(daily_files)} daily files")

    # Create progress file for this worker
    progress_file_path = os.path.join("outputs/m2_flow_stat", f"w{worker_id}_progress.txt")
    os.makedirs("outputs/m2_flow_stat", exist_ok=True)
    pbar_file = open(progress_file_path, "w")

    try:
        for file_idx, csv_path in enumerate(daily_files):
            day_version = _extract_day_version(csv_path)
            has_header = _detect_has_header(csv_path)
            file_basename = os.path.basename(csv_path)
            logger.info(
                f"W{worker_id}: Processing file {file_idx + 1}/{len(daily_files)}: "
                f"{file_basename} -> table _{day_version}"
            )

            # Count total records in this daily file for progress bar
            file_total_records = count_csv_lines(csv_path, has_header=has_header)
            pbar = tqdm(
                total=file_total_records,
                desc=f"W{worker_id} {file_basename}",
                unit="rec",
                unit_scale=True,
                dynamic_ncols=True,
                file=pbar_file,
            )

            for mini_batch in iter_csv_batches(
                file_path=csv_path,
                batch_size=mini_batch_size,
                columns=CSV_COLUMNS if has_header else CSV_COLUMNS_IN_FILE_ORDER,
                has_header=has_header,
            ):
                batch_count += 1
                batch_start = time.time()

                # ---- Step 1: Fix intervalgroup ----
                fix_results = fix_intervalgroup_batch(mini_batch, topology=topo_checker)

                # ---- Step 2: Per-record processing ----
                pending_od_path_maps: list[dict] = []
                local_agg: dict[tuple, int] = defaultdict(int)

                for record, fix_result in zip(mini_batch, fix_results):
                    enid = record.get("enid", "")
                    exid = record.get("exid", "")
                    if not enid or not exid:
                        continue

                    if fix_result.error:
                        failure_logger.log_failure(record, fix_result.error)
                        fix_failures += 1
                        continue

                    fixed_ig = fix_result.fixed
                    fixed_itg = fix_result.fixed_timegroup
                    if not fixed_ig:
                        continue

                    # Step 2a: Map to numpath
                    numpath = _map_and_dedupe_static(section_map, fixed_ig)
                    if not numpath:
                        continue

                    # Step 2b: Lookup od_path_id (cache-first)
                    lookup_key = (enid, exid, numpath, version)
                    od_path_id = od_path_lookup.get(lookup_key)

                    if od_path_id is None:
                        # Collect for batch upsert
                        vehicle_type = _resolve_vehicle_type(record)
                        pending_od_path_maps.append({
                            "enid": enid,
                            "exid": exid,
                            "numpath": numpath,
                            "fixed_intervalpath": fixed_ig,
                            "fixed_itg": fixed_itg or "",
                            "intervalpath_cnt": 1,
                            "total_trip_cnt": 1,
                            "path_freq_ratio": 1.0,
                            "source_flag": "computed",
                            "vehicle_type": vehicle_type,
                        })
                        continue

                    # Step 2c: Resolve vehicle type
                    vehicle_type = _resolve_vehicle_type(record)

                    # Step 2d: Split sections and times, aggregate
                    _aggregate_record(
                        fixed_ig, fixed_itg, od_path_id, vehicle_type, local_agg
                    )

                # ---- Step 3: Batch upsert pending od_path_maps ----
                if pending_od_path_maps:
                    try:
                        new_ids = repository.batch_upsert_od_path_map(
                            pending_od_path_maps, version
                        )
                        for (enid, exid, numpath), new_id in new_ids.items():
                            lookup_key = (enid, exid, numpath, version)
                            od_path_lookup[lookup_key] = new_id
                            map_records_inserted += 1

                        # Re-process records that were waiting for od_path_id
                        for pm in pending_od_path_maps:
                            lookup_key = (pm["enid"], pm["exid"], pm["numpath"], version)
                            od_path_id = od_path_lookup.get(lookup_key)
                            if od_path_id is None:
                                continue
                            fixed_ig = pm["fixed_intervalpath"]
                            fixed_itg = pm.get("fixed_itg", "")
                            _aggregate_record(
                                fixed_ig, fixed_itg, od_path_id, pm["vehicle_type"], local_agg
                            )
                    except Exception as e:
                        logger.warning(f"W{worker_id}: batch_upsert_od_path_map failed: {e}")
                        errors.append(f"batch_upsert_od_path_map: {e}")

                # ---- Step 4: Flush local_agg to daily table ----
                if local_agg:
                    records = []
                    for (section_id, od_path_id, stat_hour, vehicle_type), count in local_agg.items():
                        records.append({
                            "section_id": section_id,
                            "od_section_path_id": od_path_id,
                            "stat_hour": stat_hour,
                            "vehicle_type": vehicle_type,
                            "flow_cnt": count,
                            "source_flag": "computed",
                        })
                    try:
                        repository.upsert_flow_records(records, day_version)
                        flow_records_written += len(records)
                    except Exception as e:
                        logger.warning(f"W{worker_id}: upsert_flow_records failed: {e}")
                        errors.append(f"upsert_flow_records: {e}")

                records_processed += len(mini_batch)
                batch_time = time.time() - batch_start

                # Update progress bar
                pbar.update(len(mini_batch))

                # Save checkpoint every 5 batches
                if batch_count % 5 == 0:
                    save_daily_checkpoint(
                        worker_id=worker_id,
                        version=version,
                        completed_files=completed_files,
                        current_file=csv_path,
                        records_processed=records_processed,
                        flow_records_written=flow_records_written,
                        map_records_inserted=map_records_inserted,
                    )

                if batch_count % 10 == 0:
                    logger.info(
                        f"W{worker_id}: batch {batch_count}, "
                        f"{len(mini_batch):,} recs, "
                        f"{len(local_agg):,} flow entries, "
                        f"{batch_time:.2f}s"
                    )

            # Close progress bar for this file
            pbar.close()

            # Mark this daily file as completed
            completed_files.append(csv_path)

            # Save checkpoint after each file completes
            save_daily_checkpoint(
                worker_id=worker_id,
                version=version,
                completed_files=completed_files,
                current_file="",
                records_processed=records_processed,
                flow_records_written=flow_records_written,
                map_records_inserted=map_records_inserted,
            )
            logger.info(
                f"W{worker_id}: Completed {file_basename}, "
                f"{records_processed:,} total records so far"
            )

        execution_time = time.time() - start_time
        logger.info(
            f"W{worker_id}: Done. {records_processed:,} records in {execution_time:.1f}s"
        )

        status = WorkerStatus.PARTIAL if errors else WorkerStatus.SUCCESS

        return WorkerResult(
            worker_id=worker_id,
            status=status,
            last_batch_offset=0,
            records_processed=records_processed,
            flow_records_written=flow_records_written,
            map_records_inserted=map_records_inserted,
            fix_failures=fix_failures,
            batches=batch_count,
            errors=errors,
            execution_time=execution_time,
            completed_files=completed_files,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.exception(f"W{worker_id}: FAILED: {e}")
        return WorkerResult(
            worker_id=worker_id,
            status=WorkerStatus.FAILED,
            last_batch_offset=0,
            records_processed=records_processed,
            flow_records_written=flow_records_written,
            map_records_inserted=map_records_inserted,
            fix_failures=fix_failures,
            batches=batch_count,
            errors=[str(e)],
            execution_time=execution_time,
            completed_files=completed_files,
        )

    finally:
        failure_logger.close()
        clear_daily_checkpoint(worker_id, version)
        if topo_checker:
            topo_checker.close()
        pbar_file.close()


# ============================================================================
# Helper functions (module-level for worker access)
# ============================================================================


def _split_partitions(
    offsets: list[int],
    num_workers: int,
    csv_path: str,
    params: FlowStatParams,
) -> list[dict]:
    """Split offset index into partitions for each worker (byte-offset mode).

    Each partition covers an approximately equal range of offsets.
    The last partition extends to 0 (EOF) for its end_offset.
    """
    n = len(offsets)
    if n == 0:
        return []

    # If we have fewer offset checkpoints than workers, just assign one per worker
    chunk_size = max(1, n // num_workers)
    partitions = []

    for i in range(num_workers):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size - 1 if i < num_workers - 1 else n - 1

        if start_idx >= n:
            break

        start_offset = offsets[start_idx]
        end_offset = offsets[end_idx] if end_idx < n else 0  # 0 = read to EOF

        partitions.append({
            "worker_id": i,
            "csv_path": csv_path,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "mini_batch_size": params.mini_batch_size,
            "version": params.version_yyyyMM,
            "section_version": params.section_version,
            "topo_version": params.topo_version,
        })

    return partitions


def _assign_daily_files(
    daily_files: list[str],
    num_workers: int,
) -> list[list[str]]:
    """Distribute daily files across workers using round-robin.

    Returns:
        List of file lists, one per worker. Worker i gets the files
        at indices i, i+N, i+2N, etc.
    """
    assignments: list[list[str]] = [[] for _ in range(num_workers)]
    for idx, filepath in enumerate(daily_files):
        worker_idx = idx % num_workers
        assignments[worker_idx].append(filepath)
    return assignments


def _map_and_dedupe_static(
    section_map: dict[str, int],
    intervalgroup: str,
) -> Optional[str]:
    """Standalone version of _map_and_dedupe for use in worker processes.

    Takes section_map as an explicit argument instead of relying on self.
    """
    section_ids = split_intervalgroup(intervalgroup)
    if not section_ids:
        return None

    numbers = [section_map.get(sid) for sid in section_ids]

    # Step 1: adjacent dedup
    deduped = _adjacent_dedup([n for n in numbers if n is not None])
    if not deduped:
        return None

    # Step 2: pair dedup (try offset 0 and 1, pick shorter)
    best_result = None
    best_elem_count = float("inf")

    for offset in range(2):
        pairs = []
        i = offset
        if i > 0:
            pairs.append(("", deduped[0]))
        while i + 1 < len(deduped):
            pairs.append((deduped[i], deduped[i + 1]))
            i += 2
        if (i + 1) == len(deduped):
            pairs.append((deduped[i], ""))

        results_list = []
        k = 0
        while k < len(pairs):
            a, b = pairs[k]
            if a:
                results_list.append(a)
            if b:
                results_list.append(b)
            if k + 1 < len(pairs):
                c, d = pairs[k + 1]
                if (a, b) == (c, d):
                    k += 2
                    continue
            k += 1

        if offset == 0 and i < len(deduped):
            results_list.append(deduped[-1])
        if offset == 1:
            if deduped[0] not in results_list:
                results_list.insert(0, deduped[0])
            if i >= len(deduped) and len(deduped) % 2 == 1:
                results_list.append(deduped[-1])

        if len(results_list) < best_elem_count:
            best_elem_count = len(results_list)
            best_result = results_list

    if not best_result:
        return None

    # Step 3: adjacent dedup again (Step 2 may leave adjacent duplicates)
    best_result = _adjacent_dedup(best_result)

    return "|".join(str(x) for x in best_result)


def _aggregate_record(
    fixed_ig: str,
    fixed_itg: str,
    od_path_id: int,
    vehicle_type: str,
    local_agg: dict[tuple, int],
) -> None:
    """Aggregate a single fixed record into local_agg dict.

    Splits the fixed intervalgroup into section IDs, truncates times to hours,
    deduplicates (section_id, stat_hour) within the same record, and increments counts.
    """
    section_ids = split_intervalgroup(fixed_ig)
    time_strs = split_intervalgroup(fixed_itg) if fixed_itg else []

    seen: set[tuple[str, str]] = set()

    for idx, sid in enumerate(section_ids):
        stat_hour = None
        if idx < len(time_strs):
            stat_hour = FlowStatService._truncate_to_hour(time_strs[idx])
        if not stat_hour:
            continue

        key = (sid, stat_hour)
        if key in seen:
            continue
        seen.add(key)

        local_agg[(sid, od_path_id, stat_hour, vehicle_type)] += 1
