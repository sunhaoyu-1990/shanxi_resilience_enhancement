"""
M3 交通影响分析 - 动态测算综合汇总服务

将流程1（受影响OD流量）、流程2（中途下站检测）、流程3（绕行记录检测）的输出数据
按 (enid, exid, vehicle_type, section_od) 维度合并，进行派生计算，输出汇总基础表、OD汇总表、路段汇总表。

处理步骤：
1. 流程1 raw_records 按 (enid, exid, vehicle_type, section_od) × is_affected 聚合透视
2. 流程2/3 数据聚合 + 重命名 + 单次费率计算
3. Left Join: 步骤1 LEFT JOIN 步骤2/3
4. 派生计算: 受影响流量、绕行流量、保留路径、流失流量、通行费等
5. 汇总: OD汇总表 + 路段汇总表
"""

import csv
import os
import time
from collections import defaultdict
from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdPathRecord,
    DetourFlowStatRecord,
    ImpactSummaryRecord,
    MidTripExitFlowStatRecord,
    OdsSummaryRecord,
    SectionSummaryRecord,
)

logger = get_logger(__name__)

OUTPUT_DIR = "analysis_results"

# CSV 列名映射：Python 属性名 → 中文列名
_CSV_COLUMN_ALIASES: dict[str, str] = {
    "con_fee": "施工影响路径通行费",
    "con_control_fee": "施工影响路径交控通行费",
    "con_flow": "施工影响路径施工期间流量",
    "con_sp2025_flow": "施工影响路径2025年同期流量",
    "con_length": "施工影响路径通行里程",
    "con_control_length": "施工影响路径交控通行里程",
    "other_fee": "其他路径通行费",
    "other_control_fee": "其他路径交控通行费",
    "other_flow": "其他路径施工期间流量",
    "other_sp2025_flow": "其他路径2025年同期流量",
    "other_length": "其他路径通行里程",
    "other_control_length": "其他路径交控通行里程",
    "mid_flow": "中途上下站流量",
    "mid_sp2025_flow": "2025年同期中途上下站流量",
    "mid_loss_fee": "中途上下站损失通行费",
    "mid_control_loss_fee": "中途上下站损失交控通行费",
    "mid_unit_loss_fee": "单次通行损失费额(中途上下站)",
    "mid_unit_control_loss_fee": "单次通行交控损失费额(中途上下站)",
    "detour_flow": "附近上下车流量",
    "detour_sp2025_flow": "2025年同期车流量",
    "detour_loss_fee": "附近上下车损失通行费",
    "detour_control_loss_fee": "附近上下车损失交控通行费",
    "detour_unit_loss_fee": "单次通行损失费额(附近上下车)",
    "detour_unit_control_loss_fee": "单次通行交控损失费额(附近上下车)",
    "original_path_fee": "原路径通行车流费用",
    "ref_total_flow": "参考总流量",
    "unaffected_flow": "未收影响流量",
    "affected_flow": "受影响流量",
    "detour_flow_final": "绕行流量",
    "retained_nearby": "保留路径(附近上下站）",
    "retained_midtrip": "保留路径(中途上下站）",
    "lost_flow": "流失流量",
    "original_control_fee": "原交控通行费",
    "unaffected_control_fee": "未收影响交控通行费",
    "detour_control_fee_final": "绕行交控通行费",
    "retained_nearby_control_fee": "保留交控通行费(附近上下站）",
    "retained_midtrip_control_fee": "保留交控通行费(中途上下站）",
    "lost_control_fee": "流失交控通行费",
}

IMPACT_SUMMARY_CSV_COLUMNS = ["enid", "exid", "vehicle_type", "section_od"] + [
    _CSV_COLUMN_ALIASES.get(f, f) for f in ImpactSummaryRecord.model_fields
    if f not in ("enid", "exid", "vehicle_type", "section_od")
]

ODS_SUMMARY_CSV_COLUMNS = ["enid", "exid"] + [
    _CSV_COLUMN_ALIASES.get(f, f) for f in OdsSummaryRecord.model_fields
    if f not in ("enid", "exid")
]

SECTION_SUMMARY_CSV_COLUMNS = ["section_od"] + [
    _CSV_COLUMN_ALIASES.get(f, f) for f in SectionSummaryRecord.model_fields
    if f != "section_od"
]


def _safe_sum(values: list) -> float:
    """对非 None 的值求和"""
    return sum(v for v in values if v is not None)


def _safe_mean(values: list) -> float:
    """对非 None 的值求平均"""
    valid = [v for v in values if v is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def _safe_div(numerator: float, denominator: float) -> float:
    """安全除法，分母为0返回0"""
    return numerator / denominator if denominator != 0 else 0.0


def _compute_retained_nearby(
    affectedFlow: int,
    detourFlowFinal: int,
    midFlow: float,
    midSp2025Flow: float,
    detourFlowRaw: float,
    detourSp2025Flow: float,
) -> int:
    """计算保留路径(附近上下站)"""
    nearbyIncrement = detourFlowRaw - detourSp2025Flow
    midIncrement = midFlow - midSp2025Flow
    combinedIncrement = midIncrement + nearbyIncrement
    remainingAffected = affectedFlow - detourFlowFinal

    if nearbyIncrement <= 0:
        return 0
    if combinedIncrement < 0:
        return 0
    if combinedIncrement > remainingAffected:
        return int(min(nearbyIncrement, remainingAffected))
    return int(nearbyIncrement)


def _compute_retained_midtrip(
    midFlow: float,
    midSp2025Flow: float,
    affectedFlow: int,
    detourFlowFinal: int,
    retainedNearby: int,
) -> int:
    """计算保留路径(中途上下站)"""
    midIncrement = midFlow - midSp2025Flow
    remainingAffected = affectedFlow - detourFlowFinal - retainedNearby

    if midIncrement <= 0:
        return 0
    if remainingAffected <= 0:
        return 0
    if midIncrement <= remainingAffected:
        return int(midIncrement)
    return int(remainingAffected)


def _step1_aggregate_flow1(
    raw_records: list[AffectedOdPathRecord],
) -> dict[tuple[str, str, str, str], dict]:
    """
    步骤1: 流程1数据按 (enid, exid, vehicle_type, section_od) × is_affected 聚合透视

    Returns:
        {(enid, exid, vehicle_type, section_od): {con_fee, con_control_fee, ...}}
    """
    grouped: dict[tuple[str, str, str, str, bool], dict[str, list]] = defaultdict(
        lambda: {
            "fee_yuan": [],
            "control_fee_yuan": [],
            "construction_flow": [],
            "same_period_2025_flow": [],
            "total_length_meters": [],
            "control_length_meters": [],
        }
    )

    for rec in raw_records:
        sectionOd = rec.section_od or ""
        key = (rec.enid, rec.exid, rec.vehicle_type, sectionOd, rec.is_affected)
        g = grouped[key]
        g["fee_yuan"].append(rec.fee_yuan)
        g["control_fee_yuan"].append(rec.control_fee_yuan)
        g["construction_flow"].append(rec.construction_flow)
        g["same_period_2025_flow"].append(rec.same_period_2025_flow)
        g["total_length_meters"].append(rec.total_length_meters)
        g["control_length_meters"].append(rec.control_length_meters)

    # 按 (enid, exid, vehicle_type, section_od) 透视合并 is_affected
    result: dict[tuple[str, str, str, str], dict] = {}
    for (enid, exid, vehicleType, sectionOd, isAffected), g in grouped.items():
        pivotKey = (enid, exid, vehicleType, sectionOd)
        if pivotKey not in result:
            result[pivotKey] = {
                "con_fee": 0.0, "con_control_fee": 0.0,
                "con_flow": 0, "con_sp2025_flow": 0,
                "con_length": 0, "con_control_length": 0,
                "other_fee": 0.0, "other_control_fee": 0.0,
                "other_flow": 0, "other_sp2025_flow": 0,
                "other_length": 0, "other_control_length": 0,
            }

        prefix = "con" if isAffected else "other"
        r = result[pivotKey]
        r[f"{prefix}_fee"] = _safe_mean(g["fee_yuan"])
        r[f"{prefix}_control_fee"] = _safe_mean(g["control_fee_yuan"])
        r[f"{prefix}_flow"] = int(_safe_sum(g["construction_flow"]))
        r[f"{prefix}_sp2025_flow"] = int(_safe_sum(g["same_period_2025_flow"]))
        r[f"{prefix}_length"] = int(_safe_sum(g["total_length_meters"]))
        r[f"{prefix}_control_length"] = int(_safe_sum(g["control_length_meters"]))

    # 过滤: 施工影响路径2025年同期流量 <= 0 的行删除
    filtered = {
        k: v for k, v in result.items()
        if v["con_sp2025_flow"] > 0
    }

    return filtered


def _step2_aggregate_flow2(
    mid_data: list[MidTripExitFlowStatRecord],
) -> dict[tuple[str, str, str], dict]:
    """
    步骤2a: 流程2数据按 (od_enid, od_exid, vehicle_type) 聚合 + 重命名

    Returns:
        {(od_enid, od_exid, vehicle_type): {mid_flow, mid_sp2025_flow, ...}}
    """
    agg: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {
            "construction_flow": 0.0,
            "same_period_2025_flow": 0.0,
            "loss_fee_yuan": 0.0,
            "control_loss_fee_yuan": 0.0,
        }
    )

    for rec in mid_data:
        key = (rec.od_enid, rec.od_exid, rec.vehicle_type)
        a = agg[key]
        a["construction_flow"] += rec.construction_flow or 0
        a["same_period_2025_flow"] += rec.same_period_2025_flow or 0
        a["loss_fee_yuan"] += rec.loss_fee_yuan or 0.0
        a["control_loss_fee_yuan"] += rec.control_loss_fee_yuan or 0.0

    result: dict[tuple[str, str, str], dict] = {}
    for key, a in agg.items():
        midFlow = a["construction_flow"]
        result[key] = {
            "mid_flow": midFlow,
            "mid_sp2025_flow": a["same_period_2025_flow"],
            "mid_loss_fee": a["loss_fee_yuan"],
            "mid_control_loss_fee": a["control_loss_fee_yuan"],
            "mid_unit_loss_fee": _safe_div(a["loss_fee_yuan"], midFlow),
            "mid_unit_control_loss_fee": _safe_div(a["control_loss_fee_yuan"], midFlow),
        }
    return result


def _step2_aggregate_flow3(
    detour_data: list[DetourFlowStatRecord],
) -> dict[tuple[str, str, str], dict]:
    """
    步骤2b: 流程3数据按 (od_enid, od_exid, vehicle_type) 聚合 + 重命名

    Returns:
        {(od_enid, od_exid, vehicle_type): {detour_flow, detour_sp2025_flow, ...}}
    """
    agg: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {
            "construction_flow": 0.0,
            "same_period_2025_flow": 0.0,
            "loss_fee_yuan": 0.0,
            "control_loss_fee_yuan": 0.0,
        }
    )

    for rec in detour_data:
        key = (rec.od_enid, rec.od_exid, rec.vehicle_type)
        a = agg[key]
        a["construction_flow"] += rec.construction_flow or 0.0
        a["same_period_2025_flow"] += rec.same_period_2025_flow or 0.0
        a["loss_fee_yuan"] += rec.loss_fee_yuan or 0.0
        a["control_loss_fee_yuan"] += rec.control_loss_fee_yuan or 0.0

    result: dict[tuple[str, str, str], dict] = {}
    for key, a in agg.items():
        detourFlow = a["construction_flow"]
        result[key] = {
            "detour_flow": detourFlow,
            "detour_sp2025_flow": a["same_period_2025_flow"],
            "detour_loss_fee": a["loss_fee_yuan"],
            "detour_control_loss_fee": a["control_loss_fee_yuan"],
            "detour_unit_loss_fee": _safe_div(a["loss_fee_yuan"], detourFlow),
            "detour_unit_control_loss_fee": _safe_div(a["control_loss_fee_yuan"], detourFlow),
        }
    return result


_MID_DEFAULTS = {
    "mid_flow": 0.0, "mid_sp2025_flow": 0.0,
    "mid_loss_fee": 0.0, "mid_control_loss_fee": 0.0,
    "mid_unit_loss_fee": 0.0, "mid_unit_control_loss_fee": 0.0,
}

_DETOUR_DEFAULTS = {
    "detour_flow": 0.0, "detour_sp2025_flow": 0.0,
    "detour_loss_fee": 0.0, "detour_control_loss_fee": 0.0,
    "detour_unit_loss_fee": 0.0, "detour_unit_control_loss_fee": 0.0,
}


def _step4_derive_calculations(row: dict) -> dict:
    """
    步骤4: 对合并后的行进行派生计算

    Returns: 追加派生字段的行字典
    """
    conControlFee = row["con_control_fee"]
    conFlow = row["con_flow"]
    conSp2025Flow = row["con_sp2025_flow"]
    otherControlFee = row["other_control_fee"]
    otherFlow = row["other_flow"]
    otherSp2025Flow = row["other_sp2025_flow"]

    midFlow = row["mid_flow"]
    midSp2025Flow = row["mid_sp2025_flow"]
    midUnitControlLossFee = row["mid_unit_control_loss_fee"]

    detourFlowRaw = row["detour_flow"]
    detourSp2025Flow = row["detour_sp2025_flow"]
    detourUnitControlLossFee = row["detour_unit_control_loss_fee"]

    # 原路径通行车流费用（万元）
    originalPathFee = conControlFee * conFlow / 10000

    # 参考总流量 = 施工影响路径2025年同期流量
    refTotalFlow = conSp2025Flow

    # 未收影响流量 = 施工影响路径施工期间流量
    unaffectedFlow = conFlow

    # 受影响流量 = MAX(0, 参考总流量 - 未收影响流量)
    affectedFlow = max(0, refTotalFlow - unaffectedFlow)

    # 绕行流量 = MIN(MAX(0, 其他路径施工期间流量 - 其他路径2025年同期流量), 受影响流量)
    detourFlowFinal = min(max(0, otherFlow - otherSp2025Flow), affectedFlow)

    # 保留路径(附近上下站)
    retainedNearby = _compute_retained_nearby(
        affectedFlow, detourFlowFinal,
        midFlow, midSp2025Flow,
        detourFlowRaw, detourSp2025Flow,
    )

    # 保留路径(中途上下站)
    retainedMidtrip = _compute_retained_midtrip(
        midFlow, midSp2025Flow,
        affectedFlow, detourFlowFinal, retainedNearby,
    )

    # 流失流量
    lostFlow = affectedFlow - detourFlowFinal - retainedNearby - retainedMidtrip

    # 费用计算（万元）
    originalControlFee = refTotalFlow * conControlFee / 10000
    unaffectedControlFee = unaffectedFlow * conControlFee / 10000
    detourControlFeeFinal = detourFlowFinal * otherControlFee / 10000
    retainedNearbyControlFee = retainedNearby * detourUnitControlLossFee / 10000
    retainedMidtripControlFee = retainedMidtrip * midUnitControlLossFee / 10000
    lostControlFee = lostFlow * conControlFee / 10000

    row.update({
        "original_path_fee": originalPathFee,
        "ref_total_flow": refTotalFlow,
        "unaffected_flow": unaffectedFlow,
        "affected_flow": affectedFlow,
        "detour_flow_final": detourFlowFinal,
        "retained_nearby": retainedNearby,
        "retained_midtrip": retainedMidtrip,
        "lost_flow": lostFlow,
        "original_control_fee": originalControlFee,
        "unaffected_control_fee": unaffectedControlFee,
        "detour_control_fee_final": detourControlFeeFinal,
        "retained_nearby_control_fee": retainedNearbyControlFee,
        "retained_midtrip_control_fee": retainedMidtripControlFee,
        "lost_control_fee": lostControlFee,
    })
    return row


_SUMMARY_SUM_FIELDS = [
    "ref_total_flow", "unaffected_flow", "affected_flow",
    "detour_flow_final", "retained_nearby", "retained_midtrip", "lost_flow",
    "original_control_fee", "unaffected_control_fee", "detour_control_fee_final",
    "retained_nearby_control_fee", "retained_midtrip_control_fee", "lost_control_fee",
]


def _step5_aggregate_summaries(
    records: list[ImpactSummaryRecord],
) -> tuple[list[OdsSummaryRecord], list[SectionSummaryRecord]]:
    """步骤5: OD汇总表 + 路段汇总表"""
    # OD汇总: 按 (enid, exid)
    odsAgg: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {f: 0 for f in _SUMMARY_SUM_FIELDS}
    )
    # 路段汇总: 按 section_od
    sectionAgg: dict[str, dict[str, float]] = defaultdict(
        lambda: {f: 0 for f in _SUMMARY_SUM_FIELDS}
    )

    for rec in records:
        odsKey = (rec.enid, rec.exid)
        sectionKey = rec.section_od or ""

        for f in _SUMMARY_SUM_FIELDS:
            odsAgg[odsKey][f] += getattr(rec, f)
            sectionAgg[sectionKey][f] += getattr(rec, f)

    odsRecords = [
        OdsSummaryRecord(enid=enid, exid=exid, **v)
        for (enid, exid), v in sorted(odsAgg.items())
    ]
    sectionRecords = [
        SectionSummaryRecord(section_od=sectionOd, **v)
        for sectionOd, v in sorted(sectionAgg.items()) if sectionOd
    ]

    return odsRecords, sectionRecords


def _write_csv(
    records: list,
    columns: list[str],
    aliases: dict[str, str],
    output_path: str,
) -> None:
    """写入 CSV，使用中文列名"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for rec in records:
            if isinstance(rec, dict):
                row = rec
            else:
                row = rec.model_dump()
            # 替换为中文列名
            aliasedRow = {aliases.get(k, k): v for k, v in row.items()}
            writer.writerow(aliasedRow)


class ImpactSummaryService(LoggerMixin):
    """动态测算综合汇总服务：步骤1-5"""

    def run(
        self,
        raw_records: list[AffectedOdPathRecord],
        mid_data: list[MidTripExitFlowStatRecord],
        detour_data: list[DetourFlowStatRecord],
        output_path: Optional[str] = None,
        ods_output_path: Optional[str] = None,
        section_output_path: Optional[str] = None,
    ) -> tuple[list[ImpactSummaryRecord], list[OdsSummaryRecord], list[SectionSummaryRecord]]:
        """
        执行动态测算步骤1-5。

        Args:
            raw_records: 流程1输出的原始记录
            mid_data: 流程2输出的流量统计记录
            detour_data: 流程3输出的流量统计记录
            output_path: 汇总基础表 CSV 路径
            ods_output_path: OD汇总表 CSV 路径
            section_output_path: 路段汇总表 CSV 路径

        Returns:
            (汇总基础表记录, OD汇总表记录, 路段汇总表记录)
        """
        start_time = time.time()
        logger.info("开始动态测算综合汇总...")

        # Step 1: 流程1聚合 + 透视
        flow1_agg = _step1_aggregate_flow1(raw_records)
        logger.info(f"步骤1完成: {len(flow1_agg)} 个组")

        # Step 2: 流程2/3聚合
        flow2_lookup = _step2_aggregate_flow2(mid_data)
        flow3_lookup = _step2_aggregate_flow3(detour_data)
        logger.info(f"步骤2完成: flow2={len(flow2_lookup)} 条, flow3={len(flow3_lookup)} 条")

        # Step 3: Left Join + Step 4: 派生计算
        records: list[ImpactSummaryRecord] = []
        for key in sorted(flow1_agg.keys()):
            enid, exid, vehicleType, sectionOd = key
            flow1 = flow1_agg[key]
            joinKey = (enid, exid, vehicleType)
            mid = flow2_lookup.get(joinKey, _MID_DEFAULTS)
            detour = flow3_lookup.get(joinKey, _DETOUR_DEFAULTS)

            # 合并所有字段
            merged = {**flow1, **mid, **detour}

            # 步骤4: 派生计算
            merged = _step4_derive_calculations(merged)

            merged["enid"] = enid
            merged["exid"] = exid
            merged["vehicle_type"] = vehicleType
            merged["section_od"] = sectionOd or None

            records.append(ImpactSummaryRecord(**merged))

        logger.info(f"步骤3-4完成: {len(records)} 条汇总基础表记录")

        # Step 5: 汇总
        odsRecords, sectionRecords = _step5_aggregate_summaries(records)
        logger.info(f"步骤5完成: OD汇总={len(odsRecords)} 条, 路段汇总={len(sectionRecords)} 条")

        # 写入 CSV
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")

        if output_path is None:
            output_path = os.path.join(OUTPUT_DIR, f"impact_summary_{ts}.csv")
        _write_csv(records, IMPACT_SUMMARY_CSV_COLUMNS, _CSV_COLUMN_ALIASES, output_path)
        logger.info(f"汇总基础表已写入: {output_path}")

        if ods_output_path is None:
            ods_output_path = os.path.join(OUTPUT_DIR, f"ods_summary_{ts}.csv")
        _write_csv(odsRecords, ODS_SUMMARY_CSV_COLUMNS, _CSV_COLUMN_ALIASES, ods_output_path)
        logger.info(f"OD汇总表已写入: {ods_output_path}")

        if section_output_path is None:
            section_output_path = os.path.join(OUTPUT_DIR, f"section_summary_{ts}.csv")
        _write_csv(sectionRecords, SECTION_SUMMARY_CSV_COLUMNS, _CSV_COLUMN_ALIASES, section_output_path)
        logger.info(f"路段汇总表已写入: {section_output_path}")

        elapsed = time.time() - start_time
        logger.info(f"动态测算综合汇总完成，耗时 {elapsed:.2f}s")

        return records, odsRecords, sectionRecords
