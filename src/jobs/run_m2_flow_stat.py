#!/usr/bin/env python3
"""
M2 收费单元-OD(path)小时流量统计 — 命令行入口

支持单月和多月处理模式。

Usage:
    # 单月处理 (原有模式)
    uv run python -m src.jobs.run_m2_flow_stat --version 202603 --data-dir /home/shy/gaosu_data

    # 多月处理 (逗号分隔)
    uv run python -m src.jobs.run_m2_flow_stat --versions 202603,202604,202605 --data-dir /home/shy/gaosu_data

    # 多月处理 (范围)
    uv run python -m src.jobs.run_m2_flow_stat --from-version 202603 --to-version 202605 --data-dir /home/shy/gaosu_data

    # 并行处理多个月
    uv run python -m src.jobs.run_m2_flow_stat --versions 202603,202604,202605 --data-dir /home/shy/gaosu_data --workers 5 --mini-batch-size 50000
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams
from src.modules.m2_od_flow.flow_stat_service import FlowStatService


def parse_version_list(versions_str: str) -> list[str]:
    """解析逗号分隔的月份列表"""
    return [v.strip() for v in versions_str.split(",") if v.strip()]


def expand_version_range(from_version: str, to_version: str) -> list[str]:
    """
    扩展月份范围为月份列表

    Args:
        from_version: 起始月份 YYYYMM
        to_version: 结束月份 YYYYMM

    Returns:
        月份列表，如 [202603, 202604, 202605]
    """
    from_year = int(from_version[:4])
    from_month = int(from_version[4:6])
    to_year = int(to_version[:4])
    to_month = int(to_version[4:6])

    versions = []
    current_year = from_year
    current_month = from_month

    while (current_year < to_year) or (current_year == to_year and current_month <= to_month):
        versions.append(f"{current_year}{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return versions


def run_monthly(
    version: str,
    args: argparse.Namespace,
) -> dict:
    """
    处理单个月份

    Returns:
        包含 records_processed, flow_records_written, execution_time 的字典
    """
    params = FlowStatParams(
        version_yyyyMM=version,
        csv_path=args.csv_path,
        data_dir=args.data_dir,
        section_version=args.section_version or version,
        topo_version=args.topo_version or version,
        batch_size=args.batch_size,
        upsert_interval=args.upsert_interval,
        max_records=args.max_records,
        save_local=args.save_local,
        output_dir=args.output_dir,
        num_workers=args.workers,
        mini_batch_size=args.mini_batch_size,
    )

    service = FlowStatService()
    result = service.run(params)

    return {
        "version": version,
        "status": result.status,
        "records_processed": result.records_processed,
        "flow_records_written": result.flow_records_written,
        "map_records_inserted": result.map_records_inserted,
        "execution_time": result.execution_time,
        "errors": result.errors,
    }


def main():
    parser = argparse.ArgumentParser(
        description="M2 Flow Stat: section-OD(path)-hour flow statistics (支持多月份处理)"
    )

    # 单月参数
    parser.add_argument(
        "--version", default="202603",
        help="Version YYYYMM (单个月份，与 --versions 互斥)",
    )
    parser.add_argument(
        "--csv-path", default="",
        help="CSV file path (auto-generated if empty, monthly mode only)",
    )
    parser.add_argument(
        "--data-dir", default="/home/shy/gaosu_data",
        help=(
            "Daily CSV data directory. When set, processes "
            "{data_dir}/{version}/data_*.csv instead of a single monthly file. "
            "Output goes to daily tables. Default: empty (use monthly CSV mode)"
        ),
    )
    parser.add_argument(
        "--section-version", default="202603",
        help="dwd_section_path version (default: 与 --version 相同)",
    )
    parser.add_argument(
        "--topo-version", default="202603",
        help="Topology version (default: 与 --version 相同)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50000,
        help="Batch size for single-process mode (default: 50000)",
    )
    parser.add_argument(
        "--upsert-interval", type=int, default=5,
        help="Upsert to DB every N batches in single-process mode (default: 5)",
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
    parser.add_argument(
        "--workers", type=int, default=2,
        help="Number of worker processes per month, 1=single-process, >1=parallel (default: 2)",
    )
    parser.add_argument(
        "--mini-batch-size", type=int, default=50000,
        help="Mini-batch size for parallel mode (default: 50000)",
    )

    # 多月处理参数
    parser.add_argument(
        "--versions", default="",
        help=(
            "多个月份列表，逗号分隔，如 202603,202604,202605 "
            "(与 --version 和 --from-version/--to-version 互斥)"
        ),
    )
    parser.add_argument(
        "--from-version", default="",
        help="起始月份 YYYYMM (与 --to-version 配合使用)",
    )
    parser.add_argument(
        "--to-version", default="",
        help="结束月份 YYYYMM (与 --from-version 配合使用)",
    )
    parser.add_argument(
        "--skip-months", default="",
        help="跳过的月份，逗号分隔，如 202604,202605",
    )

    args = parser.parse_args()

    # 解析月份列表
    versions = []

    # 优先级: --versions > --from/to > --version
    if args.versions:
        versions = parse_version_list(args.versions)
    elif args.from_version and args.to_version:
        versions = expand_version_range(args.from_version, args.to_version)
    elif args.version:
        versions = [args.version]
    else:
        print("Error: 必须指定 --version, --versions 或 --from-version/--to-version")
        sys.exit(1)

    # 解析跳过的月份
    skip_months = set()
    if args.skip_months:
        skip_months = set(parse_version_list(args.skip_months))
    versions = [v for v in versions if v not in skip_months]

    if not versions:
        print("Error: 没有可处理的月份")
        sys.exit(1)

    print(f"{'=' * 60}")
    print(f"M2 流量统计 - 多月处理模式")
    print(f"待处理月份: {len(versions)} 个")
    print(f"月份列表: {', '.join(versions)}")
    if skip_months:
        print(f"跳过月份: {', '.join(skip_months)}")
    print(f"{'=' * 60}\n")

    # 汇总统计
    total_records = 0
    total_flow_records = 0
    total_map_inserts = 0
    total_time = 0.0
    failed_versions = []

    for i, version in enumerate(versions, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(versions)}] 处理月份: {version}")
        print(f"{'=' * 60}")

        try:
            result = run_monthly(version, args)

            if result["status"] == "success":
                mode = "daily" if args.data_dir else "monthly"
                print(f"\n[{version}] 完成!")
                print(f"  模式: {mode}")
                print(f"  处理记录: {result['records_processed']:,}")
                print(f"  流量记录: {result['flow_records_written']:,}")
                print(f"  映射插入: {result['map_records_inserted']}")
                print(f"  执行时间: {result['execution_time']:.1f}s")

                total_records += result["records_processed"]
                total_flow_records += result["flow_records_written"]
                total_map_inserts += result["map_records_inserted"]
                total_time += result["execution_time"]
            else:
                print(f"\n[{version}] 失败!")
                print(f"  错误: {result['errors']}")
                failed_versions.append(version)
        except Exception as e:
            print(f"\n[{version}] 异常!")
            print(f"  异常: {e}")
            failed_versions.append(version)

    # 输出汇总
    print(f"\n{'=' * 60}")
    print(f"多月份处理完成")
    print(f"{'=' * 60}")
    print(f"总处理月份: {len(versions)}")
    print(f"成功: {len(versions) - len(failed_versions)}")
    print(f"失败: {len(failed_versions)}")
    print(f"总处理记录: {total_records:,}")
    print(f"总流量记录: {total_flow_records:,}")
    print(f"总映射插入: {total_map_inserts:,}")
    print(f"总执行时间: {total_time:.1f}s")

    if failed_versions:
        print(f"\n失败月份: {', '.join(failed_versions)}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
