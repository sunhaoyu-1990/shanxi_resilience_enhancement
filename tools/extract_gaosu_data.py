#!/usr/bin/env python3
"""
高速公路数据提取工具
输入日期范围（YYYYMMDD-YYYYMMDD），从 /home/shy/gaosu_data 中提取相应数据
逐行扫描，不使用pandas，适合大数据量场景
"""

import argparse
import csv
import os
import sys
from datetime import datetime

from tqdm import tqdm


def parse_date_range(date_range: str) -> tuple[str, str]:
    """解析日期范围字符串，返回 (start_date, end_date)"""
    if "-" not in date_range:
        raise ValueError("日期范围格式错误，应为 YYYYMMDD-YYYYMMDD")

    start_str, end_str = date_range.split("-", 1)
    start_str = start_str.strip()
    end_str = end_str.strip()

    if len(start_str) != 8 or len(end_str) != 8:
        raise ValueError("日期格式错误，应为 YYYYMMDD")

    return start_str, end_str


def get_data_files(start_date: str, end_date: str, data_dir: str = "/home/shy/gaosu_data") -> list[str]:
    """根据日期范围获取需要的数据文件"""
    start_year_month = start_date[:6]
    end_year_month = end_date[:6]

    start_year = int(start_date[:4])
    start_month = int(start_date[4:6])
    end_year = int(end_date[:4])
    end_month = int(end_date[4:6])

    files = []
    year, month = start_year, start_month
    while (year < end_year) or (year == end_year and month <= end_month):
        month_str = f"{year}{month:02d}"
        filename = f"gstx_exit_with_min_fee{month_str}.csv"
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            files.append(filepath)
        else:
            print(f"警告: 文件不存在 {filepath}", file=sys.stderr)

        month += 1
        if month > 12:
            month = 1
            year += 1

    return files


def extract_extime_date(extime_value: str) -> str:
    """从 extime 值提取日期部分 YYYYMMDD"""
    if not extime_value:
        return ""
    extime_value = extime_value.strip()
    if len(extime_value) >= 10:
        return extime_value[:4] + extime_value[5:7] + extime_value[8:10]
    return ""


def filter_csv_file(
    filepath: str,
    start_date: str,
    end_date: str,
) -> tuple[list[list[str]], int, int]:
    """
    逐行扫描CSV文件，筛选符合日期范围的数据
    返回: (匹配的记录列表, 总行数, 匹配行数)
    """
    matched_rows = []
    total_count = 0
    matched_count = 0

    # 先统计文件行数
    with open(filepath, "r", encoding="utf-8") as f:
        for total_count, _ in enumerate(f, 1):
            pass
    total_count -= 1  # 减去表头行

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        extime_idx = None
        for idx, col in enumerate(header):
            if col == "extime":
                extime_idx = idx
                break

        if extime_idx is None:
            raise ValueError(f"文件 {filepath} 中没有 extime 列")

        for row in tqdm(reader, desc=os.path.basename(filepath), ncols=80, unit="行", total=total_count):
            if len(row) > extime_idx:
                extime_value = row[extime_idx]
                extime_date = extract_extime_date(extime_value)

                if extime_date and start_date <= extime_date <= end_date:
                    matched_rows.append(row)
                    matched_count += 1

    return matched_rows, total_count, matched_count


def main():
    parser = argparse.ArgumentParser(description="提取高速公路数据")
    parser.add_argument(
        "date_range",
        help="日期范围，格式 YYYYMMDD-YYYYMMDD，例如 20260301-20260303",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径，默认输出到标准输出",
    )
    parser.add_argument(
        "-d", "--data-dir",
        default="/home/shy/gaosu_data",
        help="数据目录，默认 /home/shy/gaosu_data",
    )

    args = parser.parse_args()

    try:
        start_date, end_date = parse_date_range(args.date_range)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"正在提取 {start_date} 至 {end_date} 的数据...")

    files = get_data_files(start_date, end_date, args.data_dir)
    if not files:
        print("错误: 未找到任何数据文件", file=sys.stderr)
        sys.exit(1)

    print(f"将读取 {len(files)} 个文件: {[os.path.basename(f) for f in files]}")

    all_matched_rows = []
    total_records = 0
    total_matched = 0
    header = None

    for filepath in files:
        print(f"处理文件: {os.path.basename(filepath)}", flush=True)
        try:
            matched_rows, total_count, matched_count = filter_csv_file(
                filepath, start_date, end_date
            )
            if not header:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader)

            all_matched_rows.extend(matched_rows)
            total_records += total_count
            total_matched += matched_count
            print(f"  -> 扫描 {total_count} 行，提取 {matched_count} 条记录")
        except Exception as e:
            print(f"  -> 错误: {e}", file=sys.stderr)
            continue

    if not all_matched_rows:
        print("错误: 未能提取任何数据", file=sys.stderr)
        sys.exit(1)

    print(f"\n总共扫描 {total_records} 行，提取 {total_matched} 条记录")

    output_file = None
    output_handle = None

    if args.output:
        output_file = open(args.output, "w", encoding="utf-8", newline="")
        output_handle = output_file
    else:
        output_handle = sys.stdout

    writer = csv.writer(output_handle)
    writer.writerow(header)
    writer.writerows(all_matched_rows)

    if output_file:
        output_file.close()
        print(f"数据已保存到: {args.output}")


if __name__ == "__main__":
    main()
