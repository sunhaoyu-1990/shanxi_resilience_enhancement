#!/usr/bin/env python3
"""
路径费额批量查询工具

输入：CSV 文件（每行一个 | 分隔的收费单元路径字符串）+ fee_version
输出：每条路径 × 每种车型的费额、交控费额、里程、交控里程

用法:
    python tools/query_path_fee.py --fee-version 202604
    python tools/query_path_fee.py --input tools/data/path.csv --fee-version 202604 -o result.csv
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

# 项目根目录
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from src.common.toll_calculator import TollCalculator, split_intervalgroup
from src.app.logger import get_logger

logger = get_logger(__name__)

# 10 种车型：客车 1-4 + 货车 11-16
VEHICLE_TYPES: list[tuple[int, str]] = [
    (1, "客车1型"),
    (2, "客车2型"),
    (3, "客车3型"),
    (4, "客车4型"),
    (11, "货车1型"),
    (12, "货车2型"),
    (13, "货车3型"),
    (14, "货车4型"),
    (15, "货车5型"),
    (16, "货车6型"),
]

OUTPUT_COLUMNS = [
    "path",
    "vehicle_type",
    "vehicle_type_name",
    "fee_yuan",
    "control_fee_yuan",
    "length_km",
    "control_length_km",
    "section_count",
    "skipped_count",
]


def read_paths(csv_path: str) -> list[str]:
    """读取输入 CSV，每行一个路径字符串（| 分隔或单个收费单元 ID）"""
    paths: list[str] = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                paths.append(line)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="路径费额批量查询：输入路径字符串 CSV，输出所有车型的费额/里程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
    python tools/query_path_fee.py --fee-version 202604
    python tools/query_path_fee.py --input tools/data/path.csv --fee-version 202604 -o result.csv""",
    )
    parser.add_argument(
        "--input",
        default=str(project_root / "tools" / "data" / "path.csv"),
        help="输入 CSV 路径，每行一个 | 分隔的路径字符串 (默认: tools/data/path.csv)",
    )
    parser.add_argument(
        "--fee-version",
        required=True,
        help="费率版本，如 202604 (对应 dwd_section_path 的 version_yyyyMM)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出 CSV 路径 (默认: outputs/tmp/path_fee_result_{fee_version}.csv)",
    )

    args = parser.parse_args()

    # 输出路径
    if args.output:
        output_path = args.output
    else:
        output_dir = project_root / "outputs" / "tmp"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"path_fee_result_{args.fee_version}.csv")

    # 读取路径
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在 {args.input}", file=sys.stderr)
        sys.exit(1)

    paths = read_paths(args.input)
    if not paths:
        print("错误: 输入文件为空或无有效路径", file=sys.stderr)
        sys.exit(1)

    print(f"输入文件: {args.input}")
    print(f"路径数量: {len(paths)}")
    print(f"费率版本: {args.fee_version}")
    print(f"车型数量: {len(VEHICLE_TYPES)}")
    print(f"输出文件: {output_path}")
    print()

    # 初始化计算器
    calculator = TollCalculator()

    start_time = time.time()
    total_rows = len(paths) * len(VEHICLE_TYPES)
    done = 0
    error_count = 0

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_COLUMNS)

        for path_idx, path_str in enumerate(paths, 1):
            section_ids = split_intervalgroup(path_str)
            if not section_ids:
                print(f"  路径 {path_idx}: 无效路径，跳过")
                for vtype, vname in VEHICLE_TYPES:
                    writer.writerow([
                        path_str, vtype, vname,
                        0, 0, 0, 0, 0, 0,
                    ])
                    done += 1
                continue

            for vtype, vname in VEHICLE_TYPES:
                try:
                    result = calculator.calculate_path_fee(
                        section_ids=section_ids,
                        vehicle_type=vtype,
                        version=args.fee_version,
                    )
                    writer.writerow([
                        path_str,
                        vtype,
                        vname,
                        round(result.fee_yuan, 2),
                        round(result.control_fee_yuan, 2),
                        round(result.total_length_meters / 1000, 3),
                        round(result.control_length_meters / 1000, 3),
                        len(section_ids),
                        len(result.skipped_sections),
                    ])
                except Exception as e:
                    logger.warning(f"路径 {path_idx} 车型 {vname} 计算失败: {e}")
                    writer.writerow([
                        path_str, vtype, vname,
                        0, 0, 0, 0, len(section_ids), len(section_ids),
                    ])
                    error_count += 1

                done += 1

            if path_idx % 5 == 0 or path_idx == len(paths):
                elapsed = time.time() - start_time
                pct = done / total_rows * 100
                print(f"  进度: {path_idx}/{len(paths)} 路径 ({pct:.0f}%)  耗时: {elapsed:.1f}s")

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"完成: {len(paths)} 条路径 × {len(VEHICLE_TYPES)} 种车型 = {done} 行")
    if error_count:
        print(f"错误: {error_count} 行")
    print(f"耗时: {elapsed:.1f}s")
    print(f"输出: {output_path}")


if __name__ == "__main__":
    main()
