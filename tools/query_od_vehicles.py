#!/usr/bin/env python3
"""
OD 车辆查询工具
按 OD 对（enid:exid）和日期范围，从 /home/shy/gaosu_data 每日文件中查找匹配的车辆记录
支持多 OD 对查询，输出明细 CSV 及车辆类型统计
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from tqdm import tqdm


# feevehicletype 中文映射（参考项目已有口径）
VEHICLE_TYPE_NAMES: dict[str, str] = {
    "1": "一型客车",
    "2": "二型客车",
    "3": "三型客车",
    "4": "四型客车",
    "11": "一型货车",
    "12": "二型货车",
    "13": "三型货车",
    "14": "四型货车",
    "15": "五型货车",
    "16": "六型货车",
    "21": "一型专项作业车",
    "22": "二型专项作业车",
    "23": "三型专项作业车",
    "24": "四型专项作业车",
    "25": "五型专项作业车",
    "26": "六型专项作业车",
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

    # 校验日期合法性
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
    start_date: str, end_date: str, data_dir: str
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
            print(f"警告: 文件不存在 {daily_file}", file=sys.stderr)
        current += timedelta(days=1)

    return files


def scan_file(
    filepath: str,
    od_pairs: set[tuple[str, str]],
    summary_only: bool = False,
) -> tuple[list[list[str]], dict[tuple[str, str], dict[str, int]], int]:
    """
    扫描单个每日 CSV 文件，返回 (匹配行, OD→车型统计, 总行数)
    CSV 列顺序: exid,enid,...（注意 exid 在前）
    """
    matched_rows: list[list[str]] = []
    od_vehicle_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))  # type: ignore[var-annotated]
    total_count = 0

    # 先统计行数用于进度条
    with open(filepath, "r", encoding="utf-8") as f:
        for total_count, _ in enumerate(f, 1):
            pass
    total_count -= 1  # 减去表头

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        enid_idx: int | None = None
        exid_idx: int | None = None
        feevehicletype_idx: int | None = None
        for idx, col in enumerate(header):
            if col == "enid":
                enid_idx = idx
            elif col == "exid":
                exid_idx = idx
            elif col == "feevehicletype":
                feevehicletype_idx = idx

        if enid_idx is None or exid_idx is None:
            raise ValueError(f"文件 {filepath} 缺少 enid 或 exid 列")

        filename = os.path.basename(filepath)
        for row in tqdm(reader, desc=filename, ncols=80, unit="行", total=total_count):
            if len(row) <= max(enid_idx, exid_idx):
                continue

            enid_val = row[enid_idx]
            exid_val = row[exid_idx]

            if (enid_val, exid_val) in od_pairs:
                if not summary_only:
                    matched_rows.append(row)

                if feevehicletype_idx is not None and len(row) > feevehicletype_idx:
                    vtype = row[feevehicletype_idx]
                else:
                    vtype = "unknown"
                od_vehicle_stats[(enid_val, exid_val)][vtype] += 1

    return matched_rows, dict(od_vehicle_stats), total_count


def print_summary(
    od_vehicle_stats: dict[tuple[str, str], dict[str, int]],
    total_matched: int,
    total_scanned: int,
) -> None:
    """打印各 OD 对的车辆类型统计"""
    print(f"\n{'='*60}")
    print(f"扫描总行数: {total_scanned:,}")
    print(f"匹配总记录: {total_matched:,}")
    print(f"{'='*60}")

    for (enid, exid), vtype_counts in sorted(od_vehicle_stats.items()):
        od_total = sum(vtype_counts.values())
        print(f"\nOD: {enid} → {exid}  (共 {od_total:,} 条)")
        print(f"  {'车型类型':<20} {'编码':<6} {'数量':>10} {'占比':>8}")
        print(f"  {'-'*46}")

        for vtype, count in sorted(vtype_counts.items(), key=lambda x: -x[1]):
            name = VEHICLE_TYPE_NAMES.get(vtype, f"未知({vtype})")
            pct = count / od_total * 100 if od_total > 0 else 0
            print(f"  {name:<20} {vtype:<6} {count:>10,} {pct:>7.2f}%")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="按 OD 对和日期范围查询高速公路车辆记录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  # 查询单个 OD 对
  python tools/query_od_vehicles.py --od S0030610010030:G0070610020010 --date-range 20260301-20260331 -o result.csv

  # 查询多个 OD 对
  python tools/query_od_vehicles.py --od S0030610010030:G0070610020010 --od G000561001000110:G000561001000120 --date-range 20260301-20260315

  # 仅看统计
  python tools/query_od_vehicles.py --od S0030610010030:G0070610020010 --date-range 20260301-20260331 --summary-only""",
    )
    parser.add_argument(
        "--od",
        action="append",
        required=True,
        metavar="ENID:EXID",
        help="OD 对，格式 enid:exid，可多次指定",
    )
    parser.add_argument(
        "--date-range",
        required=True,
        metavar="YYYYMMDD-YYYYMMDD",
        help="日期范围，如 20260301-20260331",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 CSV 文件路径，默认 outputs/tmp/od_vehicles_{enid}_{exid}_{daterange}.csv",
    )
    parser.add_argument(
        "-d", "--data-dir",
        default="/home/shy/gaosu_data",
        help="数据目录，默认 /home/shy/gaosu_data",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="仅输出统计汇总，不输出明细行",
    )

    args = parser.parse_args()

    # 解析参数
    try:
        start_date, end_date = parse_date_range(args.date_range)
        od_pairs = parse_od_pairs(args.od)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    od_display = ", ".join(f"{enid}→{exid}" for enid, exid in sorted(od_pairs))
    print(f"查询 OD: {od_display}")
    print(f"日期范围: {start_date} ~ {end_date}")

    # 获取文件列表
    files = get_daily_files(start_date, end_date, args.data_dir)
    if not files:
        print("错误: 未找到任何数据文件", file=sys.stderr)
        sys.exit(1)

    print(f"将扫描 {len(files)} 个文件")

    # 逐文件扫描
    all_matched_rows: list[list[str]] = []
    all_od_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))  # type: ignore[var-annotated]
    total_scanned = 0
    total_matched = 0
    header = None

    for filepath in files:
        try:
            matched_rows, od_stats, file_total = scan_file(
                filepath, od_pairs, args.summary_only
            )

            # 取第一个文件的 header
            if header is None:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader)

            all_matched_rows.extend(matched_rows)
            for od_key, vtype_counts in od_stats.items():
                for vtype, count in vtype_counts.items():
                    all_od_stats[od_key][vtype] += count

            total_scanned += file_total
            matched_count = sum(sum(c.values()) for c in od_stats.values())
            total_matched += matched_count
            print(f"  -> 扫描 {file_total:,} 行，匹配 {matched_count:,} 条")

        except Exception as e:
            print(f"  -> 错误: {e}", file=sys.stderr)
            continue

    # 打印统计汇总
    merged_stats = {k: dict(v) for k, v in all_od_stats.items()}
    print_summary(merged_stats, total_matched, total_scanned)

    # 输出明细
    if not args.summary_only and all_matched_rows:
        if args.output:
            output_path = args.output
        else:
            # 默认输出到 outputs/tmp/
            first_od = sorted(od_pairs)[0]
            default_name = f"od_vehicles_{first_od[0]}_{first_od[1]}_{start_date}_{end_date}.csv"
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "tmp")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, default_name)

        output_file = open(output_path, "w", encoding="utf-8", newline="")
        writer = csv.writer(output_file)
        if header:
            writer.writerow(header)
            writer.writerows(all_matched_rows)
        output_file.close()
        print(f"明细数据已保存到: {output_path}")

    elif not args.summary_only and not all_matched_rows:
        print("未找到匹配记录")


if __name__ == "__main__":
    main()
