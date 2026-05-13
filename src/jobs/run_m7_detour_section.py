#!/usr/bin/env python
"""
M7 绕行高频路段挖掘 - 命令行入口

（必须通过 uv run 运行）

用法:
  # 手动指定 OD+流量
  uv run python -m src.jobs.run_m7_detour_section \
    --od-flow-list "G000561001000110,G007061001000120,100" "2,146,50"

  # 从文件读取
  uv run python -m src.jobs.run_m7_detour_section \
    --od-flow-file od_flow_list.csv \
    --base-table research/analysis/基础表.csv
"""

import argparse
import csv
import os
import sys

# 支持 uv run 和直接 python 运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.app.logger import get_logger
from src.modules.m7_data_mining.schema import ODFlowPair, DetourSectionParams
from src.modules.m7_data_mining.service import M7Service

logger = get_logger(__name__)


def parse_od_flow_list(odFlowListStr: list[str]) -> list[ODFlowPair]:
    """解析命令行 OD+流量列表，格式: "origin,destination,flow_x" """
    odFlowPairs = []
    for item in odFlowListStr:
        parts = item.split(",")
        if len(parts) != 3:
            logger.error(
                f"无效的OD流量格式: {item}，应为 'origin,destination,flow_x'"
            )
            continue
        try:
            flowX = int(parts[2].strip())
        except ValueError:
            logger.error(f"无效的流量值: {parts[2]}")
            continue
        odFlowPairs.append(
            ODFlowPair(
                origin=parts[0].strip(),
                destination=parts[1].strip(),
                flow_x=flowX,
            )
        )
    return odFlowPairs


def parse_od_flow_file(filePath: str) -> list[ODFlowPair]:
    """从CSV文件读取OD+流量列表，格式: origin,destination,flow_x"""
    odFlowPairs = []
    with open(filePath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                flowX = int(row["flow_x"])
            except (ValueError, KeyError):
                logger.error(f"无效的流量值: {row}")
                continue
            odFlowPairs.append(
                ODFlowPair(
                    origin=row["origin"].strip(),
                    destination=row["destination"].strip(),
                    flow_x=flowX,
                )
            )
    logger.info(f"从 {filePath} 读取 {len(odFlowPairs)} 个OD流量对")
    return odFlowPairs


def main():
    parser = argparse.ArgumentParser(description="M7 绕行高频路段挖掘")
    parser.add_argument(
        "--od-flow-list",
        nargs="+",
        default=["378,152,50"],
        help='OD流量对列表，格式: "origin,destination,flow_x"（可多个）',
    )
    parser.add_argument(
        "--od-flow-file",
        help="OD流量对CSV文件路径，格式: origin,destination,flow_x",
    )
    parser.add_argument(
        "--base-table",
        default="research/analysis/基础表.csv",
        help="基础表CSV路径",
    )
    parser.add_argument(
        "--output",
        default="outputs/m7/detour_sections.csv",
        help="输出CSV路径",
    )

    args = parser.parse_args()

    # 解析OD流量列表
    odFlowPairs = []
    if args.od_flow_list:
        odFlowPairs.extend(parse_od_flow_list(args.od_flow_list))
    if args.od_flow_file:
        odFlowPairs.extend(parse_od_flow_file(args.od_flow_file))

    if not odFlowPairs:
        parser.error("必须指定 --od-flow-list 或 --od-flow-file")

    # 构建参数
    params = DetourSectionParams(
        odFlowList=odFlowPairs,
        baseTablePath=args.base_table,
        outputPath=args.output,
    )

    # 执行
    service = M7Service()
    result = service.run_detour_section_mining(params)

    # 输出结果摘要
    print(f"\n{'='*60}")
    print(f"绕行高频路段挖掘结果")
    print(f"{'='*60}")
    print(f"状态: {result.status}")
    print(f"处理OD: {result.odCount}")
    print(f"输出路段: {result.totalSections}")
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
