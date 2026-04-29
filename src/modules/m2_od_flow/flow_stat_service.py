"""
M2 收费单元-OD(path)小时流量统计服务

核心流程：
CSV逐行读取 → intervalgroup+intervaltimegroup同步修复 → numPath映射
→ od_section_path_id查找/插入 → (section_id, stat_hour)去重计数 → 聚合upsert

支持两种运行模式：
1. 单进程模式 (num_workers=1): 原有逻辑，向后兼容
2. 多进程并行模式 (num_workers>1): CSV分区并行处理，每个Worker独立DB连接，即时flush
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
    build_csv_offset_index,
    count_csv_lines,
    get_csv_path,
    iter_csv_batches,
    iter_csv_partition,
)
from src.modules.m2_od_flow.fix_failure_logger import FixFailureLogger
from src.modules.m2_od_flow.flow_stat_repository import FlowStatRepository
from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams, FlowStatResult, WorkerResult
from src.modules.m2_od_flow.interval_fixer import (
    TopologyChecker,
    fix_intervalgroup_batch,
    split_intervalgroup,
)
from src.modules.m6_od_section_path.repository import M6Repository

logger = get_logger(__name__)

# Module-level shared data for fork-based multiprocessing.
# Populated by _run_parallel() before forking, read by worker processes via CoW.
_shared_section_map: dict[str, int] = {}
_shared_od_path_lookup: dict[tuple, int] = {}
_shared_topo_checker: Optional[TopologyChecker] = None

# CSV columns to extract from the source file
CSV_COLUMNS = [
    "enid", "exid", "intervalgroup", "intervaltimegroup",
    "envehicleid", "exvehicleid", "entime", "extime",
]


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
        Map intervalgroup to deduped numpath (reuse M6 two-step dedup logic).
        Only returns final_numpath, step1_numpath not needed here.
        """
        section_ids = split_intervalgroup(intervalgroup)
        if not section_ids:
            return None

        numbers = [self.section_map.get(sid) for sid in section_ids]

        # Step 1: adjacent dedup
        deduped = []
        prev = None
        for n in numbers:
            if n is not None and n != prev:
                deduped.append(n)
                prev = n
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
            Number of unique (section_id, od_path_id, stat_hour) entries in this batch
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

            # Step 2c: Split sections and times (1:1 aligned)
            section_ids = split_intervalgroup(fixed_ig)
            time_strs = split_intervalgroup(fixed_itg) if fixed_itg else []

            # Step 2d: Dedup per record — same (section_id, stat_hour) only counts once
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

                local_agg[(sid, od_path_id, stat_hour)] += 1

        # Step 3: Merge into global aggregation
        for key, count in local_agg.items():
            self._flow_agg[key] += count

        return len(local_agg)

    def _flush_to_db(self) -> int:
        """Flush aggregation results to database"""
        records = []
        for (section_id, od_path_id, stat_hour), count in self._flow_agg.items():
            records.append({
                "section_id": section_id,
                "od_section_path_id": od_path_id,
                "stat_hour": stat_hour,
                "flow_cnt": count,
                "source_flag": "computed",
            })
        if records:
            self.repository.upsert_flow_records(records, self.version)
            logger.info(f"Upserted {len(records)} flow records")
        # Clear aggregation after flush
        written = len(self._flow_agg)
        self._flow_agg = defaultdict(int)
        return written

    # ========================================================================
    # Unified entry point
    # ========================================================================

    def run(self, params: FlowStatParams) -> FlowStatResult:
        """Main entry point — dispatches to sequential or parallel based on num_workers"""
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
    # Parallel mode
    # ========================================================================

    def _run_parallel(self, params: FlowStatParams) -> FlowStatResult:
        """Parallel multi-process execution"""
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

        # Build CSV offset index for partitioned reading
        logger.info("Building CSV offset index...")
        offsets, total_records_estimate = build_csv_offset_index(csv_path, step=params.mini_batch_size)
        # total_records_estimate = count_csv_lines(csv_path)
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
            # worker_results = []
            # for partition in partitions:
            #     worker_results.append(_worker_process(partition))

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
# Module-level Worker function (must be at module level for pickle/fork)
# ============================================================================


def _worker_process(partition: dict) -> WorkerResult:
    """
    Independent worker process entry point.

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
        db_module._engine.dispose()
    db_module._engine = None
    db_module._SessionFactory = None

    # Create independent repository for this worker
    repository = FlowStatRepository()

    # Initialize failure logger for this worker
    failure_log_dir = os.path.join("outputs/m2_flow_stat", "fix_failures")
    failure_logger = FixFailureLogger(failure_log_dir, f"{version}_w{worker_id}")

    try:
        logger.info(f"W{worker_id}: Starting partition [{start_offset}, {end_offset})")

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
                    })
                    # Placeholder — will be resolved after batch upsert
                    continue

                # Step 2c: Split sections and times, aggregate
                _aggregate_record(
                    fixed_ig, fixed_itg, od_path_id, local_agg
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
                            fixed_ig, fixed_itg, od_path_id, local_agg
                        )
                except Exception as e:
                    logger.warning(f"W{worker_id}: batch_upsert_od_path_map failed: {e}")
                    errors.append(f"batch_upsert_od_path_map: {e}")

            # ---- Step 4: Flush local_agg to DB ----
            if local_agg:
                records = []
                for (section_id, od_path_id, stat_hour), count in local_agg.items():
                    records.append({
                        "section_id": section_id,
                        "od_section_path_id": od_path_id,
                        "stat_hour": stat_hour,
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
            batch_time = time.time() - batch_start

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

        return WorkerResult(
            worker_id=worker_id,
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
            records_processed=records_processed,
            flow_records_written=flow_records_written,
            map_records_inserted=map_records_inserted,
            fix_failures=fix_failures,
            batches=batch_count,
            errors=[str(e)],
            execution_time=execution_time,
        )

    finally:
        failure_logger.close()
        if topo_checker:
            topo_checker.close()


# ============================================================================
# Helper functions (module-level for worker access)
# ============================================================================


def _split_partitions(
    offsets: list[int],
    num_workers: int,
    csv_path: str,
    params: FlowStatParams,
) -> list[dict]:
    """Split offset index into partitions for each worker.

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
    deduped = []
    prev = None
    for n in numbers:
        if n is not None and n != prev:
            deduped.append(n)
            prev = n
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

    return "|".join(str(x) for x in best_result)


def _aggregate_record(
    fixed_ig: str,
    fixed_itg: str,
    od_path_id: int,
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

        local_agg[(sid, od_path_id, stat_hour)] += 1
