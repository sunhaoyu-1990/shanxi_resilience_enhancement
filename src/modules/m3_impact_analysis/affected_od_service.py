"""
M3 交通影响分析 - 受影响OD查询 业务编排层

流程1：输入施工收费单元ID和施工时间段
→ 查找受影响的 OD（提取OD对集合）
→ 查询受影响OD下所有path（含受影响和不受影响的）
→ 标记is_affected、affected_section_ids
→ 多版本去重（取最新版本）
→ 查询施工期间和2025同期流量（按车型拆分）
→ 输出CSV（每行 = path × vehicle_type）
"""

import csv
import os
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.modules.m3_impact_analysis.affected_od_repository import AffectedOdRepository
from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdQueryParams,
    AffectedOdPathRecord,
    AffectedOdQueryResult,
)
from src.common.toll_calculator import calculate_toll_fee
from src.common.time_utils import to_same_period

logger = get_logger(__name__)

OUTPUT_DIR = "analysis_results"

# CSV 输出列（含 vehicle_type + 通行费）
AFFECTED_OD_CSV_COLUMNS = [
    "od_section_path_id", "enid", "exid", "numpath",
    "fixed_intervalpath", "affected_section_ids", "is_affected", "map_version",
    "vehicle_type", "construction_flow", "same_period_2025_flow",
    "fee_yuan", "total_length_meters", "control_fee_yuan", "control_length_meters",
    "section_od",
]


def _parse_date(dateStr: str) -> date:
    """解析 YYYYMMDD 格式日期"""
    return date(int(dateStr[:4]), int(dateStr[4:6]), int(dateStr[6:8]))


def _get_month_from_date(date_str: str) -> str:
    """从 YYYYMMDD 格式获取 YYYYMM 格式"""
    return date_str[:4] + date_str[4:6]


from src.common.version_utils import get_nearest_version


def _batch_calculate_toll_fee(
    raw_records: list[AffectedOdPathRecord],
    start_date: str,
    end_date: str,
) -> None:
    """
    批量计算通行费（去重优化）

    先将唯一组合去重，计算后合并回记录
    """
    # 构建唯一组合：(enid, exid, fixed_intervalpath, vehicle_type, version) -> idx
    unique_combos: dict[tuple, int] = {}
    combo_list: list[tuple] = []

    for record in raw_records:
        # 拓扑版本：根据数据日期动态获取（用于 find_shortest_path_pgr）
        pgr_version = get_nearest_version(record.map_version + '01')
        # 费率版本：直接使用 record.map_version（用于 dwd_section_path）
        fee_version = get_nearest_version(record.map_version + '01', 'dim_section_path_version')

        key = (record.enid, record.exid, record.fixed_intervalpath, record.vehicle_type, pgr_version, fee_version)
        if key not in unique_combos:
            idx = len(combo_list)
            unique_combos[key] = idx
            combo_list.append(key)

    logger.info(f"通行费计算：{len(raw_records)} 条记录 → {len(combo_list)} 个唯一组合")

    # 批量计算通行费
    toll_results: list[Optional[dict]] = [None] * len(combo_list)
    for i, (enid, exid, fixed_intervalpath, vtype, pgr_version, fee_version) in enumerate(combo_list):
        try:
            vtype_int = int(vtype) if vtype and vtype.isdigit() else 0
            toll_result = calculate_toll_fee(
                enid=enid,
                exid=exid,
                intervalgroup=fixed_intervalpath,
                vehicle_type=vtype_int,
                version=pgr_version,      # 拓扑版本（用于路径查询）
                fee_version=fee_version,  # 费率版本（用于 dwd_section_path 查询）
            )
            toll_results[i] = {
                "fee_yuan": toll_result.fee_yuan,
                "total_length_meters": toll_result.total_length_meters,
                "control_fee_yuan": toll_result.control_fee_yuan,
                "control_length_meters": toll_result.control_length_meters,
            }
        except Exception as e:
            logger.warning(f"通行费计算失败 {enid}->{exid}: {e}")
            toll_results[i] = {
                "fee_yuan": None,
                "total_length_meters": None,
                "control_fee_yuan": None,
                "control_length_meters": None,
            }

    # 合并结果回记录
    for record in raw_records:
        # 拓扑版本：根据数据日期动态获取（用于 find_shortest_path_pgr）
        pgr_version = get_nearest_version(record.map_version + '01')
        # 费率版本：直接使用 record.map_version（用于 dwd_section_path）
        fee_version = get_nearest_version(record.map_version + '01', 'dim_section_path_version')

        key = (record.enid, record.exid, record.fixed_intervalpath, record.vehicle_type, pgr_version, fee_version)
        idx = unique_combos.get(key)
        if idx is not None and toll_results[idx]:
            result = toll_results[idx]
            record.fee_yuan = result["fee_yuan"]
            record.total_length_meters = result["total_length_meters"]
            record.control_fee_yuan = result["control_fee_yuan"]
            record.control_length_meters = result["control_length_meters"]


def _get_month_list(start: date, end: date) -> list[str]:
    """获取日期范围覆盖的月份列表 (YYYYMM)"""
    months = set()
    current = start.replace(day=1)
    end_month = end.replace(day=1)
    while current <= end_month:
        months.add(current.strftime("%Y%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return sorted(months)


def _dedup_by_latest_version(rows: list[dict]) -> list[dict]:
    """
    多版本去重：同一 (enid, exid, numpath) 只保留最新版本

    如果同一path在多个版本中都受影响，合并 affected_section_ids
    """
    best: dict[tuple, dict] = {}

    for row in rows:
        key = row["id"]

        existing = best.get(key)
        if existing is None or row["version_yyyymm"] > existing["version_yyyymm"]:
            best[key] = dict(row)
        elif row["version_yyyymm"] == existing["version_yyyymm"]:
            if "affected_section_ids" in row and "affected_section_ids" in existing:
                merged = set(row["affected_section_ids"].split("|")) | set(existing["affected_section_ids"].split("|"))
                best[key]["affected_section_ids"] = "|".join(sorted(merged))
    return list(best.values())


def _mark_affected_sections(
    row: dict, section_id_list: list[str]
) -> tuple[str, bool]:
    """
    标记受影响的施工收费单元和is_affected标志

    Returns:
        (affected_section_ids, is_affected)
    """
    path_sections = set(row["fixed_intervalpath"].split("|"))
    affected = [s for s in section_id_list if s in path_sections]
    affected_str = "|".join(affected)
    is_affected = len(affected) > 0
    return affected_str, is_affected


def _query_daily_flow_by_vtype(
    repo: AffectedOdRepository,
    section_to_path_ids: dict[str, list[int]],
    daily_tables: list[tuple[str, str]],
    startDate: date,
    endDate: date,
) -> tuple[dict[tuple[int, str], int], set[str]]:
    """
    查询多个日表的流量（按vehicle_type分组）

    Returns:
        ({(path_id, vehicle_type): flow}, all_vehicle_types)
    """
    flow_results: dict[tuple[int, str], int] = defaultdict(int)
    all_vtypes: set[str] = set()

    for day_str, table_name in daily_tables:
        day_start = f"{day_str[:4]}-{day_str[4:6]}-{day_str[6:8]} 00:00:00"
        day_end = (date(int(day_str[:4]), int(day_str[4:6]), int(day_str[6:8])) + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

        for sec_id, path_ids in section_to_path_ids.items():
            if 814644 in path_ids:
                print(1)
            vtype_flow = repo.query_flow_by_vehicle_type(
                table_name=table_name,
                section_id=sec_id,
                path_id_list=path_ids,
                start_timestamp=day_start,
                end_timestamp=day_end,
            )
            for (path_id, vtype), flow in vtype_flow.items():
                if 814644 == path_id:
                    print(1)
                flow_results[(path_id, vtype)] += flow
                all_vtypes.add(vtype)

    return flow_results, all_vtypes


def _query_monthly_flow_by_vtype(
    repo: AffectedOdRepository,
    section_to_path_ids: dict[str, list[int]],
    months: list[str],
    start_ts: str,
    end_ts: str,
) -> tuple[dict[tuple[int, str], int], set[str], bool]:
    """
    查询月表的流量（按vehicle_type分组）

    Returns:
        ({(path_id, vehicle_type): flow}, all_vehicle_types, table_exists)
    """
    flow_results: dict[tuple[int, str], int] = defaultdict(int)
    all_vtypes: set[str] = set()
    table_exists = False

    for month in months:
        table_name = f"dws_section_od_path_flow_hour_{month}"
        if not repo.check_dws_table_exists(table_name):
            continue
        table_exists = True

        for sec_id, path_ids in section_to_path_ids.items():
            vtype_flow = repo.query_flow_by_vehicle_type(
                table_name=table_name,
                section_id=sec_id,
                path_id_list=path_ids,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
            )
            for (path_id, vtype), flow in vtype_flow.items():
                flow_results[(path_id, vtype)] += flow
                all_vtypes.add(vtype)

    return flow_results, all_vtypes, table_exists


class AffectedOdService(LoggerMixin):
    """受影响OD查询 服务"""

    def __init__(self):
        self.repository = AffectedOdRepository()

    def run(self, params: AffectedOdQueryParams, output_path: Optional[str] = None) -> AffectedOdQueryResult:
        """
        运行流程1：施工收费单元 → 受影响OD下所有Path流量查询（按车型拆分）

        Args:
            params: 查询参数
            output_path: 输出CSV路径（为空则自动生成）

        Returns:
            AffectedOdQueryResult
        """
        start_time = time.time()
        result = AffectedOdQueryResult(status="running")
        errors = []
        warnings = []

        try:
            section_id_list = params.sectionIds.split("|")
            startDate = _parse_date(params.startDate)
            endDate = _parse_date(params.endDate)

            logger.info(f"查询受影响OD-Path: 施工段={section_id_list}, 时间={params.startDate}~{params.endDate}")

            construction_months = _get_month_list(startDate, endDate)
            sp_start = to_same_period(startDate, params.samePeriodYear)
            sp_end = to_same_period(endDate, params.samePeriodYear)
            sp_months = _get_month_list(sp_start, sp_end)

            # Step 1-2: 查找受影响OD-Path
            affected_rows = self.repository.find_affected_od_paths(section_id_list)
            logger.info(f"找到 {len(affected_rows)} 条受影响的 OD-Path（多版本）")

            if not affected_rows:
                result.status = "success"
                result.affectedOdCount = 0
                result.executionTime = time.time() - start_time
                logger.info("无受影响的OD-Path，流程结束")
                return result

            # Step 3: 提取受影响的OD对集合
            affected_od_pairs: set[tuple[str, str]] = set()
            for row in affected_rows:
                affected_od_pairs.add((row["enid"], row["exid"]))
            logger.info(f"受影响OD对数: {len(affected_od_pairs)}")

            # Step 4: 查询受影响OD下所有path
            od_pairs_list = list(affected_od_pairs)
            all_path_rows = self.repository.find_all_paths_for_ods(od_pairs_list)
            logger.info(f"受影响OD下所有path: {len(all_path_rows)} 条（多版本，含重复）")

            # Step 5: 标记 is_affected 和 affected_section_ids
            for row in all_path_rows:
                affected_str, is_affected = _mark_affected_sections(row, section_id_list)
                row["affected_section_ids"] = affected_str
                row["is_affected"] = is_affected

            # Step 6: 多版本去重（同一 enid+exid+numpath 取最新版本）
            deduped_rows = _dedup_by_latest_version(all_path_rows)
            logger.info(f"去重后: {len(deduped_rows)} 条 path")

            # 构建 path_id → anchor_section 映射（用于流量查询）
            path_id_to_anchor: dict[int, str] = {}
            for row in deduped_rows:
                path_id = row["id"]
                is_affected = row["is_affected"]
                affected_section_ids = row.get("affected_section_ids", "")
                if is_affected and affected_section_ids:
                    anchor = affected_section_ids.split("|")[0]
                else:
                    anchor = row["fixed_intervalpath"].split("|")[0]
                path_id_to_anchor[path_id] = anchor

            # 构建 section → path_ids 分组
            section_to_path_ids: dict[str, list[int]] = defaultdict(list)
            for pid, sec_id in path_id_to_anchor.items():
                section_to_path_ids[sec_id].append(pid)

            # Step 7: 查询施工期间流量（按车型拆分）
            start_ts = startDate.strftime("%Y-%m-%d 00:00:00")
            end_ts = (endDate + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

            construction_flow_available = True
            daily_tables = self.repository.list_available_dws_daily_tables(startDate, endDate)
            if daily_tables:
                logger.info(f"使用 {len(daily_tables)} 个日表查询施工期间流量（按车型）")
                constr_flow_results, constr_vtypes = _query_daily_flow_by_vtype(
                    self.repository, section_to_path_ids, daily_tables, startDate, endDate
                )
            else:
                logger.info("无日表，回退到月表查询")
                constr_flow_results, constr_vtypes, table_exists = _query_monthly_flow_by_vtype(
                    self.repository, section_to_path_ids, construction_months, start_ts, end_ts
                )
                if not table_exists:
                    construction_flow_available = False
                    warnings.append("施工期间流量表不存在")

            logger.info(f"施工期间流量查到 {len(constr_flow_results)} 条(path,vtype)记录, 车型: {sorted(constr_vtypes)}")

            sp_start_ts = sp_start.strftime("%Y-%m-%d 00:00:00")
            sp_end_ts = (sp_end + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

            same_period_available = True
            sp_daily_tables = self.repository.list_available_dws_daily_tables(sp_start, sp_end)

            if sp_daily_tables:
                logger.info(f"使用 {len(sp_daily_tables)} 个日表查询同期流量（按车型）")
                sp_flow_results, sp_vtypes = _query_daily_flow_by_vtype(
                    self.repository, section_to_path_ids, sp_daily_tables, sp_start, sp_end
                )
            else:
                sp_flow_results, sp_vtypes, table_exists = _query_monthly_flow_by_vtype(
                    self.repository, section_to_path_ids, sp_months, sp_start_ts, sp_end_ts
                )
                if not table_exists:
                    same_period_available = False
                    warnings.append("同期流量表不存在")

            logger.info(f"同期流量查到 {len(sp_flow_results)} 条(path,vtype)记录, 车型: {sorted(sp_vtypes)}")

            # Step 9: 扩展每条路径为每种车型一条记录
            # 收集所有出现的车型
            all_vehicle_types = constr_vtypes | sp_vtypes
            if not all_vehicle_types:
                all_vehicle_types = {"0"}

            # 构建 path_id → row 映射
            path_id_to_row: dict[int, dict] = {row["id"]: row for row in deduped_rows}

            # 生成 (path_id, vehicle_type) 粒度的记录
            raw_records: list[AffectedOdPathRecord] = []
            for path_id in path_id_to_row:
                row = path_id_to_row[path_id]
                for vtype in all_vehicle_types:
                    constr_flow = constr_flow_results.get((path_id, vtype), 0)
                    sp_flow = sp_flow_results.get((path_id, vtype), 0)
                    if constr_flow == 0 and sp_flow == 0 and row["is_affected"]:                                                     
                        continue 
                    record = AffectedOdPathRecord(
                        od_section_path_id=path_id,
                        enid=row["enid"],
                        exid=row["exid"],
                        numpath=row["numpath"],
                        fixed_intervalpath=row["fixed_intervalpath"],
                        affected_section_ids=row.get("affected_section_ids", ""),
                        is_affected=row["is_affected"],
                        map_version=row["version_yyyymm"],
                        vehicle_type=vtype,
                        construction_flow=constr_flow,
                        same_period_2025_flow=sp_flow,
                    )
                    raw_records.append(record)

            logger.info(f"扩展车型后: {len(raw_records)} 条记录 ({len(deduped_rows)} path × {len(all_vehicle_types)} 车型)")

            # Step 10: 受影响path流量过滤（path × vehicle_type 粒度）
            if params.minAffectedPathFlow > 0:
                before_count = len(raw_records)
                raw_records = [
                    r for r in raw_records
                    if not r.is_affected
                    or (r.construction_flow is not None and r.construction_flow > params.minAffectedPathFlow)
                    or (r.same_period_2025_flow is not None and r.same_period_2025_flow > params.minAffectedPathFlow)
                ]
                logger.info(
                    f"受影响path流量过滤: minAffectedPathFlow={params.minAffectedPathFlow}, "
                    f"{before_count} → {len(raw_records)} 条"
                )

            # Step 11: 只保留至少有一条is_affected=True的OD对下的所有(path,vtype)记录
            od_has_affected = {(r.enid, r.exid) for r in raw_records if r.is_affected}
            before_count = len(raw_records)
            if od_has_affected:
                raw_records = [r for r in raw_records if (r.enid, r.exid) in od_has_affected]
            else:
                raw_records = []
            if len(raw_records) < before_count:
                logger.info(f"OD过滤: 去除无受影响path的OD, {before_count} → {len(raw_records)} 条")

            # Step 12: OD对聚合流量过滤（跨车型汇总后与阈值比较）
            qualified_ods: set[tuple[str, str]] = set()
            if params.minFlow > 0:
                od_total_flow: dict[tuple[str, str], int] = defaultdict(int)
                for r in raw_records:
                    key = (r.enid, r.exid)
                    if r.construction_flow is not None:
                        od_total_flow[key] += r.construction_flow
                    if r.same_period_2025_flow is not None:
                        od_total_flow[key] += r.same_period_2025_flow

                qualified_ods = {od for od, total in od_total_flow.items() if total > params.minFlow}

                before_count = len(raw_records)
                before_od_count = len(od_total_flow)
                raw_records = [r for r in raw_records if (r.enid, r.exid) in qualified_ods]
                logger.info(
                    f"OD流量过滤: minFlow={params.minFlow}, "
                    f"OD对 {before_od_count} → {len(qualified_ods)}, "
                    f"记录 {before_count} → {len(raw_records)}"
                )

            filtered_od_pairs = list(od_has_affected & qualified_ods) if params.minFlow > 0 else list(od_has_affected)
            logger.info(f"过滤后OD对数: {len(filtered_od_pairs)}, 记录数: {len(raw_records)}")

            # Step 13: 批量计算通行费
            if raw_records:
                logger.info("开始计算通行费...")
                _batch_calculate_toll_fee(
                    raw_records=raw_records,
                    start_date=params.startDate,
                    end_date=params.endDate,
                )
                logger.info("通行费计算完成")

            # Step 14: 输出CSV
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            if output_path is None:
                ts = time.strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(OUTPUT_DIR, f"affected_od_flow_{ts}.csv")

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=AFFECTED_OD_CSV_COLUMNS)
                writer.writeheader()
                for rec in raw_records:
                    writer.writerow(rec.model_dump())

            logger.info(f"结果已写入: {output_path} ({len(raw_records)} 条记录)")

            execution_time = time.time() - start_time
            result.status = "success"
            result.affectedOdCount = len(raw_records)
            result.constructionFlowAvailable = construction_flow_available
            result.samePeriod2025FlowAvailable = same_period_available
            result.filteredOdPairs = filtered_od_pairs
            result.outputCsvPath = output_path
            result.errors = errors
            result.warnings = warnings
            result.executionTime = execution_time

            logger.info(f"流程1完成，耗时 {execution_time:.2f}s")
            return result, raw_records

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"流程1失败: {e}")
            errors.append(str(e))
            result.status = "failed"
            result.errors = errors
            result.warnings = warnings
            result.executionTime = execution_time
            return result, raw_records
