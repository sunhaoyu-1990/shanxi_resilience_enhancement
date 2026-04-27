#!/usr/bin/env python3
"""
M2 收费单元-OD(path)小时流量统计 — 命令行入口

Usage:
    # Test mode (1000 records)
    uv run python -m src.jobs.run_m2_flow_stat --version 202603 --max-records 1000 --save-local

    # Full run
    uv run python -m src.jobs.run_m2_flow_stat --version 202603
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams
from src.modules.m2_od_flow.flow_stat_service import FlowStatService


def main():
    parser = argparse.ArgumentParser(
        description="M2 Flow Stat: section-OD(path)-hour flow statistics"
    )
    parser.add_argument(
        "--version", default="202603",
        help="Version YYYYMM (default: 202603)",
    )
    parser.add_argument(
        "--csv-path", default="",
        help="CSV file path (auto-generated if empty)",
    )
    parser.add_argument(
        "--section-version", default="202603",
        help="dwd_section_path version (default: 202603)",
    )
    parser.add_argument(
        "--topo-version", default="202512",
        help="Topology version (default: 202512)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500_000,
        help="Batch size (default: 500000)",
    )
    parser.add_argument(
        "--upsert-interval", type=int, default=5,
        help="Upsert to DB every N batches (default: 5)",
    )
    parser.add_argument(
        "--max-records", type=int, default=0,
        help="Max records to process, 0=all (default: 0)",
    )
    parser.add_argument(
        "--save-local", action="store_true",
        help="Save results to local JSON (test mode)",
    )
    parser.add_argument(
        "--output-dir", default="outputs/m2_flow_stat",
        help="Local output directory",
    )

    args = parser.parse_args()

    params = FlowStatParams(
        version_yyyyMM=args.version,
        csv_path=args.csv_path,
        section_version=args.section_version,
        topo_version=args.topo_version,
        batch_size=args.batch_size,
        upsert_interval=args.upsert_interval,
        max_records=args.max_records,
        save_local=args.save_local,
        output_dir=args.output_dir,
    )

    service = FlowStatService()
    result = service.run(params)

    if result.status == "success":
        print(f"\nDone! {result.records_processed:,} records processed in {result.execution_time:.1f}s")
        print(f"  Flow records: {result.flow_records_written:,}")
        print(f"  Map inserts: {result.map_records_inserted}")
        if result.local_output_path:
            print(f"  Output: {result.local_output_path}")
    else:
        print(f"\nFailed! {result.errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
