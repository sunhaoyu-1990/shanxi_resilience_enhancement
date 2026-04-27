"""
M2 收费单元-OD(path)小时流量统计服务

核心流程：
CSV逐行读取 → intervalgroup+intervaltimegroup同步修复 → numPath映射
→ od_section_path_id查找/插入 → (section_id, stat_hour)去重计数 → 聚合upsert
"""

import json
import os
import time
from collections import defaultdict
from typing import Optional

from src.app.enums import TaskStatus
from src.app.logger import LoggerMixin, get_logger
from src.modules.m2_od_flow.csv_reader import get_csv_path, iter_csv_batches
from src.modules.m2_od_flow.fix_failure_logger import FixFailureLogger
from src.modules.m2_od_flow.flow_stat_repository import FlowStatRepository
from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams, FlowStatResult
from src.modules.m2_od_flow.interval_fixer import (
    TopologyChecker,
    fix_intervalgroup_batch,
    split_intervalgroup,
)
from src.modules.m6_od_section_path.repository import M6Repository

logger = get_logger(__name__)


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

        for record, fix_result in zip(batch, fix_results):
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
            self.repository.upsert_flow_records(records)
            logger.info(f"Upserted {len(records)} flow records")
        # Clear aggregation after flush
        written = len(self._flow_agg)
        self._flow_agg = defaultdict(int)
        return written

    def run(self, params: FlowStatParams) -> FlowStatResult:
        """Main entry point"""
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
        self.repository.create_table()

        total_records = 0
        batch_count = 0
        total_flow_written = 0
        errors = []
        warnings = []

        logger.info("=" * 60)
        logger.info("M2 Flow Stat: section-OD(path)-hour flow statistics")
        logger.info(f"Version: {params.version_yyyyMM}")
        logger.info(f"CSV: {csv_path}")
        logger.info(f"Batch size: {params.batch_size:,}")
        logger.info(f"Upsert interval: every {params.upsert_interval} batches")
        logger.info("=" * 60)

        try:
            for batch in iter_csv_batches(
                file_path=csv_path,
                batch_size=params.batch_size,
                columns=[
                    "enid", "exid", "intervalgroup", "intervaltimegroup",
                    "envehicleid", "exvehicleid", "entime", "extime",
                ],
            ):
                batch_count += 1
                batch_start = time.time()

                entries = self._process_batch(batch)
                total_records += len(batch)

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
            validation = self.repository.validate_output()
            if not validation.get("valid", False):
                warnings.append(f"Validation warnings: {validation.get('errors', 'Unknown')}")

            # Summary
            summary = self.repository.get_summary()
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
            local_output_path = None
            if params.save_local:
                os.makedirs(params.output_dir, exist_ok=True)
                output_file = os.path.join(
                    params.output_dir,
                    f"m2_flow_stat_v{params.version_yyyyMM}.json",
                )
                output_data = {
                    "params": params.model_dump(),
                    "summary": {
                        "records_processed": total_records,
                        "map_inserted": self._map_inserted,
                        "flow_written": total_flow_written,
                        "db_summary": summary,
                    },
                }
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                local_output_path = output_file
                logger.info(f"Test results saved to: {local_output_path}")

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
            if self._failure_logger:
                self._failure_logger.close()
            if self.topo_checker:
                self.topo_checker.close()
