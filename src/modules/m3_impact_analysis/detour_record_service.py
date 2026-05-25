"""
M3 交通影响分析 - 绕行记录检测 服务

流程3：基于受影响OD，检测因施工绕行的车辆记录
两步走：OD分类 → 每日CSV扫描+pgRouting路径验证

OD分类逻辑：
- 对每个OD(O,D)，检查O/D到施工收费单元的最短路径节点数
- O靠近施工 → OD放入"找D判定O"列表（exid=D, enid≠O, 查enid→O路径）
- D靠近施工 → OD放入"找O判定D"列表（enid=O, exid≠D, 查exid→D路径）

记录检测逻辑：
- "找D判定O"：exid=D但enid≠O的记录，查enid→O最短路径，
  路径含施工段且施工段数 < maxConstructionSections 则保留
- "找O判定D"：enid=O但exid≠D的记录，查exid→D最短路径，
  路径含施工段且施工段数 < maxConstructionSections 则保留
"""

import csv
import os
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.modules.m3_impact_analysis.analysis_schema import (
    DetourFlowStatRecord,
    DetourRecordParams,
    DetourRecordRecord,
    DetourRecordResult,
)
from src.modules.m3_impact_analysis.mid_trip_exit_service import (
    _parse_date,
    _get_day_files,
    _load_od_pairs_from_csv,
    _load_od_pairs_from_string,
    get_nearest_version,
)
from src.common.time_utils import to_same_period
from src.modules.m2_od_flow.csv_reader import iter_csv_batches
from src.common.toll_calculator import calculate_toll_fee

logger = get_logger(__name__)

OUTPUT_DIR = "analysis_results"


def _resolve_vehicle_type(record: dict) -> str:
    """车型取值：new_vehicletype 非空则用，为空返回 '0'"""
    vt = record.get("new_vehicletype", "").strip()
    if vt:
        return vt
    return "0"

# CSV 需提取的列
DETOUR_COLUMNS = [
    "exvehicleid", "enid", "exid", "intervalgroup",
    "new_vehicletype",
]

# CSV 输出列
DETOUR_OUTPUT_CSV_COLUMNS = [
    "od_enid", "od_exid", "record_enid", "record_exid",
    "vehicle_id", "vehicle_type", "intervalgroup", "shortest_path",
    "construction_sections_in_path", "period", "record_type",
    "loss_fee_yuan", "control_loss_fee_yuan",
]

# 流量统计汇总输出列
DETOUR_FLOW_STAT_CSV_COLUMNS = [
    "od_enid", "od_exid", "record_enid", "record_exid",
    "record_type", "vehicle_type",
    "construction_flow", "same_period_2025_flow",
    "loss_fee_yuan", "control_loss_fee_yuan",
    "sp2025_loss_fee_yuan", "sp2025_control_loss_fee_yuan",
    "section_od",
]


class PathDetail:
    """pgRouting 最短路径详情（缓存用）"""
    __slots__ = ("node_path", "construction_in_path")

    def __init__(self, node_path: list[str], construction_in_path: list[str]):
        self.node_path = node_path
        self.construction_in_path = construction_in_path


# pgRouting 路径详情缓存（模块级，跨日共享）
_path_detail_cache: dict[tuple[str, str], Optional[PathDetail]] = {}


def _query_path_detail(
    start_node: str,
    end_node: str,
    section_id_set: set[str],
    version: str,
    sql_runner,
) -> Optional[PathDetail]:
    """
    查询 start_node → end_node 的最短路径，返回路径详情。
    结果缓存避免重复查询。

    Returns:
        PathDetail if path exists, None if no path or query failure.
    """
    key = (start_node, end_node)
    if key in _path_detail_cache:
        return _path_detail_cache[key]
    try:
        rows = sql_runner.fetch_all(
            "SELECT node_path FROM find_shortest_path_pgr(:start_node, :end_node, :version)",
            {"start_node": start_node, "end_node": end_node, "version": version},
        )
        if rows and rows[0]["node_path"]:
            node_path = list(rows[0]["node_path"])
            construction_in_path = [s for s in node_path if s in section_id_set]
            detail = PathDetail(node_path=node_path, construction_in_path=construction_in_path)
        else:
            detail = None
    except Exception as e:
        logger.debug(f"pgRouting查询失败 ({start_node}→{end_node}): {e}")
        detail = None
    _path_detail_cache[key] = detail
    return detail


def _clear_path_detail_cache():
    """清空pgRouting路径详情缓存（每次run前调用）"""
    global _path_detail_cache
    _path_detail_cache = {}


# 通行费结果缓存：(intervalgroup, vehicle_type_int, fee_version) → dict 或 None
_toll_fee_cache: dict[tuple[str, int, str], Optional[dict]] = {}


def _get_toll_fee_from_cache(
    intervalgroup: str,
    vehicle_type_int: int,
    fee_version: str,
) -> Optional[dict]:
    """从缓存获取通行费结果，命中则返回（包含None表示查不到）"""
    return _toll_fee_cache.get((intervalgroup, vehicle_type_int, fee_version))


def _set_toll_fee_to_cache(
    intervalgroup: str,
    vehicle_type_int: int,
    fee_version: str,
    result: Optional[dict],
) -> None:
    """设置通行费结果到缓存"""
    _toll_fee_cache[(intervalgroup, vehicle_type_int, fee_version)] = result


def _clear_toll_fee_cache():
    """清空通行费缓存（每次run前调用）"""
    global _toll_fee_cache
    _toll_fee_cache = {}


def _min_path_length_to_construction(
    node: str,
    section_id_set: set[str],
    max_sections: int,
    version: str,
    sql_runner,
) -> Optional[int]:
    """
    计算node到所有施工收费单元的双向最短路径中最小的节点数

    对每个S ∈ section_id_set，查 node→S 和 S→node，
    返回所有路径中最小的 len(node_path)。
    如果所有路径都不可达，返回 None。
    一旦找到 len <= max_sections 的路径，提前终止。
    """
    minLen: Optional[int] = None
    for s in section_id_set:
        for start, end in [(node, s), (s, node)]:
            detail = _query_path_detail(start, end, section_id_set, version, sql_runner)
            if detail is not None:
                pathLen = len(detail.node_path)
                if minLen is None or pathLen < minLen:
                    minLen = pathLen
                    if minLen <= max_sections:
                        return minLen
    return minLen


def _classify_od_pairs(
    od_set: set[tuple[str, str]],
    section_id_set: set[str],
    max_sections: int,
    pgr_version: str,
    sql_runner,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """
    根据O/D到施工收费单元的邻近度对OD对分类

    Returns:
        (find_d_judge_o, find_o_judge_d)
        - find_d_judge_o: {D: {O1, O2, ...}}  O靠近施工的OD对，按D索引（找exid=D, enid≠O的记录）
        - find_o_judge_d: {O: {D1, D2, ...}}  D靠近施工的OD对，按O索引（找enid=O, exid≠D的记录）
    """
    find_d_judge_o: dict[str, set[str]] = defaultdict(set)  # D → {O1, O2, ...}
    find_o_judge_d: dict[str, set[str]] = defaultdict(set)  # O → {D1, D2, ...}

    # 缓存已计算的节点邻近度
    node_closeness: dict[str, bool] = {}

    for o, d in od_set:
        # 检查O是否靠近施工
        if o not in node_closeness:
            minLen = _min_path_length_to_construction(o, section_id_set, max_sections, pgr_version, sql_runner)
            node_closeness[o] = minLen is not None and minLen <= max_sections
        if node_closeness[o]:
            find_d_judge_o[d].add(o)  # O靠近施工 → D索引下记录O

        # 检查D是否靠近施工
        if d not in node_closeness:
            minLen = _min_path_length_to_construction(d, section_id_set, max_sections, pgr_version, sql_runner)
            node_closeness[d] = minLen is not None and minLen <= max_sections
        if node_closeness[d]:
            find_o_judge_d[o].add(d)  # D靠近施工 → O索引下记录D

    logger.info(
        f"OD分类完成: 找D判定O {sum(len(v) for v in find_d_judge_o.values())} 对, "
        f"找O判定D {sum(len(v) for v in find_o_judge_d.values())} 对"
    )

    return dict(find_d_judge_o), dict(find_o_judge_d)


def _check_and_write_record(
    record: dict,
    find_d_judge_o: dict[str, set[str]],
    find_o_judge_d: dict[str, set[str]],
    section_id_set: set[str],
    max_construction_sections: int,
    pgr_version: str,
    sql_runner,
    csv_writer: csv.DictWriter,
    period: str,
    vehicle_type: str,
    construction_flow_agg: dict[tuple[str, str, str, str, str, str], int],
    sp_flow_agg: dict[tuple[str, str, str, str, str, str], int],
    fee_version: str,
    construction_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = None,
    sp_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = None,
    construction_control_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = None,
    sp_control_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = None,
) -> tuple[int, int]:
    """
    检查单条记录是否为绕行记录，匹配则即时写入CSV并累加流量统计和通行费

    Args:
        vehicle_type: 解析后的车型
        construction_flow_agg: 施工期流量统计聚合字典
        construction_loss_fee_agg: 施工期通行费聚合字典

    Returns:
        (same_dest_diff_origin_count, same_origin_diff_dest_count)
    """
    sameDestCount = 0
    sameOriginCount = 0
    recordEnid = record.get("enid", "")
    recordExid = record.get("exid", "")

    # "找D判定O"：exid=D，enid≠O，查 enid→O 路径
    if recordExid in find_d_judge_o:
        for o in find_d_judge_o[recordExid]:
            if recordEnid == o and len(recordEnid) == 16:
                continue
            detail = _query_path_detail(recordEnid, o, section_id_set, pgr_version, sql_runner)
            if detail is None:
                continue
            if len(detail.construction_in_path) == 0:
                continue
            if len(detail.node_path) >= (max_construction_sections + len(detail.construction_in_path)):
                continue

            # 计算通行费（先查缓存，miss再计算）
            shortest_path_str = "|".join(detail.node_path)
            vtype_int = int(vehicle_type) if vehicle_type and vehicle_type.isdigit() else 0
            loss_fee = None
            control_loss_fee = None
            try:
                cached = _get_toll_fee_from_cache(shortest_path_str, vtype_int, fee_version)
                if cached is not None:
                    loss_fee = cached.get("fee_yuan")
                    control_loss_fee = cached.get("control_fee_yuan")
                elif shortest_path_str:
                    toll_result = calculate_toll_fee(
                        enid="",
                        exid="",
                        intervalgroup=shortest_path_str,
                        vehicle_type=vtype_int,
                        version="",              # enid/exid为空，拓扑版本不生效
                        fee_version=fee_version,  # 费率版本（用于 dwd_section_path 查询）
                    )
                    loss_fee = toll_result.fee_yuan
                    control_loss_fee = toll_result.control_fee_yuan
                    _set_toll_fee_to_cache(shortest_path_str, vtype_int, fee_version, {
                        "fee_yuan": loss_fee,
                        "control_fee_yuan": control_loss_fee,
                    })
                else:
                    _set_toll_fee_to_cache(shortest_path_str, vtype_int, fee_version, None)
            except Exception as e:
                logger.debug(f"通行费计算失败: {e}")
                _set_toll_fee_to_cache(shortest_path_str, vtype_int, fee_version, None)

            detourRecord = DetourRecordRecord(
                od_enid=o,
                od_exid=recordExid,
                record_enid=recordEnid,
                record_exid=recordExid,
                vehicle_id=record.get("exvehicleid", ""),
                vehicle_type=vehicle_type,
                intervalgroup=record.get("intervalgroup", ""),
                shortest_path=shortest_path_str,
                construction_sections_in_path="|".join(detail.construction_in_path),
                period=period,
                record_type="same_dest_diff_origin",
                loss_fee_yuan=loss_fee,
                control_loss_fee_yuan=control_loss_fee,
            )
            csv_writer.writerow(detourRecord.model_dump())
            sameDestCount += 1

            # 累加流量统计和通行费
            agg_key = (o, recordExid, recordEnid, recordExid, "same_dest_diff_origin", vehicle_type)
            if period == "construction":
                if construction_flow_agg is not None:
                    construction_flow_agg[agg_key] += 1
                if construction_loss_fee_agg is not None and loss_fee is not None:
                    construction_loss_fee_agg[agg_key] += loss_fee
                if construction_control_loss_fee_agg is not None and control_loss_fee is not None:
                    construction_control_loss_fee_agg[agg_key] += control_loss_fee
            else:
                if sp_flow_agg is not None:
                    sp_flow_agg[agg_key] += 1
                if sp_loss_fee_agg is not None and loss_fee is not None:
                    sp_loss_fee_agg[agg_key] += loss_fee
                if sp_control_loss_fee_agg is not None and control_loss_fee is not None:
                    sp_control_loss_fee_agg[agg_key] += control_loss_fee

    # "找O判定D"：enid=O，exid≠D，查 exid→D 路径
    if recordEnid in find_o_judge_d:
        for d in find_o_judge_d[recordEnid]:
            if recordExid == d and len(recordExid) == 16:
                continue
            detail = _query_path_detail(recordExid, d, section_id_set, pgr_version, sql_runner)
            if detail is None:
                continue
            if len(detail.construction_in_path) == 0:
                continue
            if len(detail.node_path) >= (max_construction_sections + len(detail.construction_in_path)):
                continue

            # 计算通行费（先查缓存，miss再计算）
            shortest_path_str = "|".join(detail.node_path)
            vtype_int = int(vehicle_type) if vehicle_type and vehicle_type.isdigit() else 0
            loss_fee = None
            control_loss_fee = None
            try:
                cached = _get_toll_fee_from_cache(shortest_path_str, vtype_int, fee_version)
                if cached is not None:
                    loss_fee = cached.get("fee_yuan")
                    control_loss_fee = cached.get("control_fee_yuan")
                elif shortest_path_str:
                    toll_result = calculate_toll_fee(
                        enid="",
                        exid="",
                        intervalgroup=shortest_path_str,
                        vehicle_type=vtype_int,
                        version="",              # enid/exid为空，拓扑版本不生效
                        fee_version=fee_version,  # 费率版本（用于 dwd_section_path 查询）
                    )
                    loss_fee = toll_result.fee_yuan
                    control_loss_fee = toll_result.control_fee_yuan
                    _set_toll_fee_to_cache(shortest_path_str, vtype_int, fee_version, {
                        "fee_yuan": loss_fee,
                        "control_fee_yuan": control_loss_fee,
                    })
                else:
                    _set_toll_fee_to_cache(shortest_path_str, vtype_int, fee_version, None)
            except Exception as e:
                logger.debug(f"通行费计算失败: {e}")
                _set_toll_fee_to_cache(shortest_path_str, vtype_int, fee_version, None)

            detourRecord = DetourRecordRecord(
                od_enid=recordEnid,
                od_exid=d,
                record_enid=recordEnid,
                record_exid=recordExid,
                vehicle_id=record.get("exvehicleid", ""),
                vehicle_type=vehicle_type,
                intervalgroup=record.get("intervalgroup", ""),
                shortest_path=shortest_path_str,
                construction_sections_in_path="|".join(detail.construction_in_path),
                period=period,
                record_type="same_origin_diff_dest",
                loss_fee_yuan=loss_fee,
                control_loss_fee_yuan=control_loss_fee,
            )
            csv_writer.writerow(detourRecord.model_dump())
            sameOriginCount += 1

            # 累加流量统计和通行费
            agg_key = (recordEnid, d, recordEnid, recordExid, "same_origin_diff_dest", vehicle_type)
            if period == "construction":
                if construction_flow_agg is not None:
                    construction_flow_agg[agg_key] += 1
                if construction_loss_fee_agg is not None and loss_fee is not None:
                    construction_loss_fee_agg[agg_key] += loss_fee
                if construction_control_loss_fee_agg is not None and control_loss_fee is not None:
                    construction_control_loss_fee_agg[agg_key] += control_loss_fee
            else:
                if sp_flow_agg is not None:
                    sp_flow_agg[agg_key] += 1
                if sp_loss_fee_agg is not None and loss_fee is not None:
                    sp_loss_fee_agg[agg_key] += loss_fee
                if sp_control_loss_fee_agg is not None and control_loss_fee is not None:
                    sp_control_loss_fee_agg[agg_key] += control_loss_fee

    return sameDestCount, sameOriginCount


def _average_flow_by_od_count(
    construction_flow_agg: dict[tuple[str, str, str, str, str, str], int],
    sp_flow_agg: dict[tuple[str, str, str, str, str, str], int],
    construction_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float],
    sp_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float],
    construction_control_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float],
    sp_control_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float],
) -> tuple[
    dict[tuple[str, str, str, str, str, str], float],
    dict[tuple[str, str, str, str, str, str], float],
    dict[tuple[str, str, str, str, str, str], float],
    dict[tuple[str, str, str, str, str, str], float],
    dict[tuple[str, str, str, str, str, str], float],
    dict[tuple[str, str, str, str, str, str], float],
]:
    """
    对聚合字典进行OD均分：同一 (rec_enid, rec_exid, record_type, vehicle_type)
    映射到 N 个不同 (od_enid, od_exid) 时，流量和费用各除以 N。

    除数基于两期合并计算——同一物理行程的 OD 映射关系不因期间不同而变。

    Returns:
        均分后的六个新字典
    """
    all_keys = (
        set(construction_flow_agg.keys())
        | set(sp_flow_agg.keys())
        | set(construction_loss_fee_agg.keys())
        | set(sp_loss_fee_agg.keys())
        | set(construction_control_loss_fee_agg.keys())
        | set(sp_control_loss_fee_agg.keys())
    )

    # 统计每个 (rec_enid, rec_exid, record_type, vehicle_type) 映射到多少个不同的 (od_enid, od_exid)
    od_pair_count: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for key in all_keys:
        _, _, rec_enid, rec_exid, record_type, vtype = key
        od_pair_count[(rec_enid, rec_exid, record_type, vtype)] += 1

    def _divided(src: dict[tuple, float | int]) -> dict[tuple[str, str, str, str, str, str], float]:
        result: dict[tuple[str, str, str, str, str, str], float] = {}
        for key, value in src.items():
            _, _, rec_enid, rec_exid, record_type, vtype = key
            divisor = od_pair_count[(rec_enid, rec_exid, record_type, vtype)]
            result[key] = value / divisor
        return result

    return (
        _divided(construction_flow_agg),
        _divided(sp_flow_agg),
        _divided(construction_loss_fee_agg),
        _divided(sp_loss_fee_agg),
        _divided(construction_control_loss_fee_agg),
        _divided(sp_control_loss_fee_agg),
    )


class DetourRecordService(LoggerMixin):
    """绕行记录检测 服务"""

    def run(self, params: DetourRecordParams, output_path: Optional[str] = None) -> DetourRecordResult:
        """
        运行流程3：受影响OD的绕行记录检测

        Args:
            params: 检测参数
            output_path: 输出CSV路径

        Returns:
            DetourRecordResult
        """
        start_time = time.time()
        result = DetourRecordResult(status="running")
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # 清空缓存
            _clear_path_detail_cache()
            _clear_toll_fee_cache()

            # 加载OD对
            if params.odPairsList is not None:
                od_set = set(params.odPairsList)
                logger.info(f"从参数列表加载了 {len(od_set)} 个OD对")
            elif params.affectedOdCsv:
                od_set = _load_od_pairs_from_csv(params.affectedOdCsv)
            elif params.odPairs:
                od_set = _load_od_pairs_from_string(params.odPairs)
            else:
                raise ValueError("必须指定 --affected-od-csv 或 --od-pairs 或直接传入OD对列表")

            if not od_set:
                result.status = "success"
                result.executionTime = time.time() - start_time
                logger.info("无OD对需要检测，流程结束")
                return result

            # 解析施工收费单元ID
            section_id_set: Optional[set[str]] = None
            pgr_version: Optional[str] = None
            sql_runner = None

            if params.sectionIds:
                section_id_set = set(params.sectionIds.split("|"))
                logger.info(f"施工收费单元: {section_id_set}")

                from src.common.sql_runner import get_sql_runner
                sql_runner = get_sql_runner()
                version_rows = sql_runner.fetch_all(
                    "SELECT DISTINCT version_yyyymm FROM dwd_tom_network_edges ORDER BY version_yyyymm DESC LIMIT 1"
                )
                if version_rows:
                    pgr_version = version_rows[0]["version_yyyymm"]
                    logger.info(f"pgRouting版本: {pgr_version}")
                else:
                    logger.warning("未找到pgRouting拓扑数据，跳过路径过滤")
                    section_id_set = None
                    sql_runner = None

            if not section_id_set or not pgr_version or not sql_runner:
                raise ValueError("流程3必须指定施工收费单元ID且pgRouting拓扑数据可用")

            # OD分类
            find_d_judge_o, find_o_judge_d = _classify_od_pairs(
                od_set, section_id_set, params.maxSections, pgr_version, sql_runner
            )

            if not find_d_judge_o and not find_o_judge_d:
                result.status = "success"
                result.executionTime = time.time() - start_time
                logger.info("OD分类后无符合条件的OD对，流程结束")
                return result

            # 构建预过滤集合
            exid_filter_set = set(find_d_judge_o.keys())  # "找D判定O"需要 exid=D（D是key）
            enid_filter_set = set(find_o_judge_d.keys())  # "找O判定D"需要 enid=O（O是key）

            # 确定日期范围
            startDate = _parse_date(params.startDate)
            endDate = _parse_date(params.endDate)
            sp_start = to_same_period(startDate, params.samePeriodYear)
            sp_end = to_same_period(endDate, params.samePeriodYear)

            # 输出文件
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            if output_path is None:
                ts = time.strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(OUTPUT_DIR, f"detour_record_{ts}.csv")

            # 流量统计聚合字典（双期间分别累加）
            construction_flow_agg: dict[tuple[str, str, str, str, str, str], int] = defaultdict(int)
            sp_flow_agg: dict[tuple[str, str, str, str, str, str], int] = defaultdict(int)

            # 通行费聚合字典（双期间分别累加）
            construction_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = defaultdict(float)
            sp_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = defaultdict(float)
            construction_control_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = defaultdict(float)
            sp_control_loss_fee_agg: dict[tuple[str, str, str, str, str, str], float] = defaultdict(float)

            total_scanned = 0
            total_prefiltered = 0
            total_detour = 0
            total_same_dest = 0
            total_same_origin = 0
            total_days = 0

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=DETOUR_OUTPUT_CSV_COLUMNS)
                writer.writeheader()

                # 处理两个期间
                periods = [
                    ("construction", startDate, endDate),
                    (f"same_period_{params.samePeriodYear}", sp_start, sp_end),
                ]

                for period_label, period_start, period_end in periods:
                    day_files = _get_day_files(period_start, period_end, params.dataDir)
                    logger.info(
                        f"[{period_label}] 日期范围 {period_start}~{period_end}, "
                        f"找到 {len(day_files)} 个日文件"
                    )

                    if not day_files:
                        warnings.append(f"[{period_label}] 未找到日文件")
                        continue

                    for day_date, day_file in day_files:
                        logger.info(f"[{period_label}] 处理: {os.path.basename(day_file)}")

                        day_scanned = 0
                        day_prefiltered = 0
                        day_same_dest = 0
                        day_same_origin = 0
                        
                        pgr_version = get_nearest_version(day_date.strftime("%Y%m%d"))
                        fee_version = get_nearest_version(day_date.strftime("%Y%m%d"), 'dim_section_path_version')

                        for batch in iter_csv_batches(
                            day_file, batch_size=500_000, columns=DETOUR_COLUMNS
                        ):
                            day_scanned += len(batch)
                            for record in batch:
                                rec_enid = record.get("enid", "")
                                rec_exid = record.get("exid", "")
                                if rec_enid not in enid_filter_set and rec_exid not in exid_filter_set:
                                    continue
                                day_prefiltered += 1

                                vehicle_type = _resolve_vehicle_type(record)

                                sameDestCount, sameOriginCount = _check_and_write_record(
                                    record=record,
                                    find_d_judge_o=find_d_judge_o,
                                    find_o_judge_d=find_o_judge_d,
                                    section_id_set=section_id_set,
                                    max_construction_sections=params.maxConstructionSections,
                                    pgr_version=pgr_version,
                                    sql_runner=sql_runner,
                                    csv_writer=writer,
                                    period=period_label,
                                    vehicle_type=vehicle_type,
                                    construction_flow_agg=construction_flow_agg,
                                    sp_flow_agg=sp_flow_agg,
                                    fee_version=fee_version,
                                    construction_loss_fee_agg=construction_loss_fee_agg,
                                    sp_loss_fee_agg=sp_loss_fee_agg,
                                    construction_control_loss_fee_agg=construction_control_loss_fee_agg,
                                    sp_control_loss_fee_agg=sp_control_loss_fee_agg,
                                )
                                day_same_dest += sameDestCount
                                day_same_origin += sameOriginCount

                        total_scanned += day_scanned
                        total_prefiltered += day_prefiltered
                        total_same_dest += day_same_dest
                        total_same_origin += day_same_origin
                        total_days += 1

                        day_detour = day_same_dest + day_same_origin
                        if day_detour > 0:
                            logger.info(
                                f"  扫描 {day_scanned:,} 条, 预过滤 {day_prefiltered:,} 条, "
                                f"匹配 {day_detour} 条绕行记录"
                                f" (找D判定O={day_same_dest}, 找O判定D={day_same_origin})"
                            )

            total_detour = total_same_dest + total_same_origin
            logger.info(f"结果已写入: {output_path}")
            logger.info(
                f"总计: 扫描 {total_scanned:,} 条, "
                f"预过滤 {total_prefiltered:,} 条, "
                f"匹配 {total_detour} 条绕行记录"
                f" (找D判定O={total_same_dest}, 找O判定D={total_same_origin}), "
                f"处理 {total_days} 天"
            )

            # ====== 流量均分：同一 (rec_enid, rec_exid) 对应多个 OD 对时均分流量和费用 ======
            (
                construction_flow_avg,
                sp_flow_avg,
                construction_loss_fee_avg,
                sp_loss_fee_avg,
                construction_control_loss_fee_avg,
                sp_control_loss_fee_avg,
            ) = _average_flow_by_od_count(
                construction_flow_agg,
                sp_flow_agg,
                construction_loss_fee_agg,
                sp_loss_fee_agg,
                construction_control_loss_fee_agg,
                sp_control_loss_fee_agg,
            )
            logger.info("流量均分完成")

            # ====== 流量统计汇总 ======
            flow_stat_path: Optional[str] = None
            all_keys = set(construction_flow_avg.keys()) | set(sp_flow_avg.keys())
            result_data = []
            if all_keys:
                logger.info("开始生成流量统计汇总...")
                flow_stat_path = output_path.replace(".csv", "_flow_stat.csv")

                with open(flow_stat_path, "w", newline="", encoding="utf-8") as f:
                    stat_writer = csv.DictWriter(f, fieldnames=DETOUR_FLOW_STAT_CSV_COLUMNS)
                    stat_writer.writeheader()
                    for key in sorted(all_keys):
                        od_enid, od_exid, rec_enid, rec_exid, record_type, vtype = key
                        stat_record = DetourFlowStatRecord(
                            od_enid=od_enid,
                            od_exid=od_exid,
                            record_enid=rec_enid,
                            record_exid=rec_exid,
                            record_type=record_type,
                            vehicle_type=vtype,
                            construction_flow=construction_flow_avg.get(key, 0.0),
                            same_period_2025_flow=sp_flow_avg.get(key, 0.0),
                            loss_fee_yuan=construction_loss_fee_avg.get(key, 0.0) if construction_loss_fee_avg else None,
                            control_loss_fee_yuan=construction_control_loss_fee_avg.get(key, 0.0) if construction_control_loss_fee_avg else None,
                            sp2025_loss_fee_yuan=sp_loss_fee_avg.get(key, 0.0) if sp_loss_fee_avg else None,
                            sp2025_control_loss_fee_yuan=sp_control_loss_fee_avg.get(key, 0.0) if sp_control_loss_fee_avg else None,
                        )
                        stat_writer.writerow(stat_record.model_dump())
                        result_data.append(stat_record)

                logger.info(f"流量统计汇总已写入: {flow_stat_path}, 共 {len(all_keys)} 条记录")

            execution_time = time.time() - start_time
            result.status = "success"
            result.totalRecordsScanned = total_scanned
            result.prefilteredRecords = total_prefiltered
            result.detourRecordCount = total_detour
            result.sameDestDiffOriginCount = total_same_dest
            result.sameOriginDiffDestCount = total_same_origin
            result.daysProcessed = total_days
            result.outputCsvPath = output_path
            result.flowStatCsvPath = flow_stat_path
            result.errors = errors
            result.warnings = warnings
            result.executionTime = execution_time

            logger.info(f"流程3完成，耗时 {execution_time:.2f}s")
            return result, result_data

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"流程3失败: {e}")
            errors.append(str(e))
            result.status = "failed"
            result.errors = errors
            result.warnings = warnings
            result.executionTime = execution_time
            return result
