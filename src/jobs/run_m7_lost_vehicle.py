#!/usr/bin/env python
"""
M7 流失高频车辆挖掘 - 命令行入口

用法（必须通过 uv run 运行，以正确解析 src 包路径）:
  # enid/exid 格式
  uv run python -m src.jobs.run_m7_lost_vehicle \
    --od-list "G000561001000110,G007061001000120" "G000561001000110,G0070610010020" \
    --start-date 2026-03-01 --end-date 2026-03-31

  # section_number 格式
  uv run python -m src.jobs.run_m7_lost_vehicle \
    --od-list "2,146" "378,152" \
    --start-date 2026-03-01 --end-date 2026-03-31

  # 从文件读取OD列表
  uv run python -m src.jobs.run_m7_lost_vehicle \
    --od-file od_list.csv \
    --start-date 2026-03-01 --end-date 2026-03-31 \
    --top-n 50
"""

import argparse
import os
import sys

# 支持 uv run 和直接 python 运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.app.logger import get_logger
from src.modules.m7_data_mining.schema import ODPair, LostVehicleParams
from src.modules.m7_data_mining.service import M7Service

logger = get_logger(__name__)


def parse_od_list(odListStr: list[str]) -> list[ODPair]:
    """解析命令行 OD 列表，格式: "origin,destination"

    支持两种传参方式:
      --od-list "G000561001000110,G007061001000120"
      --od-list G000561001000110 G007061001000120
    后者每两个参数为一组 OD 对。
    """
    odPairs = []

    # 判断是逗号分隔还是空格分隔
    hasComma = any("," in item for item in odListStr)

    if hasComma:
        for item in odListStr:
            parts = item.split(",")
            if len(parts) != 2:
                logger.error(f"无效的OD格式: {item}，应为 'origin,destination'")
                continue
            odPairs.append(ODPair(origin=parts[0].strip(), destination=parts[1].strip()))
    else:
        # 空格分隔：每两个一组
        if len(odListStr) % 2 != 0:
            logger.error(f"OD参数数量为奇数({len(odListStr)})，必须成对出现")
            return odPairs
        for i in range(0, len(odListStr), 2):
            odPairs.append(ODPair(origin=odListStr[i], destination=odListStr[i + 1]))

    return odPairs


def parse_od_file(filePath: str) -> list[ODPair]:
    """从文件读取OD列表，支持 CSV 和 xlsx 格式

    格式: origin,destination
    """
    from src.common.file_loader import load_tabular

    odPairs = []
    rows = load_tabular(filePath, columns=["origin", "destination"])
    for row in rows:
        odPairs.append(
            ODPair(
                origin=row.get("origin", "").strip(),
                destination=row.get("destination", "").strip(),
            )
        )
    logger.info(f"从 {filePath} 读取 {len(odPairs)} 个OD对")
    return odPairs


def main():
    parser = argparse.ArgumentParser(description="M7 流失高频车辆挖掘")
    parser.add_argument(
        "--od-list",
        nargs="+",
        default=["378,152", "176,146"],
        help='OD对列表，格式: "origin,destination" 或 origin destination（可多个）',
    )
    parser.add_argument(
        "--od-file", help="OD对文件路径（支持 CSV 和 xlsx）"
    )
    parser.add_argument(
        "--start-date", default="2026-03-01", required=False, help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", default="2026-03-02", required=False, help="结束日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--data-dir",
        default="/home/shy/gaosu_data",
        help="日表数据根目录",
    )
    parser.add_argument(
        "--base-table",
        default="research/analysis/基础表.xlsx",
        help="基础表路径（支持 CSV 和 xlsx）",
    )
    parser.add_argument(
        "--section-version",
        default="202401",
        help="section_number 映射版本",
    )
    parser.add_argument(
        "--top-n", type=int, default=0, help="输出TopN车辆，0=全部"
    )
    parser.add_argument(
        "--output",
        default="outputs/m7/lost_vehicles.csv",
        help="输出CSV路径",
    )

    args = parser.parse_args()

    # 解析OD列表
    odPairs = []
    if args.od_list:
        odPairs.extend(parse_od_list(args.od_list))
    if args.od_file:
        odPairs.extend(parse_od_file(args.od_file))

    if not odPairs:
        parser.error("必须指定 --od-list 或 --od-file")

    # 构建参数
    params = LostVehicleParams(
        odList=odPairs,
        startDate=args.start_date,
        endDate=args.end_date,
        dataDir=args.data_dir,
        baseTablePath=args.base_table,
        sectionVersion=args.section_version,
        topN=args.top_n,
        outputPath=args.output,
    )

    # 执行
    service = M7Service()
    result = service.run_lost_vehicle_mining(params)

    # 输出结果摘要
    print(f"\n{'='*60}")
    print(f"流失高频车辆挖掘结果")
    print(f"{'='*60}")
    print(f"状态: {result.status}")
    print(f"扫描记录: {result.totalTripsScanned:,}")
    print(f"匹配记录: {result.matchedTrips:,}")
    print(f"去重车辆: {result.uniqueVehicles:,}")
    print(f"输出文件: {result.outputPath}")
    print(f"耗时: {result.executionTime:.2f}s")

    if result.warnings:
        print(f"\n警告 ({len(result.warnings)}):")
        for w in result.warnings[:5]:
            print(f"  - {w}")
        if len(result.warnings) > 5:
            print(f"  ... 还有 {len(result.warnings) - 5} 条警告")

    if result.errors:
        print(f"\n错误 ({len(result.errors)}):")
        for e in result.errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
