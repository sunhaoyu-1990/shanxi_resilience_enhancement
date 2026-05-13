"""
流程1 CLI入口：施工收费单元 → 受影响OD-Path流量查询

用法:
    python src/jobs/run_affected_od_query.py \
        --section-ids "G007061003000210|G300161001002220" \
        --start-date 20260315 \
        --end-date 20260415 \
        --output analysis_results/affected_od_flow.csv
"""

import argparse
import sys
from pathlib import Path

# 项目根目录
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from src.modules.m3_impact_analysis.affected_od_service import AffectedOdService
from src.modules.m3_impact_analysis.analysis_schema import AffectedOdQueryParams


def main():
    parser = argparse.ArgumentParser(description="施工收费单元 → 受影响OD-Path流量查询")
    parser.add_argument(
        "--section-ids", default="G007061003000210",
        help="施工收费单元ID，多个用|分隔，如 'G007061003000210|G300161001002220'",
    )
    parser.add_argument(
        "--start-date", default="20260301",
        help="施工开始日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--end-date", default="20260302",
        help="施工结束日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--output", default=None,
        help="输出CSV路径 (默认自动生成到 analysis_results/)",
    )
    parser.add_argument(
        "--min-flow", type=int, default=50,
        help="OD对聚合总流量阈值，低于该值的OD下所有path全部去掉 (默认: 0 不过滤)",
    )
    parser.add_argument(
        "--min-affected-path-flow", type=int, default=10,
        help="受影响path单条流量阈值，construction_flow或same_period_2025_flow任一>该值才保留 (默认: 0 不过滤)",
    )

    args = parser.parse_args()

    params = AffectedOdQueryParams(
        sectionIds=args.section_ids,
        startDate=args.start_date,
        endDate=args.end_date,
        minAffectedPathFlow=args.min_affected_path_flow,
        minFlow=args.min_flow,
    )

    service = AffectedOdService()
    result = service.run(params, output_path=args.output)

    print("\n" + "=" * 60)
    print("流程1 执行结果")
    print("=" * 60)
    print(f"状态: {result.status}")
    print(f"受影响OD-Path数: {result.affectedOdCount}")
    print(f"过滤后OD对数: {len(result.filteredOdPairs)}")
    print(f"施工期间流量可用: {result.constructionFlowAvailable}")
    print(f"2025同期流量可用: {result.samePeriod2025FlowAvailable}")
    print(f"输出文件: {result.outputCsvPath}")
    if result.warnings:
        print(f"警告: {len(result.warnings)}")
        for w in result.warnings:
            print(f"  - {w}")
    if result.errors:
        print(f"错误: {len(result.errors)}")
        for e in result.errors:
            print(f"  - {e}")
    print(f"耗时: {result.executionTime:.2f}s")
    print("=" * 60)

    sys.exit(0 if result.status == "success" else 1)


if __name__ == "__main__":
    main()
