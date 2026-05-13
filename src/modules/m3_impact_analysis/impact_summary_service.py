"""
M3 交通影响分析 - 综合汇总服务

将流程1（受影响OD流量）、流程2（中途下站检测）、流程3（绕行记录检测）的输出数据
按 (enid, exid, vehicle_type) 维度合并，生成综合汇总 CSV。

处理步骤：
1. 流程1 raw_records 按 (enid, exid, vehicle_type) × is_affected 聚合
   - 受影响/非受影响 path 分别求均值(费用)和求和(流量)
   - 均值 × 流量 估算费用
2. 关联流程2中途下站数据 (mid_ 前缀)
3. 关联流程3绕行数据 — 先按 (od_enid, od_exid, vehicle_type) 汇总再匹配 (detour_ 前缀)
4. 输出 CSV
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
)

logger = get_logger(__name__)

OUTPUT_DIR = "analysis_results"

# 输出 CSV 列名（与 ImpactSummaryRecord 字段一一对应）
IMPACT_SUMMARY_CSV_COLUMNS = [
    "enid", "exid", "vehicle_type",
    "avg_con_fee", "avg_con_control_fee",
    "avg_other_fee", "avg_other_control_fee",
    "sp2025_con_flow", "con_construction_flow",
    "sp2025_other_flow", "other_construction_flow",
    "sp2025_con_fee", "sp2025_other_fee",
    "con_construction_fee", "other_construction_fee",
    "sp2025_con_control_fee", "sp2025_other_control_fee",
    "con_construction_control_fee", "other_construction_control_fee",
    "mid_construction_flow", "mid_same_period_2025_flow",
    "mid_loss_fee_yuan", "mid_control_loss_fee_yuan",
    "mid_sp2025_loss_fee_yuan", "mid_sp2025_control_loss_fee_yuan",
    "detour_construction_flow", "detour_same_period_2025_flow",
    "detour_loss_fee_yuan", "detour_control_loss_fee_yuan",
    "detour_sp2025_loss_fee_yuan", "detour_sp2025_control_loss_fee_yuan",
]


def _safe_mean(values: list[Optional[float]]) -> float:
    """对非 None 的值求均值，全部为 None 则返回 0.0"""
    valid = [v for v in values if v is not None]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def _safe_sum_int(values: list[Optional[int]]) -> int:
    """对非 None 的整数值求和"""
    return sum(v for v in values if v is not None)


def _aggregate_flow1_records(
    raw_records: list[AffectedOdPathRecord],
) -> dict[tuple[str, str, str], dict]:
    """
    对流程1 raw_records 按 (enid, exid, vehicle_type) 聚合，
    分别处理 is_affected=True 和 is_affected=False 子组。

    Returns:
        {(enid, exid, vehicle_type): {聚合字段...}}
    """
    # 按 key + is_affected 分组收集原始值
    grouped: dict[tuple[str, str, str], dict[str, list]] = defaultdict(
        lambda: {
            "con_fee_yuan": [],
            "con_control_fee_yuan": [],
            "con_2025_flow": [],
            "con_construction_flow": [],
            "other_fee_yuan": [],
            "other_control_fee_yuan": [],
            "other_2025_flow": [],
            "other_construction_flow": [],
        }
    )

    for rec in raw_records:
        key = (rec.enid, rec.exid, rec.vehicle_type)
        g = grouped[key]
        if rec.is_affected:
            g["con_fee_yuan"].append(rec.fee_yuan)
            g["con_control_fee_yuan"].append(rec.control_fee_yuan)
            g["con_2025_flow"].append(rec.same_period_2025_flow)
            g["con_construction_flow"].append(rec.construction_flow)
        else:
            g["other_fee_yuan"].append(rec.fee_yuan)
            g["other_control_fee_yuan"].append(rec.control_fee_yuan)
            g["other_2025_flow"].append(rec.same_period_2025_flow)
            g["other_construction_flow"].append(rec.construction_flow)

    # 计算聚合结果
    result: dict[tuple[str, str, str], dict] = {}
    for key, g in grouped.items():
        avg_con_fee = _safe_mean(g["con_fee_yuan"])
        avg_con_control_fee = _safe_mean(g["con_control_fee_yuan"])
        avg_other_fee = _safe_mean(g["other_fee_yuan"])
        avg_other_control_fee = _safe_mean(g["other_control_fee_yuan"])

        sp2025_con_flow = _safe_sum_int(g["con_2025_flow"])
        con_construction_flow = _safe_sum_int(g["con_construction_flow"])
        sp2025_other_flow = _safe_sum_int(g["other_2025_flow"])
        other_construction_flow = _safe_sum_int(g["other_construction_flow"])

        result[key] = {
            "avg_con_fee": avg_con_fee,
            "avg_con_control_fee": avg_con_control_fee,
            "avg_other_fee": avg_other_fee,
            "avg_other_control_fee": avg_other_control_fee,
            "sp2025_con_flow": sp2025_con_flow,
            "con_construction_flow": con_construction_flow,
            "sp2025_other_flow": sp2025_other_flow,
            "other_construction_flow": other_construction_flow,
            "sp2025_con_fee": avg_con_fee * sp2025_con_flow,
            "sp2025_other_fee": avg_con_fee * sp2025_other_flow,
            "con_construction_fee": avg_con_fee * con_construction_flow,
            "other_construction_fee": avg_con_fee * other_construction_flow,
            "sp2025_con_control_fee": avg_con_control_fee * sp2025_con_flow,
            "sp2025_other_control_fee": avg_con_control_fee * sp2025_other_flow,
            "con_construction_control_fee": avg_con_control_fee * con_construction_flow,
            "other_construction_control_fee": avg_con_control_fee * other_construction_flow,
        }

    return result


def _build_mid_trip_lookup(
    mid_data: list[MidTripExitFlowStatRecord],
) -> dict[tuple[str, str, str], dict]:
    """
    将流程2数据构建为 {(od_enid, od_exid, vehicle_type): {字段...}} 查找表。
    """
    lookup: dict[tuple[str, str, str], dict] = {}
    for rec in mid_data:
        key = (rec.od_enid, rec.od_exid, rec.vehicle_type)
        lookup[key] = {
            "mid_construction_flow": rec.construction_flow,
            "mid_same_period_2025_flow": rec.same_period_2025_flow,
            "mid_loss_fee_yuan": rec.loss_fee_yuan,
            "mid_control_loss_fee_yuan": rec.control_loss_fee_yuan,
            "mid_sp2025_loss_fee_yuan": rec.sp2025_loss_fee_yuan,
            "mid_sp2025_control_loss_fee_yuan": rec.sp2025_control_loss_fee_yuan,
        }
    return lookup


def _aggregate_and_build_detour_lookup(
    detour_data: list[DetourFlowStatRecord],
) -> dict[tuple[str, str, str], dict]:
    """
    将流程3数据先按 (od_enid, od_exid, vehicle_type) 汇总，
    再构建为查找表。
    """
    agg: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: {
            "construction_flow": 0.0,
            "same_period_2025_flow": 0.0,
            "loss_fee_yuan": 0.0,
            "control_loss_fee_yuan": 0.0,
            "sp2025_loss_fee_yuan": 0.0,
            "sp2025_control_loss_fee_yuan": 0.0,
        }
    )

    for rec in detour_data:
        key = (rec.od_enid, rec.od_exid, rec.vehicle_type)
        a = agg[key]
        a["construction_flow"] += rec.construction_flow or 0.0
        a["same_period_2025_flow"] += rec.same_period_2025_flow or 0.0
        a["loss_fee_yuan"] += rec.loss_fee_yuan or 0.0
        a["control_loss_fee_yuan"] += rec.control_loss_fee_yuan or 0.0
        a["sp2025_loss_fee_yuan"] += rec.sp2025_loss_fee_yuan or 0.0
        a["sp2025_control_loss_fee_yuan"] += rec.sp2025_control_loss_fee_yuan or 0.0

    # 转换为带前缀的查找表
    lookup: dict[tuple[str, str, str], dict] = {}
    for key, a in agg.items():
        lookup[key] = {
            "detour_construction_flow": a["construction_flow"],
            "detour_same_period_2025_flow": a["same_period_2025_flow"],
            "detour_loss_fee_yuan": a["loss_fee_yuan"],
            "detour_control_loss_fee_yuan": a["control_loss_fee_yuan"],
            "detour_sp2025_loss_fee_yuan": a["sp2025_loss_fee_yuan"],
            "detour_sp2025_control_loss_fee_yuan": a["sp2025_control_loss_fee_yuan"],
        }
    return lookup


_MID_DEFAULTS = {
    "mid_construction_flow": 0,
    "mid_same_period_2025_flow": 0,
    "mid_loss_fee_yuan": None,
    "mid_control_loss_fee_yuan": None,
    "mid_sp2025_loss_fee_yuan": None,
    "mid_sp2025_control_loss_fee_yuan": None,
}

_DETOUR_DEFAULTS = {
    "detour_construction_flow": 0.0,
    "detour_same_period_2025_flow": 0.0,
    "detour_loss_fee_yuan": None,
    "detour_control_loss_fee_yuan": None,
    "detour_sp2025_loss_fee_yuan": None,
    "detour_sp2025_control_loss_fee_yuan": None,
}


class ImpactSummaryService(LoggerMixin):
    """综合汇总服务：合并流程1/2/3输出数据"""

    def run(
        self,
        raw_records: list[AffectedOdPathRecord],
        mid_data: list[MidTripExitFlowStatRecord],
        detour_data: list[DetourFlowStatRecord],
        output_path: Optional[str] = None,
    ) -> list[ImpactSummaryRecord]:
        """
        执行综合汇总，返回 ImpactSummaryRecord 列表并写入 CSV。

        Args:
            raw_records: 流程1输出的原始记录
            mid_data: 流程2输出的流量统计记录
            detour_data: 流程3输出的流量统计记录
            output_path: 输出 CSV 路径（默认自动生成）

        Returns:
            ImpactSummaryRecord 列表
        """
        start_time = time.time()
        logger.info("开始综合汇总处理...")

        # Step 1: 聚合流程1数据
        flow1_agg = _aggregate_flow1_records(raw_records)
        logger.info(f"流程1聚合完成: {len(flow1_agg)} 个 (enid, exid, vehicle_type) 组合")

        # Step 2: 构建流程2查找表
        mid_lookup = _build_mid_trip_lookup(mid_data)
        logger.info(f"流程2查找表构建完成: {len(mid_lookup)} 条记录")

        # Step 3: 构建流程3查找表
        detour_lookup = _aggregate_and_build_detour_lookup(detour_data)
        logger.info(f"流程3查找表构建完成: {len(detour_lookup)} 条记录")

        # Step 4: 合并生成 ImpactSummaryRecord
        records: list[ImpactSummaryRecord] = []
        for key in sorted(flow1_agg.keys()):
            enid, exid, vehicle_type = key
            agg = flow1_agg[key]
            mid = mid_lookup.get(key, _MID_DEFAULTS)
            detour = detour_lookup.get(key, _DETOUR_DEFAULTS)

            record = ImpactSummaryRecord(
                enid=enid,
                exid=exid,
                vehicle_type=vehicle_type,
                **agg,
                **mid,
                **detour,
            )
            records.append(record)

        logger.info(f"综合汇总生成 {len(records)} 条记录")

        # Step 5: 写入 CSV
        if output_path is None:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(OUTPUT_DIR, f"impact_summary_{ts}.csv")

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=IMPACT_SUMMARY_CSV_COLUMNS)
            writer.writeheader()
            for rec in records:
                writer.writerow(rec.model_dump())

        elapsed = time.time() - start_time
        logger.info(f"综合汇总已写入: {output_path}, 耗时 {elapsed:.2f}s")

        return records
