"""
流程2 CLI入口：受影响OD的中途下站检测

用法:
    # 从流程1结果CSV读取OD
    python src/jobs/run_mid_trip_exit_detector.py \
        --affected-od-csv analysis_results/affected_od_flow.csv \
        --start-date 20260315 \
        --end-date 20260415 \
        --output analysis_results/mid_trip_exit.csv

    # 直接指定OD对（调试用）
    python src/jobs/run_mid_trip_exit_detector.py \
        --od-pairs "enid1:exid1,enid2:exid2" \
        --start-date 20260315 \
        --end-date 20260415 \
        --output analysis_results/mid_trip_exit.csv
"""

import argparse
import sys
from pathlib import Path

# 项目根目录
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from src.modules.m3_impact_analysis.mid_trip_exit_service import MidTripExitService
from src.modules.m3_impact_analysis.analysis_schema import MidTripExitParams


def main():
    parser = argparse.ArgumentParser(description="受影响OD的中途下站检测")
    parser.add_argument(
        "--affected-od-csv",
        help="流程1输出CSV路径",
    )
    parser.add_argument(
        "--od-pairs",
        help="手动指定OD对: enid1:exid1,enid2:exid2",
    )
    parser.add_argument(
        "--section-ids",
        help="施工收费单元ID，多个用|分隔（用于中途下站路径过滤）",
    )
    parser.add_argument(
        "--start-date", required=True,
        help="施工开始日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--end-date", required=True,
        help="施工结束日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--data-dir", default="/home/shy/gaosu_data",
        help="CSV数据根目录 (默认: /home/shy/gaosu_data)",
    )
    parser.add_argument(
        "--output", default=None,
        help="输出CSV路径 (默认自动生成到 analysis_results/)",
    )

    args = parser.parse_args()

    params = MidTripExitParams(
        sectionIds=args.section_ids,
        affectedOdCsv=args.affected_od_csv,
        odPairs=args.od_pairs,
        startDate=args.start_date,
        endDate=args.end_date,
        dataDir=args.data_dir,
    )

    service = MidTripExitService()
    result = service.run(params, output_path=args.output)

    print("\n" + "=" * 60)
    print("流程2 执行结果")
    print("=" * 60)
    print(f"状态: {result.status}")
    print(f"扫描总记录数: {result.totalRecordsScanned:,}")
    print(f"过滤后记录数: {result.matchedRecordsScanned:,}")
    print(f"中途下站记录数: {result.midTripExitCount}")
    print(f"处理天数: {result.daysProcessed}")
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
