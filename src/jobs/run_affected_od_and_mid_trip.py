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
from src.common.section_od_matcher import SectionOdMatcher
from src.modules.m3_impact_analysis.affected_od_service import AFFECTED_OD_CSV_COLUMNS
from src.modules.m3_impact_analysis.mid_trip_exit_service import MID_TRIP_FLOW_STAT_CSV_COLUMNS
from src.modules.m3_impact_analysis.detour_record_service import DETOUR_FLOW_STAT_CSV_COLUMNS
from src.modules.m3_impact_analysis.impact_summary_service import (
    IMPACT_SUMMARY_CSV_COLUMNS,
    ODS_SUMMARY_CSV_COLUMNS,
    SECTION_SUMMARY_CSV_COLUMNS,
    _CSV_COLUMN_ALIASES,
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
        help="汇总基础表输出CSV路径 (默认自动生成)",
    )
    parser.add_argument(
        "--output-ods-summary", default=None,
        help="OD汇总表输出CSV路径 (默认自动生成)",
    )
    parser.add_argument(
        "--output-section-summary", default=None,
        help="路段汇总表输出CSV路径 (默认自动生成)",
    )
    parser.add_argument(
        "--skip-loss-analysis", action="store_true",
        help="跳过步骤6（流失车辆分析）",
    )
    parser.add_argument(
        "--skip-vehicle-query", action="store_true",
        help="跳过步骤7（高频车辆查询）",
    )
    parser.add_argument(
        "--same-period-year", type=int, default=2025,
        help="同期参考年份 (默认: 2025)",
    )

    args = parser.parse_args()

    # 路段级别OD匹配器（全流程共享，缓存跨流程复用）
    section_od_matcher = SectionOdMatcher()

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
        samePeriodYear=args.same_period_year,
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

    # 流程1后处理：添加 section_od 并重写 CSV
    print("添加路段级别OD (section_od)...")
    section_od_matcher.enrich_records(
        raw_records, "enid", "exid",
        dataDate=args.start_date,
        dataDateGetter=lambda r: r.map_version + "01",
    )
    section_od_matcher.rewrite_csv_with_section_od(
        result1.outputCsvPath, raw_records, AFFECTED_OD_CSV_COLUMNS,
    )

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
        samePeriodYear=args.same_period_year,
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

    # 流程3后处理：添加 section_od 并重写 flow_stat CSV
    print("添加路段级别OD (section_od)...")
    section_od_matcher.enrich_records(
        result3_data, "od_enid", "od_exid", dataDate=args.start_date,
    )
    section_od_matcher.rewrite_csv_with_section_od(
        result3.flowStatCsvPath, result3_data, DETOUR_FLOW_STAT_CSV_COLUMNS,
    )

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
        samePeriodYear=args.same_period_year,
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

    # 流程2后处理：添加 section_od 并重写 flow_stat CSV
    print("添加路段级别OD (section_od)...")
    section_od_matcher.enrich_records(
        result2_data, "od_enid", "od_exid", dataDate=args.start_date,
    )
    section_od_matcher.rewrite_csv_with_section_od(
        result2.flowStatCsvPath, result2_data, MID_TRIP_FLOW_STAT_CSV_COLUMNS,
    )

    # ============================================================
    # 综合汇总：流程1+2+3 数据合并（步骤1-5）
    # ============================================================
    print("\n" + "=" * 60)
    print("综合汇总：流程1+2+3 数据合并（动态测算）")
    print("=" * 60)

    # 确定输出路径
    summary_output_path = args.output_summary
    import os
    import time
    os.makedirs("analysis_results", exist_ok=True)
    if summary_output_path is None:
        summary_output_path = os.path.join(
            "analysis_results", f"impact_summary_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
    ods_output_path = args.output_ods_summary
    if ods_output_path is None:
        ods_output_path = os.path.join(
            "analysis_results", f"ods_summary_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
    section_output_path = args.output_section_summary
    if section_output_path is None:
        section_output_path = os.path.join(
            "analysis_results", f"section_summary_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )

    summary_service = ImpactSummaryService()
    summary_records, ods_records, section_records = summary_service.run(
        raw_records=raw_records,
        mid_data=result2_data,
        detour_data=result3_data,
        output_path=summary_output_path,
        ods_output_path=ods_output_path,
        section_output_path=section_output_path,
    )

    print(f"汇总基础表记录数: {len(summary_records)}")
    print(f"OD汇总表记录数: {len(ods_records)}")
    print(f"路段汇总表记录数: {len(section_records)}")

    # 综合汇总后处理：添加 section_od 并重写 CSV
    print("添加路段级别OD (section_od)...")
    section_od_matcher.enrich_records(
        summary_records, "enid", "exid", dataDate=args.start_date,
    )
    section_od_matcher.rewrite_csv_with_section_od(
        summary_output_path, summary_records, IMPACT_SUMMARY_CSV_COLUMNS,
        aliases=_CSV_COLUMN_ALIASES,
    )

    # ============================================================
    # 步骤6：流失车辆分析
    # ============================================================
    if not args.skip_loss_analysis:
        print("\n" + "=" * 60)
        print("步骤6：流失车辆分析")
        print("=" * 60)

        from src.modules.m3_impact_analysis.flow_loss_analysis import FlowLossAnalysisService

        loss_analysis = FlowLossAnalysisService(section_od_matcher=section_od_matcher)
        loss_results = loss_analysis.run(
            summary_records=summary_records,
            section_records=section_records,
            output_dir=os.path.join("analysis_results", "flow_loss_analysis"),
            dataDate=args.start_date,
        )
        print(f"TOP15 流失路段数: {loss_results['top15_count']}")

        # ============================================================
        # 步骤7：高频车辆查询
        # ============================================================
        if not args.skip_vehicle_query and loss_results["top15_od_pairs"]:
            print("\n" + "=" * 60)
            print("步骤7：高频车辆查询（TOP15 流失OD）")
            print("=" * 60)

            from src.modules.m3_impact_analysis.vehicle_query_service import VehicleQueryService

            vehicle_query = VehicleQueryService()
            top_od_pairs = loss_results["top15_od_pairs"]
            print(f"查询 {len(top_od_pairs)} 个 OD 对...")
            vehicle_results = vehicle_query.run(
                top_od_pairs=top_od_pairs,
                start_date=args.start_date,
                end_date=args.end_date,
                data_dir=args.data_dir,
                output_dir=os.path.join("analysis_results", "vehicle_query"),
                od_mapping=loss_results.get("od_mapping"),
                od_pair_to_section_od=loss_results.get("od_pair_to_section_od"),
            )
            print(f"车辆查询完成: {len(vehicle_results)} 个输出文件")
    else:
        print("\n跳过步骤6（流失分析）和步骤7（车辆查询）")

    sys.exit(0 if result2.status == "success" else 1)


if __name__ == "__main__":
    main()
