#!/usr/bin/env python3
"""
高速公路月度数据拆分工具
输入月份（YYYYMM），拆分为每日数据
首日：包含所有 extime <= 首日 的数据
末日：包含所有 extime >= 末日 的数据
中间日：严格按日期筛选
"""

import argparse
import csv
import os
import sys
from calendar import monthrange

from tqdm import tqdm


def get_month_file(year_month: str, data_dir: str = "/home/shy/gaosu_data") -> str:
    """获取指定月份的数据文件"""
    filename = f"gstx_exit_with_min_fee{year_month}.csv"
    filepath = os.path.join(data_dir, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    return filepath


def extract_extime_date(extime_value: str) -> str:
    """从 extime 值提取日期部分 YYYYMMDD"""
    if not extime_value:
        return ""
    extime_value = extime_value.strip()
    if len(extime_value) >= 10:
        return extime_value[:4] + extime_value[5:7] + extime_value[8:10]
    return ""


def scan_and_split_by_day(
    filepath: str,
    year: int,
    month: int,
    output_dir: str,
) -> dict:
    """
    扫描文件并按天拆分数据
    返回每天的记录数统计
    """
    _, last_day = monthrange(year, month)

    first_day_str = f"{year}{month:02d}01"
    last_day_str = f"{year}{month:02d}{last_day:02d}"

    day_files = {}
    day_writers = {}
    day_counts = {}

    for day in range(1, last_day + 1):
        day_str = f"{year}{month:02d}{day:02d}"
        output_path = os.path.join(output_dir, f"data_{day_str}.csv")
        day_files[day_str] = open(output_path, "w", encoding="utf-8", newline="")
        day_writers[day_str] = csv.writer(day_files[day_str])
        day_counts[day_str] = 0

    header = None
    extime_idx = None
    total_count = 0

    # 先统计文件行数
    with open(filepath, "r", encoding="utf-8") as f:
        for total_count, _ in enumerate(f, 1):
            pass
    total_count -= 1  # 减去表头行

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        for idx, col in enumerate(header):
            if col == "extime":
                extime_idx = idx
                break

        if extime_idx is None:
            raise ValueError(f"文件中没有 extime 列")

        # Write header to each daily file
        for day_str, writer in day_writers.items():
            writer.writerow(header)

        for row in tqdm(reader, desc=os.path.basename(filepath), ncols=80, unit="行", total=total_count):
            if len(row) <= extime_idx:
                continue

            extime_value = row[extime_idx]
            extime_date = extract_extime_date(extime_value)

            if not extime_date:
                continue

            assigned = False

            if extime_date <= first_day_str:
                day_writers[first_day_str].writerow(row)
                day_counts[first_day_str] += 1
                assigned = True
            elif extime_date >= last_day_str:
                day_writers[last_day_str].writerow(row)
                day_counts[last_day_str] += 1
                assigned = True
            else:
                for day in range(2, last_day):
                    day_str = f"{year}{month:02d}{day:02d}"
                    if extime_date == day_str:
                        day_writers[day_str].writerow(row)
                        day_counts[day_str] += 1
                        assigned = True
                        break

    for f in day_files.values():
        f.close()

    return {
        "total": total_count,
        "days": day_counts,
    }


def main():
    parser = argparse.ArgumentParser(description="按月拆分高速公路数据为每日数据")
    parser.add_argument(
        "year_month",
        help="月份，格式 YYYYMM，例如 202603",
    )
    parser.add_argument(
        "-o", "--output-dir",
        required=True,
        help="输出目录路径",
    )
    parser.add_argument(
        "-d", "--data-dir",
        default="/home/shy/gaosu_data",
        help="数据目录，默认 /home/shy/gaosu_data",
    )

    args = parser.parse_args()

    year_month = args.year_month.strip()
    if len(year_month) != 6 or not year_month.isdigit():
        print("错误: 月份格式应为 YYYYMM", file=sys.stderr)
        sys.exit(1)

    year = int(year_month[:4])
    month = int(year_month[4:6])

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"正在处理 {year_month} 月数据...")

    filepath = get_month_file(year_month, args.data_dir)
    print(f"数据文件: {filepath}")

    stats = scan_and_split_by_day(filepath, year, month, args.output_dir)

    print(f"\n扫描完成，总行数: {stats['total']}")
    print("\n每日数据量:")
    for day_str, count in sorted(stats["days"].items()):
        print(f"  {day_str}: {count} 条")

    print(f"\n数据已保存到: {args.output_dir}/")


if __name__ == "__main__":
    main()