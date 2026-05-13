"""
流程1+3+2 串联CLI入口：施工收费单元 → 受影响OD流量查询 → 绕行记录检测 → 中途下站检测

执行顺序：流程1 → 流程3 → 流程2

用法:
    python src/jobs/run_affected_od_and_mid_trip.py \
        --section-ids "G065W610010020" \
        --start-date 20260301 \
        --end-date 20260302 \
        --min-flow 10 \
        --output-od analysis_results/affected_od_flow.csv \
        --output-detour analysis_results/detour_record.csv \
        --output-mid analysis_results/mid_trip_exit.csv
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
from src.modules.m3_impact_analysis.detour_record_service import DetourRecordService
from src.modules.m3_impact_analysis.mid_trip_exit_service import MidTripExitService
from src.modules.m3_impact_analysis.impact_summary_service import ImpactSummaryService
from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdQueryParams,
    DetourRecordParams,
    MidTripExitParams,
)


def main():
    parser = argparse.ArgumentParser(description="施工收费单元 → 受影响OD流量查询 → 绕行记录检测 → 中途下站检测（串联）")
    parser.add_argument(
        "--section-ids", default="G000561005000910|G000561006000110|G000561006000210|G000561006000310|G000561007000110|G000551001000110|G0005610070010",
        help="施工收费单元ID，多个用|分隔",
    )
    parser.add_argument(
        "--start-date", default="20260415",
        help="施工开始日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--end-date", default="20260430",
        help="施工结束日期 (YYYYMMDD)",
    )
    parser.add_argument(
        "--min-flow", type=int, default=10,
        help="OD对聚合总流量阈值，低于该值的OD下所有path全部去掉 (默认: 0 不过滤)",
    )
    parser.add_argument(
        "--min-affected-path-flow", type=int, default=5,
        help="受影响path单条流量阈值，construction_flow或same_period_2025_flow任一>该值才保留 (默认: 0 不过滤)",
    )
    parser.add_argument(
        "--data-dir", default="/home/shy/gaosu_data",
        help="CSV数据根目录 (默认: /home/shy/gaosu_data)",
    )
    parser.add_argument(
        "--max-sections", type=int, default=5,
        help="流程3 OD分类：O/D到施工单元最短路径节点数上限 (默认: 5)",
    )
    parser.add_argument(
        "--max-construction-sections", type=int, default=6,
        help="流程3 记录过滤：最短路径中施工段个数上限 (默认: 5)",
    )
    parser.add_argument(
        "--output-od", default=None,
        help="流程1输出CSV路径 (默认自动生成)",
    )
    parser.add_argument(
        "--output-detour", default=None,
        help="流程3输出CSV路径 (默认自动生成)",
    )
    parser.add_argument(
        "--output-mid", default=None,
        help="流程2输出CSV路径 (默认自动生成)",
    )
    parser.add_argument(
        "--output-summary", default=None,
        help="综合汇总输出CSV路径 (默认自动生成)",
    )

    args = parser.parse_args()

    # ============================================================
    # 流程1：受影响OD-Path流量查询
    # ============================================================
    print("=" * 60)
    print("流程1：受影响OD-Path流量查询")
    print("=" * 60)

    params1 = AffectedOdQueryParams(
        sectionIds=args.section_ids,
        startDate=args.start_date,
        endDate=args.end_date,
        minAffectedPathFlow=args.min_affected_path_flow,
        minFlow=args.min_flow,
    )

    service1 = AffectedOdService()
    result1, raw_records = service1.run(params1, output_path=args.output_od)

    print(f"状态: {result1.status}")
    print(f"受影响OD-Path数: {result1.affectedOdCount}")
    print(f"过滤后OD对数: {len(result1.filteredOdPairs)}")
    print(f"施工期间流量可用: {result1.constructionFlowAvailable}")
    print(f"2025同期流量可用: {result1.samePeriod2025FlowAvailable}")
    print(f"输出文件: {result1.outputCsvPath}")
    print(f"耗时: {result1.executionTime:.2f}s")

    if result1.status != "success":
        print("\n流程1失败，终止后续流程")
        sys.exit(1)

    if not result1.filteredOdPairs:
        print("\n过滤后无OD对，无需执行后续流程")
        sys.exit(0)

    # ============================================================
    # 流程3：绕行记录检测
    # ============================================================
    print("\n" + "=" * 60)
    print("流程3：绕行记录检测")
    print("=" * 60)

    params3 = DetourRecordParams(
        sectionIds=args.section_ids,
        odPairsList=result1.filteredOdPairs,
        startDate=args.start_date,
        endDate=args.end_date,
        dataDir=args.data_dir,
        maxSections=args.max_sections,
        maxConstructionSections=args.max_construction_sections,
    )

    service3 = DetourRecordService()
    result3, result3_data = service3.run(params3, output_path=args.output_detour)

    print(f"状态: {result3.status}")
    print(f"扫描总记录数: {result3.totalRecordsScanned:,}")
    print(f"预过滤记录数: {result3.prefilteredRecords:,}")
    print(f"绕行记录数: {result3.detourRecordCount}")
    print(f"  找D判定O: {result3.sameDestDiffOriginCount}")
    print(f"  找O判定D: {result3.sameOriginDiffDestCount}")
    print(f"处理天数: {result3.daysProcessed}")
    print(f"输出文件: {result3.outputCsvPath}")
    print(f"耗时: {result3.executionTime:.2f}s")

    if result3.status != "success":
        print("\n流程3失败，终止流程2")
        sys.exit(1)

    # ============================================================
    # 流程2：中途下站检测
    # ============================================================
    print("\n" + "=" * 60)
    print("流程2：中途下站检测")
    print("=" * 60)

    params2 = MidTripExitParams(
        sectionIds=args.section_ids,
        odPairsList=result1.filteredOdPairs,
        startDate=args.start_date,
        endDate=args.end_date,
        dataDir=args.data_dir,
    )

    service2 = MidTripExitService()
    result2, result2_data = service2.run(params2, output_path=args.output_mid)

    print(f"状态: {result2.status}")
    print(f"扫描总记录数: {result2.totalRecordsScanned:,}")
    print(f"过滤后记录数: {result2.matchedRecordsScanned:,}")
    print(f"中途下站记录数: {result2.midTripExitCount}")
    print(f"处理天数: {result2.daysProcessed}")
    print(f"输出文件: {result2.outputCsvPath}")
    print(f"耗时: {result2.executionTime:.2f}s")

    # ============================================================
    # 综合汇总：流程1+2+3 数据合并
    # ============================================================
    print("\n" + "=" * 60)
    print("综合汇总：流程1+2+3 数据合并")
    print("=" * 60)

    summary_service = ImpactSummaryService()
    summary_records = summary_service.run(
        raw_records=raw_records,
        mid_data=result2_data,
        detour_data=result3_data,
        output_path=args.output_summary,
    )

    print(f"综合汇总记录数: {len(summary_records)}")

    sys.exit(0 if result2.status == "success" else 1)


if __name__ == "__main__":
    main()
