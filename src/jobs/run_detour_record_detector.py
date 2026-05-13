"""
流程3 CLI入口：受影响OD的绕行记录检测

用法:
    # 从流程1结果CSV读取OD
    python src/jobs/run_detour_record_detector.py \
        --affected-od-csv analysis_results/affected_od_flow.csv \
        --section-ids "G007061001000610" \
        --start-date 20260301 \
        --end-date 20260331 \
        --output analysis_results/detour_record.csv

    # 直接指定OD对（调试用）
    python src/jobs/run_detour_record_detector.py \
        --od-pairs "enid1:exid1,enid2:exid2" \
        --section-ids "G007061001000610" \
        --start-date 20260301 \
        --end-date 20260331 \
        --output analysis_results/detour_record.csv
"""

import argparse
import sys
from pathlib import Path

# 项目根目录
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from src.modules.m3_impact_analysis.detour_record_service import DetourRecordService
from src.modules.m3_impact_analysis.analysis_schema import DetourRecordParams


def main():
    parser = argparse.ArgumentParser(description="受影响OD的绕行记录检测")
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
        required=True,
        help="施工收费单元ID，多个用|分隔",
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
        "--max-sections", type=int, default=5,
        help="OD分类：O/D到施工单元最短路径节点数上限 (默认: 5)",
    )
    parser.add_argument(
        "--max-construction-sections", type=int, default=5,
        help="记录过滤：最短路径中施工段个数上限 (默认: 5)",
    )
    parser.add_argument(
        "--output", default=None,
        help="输出CSV路径 (默认自动生成到 analysis_results/)",
    )

    args = parser.parse_args()

    params = DetourRecordParams(
        sectionIds=args.section_ids,
        affectedOdCsv=args.affected_od_csv,
        odPairs=args.od_pairs,
        startDate=args.start_date,
        endDate=args.end_date,
        dataDir=args.data_dir,
        maxSections=args.max_sections,
        maxConstructionSections=args.max_construction_sections,
    )

    service = DetourRecordService()
    result = service.run(params, output_path=args.output)

    print("\n" + "=" * 60)
    print("流程3 执行结果")
    print("=" * 60)
    print(f"状态: {result.status}")
    print(f"扫描总记录数: {result.totalRecordsScanned:,}")
    print(f"预过滤记录数: {result.prefilteredRecords:,}")
    print(f"绕行记录数: {result.detourRecordCount}")
    print(f"  找D判定O: {result.sameDestDiffOriginCount}")
    print(f"  找O判定D: {result.sameOriginDiffDestCount}")
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
