"""
M3 交通影响分析 - 高频车辆查询服务

从每日 CSV 文件中按 OD 对查询匹配的车辆记录，输出明细 CSV 和多维度统计。
核心逻辑从 tools/query_od_vehicles.py 提取，供流水线步骤7和 CLI 工具复用。

输出4个CSV:
1. od_vehicles — 明细（含 TOP、section_od）
2. od_vehicle_stats — 车型统计（含 TOP、section_od）
3. od_vehicle_plate_stats — 车牌统计（含 TOP、section_od）
4. od_top_vehicles — TOP 高频车辆（按 section_od 分组排名）
"""

import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from src.app.logger import get_logger

logger = get_logger(__name__)

# new_vehicletype 中文映射
VEHICLE_TYPE_NAMES: dict[str, str] = {
    "1": "一型客车", "2": "二型客车", "3": "三型客车", "4": "四型客车",
    "11": "一型货车", "12": "二型货车", "13": "三型货车", "14": "四型货车",
    "15": "五型货车", "16": "六型货车",
    "21": "一型专项作业车", "22": "二型专项作业车", "23": "三型专项作业车",
    "24": "四型专项作业车", "25": "五型专项作业车", "26": "六型专项作业车",
}


def parse_date_range(date_range: str) -> tuple[str, str]:
    """解析日期范围字符串，返回 (start_date, end_date)，格式 YYYYMMDD"""
    if "-" not in date_range:
        raise ValueError("日期范围格式错误，应为 YYYYMMDD-YYYYMMDD")

    start_str, end_str = date_range.split("-", 1)
    start_str = start_str.strip()
    end_str = end_str.strip()

    if len(start_str) != 8 or len(end_str) != 8:
        raise ValueError("日期格式错误，应为 YYYYMMDD")

    datetime.strptime(start_str, "%Y%m%d")
    datetime.strptime(end_str, "%Y%m%d")

    if start_str > end_str:
        raise ValueError("开始日期不能晚于结束日期")

    return start_str, end_str


def parse_od_pairs(od_list: list[str]) -> set[tuple[str, str]]:
    """解析 OD 对参数，返回 {(enid, exid), ...}"""
    od_pairs: set[tuple[str, str]] = set()
    for od in od_list:
        if ":" not in od:
            raise ValueError(f"OD 对格式错误: {od}，应为 enid:exid")
        enid, exid = od.split(":", 1)
        enid = enid.strip()
        exid = exid.strip()
        if not enid or not exid:
            raise ValueError(f"OD 对 enid 和 exid 不能为空: {od}")
        od_pairs.add((enid, exid))
    return od_pairs


def get_daily_files(
    start_date: str, end_date: str, data_dir: str,
) -> list[str]:
    """根据日期范围获取需要扫描的每日 CSV 文件列表（按日期排序）"""
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")

    files: list[str] = []
    current = start_dt
    while current <= end_dt:
        month_dir = os.path.join(data_dir, current.strftime("%Y%m"))
        daily_file = os.path.join(month_dir, f"data_{current.strftime('%Y%m%d')}.csv")
        if os.path.exists(daily_file):
            files.append(daily_file)
        else:
            logger.warning(f"文件不存在: {daily_file}")
        current += timedelta(days=1)

    return files


def scan_file(
    filepath: str,
    od_pairs: set[tuple[str, str]],
    summary_only: bool = False,
) -> tuple[list[list[str]], dict[tuple[str, str], dict[str, int]], dict[tuple[str, str, str, str], int], int, list[str]]:
    """
    扫描单个每日 CSV 文件。

    Args:
        filepath: CSV 文件路径
        od_pairs: OD 对集合 {(enid, exid), ...}
        summary_only: 仅统计，不返回明细行

    Returns:
        (匹配行, OD→车型统计, 车牌级统计, 总行数(不含表头), 表头列名)

        车牌级统计: {(enid, exid, vehicle_id, vehicle_type): count}
    """
    matched_rows: list[list[str]] = []
    od_vehicle_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))  # type: ignore[var-annotated]
    od_vehicle_detail_stats: dict[tuple[str, str, str, str], int] = defaultdict(int)
    total_count = 0
    header: list[str] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        enid_idx: Optional[int] = None
        exid_idx: Optional[int] = None
        new_vehicletype_idx: Optional[int] = None
        envehicleid_idx: Optional[int] = None
        for idx, col in enumerate(header):
            if col == "enid":
                enid_idx = idx
            elif col == "exid":
                exid_idx = idx
            elif col == "new_vehicletype":
                new_vehicletype_idx = idx
            elif col == "envehicleid":
                envehicleid_idx = idx

        if enid_idx is None or exid_idx is None:
            raise ValueError(f"文件 {filepath} 缺少 enid 或 exid 列")

        for row in reader:
            total_count += 1
            if len(row) <= max(enid_idx, exid_idx):
                continue

            enid_val = row[enid_idx]
            exid_val = row[exid_idx]

            if (enid_val, exid_val) in od_pairs:
                if not summary_only:
                    matched_rows.append(row)

                if new_vehicletype_idx is not None and len(row) > new_vehicletype_idx:
                    vtype = row[new_vehicletype_idx]
                else:
                    vtype = "unknown"
                od_vehicle_stats[(enid_val, exid_val)][vtype] += 1

                # 车牌级统计
                if envehicleid_idx is not None and len(row) > envehicleid_idx:
                    vehicle_id = row[envehicleid_idx]
                else:
                    vehicle_id = "unknown"
                od_vehicle_detail_stats[(enid_val, exid_val, vehicle_id, vtype)] += 1

    return matched_rows, dict(od_vehicle_stats), dict(od_vehicle_detail_stats), total_count, header


def query_od_vehicles(
    od_pairs: set[tuple[str, str]],
    start_date: str,
    end_date: str,
    data_dir: str = "/home/shy/gaosu_data",
    output_dir: str = "analysis_results/vehicle_query",
    summary_only: bool = False,
    od_mapping: Optional[dict[str, str]] = None,
    od_pair_to_section_od: Optional[dict[tuple[str, str], str]] = None,
) -> dict[tuple[str, str], str]:
    """
    查询指定 OD 对的车辆记录。

    Args:
        od_pairs: OD 对集合
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        data_dir: CSV 数据根目录
        output_dir: 输出目录
        summary_only: 仅统计
        od_mapping: section_od → TOP 标签映射，如 {"1|2": "TOP01"}
        od_pair_to_section_od: (enid, exid) → section_od 映射

    Returns:
        {(enid, exid): output_csv_path}
    """
    files = get_daily_files(start_date, end_date, data_dir)
    if not files:
        logger.error("未找到任何数据文件")
        return {}

    logger.info(f"将扫描 {len(files)} 个文件，OD 对数: {len(od_pairs)}")

    all_matched_rows: list[list[str]] = []
    all_od_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))  # type: ignore[var-annotated]
    all_detail_stats: dict[tuple[str, str, str, str], int] = defaultdict(int)
    total_scanned = 0
    total_matched = 0
    header: Optional[list[str]] = None

    for filepath in files:
        try:
            matched_rows, od_stats, detail_stats, file_total, file_header = scan_file(
                filepath, od_pairs, summary_only,
            )

            if header is None:
                header = file_header

            all_matched_rows.extend(matched_rows)
            for od_key, vtype_counts in od_stats.items():
                for vtype, count in vtype_counts.items():
                    all_od_stats[od_key][vtype] += count

            for detail_key, count in detail_stats.items():
                all_detail_stats[detail_key] += count

            total_scanned += file_total
            matched_count = sum(sum(c.values()) for c in od_stats.values())
            total_matched += matched_count
            logger.info(f"  {os.path.basename(filepath)}: 扫描 {file_total:,} 行，匹配 {matched_count:,} 条")

        except Exception as e:
            logger.error(f"  扫描出错: {e}")
            continue

    # 打印统计
    _print_summary(all_od_stats, total_matched, total_scanned)

    os.makedirs(output_dir, exist_ok=True)

    # 辅助函数: 查 TOP 和 section_od
    def _lookup_top(od_key: tuple[str, str]) -> tuple[str, str]:
        """返回 (top_label, section_od)"""
        if od_pair_to_section_od and od_key in od_pair_to_section_od:
            section_od = od_pair_to_section_od[od_key]
            top_label = od_mapping.get(section_od, "") if od_mapping else ""
            return top_label, section_od
        return "", ""

    # ============================================================
    # 输出1: od_vehicles 明细 CSV（含 TOP、section_od）
    # ============================================================
    output_paths: dict[tuple[str, str], str] = {}
    if not summary_only and all_matched_rows and header:
        # 确定 enid/exid/envehicleid 列索引
        enid_idx = header.index("enid") if "enid" in header else None
        exid_idx = header.index("exid") if "exid" in header else None

        output_path = os.path.join(
            output_dir, f"od_vehicles_{start_date}_{end_date}.csv"
        )
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # 在原始 header 前插入 TOP、section_od
            writer.writerow(["TOP", "section_od"] + header)
            for row in all_matched_rows:
                top_label, section_od = "", ""
                if enid_idx is not None and exid_idx is not None:
                    od_key = (row[enid_idx], row[exid_idx])
                    top_label, section_od = _lookup_top(od_key)
                writer.writerow([top_label, section_od] + row)

        for od_pair in sorted(od_pairs):
            output_paths[od_pair] = output_path
        logger.info(f"明细数据已保存到: {output_path}")

    # ============================================================
    # 输出2: od_vehicle_plate_stats 车牌统计 CSV（含 TOP、section_od）
    # ============================================================
    plate_stats_path = os.path.join(output_dir, f"od_vehicle_plate_stats_{start_date}_{end_date}.csv")
    with open(plate_stats_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["TOP", "section_od", "enid", "exid", "vehicle_id", "vehicle_type", "count"])
        for (enid, exid, vehicle_id, vtype), count in sorted(all_detail_stats.items(), key=lambda x: -x[1]):
            top_label, section_od = _lookup_top((enid, exid))
            writer.writerow([top_label, section_od, enid, exid, vehicle_id, vtype, count])
    logger.info(f"车牌统计已保存到: {plate_stats_path}")

    return output_paths


def _print_summary(
    od_vehicle_stats: dict[tuple[str, str], dict[str, int]],
    total_matched: int,
    total_scanned: int,
) -> None:
    """打印各 OD 对的车辆类型统计"""
    logger.info(f"扫描总行数: {total_scanned:,}, 匹配总记录: {total_matched:,}")

    for (enid, exid), vtype_counts in sorted(od_vehicle_stats.items()):
        od_total = sum(vtype_counts.values())
        logger.info(f"  OD: {enid} → {exid}  (共 {od_total:,} 条)")


class VehicleQueryService:
    """步骤7: 高频车辆查询服务"""

    def run(
        self,
        top_od_pairs: list[tuple[str, str]],
        start_date: str,
        end_date: str,
        data_dir: str = "/home/shy/gaosu_data",
        output_dir: str = "analysis_results/vehicle_query",
        od_mapping: Optional[dict[str, str]] = None,
        od_pair_to_section_od: Optional[dict[tuple[str, str], str]] = None,
    ) -> dict[tuple[str, str], str]:
        """
        对 TOP N 流失 OD 进行高频车辆查询。

        Args:
            top_od_pairs: OD 对列表 [(enid, exid), ...]
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            data_dir: CSV 数据根目录
            output_dir: 输出目录
            od_mapping: section_od → TOP 标签映射
            od_pair_to_section_od: (enid, exid) → section_od 映射

        Returns:
            {(enid, exid): output_csv_path}
        """
        logger.info(f"开始高频车辆查询: {len(top_od_pairs)} 个 OD 对")
        od_pairs = set(top_od_pairs)

        return query_od_vehicles(
            od_pairs=od_pairs,
            start_date=start_date,
            end_date=end_date,
            data_dir=data_dir,
            output_dir=output_dir,
            od_mapping=od_mapping,
            od_pair_to_section_od=od_pair_to_section_od,
        )
