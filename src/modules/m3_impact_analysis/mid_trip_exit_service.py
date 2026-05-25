"""
M3 交通影响分析 - 中途下站检测 服务

流程2：基于受影响OD，从原始CSV中检测中途下站车辆
采用按日滑动窗口策略，内存恒定~100MB

匹配逻辑：
同一车牌(exvehicleid)的相邻两次行程，若：
1. trip1.enid = OD.enid（第一次从OD入口进）
2. trip2.exid = OD.exid（第二次从OD出口出）
3. trip1.extime 到 trip2.entime 间隔 < 24小时
4. trip1.exid ≠ trip2.enid（排除连续两段合为一次完整行程）
5. trip1.exid → trip2.enid 最短路径经过施工收费单元（pgRouting验证）
则判定为该OD的中途下站
"""

import csv
import os
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.modules.m3_impact_analysis.analysis_schema import (
    MidTripExitParams,
    MidTripExitRecord,
    MidTripExitResult,
    MidTripExitFlowStatRecord,
)
from src.modules.m2_od_flow.csv_reader import iter_csv_batches, _detect_has_header
from src.common.toll_calculator import calculate_toll_fee
from src.common.time_utils import to_same_period

logger = get_logger(__name__)

OUTPUT_DIR = "analysis_results"


def _resolve_vehicle_type(record: dict) -> str:
    """车型取值：new_vehicletype 非空则用，为空返回 '0'"""
    vt = record.get("new_vehicletype", "").strip()
    if vt:
        return vt
    return "0"

# CSV 需提取的列
MID_TRIP_COLUMNS = [
    "exvehicleid", "enid", "exid",
    "intervalgroup", "entime", "extime",
    "new_vehicletype",
]

# CSV 输出列
MID_TRIP_CSV_COLUMNS = [
    "od_enid", "od_exid", "vehicle_id", "vehicle_type",
    "trip1_enid", "trip1_exid", "trip1_intervalgroup",
    "trip1_entime", "trip1_extime",
    "trip2_enid", "trip2_exid", "trip2_intervalgroup",
    "trip2_entime", "trip2_extime",
    "mid_path", "time_gap_hours", "period",
    "loss_fee_yuan", "control_loss_fee_yuan",
]

# 流量统计汇总输出列
MID_TRIP_FLOW_STAT_CSV_COLUMNS = [
    "od_enid", "od_exid", "vehicle_type",
    "construction_flow", "same_period_2025_flow",
    "loss_fee_yuan", "control_loss_fee_yuan",
    "sp2025_loss_fee_yuan", "sp2025_control_loss_fee_yuan",
    "section_od",
]

# 最大时间间隔
MAX_GAP = timedelta(hours=6)


def _parse_date(dateStr: str) -> date:
    """解析 YYYYMMDD 格式日期"""
    return date(int(dateStr[:4]), int(dateStr[4:6]), int(dateStr[6:8]))


def _parse_time(timeStr: str) -> datetime:
    """解析 CSV 中的时间字符串"""
    return datetime.strptime(timeStr.strip(), "%Y-%m-%d %H:%M:%S")


def _get_day_files(start: date, end: date, data_dir: str) -> list[tuple[date, str]]:
    """获取日期范围内的日文件路径列表"""
    files = []
    current = start
    while current <= end:
        month_key = current.strftime("%Y%m")
        day_file = os.path.join(data_dir, month_key, f"data_{current.strftime('%Y%m%d')}.csv")
        if os.path.exists(day_file):
            files.append((current, day_file))
        else:
            logger.warning(f"日文件不存在: {day_file}")
        current += timedelta(days=1)
    return files


def _load_od_pairs_from_csv(csv_path: str) -> set[tuple[str, str]]:
    """从流程1输出CSV读取OD对"""
    od_set = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            enid = row["enid"].strip()
            exid = row["exid"].strip()
            od_set.add((enid, exid))
    logger.info(f"从 {csv_path} 加载了 {len(od_set)} 个OD对")
    return od_set


def _load_od_pairs_from_string(od_pairs_str: str) -> set[tuple[str, str]]:
    """从字符串参数解析OD对 (enid1:exid1,enid2:exid2)"""
    od_set = set()
    for pair in od_pairs_str.split(","):
        parts = pair.strip().split(":")
        if len(parts) == 2:
            od_set.add((parts[0].strip(), parts[1].strip()))
    logger.info(f"从参数加载了 {len(od_set)} 个OD对")
    return od_set


from src.common.version_utils import get_nearest_version


def _extract_pending_trips(
    day_trips: dict[str, list[dict]], day_date: date
) -> dict[str, list[dict]]:
    """
    从当日记录中提取可能跨日匹配的待匹配行程

    保留条件：extime 在当日 06:00 之后（下次行程可能在次日）
    """
    cutoff = day_date.strftime("%Y-%m-%d") + " 18:00:00"
    pending = defaultdict(list)
    for vehicle_id, trips in day_trips.items():
        for trip in trips:
            if trip["extime"] >= cutoff:
                pending[vehicle_id].append(trip)
    return dict(pending)


# pgRouting 最短路径缓存（模块级，跨日共享）
# 值: (是否经过施工段, 路径节点列表)
_path_cache: dict[tuple[str, str], tuple[bool, list[str]]] = {}


def _check_path_through_construction(
    exid: str,
    enid: str,
    section_id_set: set[str],
    version: str,
    sql_runner,
) -> bool:
    """
    检查 exid → enid 的最短路径是否经过施工收费单元

    使用 pgRouting 查最短路径，结果和节点列表一并缓存避免重复查询
    """
    key = (exid, enid)
    if key in _path_cache:
        return _path_cache[key][0]
    try:
        rows = sql_runner.fetch_all(
            "SELECT node_path FROM find_shortest_path_pgr(:start_node, :end_node, :version)",
            {"start_node": exid, "end_node": enid, "version": version},
        )
        if rows and rows[0]["node_path"]:
            node_path = list(rows[0]["node_path"])
            result = bool(set(node_path) & section_id_set)
        else:
            node_path = []
            result = False
    except Exception as e:
        logger.debug(f"pgRouting查询失败 ({exid}→{enid}): {e}")
        node_path = []
        result = False
    _path_cache[key] = (result, node_path)
    return result


def _get_path_nodes(
    exid: str,
    enid: str,
    section_id_set: set[str],
    version: str,
    sql_runner,
) -> list[str]:
    """获取 exid → enid 的最短路径节点列表（复用 _path_cache）"""
    key = (exid, enid)
    if key in _path_cache:
        return _path_cache[key][1]
    # 未缓存，调用 _check_path_through_construction 触发查询
    _check_path_through_construction(exid, enid, section_id_set, version, sql_runner)
    return _path_cache[key][1] if key in _path_cache else []


def _clear_path_cache():
    """清空pgRouting缓存（每次run前调用）"""
    global _path_cache
    _path_cache = {}


# 通行费结果缓存：(intervalgroup, vehicle_type_int, fee_version) → TollFeeResult
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


def _match_and_write(
    pending_trips: dict[str, list[dict]],
    current_trips: dict[str, list[dict]],
    od_set: set[tuple[str, str]],
    enid_set: set[str],
    exid_set: set[str],
    csv_writer: csv.DictWriter,
    period: str,
    section_id_set: Optional[set[str]] = None,
    pgr_version: Optional[str] = None,
    fee_version: Optional[str] = None,
    sql_runner=None,
    construction_flow_agg: Optional[dict[tuple[str, str, str], int]] = None,
    sp_flow_agg: Optional[dict[tuple[str, str, str], int]] = None,
    construction_loss_fee_agg: Optional[dict[tuple[str, str, str], float]] = None,
    sp_loss_fee_agg: Optional[dict[tuple[str, str, str], float]] = None,
    construction_control_loss_fee_agg: Optional[dict[tuple[str, str, str], float]] = None,
    sp_control_loss_fee_agg: Optional[dict[tuple[str, str, str], float]] = None,
) -> int:
    """
    合并前一日pending + 当日记录，匹配中途下站模式，即时写入CSV并累加流量统计和通行费

    Args:
        construction_flow_agg: 施工期流量聚合字典 (od_enid, od_exid, vehicle_type) → count
        construction_loss_fee_agg: 施工期通行费聚合字典
        sp_flow_agg: 同流量聚合字典 (od_enid, od_exid, vehicle_type) → count

    Returns:
        匹配的记录数
    """
    match_count = 0

    # 合并所有涉及的车辆ID
    all_vehicle_ids = set(pending_trips.keys()) | set(current_trips.keys())

    for vehicle_id in all_vehicle_ids:
        # 合并 pending + 当日记录
        trips = list(pending_trips.get(vehicle_id, [])) + list(
            current_trips.get(vehicle_id, [])
        )
        trips.sort(key=lambda t: t["entime"])

        # 遍历相邻记录对
        for i in range(len(trips) - 1):
            trip1 = trips[i]
            trip2 = trips[i + 1]

            # 时间间隔检查
            try:
                t1_exit = _parse_time(trip1["extime"])
                t2_entry = _parse_time(trip2["entime"])
            except (ValueError, KeyError):
                continue

            gap = t2_entry - t1_exit
            if gap < timedelta(0) or gap > MAX_GAP:
                continue

            # OD匹配：trip1从OD入口进，trip2从OD出口出
            od_key = (trip1["enid"], trip2["exid"])
            if od_key not in od_set:
                continue

            # trip1出口不能是trip2入口（排除连续两段合为一次完整行程的情况）
            if trip1["exid"] == trip2["enid"]:
                continue

            # pgRouting验证：trip1.exid → trip2.enid 最短路径需经过施工收费单元
            if section_id_set and pgr_version and sql_runner:
                if not _check_path_through_construction(
                    trip1["exid"], trip2["enid"],
                    section_id_set, pgr_version, sql_runner,
                ):
                    continue

            vtype = _resolve_vehicle_type(trip1)

            # 获取 trip1.exid → trip2.enid 的最短路径（复用 _path_cache）
            if section_id_set and pgr_version and sql_runner:
                mid_path_nodes = _get_path_nodes(
                    trip1["exid"], trip2["enid"],
                    section_id_set, pgr_version, sql_runner,
                )
                mid_path_str = "|".join(mid_path_nodes)
            else:
                mid_path_str = ""

            # 计算通行费（先查缓存，miss再计算）
            vtype_int = int(vtype) if vtype and vtype.isdigit() else 0
            loss_fee = None
            control_loss_fee = None
            try:
                cached = _get_toll_fee_from_cache(mid_path_str, vtype_int, fee_version)
                if cached is not None:
                    loss_fee = cached.get("fee_yuan")
                    control_loss_fee = cached.get("control_fee_yuan")
                elif mid_path_str:
                    toll_result = calculate_toll_fee(
                        enid="",
                        exid="",
                        intervalgroup=mid_path_str,
                        vehicle_type=vtype_int,
                        version="",          # enid/exid为空，拓扑版本不生效
                        fee_version=fee_version,  # 费率版本（用于 dwd_section_path 查询）
                    )
                    loss_fee = toll_result.fee_yuan
                    control_loss_fee = toll_result.control_fee_yuan
                    _set_toll_fee_to_cache(mid_path_str, vtype_int, fee_version, {
                        "fee_yuan": loss_fee,
                        "control_fee_yuan": control_loss_fee,
                    })
                else:
                    _set_toll_fee_to_cache(mid_path_str, vtype_int, fee_version, None)
            except Exception as e:
                logger.debug(f"通行费计算失败: {e}")
                _set_toll_fee_to_cache(mid_path_str, vtype_int, fee_version, None)

            record = MidTripExitRecord(
                od_enid=trip1["enid"],
                od_exid=trip2["exid"],
                vehicle_id=vehicle_id,
                vehicle_type=vtype,
                trip1_enid=trip1["enid"],
                trip1_exid=trip1["exid"],
                trip1_intervalgroup=trip1.get("intervalgroup", ""),
                trip1_entime=trip1["entime"],
                trip1_extime=trip1["extime"],
                trip2_enid=trip2["enid"],
                trip2_exid=trip2["exid"],
                trip2_intervalgroup=trip2.get("intervalgroup", ""),
                trip2_entime=trip2["entime"],
                trip2_extime=trip2["extime"],
                mid_path=mid_path_str,
                time_gap_hours=round(gap.total_seconds() / 3600, 2),
                period=period,
                loss_fee_yuan=loss_fee,
                control_loss_fee_yuan=control_loss_fee,
            )
            csv_writer.writerow(record.model_dump())
            match_count += 1

            # 累加流量统计和通行费
            agg_key = (trip1["enid"], trip2["exid"], vtype)
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

    return match_count


class MidTripExitService(LoggerMixin):
    """中途下站检测 服务"""

    def run(self, params: MidTripExitParams, output_path: Optional[str] = None) -> MidTripExitResult:
        """
        运行流程2：受影响OD的中途下站检测

        Args:
            params: 检测参数
            output_path: 输出CSV路径

        Returns:
            MidTripExitResult
        """
        start_time = time.time()
        result = MidTripExitResult(status="running")
        errors = []
        warnings = []

        try:
            # 清空缓存
            _clear_path_cache()
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

            enid_set = {enid for enid, _ in od_set}
            exid_set = {exid for _, exid in od_set}

            # 解析施工收费单元ID（用于pgRouting路径过滤）
            section_id_set: Optional[set[str]] = None
            pgr_version: Optional[str] = None
            sql_runner = None

            if params.sectionIds:
                section_id_set = set(params.sectionIds.split("|"))
                logger.info(f"施工收费单元: {section_id_set}")

                from src.common.sql_runner import get_sql_runner
                sql_runner = get_sql_runner()

            # 确定日期范围
            startDate = _parse_date(params.startDate)
            endDate = _parse_date(params.endDate)
            sp_start = to_same_period(startDate, params.samePeriodYear)
            sp_end = to_same_period(endDate, params.samePeriodYear)

            # 输出文件
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            if output_path is None:
                ts = time.strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(OUTPUT_DIR, f"mid_trip_exit_{ts}.csv")

            # 流量统计聚合字典
            construction_flow_agg: dict[tuple[str, str, str], int] = defaultdict(int)
            sp_flow_agg: dict[tuple[str, str, str], int] = defaultdict(int)

            # 通行费聚合字典（分别累加施工期间和同期）
            construction_loss_fee_agg: dict[tuple[str, str, str], float] = defaultdict(float)
            sp_loss_fee_agg: dict[tuple[str, str, str], float] = defaultdict(float)
            construction_control_loss_fee_agg: dict[tuple[str, str, str], float] = defaultdict(float)
            sp_control_loss_fee_agg: dict[tuple[str, str, str], float] = defaultdict(float)

            total_scanned = 0
            total_matched_scanned = 0
            total_mid_trip = 0
            total_days = 0

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=MID_TRIP_CSV_COLUMNS)
                writer.writeheader()

                # 处理两个期间
                periods = [
                    ("construction", startDate, endDate),
                    (f"same_period_{params.samePeriodYear}", sp_start, sp_end),
                ]

                for period_label, period_start, period_end in periods:
                    # 扩展1天边界
                    ext_start = period_start - timedelta(days=1)
                    ext_end = period_end

                    day_files = _get_day_files(ext_start, ext_end, params.dataDir)
                    logger.info(
                        f"[{period_label}] 日期范围 {ext_start}~{ext_end}, "
                        f"找到 {len(day_files)} 个日文件"
                    )

                    if not day_files:
                        warnings.append(f"[{period_label}] 未找到日文件")
                        continue

                    # 按日滑动窗口处理
                    pending_trips: dict[str, list[dict]] = {}
                    
                    i = 0

                    for day_date, day_file in day_files:
                        logger.info(f"[{period_label}] 处理: {os.path.basename(day_file)}")

                        # 读取当日匹配记录
                        current_trips: dict[str, list[dict]] = defaultdict(list)
                        day_scanned = 0
                        day_matched = 0
                        
                        pgr_version = get_nearest_version(day_date.strftime("%Y%m%d"))
                        fee_version = get_nearest_version(day_date.strftime("%Y%m%d"), 'dim_section_path_version')

                        for batch in iter_csv_batches(
                            day_file, batch_size=500_000, columns=MID_TRIP_COLUMNS
                        ):
                            day_scanned += len(batch)
                            for record in batch:
                                if (
                                    record.get("enid") in enid_set
                                    or record.get("exid") in exid_set
                                ):
                                    current_trips[record["exvehicleid"]].append(record)
                                    day_matched += 1

                        total_scanned += day_scanned
                        total_matched_scanned += day_matched
                        total_days += 1

                        logger.info(
                            f"  扫描 {day_scanned:,} 条, 过滤 {day_matched:,} 条, "
                            f"涉及 {len(current_trips)} 辆车"
                        )
                        
                        if i == 0:
                            i += 1
                            pending_trips = _extract_pending_trips(current_trips, day_date)
                            continue

                        # 匹配中途下站
                        match_count = _match_and_write(
                            pending_trips=pending_trips,
                            current_trips=current_trips,
                            od_set=od_set,
                            enid_set=enid_set,
                            exid_set=exid_set,
                            csv_writer=writer,
                            period=period_label,
                            section_id_set=section_id_set,
                            pgr_version=pgr_version,
                            fee_version=fee_version,
                            sql_runner=sql_runner,
                            construction_flow_agg=construction_flow_agg,
                            sp_flow_agg=sp_flow_agg,
                            construction_loss_fee_agg=construction_loss_fee_agg,
                            sp_loss_fee_agg=sp_loss_fee_agg,
                            construction_control_loss_fee_agg=construction_control_loss_fee_agg,
                            sp_control_loss_fee_agg=sp_control_loss_fee_agg,
                        )
                        total_mid_trip += match_count

                        if match_count > 0:
                            logger.info(f"  匹配到 {match_count} 条中途下站记录")

                        # 提取当日待匹配行程（用于与次日匹配）
                        pending_trips = _extract_pending_trips(current_trips, day_date)

            logger.info(f"结果已写入: {output_path}")
            logger.info(
                f"总计: 扫描 {total_scanned:,} 条, "
                f"过滤 {total_matched_scanned:,} 条, "
                f"匹配 {total_mid_trip} 条中途下站, "
                f"处理 {total_days} 天"
            )

            # ====== 流量统计汇总 ======
            flow_stat_path: Optional[str] = None
            result_data = []
            if construction_flow_agg or sp_flow_agg:
                flow_stat_path = output_path.replace(".csv", "_flow_stat.csv")
                all_keys = set(construction_flow_agg.keys()) | set(sp_flow_agg.keys())

                with open(flow_stat_path, "w", newline="", encoding="utf-8") as f:
                    stat_writer = csv.DictWriter(f, fieldnames=MID_TRIP_FLOW_STAT_CSV_COLUMNS)
                    stat_writer.writeheader()
                    for (od_enid, od_exid, vtype) in sorted(all_keys):
                        stat_record = MidTripExitFlowStatRecord(
                            od_enid=od_enid,
                            od_exid=od_exid,
                            vehicle_type=vtype,
                            construction_flow=construction_flow_agg.get((od_enid, od_exid, vtype), 0),
                            same_period_2025_flow=sp_flow_agg.get((od_enid, od_exid, vtype), 0),
                            loss_fee_yuan=construction_loss_fee_agg.get((od_enid, od_exid, vtype), 0.0) if construction_loss_fee_agg else None,
                            control_loss_fee_yuan=construction_control_loss_fee_agg.get((od_enid, od_exid, vtype), 0.0) if construction_control_loss_fee_agg else None,
                            sp2025_loss_fee_yuan=sp_loss_fee_agg.get((od_enid, od_exid, vtype), 0.0) if sp_loss_fee_agg else None,
                            sp2025_control_loss_fee_yuan=sp_control_loss_fee_agg.get((od_enid, od_exid, vtype), 0.0) if sp_control_loss_fee_agg else None,
                        )
                        stat_writer.writerow(stat_record.model_dump())
                        result_data.append(stat_record)

                logger.info(f"流量统计汇总已写入: {flow_stat_path}, 共 {len(all_keys)} 条记录")

            execution_time = time.time() - start_time
            result.status = "success"
            result.totalRecordsScanned = total_scanned
            result.matchedRecordsScanned = total_matched_scanned
            result.midTripExitCount = total_mid_trip
            result.daysProcessed = total_days
            result.outputCsvPath = output_path
            result.flowStatCsvPath = flow_stat_path
            result.errors = errors
            result.warnings = warnings
            result.executionTime = execution_time

            logger.info(f"流程2完成，耗时 {execution_time:.2f}s")
            return result, result_data

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"流程2失败: {e}")
            errors.append(str(e))
            result.status = "failed"
            result.errors = errors
            result.warnings = warnings
            result.executionTime = execution_time
            return result
