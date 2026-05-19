#!/usr/bin/env python3
"""
车辆行为挖掘脚本

根据车辆信息，从每日通行数据中提取指定车辆的通行记录，
并与"附近上下站车辆明细"和"中途上下站车辆明细"进行比对打标。

用法:
    python tools/vehicle_treat_analyse.py \
        --start-date 2026-03-01 \
        --end-date 2026-03-31 \
        --output tools/data/vehicle_treat_analyse/output.csv
"""

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 数据目录
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data" / "vehicle_treat_analyse"
GAOSU_DATA_ROOT = Path("/home/shy/gaosu_data")

# 匹配标签
LABEL_NEARBY = "附近上下站"
LABEL_MID_TRIP1 = "中途上下站-前段"
LABEL_MID_TRIP2 = "中途上下站-后段"


def load_vehicle_info(path: Path) -> Dict[str, Optional[int]]:
    """加载车辆信息，返回 vehicle_id -> vehicle_type 映射
    vehicle_info.csv 无表头行，格式: vehicle_id 或 vehicle_id,vehicle_type
    若无 vehicle_type 则映射值为 None
    """
    vehicleMap: Dict[str, Optional[int]] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for cols in reader:
            if not cols:
                continue
            vid = cols[0].strip()
            if not vid:
                continue
            vtype: Optional[int] = None
            if len(cols) >= 2 and cols[1].strip():
                try:
                    vtype = int(cols[1].strip())
                except ValueError:
                    pass
            vehicleMap[vid] = vtype
    logger.info(f"加载车辆信息: {len(vehicleMap)} 辆车")
    return vehicleMap


def build_nearby_index(path: Path) -> Set[str]:
    """构建附近上下站匹配索引: {vehicle_id}_{record_enid}_{record_exid}"""
    index: Set[str] = set()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vid = row["vehicle_id"].strip()
            enid = row["record_enid"].strip()
            exid = row["record_exid"].strip()
            index.add(f"{vid}_{enid}_{exid}")
    logger.info(f"附近上下站索引: {len(index)} 条")
    return index


def build_mid_trip_index(path: Path) -> tuple[Set[str], Set[str]]:
    """构建中途上下站匹配索引
    前段: {vehicle_id}_{trip1_enid}_{trip1_exid}_{trip1_entime}_{trip1_extime}
    后段: {vehicle_id}_{trip2_enid}_{trip2_exid}_{trip2_entime}_{trip2_extime}
    """
    trip1Index: Set[str] = set()
    trip2Index: Set[str] = set()

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vid = row["vehicle_id"].strip()

            t1Enid = row["trip1_enid"].strip()
            t1Exid = row["trip1_exid"].strip()
            t1Entime = row["trip1_entime"].strip()
            t1Extime = row["trip1_extime"].strip()
            if t1Enid and t1Exid and t1Entime and t1Extime:
                trip1Index.add(f"{vid}_{t1Enid}_{t1Exid}_{t1Entime}_{t1Extime}")

            t2Enid = row["trip2_enid"].strip()
            t2Exid = row["trip2_exid"].strip()
            t2Entime = row["trip2_entime"].strip()
            t2Extime = row["trip2_extime"].strip()
            if t2Enid and t2Exid and t2Entime and t2Extime:
                trip2Index.add(f"{vid}_{t2Enid}_{t2Exid}_{t2Entime}_{t2Extime}")

    logger.info(f"中途上下站索引: 前段 {len(trip1Index)} 条, 后段 {len(trip2Index)} 条")
    return trip1Index, trip2Index


def format_datetime(dtStr: str) -> str:
    """统一日期时间格式，去除多余空格"""
    return dtStr.strip()


def match_record(
    vehicleId: str,
    enid: str,
    exid: str,
    entime: str,
    extime: str,
    nearbyIndex: Set[str],
    trip1Index: Set[str],
    trip2Index: Set[str],
) -> str:
    """对一条通行记录进行匹配打标，返回匹配来源标签（逗号分隔），无匹配返回空字符串"""
    tags: list[str] = []

    # 附近上下站匹配（无时间字段，仅 enid+exid）
    nearbyKey = f"{vehicleId}_{enid}_{exid}"
    if nearbyKey in nearbyIndex:
        tags.append(LABEL_NEARBY)

    # 中途上下站-前段匹配
    entimeFmt = format_datetime(entime)
    extimeFmt = format_datetime(extime)
    trip1Key = f"{vehicleId}_{enid}_{exid}_{entimeFmt}_{extimeFmt}"
    if trip1Key in trip1Index:
        tags.append(LABEL_MID_TRIP1)

    # 中途上下站-后段匹配
    trip2Key = f"{vehicleId}_{enid}_{exid}_{entimeFmt}_{extimeFmt}"
    if trip2Key in trip2Index:
        tags.append(LABEL_MID_TRIP2)

    return ",".join(tags)


def generate_date_range(startDateStr: str, endDateStr: str) -> list[tuple[str, str]]:
    """生成日期范围内的 (YYYYMM, YYYYMMDD) 列表"""
    startDate = datetime.strptime(startDateStr, "%Y-%m-%d")
    endDate = datetime.strptime(endDateStr, "%Y-%m-%d")
    result: list[tuple[str, str]] = []
    current = startDate
    while current <= endDate:
        ym = current.strftime("%Y%m")
        ymd = current.strftime("%Y%m%d")
        result.append((ym, ymd))
        current += timedelta(days=1)
    return result


def process_daily_file(
    dailyPath: Path,
    vehicleSet: Set[str],
    nearbyIndex: Set[str],
    trip1Index: Set[str],
    trip2Index: Set[str],
    vehicleTypeMap: Dict[str, Optional[int]],
    writer: csv.DictWriter,
) -> int:
    """处理单日通行数据文件，返回匹配到的记录数"""
    if not dailyPath.exists():
        logger.warning(f"文件不存在: {dailyPath}")
        return 0

    matchedCount = 0
    totalLines = 0

    with open(dailyPath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            totalLines += 1

            # 车辆匹配：优先 exvehicleid，为空时用 envehicleid
            exVid = row.get("exvehicleid", "").strip()
            enVid = row.get("envehicleid", "").strip()
            vehicleId = exVid if exVid else enVid
            if not vehicleId or vehicleId not in vehicleSet:
                continue

            enid = row["enid"].strip()
            exid = row["exid"].strip()
            entime = row["entime"].strip()
            extime = row["extime"].strip()
            intervalgroup = row.get("intervalgroup", "").strip()
            passid = row.get("passid", "").strip()

            matchSource = match_record(
                vehicleId, enid, exid, entime, extime,
                nearbyIndex, trip1Index, trip2Index,
            )

            writer.writerow({
                "vehicle_id": vehicleId,
                "vehicle_type": vehicleTypeMap.get(vehicleId) or "",
                "passid": passid,
                "enid": enid,
                "exid": exid,
                "entime": entime,
                "extime": extime,
                "intervalgroup": intervalgroup,
                "match_source": matchSource,
            })
            matchedCount += 1

    logger.info(f"  {dailyPath.name}: 扫描 {totalLines:,} 行, 匹配 {matchedCount} 条")
    return matchedCount


def main():
    parser = argparse.ArgumentParser(description="车辆行为挖掘脚本")
    parser.add_argument(
        "--start-date", required=True,
        help="开始日期，格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date", required=True,
        help="结束日期，格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--output", default=str(DATA_DIR / "output.csv"),
        help="输出 CSV 路径 (默认: tools/data/vehicle_treat_analyse/output.csv)",
    )
    args = parser.parse_args()

    # Step 1: 加载车辆信息
    logger.info("=" * 60)
    logger.info("Step 1: 加载车辆信息")
    vehicleTypeMap = load_vehicle_info(DATA_DIR / "vehicle_info.csv")
    vehicleSet = set(vehicleTypeMap.keys())
    logger.info(f"目标车辆: {vehicleSet}")

    # Step 2: 构建匹配索引
    logger.info("=" * 60)
    logger.info("Step 2: 构建匹配索引")
    nearbyIndex = build_nearby_index(DATA_DIR / "附近上下站车辆明细.csv")
    trip1Index, trip2Index = build_mid_trip_index(DATA_DIR / "中途上下站车辆明细.csv")

    # Step 3: 扫描每日数据文件
    logger.info("=" * 60)
    logger.info("Step 3: 扫描每日通行数据")
    dateRange = generate_date_range(args.start_date, args.end_date)
    logger.info(f"日期范围: {args.start_date} ~ {args.end_date}, 共 {len(dateRange)} 天")

    outputPath = Path(args.output)
    outputPath.parent.mkdir(parents=True, exist_ok=True)

    totalMatched = 0
    with open(outputPath, "w", encoding="utf-8-sig", newline="") as outF:
        fieldnames = [
            "vehicle_id", "vehicle_type", "passid", "enid", "exid",
            "entime", "extime", "intervalgroup", "match_source",
        ]
        writer = csv.DictWriter(outF, fieldnames=fieldnames)
        writer.writeheader()

        for ym, ymd in dateRange:
            dailyPath = GAOSU_DATA_ROOT / ym / f"data_{ymd}.csv"
            count = process_daily_file(
                dailyPath, vehicleSet, nearbyIndex, trip1Index, trip2Index,
                vehicleTypeMap, writer,
            )
            totalMatched += count

    # Step 4: 汇总
    logger.info("=" * 60)
    logger.info(f"完成! 总匹配记录: {totalMatched}")
    logger.info(f"输出文件: {outputPath}")


if __name__ == "__main__":
    main()
