#!/usr/bin/env python
"""
M7 绕行高频路段挖掘 - 命令行入口

（必须通过 uv run 运行）

用法:
  # 手动指定 OD+流量
  uv run python -m src.jobs.run_m7_detour_section \
    --od-flow-list "G000561001000110,G007061001000120,100" "2,146,50"

  # 从 xlsx 文件读取
  uv run python -m src.jobs.run_m7_detour_section \
    --od-flow-file research/analysis/od_flow.xlsx \
    --base-table research/analysis/基础表.xlsx

  # 从 CSV 文件读取
  uv run python -m src.jobs.run_m7_detour_section \
    --od-flow-file od_flow_list.csv \
    --base-table research/analysis/基础表.xlsx
"""

import argparse
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
    """从文件读取OD+流量列表，支持 CSV 和 xlsx 格式

    CSV 格式: origin,destination,flow_x
    xlsx 格式: OD_num (如 "378|152"), 绕行流量
    按文件扩展名自动识别格式
    """
    from src.common.file_loader import load_tabular

    odFlowPairs = []
    ext = os.path.splitext(filePath)[1].lower()

    if ext in (".xlsx", ".xls"):
        # xlsx 格式: OD_num = "origin|destination", 绕行流量 = flow_x
        rows = load_tabular(filePath, columns=["OD_num", "绕行流量"])
        for row in rows:
            odNum = row.get("OD_num", "")
            flowStr = row.get("绕行流量", "0")
            if not odNum or "|" not in odNum:
                logger.warning(f"无效的 OD_num 格式: {odNum}")
                continue
            parts = odNum.split("|")
            if len(parts) != 2:
                logger.warning(f"无效的 OD_num 格式: {odNum}")
                continue
            try:
                flowX = int(float(flowStr))
            except (ValueError, TypeError):
                logger.error(f"无效的流量值: {flowStr}")
                continue
            odFlowPairs.append(
                ODFlowPair(
                    origin=parts[0].strip(),
                    destination=parts[1].strip(),
                    flow_x=flowX,
                )
            )
    else:
        # CSV 格式: origin,destination,flow_x
        rows = load_tabular(filePath, columns=["origin", "destination", "flow_x"])
        for row in rows:
            try:
                flowX = int(float(row.get("flow_x", "0")))
            except (ValueError, TypeError):
                logger.error(f"无效的流量值: {row}")
                continue
            odFlowPairs.append(
                ODFlowPair(
                    origin=row.get("origin", "").strip(),
                    destination=row.get("destination", "").strip(),
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
        # default=["378,152,50"],
        help='OD流量对列表，格式: "origin,destination,flow_x"（可多个）',
    )
    parser.add_argument(
        "--od-flow-file",default="research/analysis/od_flow.xlsx",
        help="OD流量对文件路径（支持 CSV 和 xlsx）",
    )
    parser.add_argument(
        "--base-table",
        default="research/analysis/基础表.xlsx",
        help="基础表路径（支持 CSV 和 xlsx）",
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
