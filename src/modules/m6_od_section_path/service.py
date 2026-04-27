"""
M6 OD-Section-Path 映射服务

主编排逻辑：
Hive分批读取 → intervalgroup修复(并行) → Section映射 → 聚合(内存) → 实时upsert到数据库
每批次完成后立即写入，不在内存中积累全部批次数据。
"""

import json
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional
from tqdm import tqdm

from src.app.enums import TaskStatus
from src.app.logger import LoggerMixin, get_logger
from src.modules.m2_od_flow.hive_repository import (
    get_total_count,
    iter_hive_batches,
)
from src.modules.m2_od_flow.interval_fixer import (
    TopologyChecker,
    fix_intervalgroup_batch,
    split_intervalgroup,
)
from src.modules.m6_od_section_path.repository import M6Repository
from src.modules.m6_od_section_path.schema import (
    BatchProcessDetail,
    M6TaskParams,
    M6TaskResult,
    M6TestResult,
)

logger = get_logger(__name__)


def _format_eta(seconds: float) -> str:
    """Format seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m{s}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h{m:02d}m"


# ---------------------------------------------------------------------------
# Per-batch aggregation result
# ---------------------------------------------------------------------------

class BatchResult:
    """Single batch aggregation result (no cross-batch accumulation)."""

    def __init__(self):
        # {(enid, exid, numpath, fixed_ig): count}
        self.ig_counts: dict[tuple, int] = {}
        # {(enid, exid, numpath): [(fixed_ig, step1_numpath), ...]}
        # step1_numpath is kept for test JSON output only
        self.ig_step1: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
        self.valid_records = 0

    def to_dict(self) -> dict:
        """Serialize to dict for logging."""
        ig_counts_list = [
            {
                "enid": k[0], "exid": k[1], "numpath": k[2],
                "fixed_ig": k[3], "count": v,
            }
            for k, v in self.ig_counts.items()
        ]
        ig_step1_list = [
            {
                "enid": k[0], "exid": k[1], "numpath": k[2],
                "entries": [{"fixed_ig": ig, "step1_numpath": s1}
                            for ig, s1 in entries],
            }
            for k, entries in self.ig_step1.items()
        ]
        return {
            "valid_records": self.valid_records,
            "ig_counts": ig_counts_list,
            "ig_step1": ig_step1_list,
        }


# ---------------------------------------------------------------------------
# Worker function (per-process, no shared state)
# ---------------------------------------------------------------------------

def _m6_worker(args: tuple) -> list[tuple]:
    """
    Process a chunk of records in a worker process.

    Returns:
        [(enid, exid, final_numpath, fixed_ig, step1_numpath), ...]
    """
    records, section_map, topo_version = args

    topo = TopologyChecker(version=topo_version)
    topo.load_topology_cache()

    results = []
    try:
        fix_results = fix_intervalgroup_batch(records, topology=topo)

        for record, fix_result in zip(records, fix_results):
            enid = record.get("enid", "")
            exid = record.get("exid", "")
            if not enid or not exid:
                continue

            original_ig = record.get("intervalgroup", "")
            fixed_ig = fix_result.fixed
            if not original_ig or not fixed_ig:
                continue

            section_ids = split_intervalgroup(fixed_ig)
            if not section_ids:
                continue

            # Map to section_number + adjacent dedup
            deduped = []
            prev = None
            for sid in section_ids:
                n = section_map.get(sid)
                if n is not None and n != prev:
                    deduped.append(n)
                    prev = n
            if not deduped:
                continue

            # Pair dedup (try offset 0 and 1, pick shorter)
            best_result = None
            best_count = float("inf")
            for offset in range(2):
                pairs = []
                i = offset
                while i + 1 < len(deduped):
                    pairs.append((deduped[i], deduped[i + 1]))
                    i += 2
                rlist = []
                k = 0
                while k < len(pairs):
                    a, b = pairs[k]
                    rlist.append(a)
                    rlist.append(b)
                    if k + 1 < len(pairs):
                        c, d = pairs[k + 1]
                        if (a, b) == (c, d):
                            k += 2
                            continue
                    k += 1
                if offset == 0 and i < len(deduped):
                    rlist.append(deduped[-1])
                if offset == 1:
                    if deduped[0] not in rlist:
                        rlist.insert(0, deduped[0])
                    if i >= len(deduped) and len(deduped) % 2 == 1:
                        rlist.append(deduped[-1])
                if len(rlist) < best_count:
                    best_count = len(rlist)
                    best_result = rlist

            if not best_result:
                continue

            step1_numpath = "|".join(str(x) for x in deduped)
            final_numpath = "|".join(str(x) for x in best_result)
            results.append((enid, exid, final_numpath, fixed_ig, step1_numpath))
    finally:
        topo.close()

    return results


# ---------------------------------------------------------------------------
# M6Service
# ---------------------------------------------------------------------------

class M6Service(LoggerMixin):
    """M6 OD-Section-Path mapping service with per-batch real-time upsert."""

    def __init__(self, workers: int = 2):
        self.repository = M6Repository()
        self.workers = workers
        self.section_map: dict[str, int] = {}
        self.topo_version: str = ""
        self.version_yyyyMM: str = ""
        self.checkpoint_table_name: str = ""
        self.checkpoint_enabled: bool = False

    def _load_dependencies(self, section_version: str, topo_version: str) -> None:
        """Pre-load section_number mapping. Topology loaded in each worker process."""
        logger.info("Loading dependencies...")
        self.section_map = self.repository.load_section_number_map(section_version)
        logger.info(f"Loaded {len(self.section_map)} section_number mappings")
        self.topo_version = topo_version
        logger.info(f"Topology cache will be loaded in each worker process (version: {topo_version})")

    # -------------------------------------------------------------------------
    # Batch processing (parallel)
    # -------------------------------------------------------------------------

    def _process_batch_parallel(self, batch: list[dict]) -> tuple[int, float]:
        """
        Process a batch in parallel using multiple worker processes.

        Returns:
            (valid_record_count, elapsed_seconds)
        """
        t0 = time.time()
        batch_len = len(batch)

        chunk_size = max(1, batch_len // self.workers)
        chunks = []
        for i in range(self.workers):
            start = i * chunk_size
            if i == self.workers - 1:
                end = batch_len
            else:
                end = start + chunk_size
            if start < batch_len:
                chunks.append(batch[start:end])

        worker_args = [
            (chunk, self.section_map, self.topo_version)
            for chunk in chunks
        ]

        worker_results: list[tuple] = []
        with ProcessPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(_m6_worker, args): i
                for i, args in enumerate(worker_args)
            }
            for future in as_completed(futures):
                worker_results.extend(future.result())

        elapsed = time.time() - t0
        return len(worker_results), elapsed, worker_results

    # -------------------------------------------------------------------------
    # Batch processing (sequential, for testing / small data)
    # -------------------------------------------------------------------------

    def _process_batch_sequential(self, batch: list[dict]) -> tuple[int, float, list[tuple]]:
        """Process a batch sequentially (single-threaded)."""
        t0 = time.time()
        topo = TopologyChecker(version=self.topo_version)
        topo.load_topology_cache()
        try:
            fix_results = fix_intervalgroup_batch(batch, topology=topo)
        finally:
            topo.close()

        results = []
        for record, fix_result in zip(batch, fix_results):
            enid = record.get("enid", "")
            exid = record.get("exid", "")
            if not enid or not exid:
                continue

            original_ig = record.get("intervalgroup", "")
            fixed_ig = fix_result.fixed
            if not original_ig or not fixed_ig:
                continue

            final_numpath, step1_numpath = self._map_and_dedupe(fixed_ig)
            if not final_numpath:
                continue

            results.append((enid, exid, final_numpath, fixed_ig, step1_numpath))

        elapsed = time.time() - t0
        return len(results), elapsed, results

    def _map_and_dedupe(self, intervalgroup: str) -> tuple[Optional[str], str]:
        """Map intervalgroup to deduped numpath."""
        section_ids = split_intervalgroup(intervalgroup)
        if not section_ids:
            return None, ""

        numbers = [self.section_map.get(sid) for sid in section_ids]

        # Step 1: adjacent dedup
        deduped = []
        prev = None
        for n in numbers:
            if n is not None and n != prev:
                deduped.append(n)
                prev = n
        if not deduped:
            return None, ""

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
            return None, ""

        step1_numpath = "|".join(str(x) for x in deduped)
        final_numpath = "|".join(str(x) for x in best_result)
        return final_numpath, step1_numpath

    # -------------------------------------------------------------------------
    # Per-batch aggregation + real-time upsert
    # -------------------------------------------------------------------------

    def _aggregate_batch(self, worker_results: list[tuple]) -> BatchResult:
        """
        Aggregate a single batch's worker results.

        Data structure:
            {(enid, exid, numpath, fixed_ig): count}           -- for DB upsert
            {(enid, exid, numpath): [(fixed_ig, step1_numpath), ...]}  -- for JSON

        step1_numpath is kept only for test JSON output, NOT written to DB.
        """
        result = BatchResult()

        for (enid, exid, numpath, fixed_ig, step1_numpath) in worker_results:
            key = (enid, exid, numpath, fixed_ig)
            result.ig_counts[key] = result.ig_counts.get(key, 0) + 1

            np_key = (enid, exid, numpath)
            # avoid duplicate (fixed_ig, step1_numpath) entries in JSON
            existing = [ig for (ig, s1) in result.ig_step1[np_key]]
            if fixed_ig not in existing:
                result.ig_step1[np_key].append((fixed_ig, step1_numpath))

            result.valid_records += 1

        return result

    def _prepare_freq_records(self, batch_result: BatchResult) -> list[dict]:
        """
        Prepare freq records from batch aggregation.
        Writes one row per (enid, exid, numpath, fixed_ig) with aggregated count.
        ig_rank is written as 0 here — computed at the end by compute_ig_rank().
        """
        freq_records = []
        for (enid, exid, numpath, fixed_ig), cnt in batch_result.ig_counts.items():
            freq_records.append({
                "enid": enid,
                "exid": exid,
                "numpath": numpath,
                "fixed_intervalgroup": fixed_ig,
                "version_yyyyMM": self.version_yyyyMM,
                "ig_count": cnt,
                "source_flag": "hive_computed",
            })
        return freq_records

    def _prepare_map_records(self, batch_result: BatchResult) -> list[dict]:
        """
        Prepare map records from batch aggregation.
        For each (enid, exid, numpath): pick fixed_ig with max aggregated count.
        Writes one row per (enid, exid, numpath) — but we need cross-batch logic.

        NOTE: Since map table needs the BEST fixed_ig across ALL batches (not just
        this batch), we CANNOT write map records per-batch. Instead, we skip map
        writes during batch processing and derive the full map table at the end
        from the complete freq table via derive_map_from_freq().

        This method is kept for interface compatibility but returns empty list.
        """
        # Map table derivation requires seeing all batches first.
        # Real-time map write would be wrong (batch 2 might have a different best_ig).
        # Derive map from freq table AFTER all batches complete.
        return []

    def _upsert_batch(self, batch_result: BatchResult) -> tuple[int, int]:
        """
        Upsert a single batch's results to DB immediately.

        - freq records: upsert with ig_count accumulation (ON CONFLICT DO UPDATE SET ig_count = ig_count + EXCLUDED.ig_count)
        - map records: NOT written per-batch (derived at the end from complete freq table)

        Returns:
            (map_records_written, freq_records_written)
        """
        freq_records = self._prepare_freq_records(batch_result)
        if freq_records:
            freq_written = self.repository.upsert_freq_maps(
                freq_records, topo_version=self.topo_version
            )
        else:
            freq_written = 0

        # Map table is derived from freq at the end, not written per-batch
        return 0, freq_written

    # -------------------------------------------------------------------------
    # Test JSON output (per-batch accumulation only for the test run)
    # -------------------------------------------------------------------------

    def _accumulate_for_test(self, batch_result: BatchResult) -> None:
        """Accumulate batch result into test data (only for test/save_local mode)."""
        if not hasattr(self, "_test_map_records"):
            self._test_map_records = []
            self._test_freq_records = []

        # Build fixed_ig counts per (enid, exid, numpath) for this batch
        # (This is just for one batch's worth of data, not cross-batch)
        np_fixed: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for (enid, exid, numpath, fixed_ig), cnt in batch_result.ig_counts.items():
            np_fixed[(enid, exid, numpath)][fixed_ig] += cnt

        for (enid, exid, numpath), fixed_cnt in np_fixed.items():
            total_trip = sum(fixed_cnt.values())
            if total_trip == 0:
                continue

            best_fixed_ig = max(fixed_cnt, key=fixed_cnt.__getitem__)
            intervalpath_cnt = fixed_cnt[best_fixed_ig]
            freq_ratio = round(intervalpath_cnt / total_trip, 4)

            # Get step1_numpath for this fixed_ig
            step1 = ""
            for (e, ex, np), entries in batch_result.ig_step1.items():
                if (e, ex, np) == (enid, exid, numpath):
                    for (ig, s1) in entries:
                        if ig == best_fixed_ig:
                            step1 = s1
                            break
                    break

            self._test_map_records.append({
                "enid": enid,
                "exid": exid,
                "numpath": numpath,
                "step1_numpath": step1,
                "fixed_intervalpath": best_fixed_ig,
                "intervalpath_cnt": intervalpath_cnt,
                "total_trip_cnt": total_trip,
                "path_freq_ratio": freq_ratio,
            })

            sorted_fixed = sorted(fixed_cnt.items(), key=lambda x: x[1], reverse=True)
            for rank, (fixed_ig, cnt) in enumerate(sorted_fixed, start=1):
                step1_for_ig = ""
                for (e, ex, np), entries in batch_result.ig_step1.items():
                    if (e, ex, np) == (enid, exid, numpath):
                        for (ig, s1) in entries:
                            if ig == fixed_ig:
                                step1_for_ig = s1
                                break
                        break
                self._test_freq_records.append({
                    "enid": enid,
                    "exid": exid,
                    "numpath": numpath,
                    "step1_numpath": step1_for_ig,
                    "fixed_intervalgroup": fixed_ig,
                    "ig_count": cnt,
                    "ig_rank": rank,
                })

    def _save_test_output(self, params: M6TaskParams, batch_details: list) -> Optional[str]:
        """Save test output to local JSON file."""
        if not hasattr(self, "_test_map_records"):
            return None

        map_records = getattr(self, "_test_map_records", [])
        freq_records = getattr(self, "_test_freq_records", [])

        output_data = {
            "map_records": map_records,
            "freq_records": freq_records,
            "summary": {
                "total_map_records": len(map_records),
                "total_freq_records": len(freq_records),
                "unique_od_pairs": len(set((r["enid"], r["exid"]) for r in map_records)),
                "unique_num_paths": len(set(r["numpath"] for r in map_records)),
            },
        }

        test_result = M6TestResult(
            params=params,
            batches=batch_details,
            summary=output_data["summary"],
            map_records_sample=output_data["map_records"][:100],
            freq_records_sample=output_data["freq_records"][:100],
        )

        os.makedirs(params.output_dir, exist_ok=True)
        output_file = os.path.join(
            params.output_dir,
            f"m6_test_v{params.version_yyyyMM}.json",
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(test_result.model_dump(), f, ensure_ascii=False, indent=2)

        logger.info(f"Test result saved to: {output_file}")
        return output_file

    # -------------------------------------------------------------------------
    # Per-batch log (for verification)
    # -------------------------------------------------------------------------

    def _save_batch_log(
        self,
        batch_no: int,
        batch_result: BatchResult,
        input_records: int,
        batch_time: float,
        db_freq_written: int,
    ) -> None:
        log_dir = os.path.join(os.path.dirname(__file__), "logs", f"v{self.version_yyyyMM}")
        os.makedirs(log_dir, exist_ok=True)
        log_data = batch_result.to_dict()
        log_data |= {
            "batch_no": batch_no,
            "version": self.version_yyyyMM,
            "topo_version": self.topo_version,
            "input_records": input_records,
            "batch_time_seconds": round(batch_time, 2),
            "db_freq_written": db_freq_written,
        }
        log_file = os.path.join(log_dir, f"batch_{batch_no:04d}.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Batch {batch_no} log saved: {log_file}")

    def _update_checkpoint(self, batch_num: int, batch_size: int, records_increment: int) -> None:
        if not self.checkpoint_enabled:
            return
        next_offset = batch_num * batch_size
        self.repository.update_checkpoint(
            self.checkpoint_table_name,
            self.version_yyyyMM,
            next_offset,
            records_increment,
        )

    def _complete_checkpoint(self) -> None:
        if not self.checkpoint_enabled:
            return
        self.repository.complete_checkpoint(
            self.checkpoint_table_name,
            self.version_yyyyMM,
        )

    # -------------------------------------------------------------------------
    # Main run
    # -------------------------------------------------------------------------

    def run(self, params: M6TaskParams) -> M6TaskResult:
        """
        Execute M6 OD-Section-Path mapping with per-batch real-time upsert.

        Pipeline:
        1. Pre-load section_number mapping
        2. Create output tables
        3. For each batch from Hive:
           a. Process batch (parallel or sequential)
           b. Aggregate batch results
           c. Upsert to freq table immediately (ig_count accumulates)
           d. Update checkpoint (if checkpointing enabled)
        4. After ALL batches: compute ig_rank + derive map from freq
        5. Validate output
        """
        self.version_yyyyMM = params.version_yyyyMM
        start_time = time.time()
        use_parallel = self.workers > 1 and not params.save_local

        # Ensure output tables exist
        self.repository.create_tables()

        total_records = 0
        batch_count = 0
        errors = []
        warnings = []
        batch_details = []

        logger.info("=" * 60)
        logger.info("M6 OD-Section-Path mapping started")
        logger.info(f"Version: {params.version_yyyyMM}")
        logger.info(f"Batch size: {params.batch_size:,}")
        logger.info(f"Workers: {self.workers} {'(parallel)' if use_parallel else '(sequential/test mode)'}")
        logger.info(f"Save local: {params.save_local}")
        logger.info("Per-batch real-time upsert: ENABLED")
        logger.info("=" * 60)

        try:
            # Load dependencies
            self._load_dependencies(params.section_version, params.topo_version)

            # Get total count
            total_hive = get_total_count(
                table=params.hive_table,
                database=params.hive_database,
            )
            logger.info(f"Hive table total records: {total_hive:,}")

            max_records = params.batch_size if params.save_local else total_hive
            total_batches = (max_records + params.batch_size - 1) // params.batch_size
            logger.info(f"Processing {max_records:,} records (~{total_batches} batches)")

            # Batch loop
            batch_num = 0
            batch_times: list[float] = []
            total_freq_written = 0

            # Init checkpoint
            if self.checkpoint_enabled:
                self.repository.init_checkpoint([(self.checkpoint_table_name, self.version_yyyyMM, self.topo_version)])

            pbar = tqdm(
                total=max_records,
                desc=f"M6 {params.version_yyyyMM}",
                unit="rec",
                unit_scale=True,
                ncols=100,
            )
            pbar.set_postfix({
                "freq_upsert": 0,
                "batches": 0,
                "ETA": "-",
            })

            for batch in iter_hive_batches(
                table=params.hive_table,
                database=params.hive_database,
                batch_size=params.batch_size,
                columns=["tradeid", "intervalgroup", "enid", "exid"],
            ):
                batch_num += 1
                batch_start = time.time()

                # Process batch
                if use_parallel:
                    valid_count, batch_time, worker_results = self._process_batch_parallel(batch)
                else:
                    valid_count, batch_time, worker_results = self._process_batch_sequential(batch)

                # Aggregate
                batch_result = self._aggregate_batch(worker_results)

                # Real-time upsert to DB
                _, freq_written = self._upsert_batch(batch_result)
                total_freq_written += freq_written

                # Save per-batch log for verification
                self._save_batch_log(batch_num, batch_result, len(batch), batch_time, freq_written)

                # Test mode: accumulate for JSON output
                if params.save_local:
                    self._accumulate_for_test(batch_result)

                total_records += len(batch)
                batch_times.append(batch_time)
                batch_count = batch_num

                # Update tqdm progress bar
                pct = min(100, total_records / max_records * 100) if max_records > 0 else 0
                recent = batch_times[-5:] if len(batch_times) >= 5 else batch_times
                avg_batch_time = sum(recent) / len(recent) if recent else 0
                remaining_batches = total_batches - batch_num
                eta_seconds = remaining_batches * avg_batch_time
                elapsed_total = time.time() - start_time
                current_rate = total_records / elapsed_total if elapsed_total > 0 else 0
                eta_str = _format_eta(eta_seconds)

                pbar.update(len(batch))
                self._update_checkpoint(batch_num, params.batch_size, len(batch))
                pbar.set_postfix({
                    "freq_upsert": total_freq_written,
                    "batches": batch_num,
                    "ETA": eta_str,
                })

                batch_details.append(
                    BatchProcessDetail(
                        batch_no=batch_num,
                        input_records=len(batch),
                        output_map_records=0,
                        output_freq_records=freq_written,
                        duration_seconds=batch_time,
                    )
                )

                if params.save_local and total_records >= max_records:
                    pbar.close()
                    logger.info(f"Reached target {max_records:,} records, stopping")
                    break

            pbar.close()

            self._complete_checkpoint()

            total_time = time.time() - start_time
            logger.info(f"\nAll {batch_count} batches done in {total_time:.1f}s")

            # Derive map from freq + compute rank (after ALL batches)
            logger.info("Computing ig_rank...")
            rank_count = self.repository.compute_ig_rank(self.version_yyyyMM)
            logger.info(f"ig_rank computed for {rank_count:,} records")

            logger.info("Deriving map from freq...")
            map_count = self.repository.derive_map_from_freq(self.version_yyyyMM)
            logger.info(f"map table derived: {map_count:,} records")

            # Save test output
            local_output_path = None
            if params.save_local:
                local_output_path = self._save_test_output(params, batch_details)

            # Validate
            logger.info("Validating output...")
            validation = self.repository.validate_output(self.version_yyyyMM)
            if not validation.get("valid", False):
                warnings.append(f"Validation warnings: {validation.get('errors', 'Unknown')}")

            # Summary
            summary = self.repository.get_summary(self.version_yyyyMM)
            consistency = self.repository.get_consistency_distribution(self.version_yyyyMM)

            logger.info("=" * 60)
            logger.info("M6 completed:")
            logger.info(f"  Raw records processed: {total_records:,}")
            logger.info(f"  Batches: {batch_count}")
            logger.info(f"  Freq records upserted: {total_freq_written:,}")
            logger.info(f"  Map records (derived): {map_count:,}")
            logger.info(f"  OD pairs: {summary.get('od_pair_count', 'N/A')}")
            logger.info(f"  Unique numpaths: {summary.get('numpath_count', 'N/A')}")
            logger.info(f"  Avg path_freq_ratio: {summary.get('avg_freq_ratio', 'N/A'):.4f}")
            logger.info("  Consistency distribution:")
            for row in consistency:
                logger.info(f"    {row['consistency']}: {row['cnt']}")
            logger.info("=" * 60)

            execution_time = time.time() - start_time
            return M6TaskResult(
                status=TaskStatus.SUCCESS,
                records_processed=total_records,
                maps_written=map_count,
                freq_written=total_freq_written,
                batches=batch_count,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
                local_output_path=local_output_path,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"M6 failed: {e}")
            errors.append(str(e))
            return M6TaskResult(
                status=TaskStatus.FAILED,
                records_processed=total_records,
                maps_written=0,
                freq_written=0,
                batches=batch_count,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time,
            )
