#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hive 通行流水数据导出脚本
支持指定表名和数据库，支持断点续传

续传策略（自动选择最优）：
1. 若表有 extime 字段 → 按日期分片导出，跳过已完成日期（Hive 端过滤，零网络开销）
2. 否则 → 回退到全表导出（无断点续传）
"""
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from pyhive import hive
from tqdm import tqdm


FIELDS = [
    "exid",
    "enid",
    "intervalgroup",
    "intervaltimegroup",
    "envehicleid",
    "exvehicleid",
    "entime",
    "extime",
]
BATCH_SIZE = 100_000
TIME_FIELD = "extime"


def get_hive_config(db_name: str = None) -> dict:
    """获取 Hive 配置"""
    import os
    return {
        "host": os.getenv("HIVE_HOST", "172.16.5.1"),
        "port": int(os.getenv("HIVE_PORT", "10000")),
        "database": db_name or os.getenv("HIVE_DATABASE", "dbbase2026"),
        "username": os.getenv("HIVE_USER", "hive"),
    }


def _progress_file(output_file: Path) -> Path:
    return output_file.with_suffix(output_file.suffix + ".progress")


def _load_progress(output_file: Path) -> dict:
    """加载进度，返回 dict 或空 dict"""
    pf = _progress_file(output_file)
    if pf.exists():
        try:
            return json.loads(pf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def _save_progress(output_file: Path, data: dict):
    """保存进度"""
    pf = _progress_file(output_file)
    pf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _remove_progress(output_file: Path):
    pf = _progress_file(output_file)
    if pf.exists():
        pf.unlink()


def _get_table_columns(cursor, table_name: str) -> list[str]:
    """获取表的字段列表"""
    cursor.execute(f"DESCRIBE {table_name}")
    rows = cursor.fetchall()
    return [row[0] for row in rows if row[0]]


def _get_date_range(cursor, table_name: str, time_field: str) -> tuple[str, str]:
    """获取时间字段的日期范围"""
    cursor.execute(
        f"SELECT MIN(CAST({time_field} AS DATE)), MAX(CAST({time_field} AS DATE)) FROM {table_name}"
    )
    row = cursor.fetchone()
    return (str(row[0]), str(row[1])) if row and row[0] else (None, None)


def _get_dates_between(start: str, end: str) -> list[str]:
    """获取两个日期之间的所有日期"""
    dates = []
    current = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def _write_rows_to_csv(output_file: Path, rows: list, is_first_write: bool) -> bool:
    """将数据写入 CSV，返回是否首次写入"""
    with open(output_file, "a" if not is_first_write else "w", encoding="utf-8", newline="") as f:
        if is_first_write:
            f.write(",".join(FIELDS) + "\n")
        for row in rows:
            f.write(",".join(_format_value(v) for v in row) + "\n")
    return False


def export(
    table_name: str,
    db_name: str,
    output_file: Path,
    force: bool = False,
) -> bool:
    """导出数据到 CSV"""
    print("\n" + "=" * 60)
    print("导出数据...")
    print("=" * 60)

    config = get_hive_config(db_name)
    field_list = ", ".join(FIELDS)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    # force 模式下清理旧文件
    if force and output_file.exists():
        output_file.unlink()
        print("  --force: 已删除旧 CSV")

    # 加载进度
    progress = _load_progress(output_file)
    if force:
        progress = {}
        _remove_progress(output_file)
        print("  --force: 已删除旧进度文件")

    start_time = time.time()
    total_exported = 0
    is_first_write = not output_file.exists() or output_file.stat().st_size == 0

    conn = None
    try:
        conn = hive.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            username=config["username"],
        )
        cursor = conn.cursor()

        # 检测是否支持按时间分片
        columns = _get_table_columns(cursor, table_name)
        can_resume_by_time = TIME_FIELD in columns

        if can_resume_by_time:
            # ===== 按日期分片导出（最优策略） =====
            start_date, end_date = _get_date_range(cursor, table_name, TIME_FIELD)
            if not start_date:
                print(f"  警告: {TIME_FIELD} 字段无有效日期范围，将全表导出")
                can_resume_by_time = False
            else:
                all_days = _get_dates_between(start_date, end_date)
                completed_days = set(progress.get("completed_days", []))
                remaining_days = [d for d in all_days if d not in completed_days]

                print(f"  表: {db_name}.{table_name}")
                print(f"  策略: 按 {TIME_FIELD} 日期分片导出")
                print(f"  日期范围: {start_date} ~ {end_date}（共 {len(all_days)} 天）")
                print(f"  已完成: {len(completed_days)} 天")
                print(f"  待导出: {len(remaining_days)} 天")
                print(f"  输出文件: {output_file}")
                print()

                for day in remaining_days:
                    day_sql = (
                        f"SELECT {field_list} FROM {table_name} "
                        f"WHERE CAST({TIME_FIELD} AS DATE) = '{day}'"
                    )
                    cursor.execute(day_sql)
                    cursor.fetchsize = BATCH_SIZE

                    day_rows = 0
                    while True:
                        rows = cursor.fetchmany(BATCH_SIZE)
                        if not rows:
                            break
                        is_first_write = _write_rows_to_csv(
                            output_file, rows, is_first_write
                        )
                        day_rows += len(rows)
                        total_exported += len(rows)

                    # 标记该天完成
                    completed_days.add(day)
                    _save_progress(
                        output_file,
                        {
                            "mode": "time",
                            "field": TIME_FIELD,
                            "completed_days": sorted(completed_days),
                            "total_exported": total_exported,
                        },
                    )
                    print(f"  [{day}] {day_rows:,} 行 ✓")

        if not can_resume_by_time:
            # ===== 全表导出（无断点续传） =====
            print(f"  表: {db_name}.{table_name}")
            print(f"  策略: 全表导出（不支持按时间分片续传）")
            print(f"  输出文件: {output_file}")
            print()

            sql = f"SELECT {field_list} FROM {table_name}"
            cursor.execute(sql)
            cursor.fetchsize = BATCH_SIZE

            pbar = tqdm(desc="导出", unit="行", unit_scale=True, ncols=80)

            while True:
                rows = cursor.fetchmany(BATCH_SIZE)
                if not rows:
                    break
                is_first_write = _write_rows_to_csv(output_file, rows, is_first_write)
                total_exported += len(rows)
                pbar.update(len(rows))

            pbar.close()

        cursor.close()
        conn.close()

        # 导出完成，删除进度文件
        _remove_progress(output_file)

        file_size = output_file.stat().st_size
        total_time = time.time() - start_time
        speed = total_exported / total_time if total_time > 0 else 0

        print()
        print("=" * 60)
        print(f"  导出完成!")
        print(f"  总记录数: {total_exported:,}")
        print(f"  文件大小: {_format_size(file_size)}")
        print(f"  总耗时:   {total_time:.1f}s")
        if speed > 0:
            print(f"  导出速度: {speed:,.0f} 行/秒")
        print(f"  输出路径: {output_file}")
        print("=" * 60)
        return True

    except KeyboardInterrupt:
        # 保存当前进度
        if can_resume_by_time and progress:
            _save_progress(output_file, progress)
        print(f"\n\n  中断! 已导出 {total_exported:,} 行")
        print(f"  进度已保存，重新运行将自动续传")
        print(f"  如需重新导出，请使用 --force 参数")
        return False

    except Exception as e:
        # 保存当前进度
        if can_resume_by_time and progress:
            _save_progress(output_file, progress)
        print(f"  导出失败: {e}")
        print(f"  已导出 {total_exported:,} 行，重新运行将自动续传")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if conn:
            conn.close()


def _format_value(v) -> str:
    """格式化单个字段值"""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace('"', '""')
    if '"' in s or "," in s or "\n" in s or "\r" in s:
        return f'"{s}"'
    return s


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def test_connection(config: dict) -> bool:
    """测试连接"""
    print("=" * 60)
    print("测试 Hive 连接...")
    print("=" * 60)

    print(f"  Host: {config['host']}:{config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  Username: {config['username']}")

    try:
        conn = hive.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            username=config["username"],
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        print(f"\n  Hive 连接成功!")
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"  Hive 连接失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Hive 通行流水数据导出（支持断点续传）"
    )
    parser.add_argument("--table", "-t", required=True, help="表名")
    parser.add_argument("--db", "-d", required=True, help="数据库名")
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="输出文件路径（默认: outputs/<table>.csv）",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制从头导出，忽略已有进度"
    )

    args = parser.parse_args()

    table_name = args.table
    db_name = args.db
    output_file = (
        Path(args.output)
        if args.output
        else project_root / "outputs" / f"{table_name}.csv"
    )

    config = get_hive_config(db_name)
    if not test_connection(config):
        sys.exit(1)

    success = export(table_name, db_name, output_file, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
