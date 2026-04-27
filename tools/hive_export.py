#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hive 通行流水数据导出脚本
支持指定表名和数据库，支持断点续传
"""
import sys
import time
import argparse
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


def get_hive_config(db_name: str = None) -> dict:
    """获取 Hive 配置"""
    import os
    return {
        "host": os.getenv("HIVE_HOST", "172.16.5.1"),
        "port": int(os.getenv("HIVE_PORT", "10000")),
        "database": db_name or os.getenv("HIVE_DATABASE", "dbbase2026"),
        "username": os.getenv("HIVE_USER", "hive"),
    }


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


# ---- 进度文件管理 ----

def _progress_file(output_file: Path) -> Path:
    """进度文件路径"""
    return output_file.with_suffix(output_file.suffix + ".progress")


def _read_progress(output_file: Path) -> int:
    """读取已导出行数，0 表示无进度"""
    pf = _progress_file(output_file)
    if pf.exists():
        try:
            return int(pf.read_text().strip())
        except ValueError:
            return 0
    return 0


def _write_progress(output_file: Path, exported: int):
    """写入已导出行数"""
    pf = _progress_file(output_file)
    pf.write_text(str(exported))


def _remove_progress(output_file: Path):
    """删除进度文件"""
    pf = _progress_file(output_file)
    if pf.exists():
        pf.unlink()


def _count_csv_rows(output_file: Path) -> int:
    """统计 CSV 数据行数（不含表头）"""
    if not output_file.exists():
        return 0
    count = 0
    with open(output_file, encoding="utf-8") as f:
        next(f, None)  # skip header
        for _ in f:
            count += 1
    return count


def _check_resume(output_file: Path, force: bool) -> int:
    """
    检查是否可续传，返回跳过的行数
    - force=True: 删除旧文件，返回 0
    - 有有效进度: 返回已导出行数
    - 无效进度: 报错退出
    """
    pf = _progress_file(output_file)

    if force:
        if output_file.exists():
            output_file.unlink()
            print("  --force: 已删除旧 CSV")
        if pf.exists():
            pf.unlink()
            print("  --force: 已删除旧进度文件")
        return 0

    if not output_file.exists() or not pf.exists():
        # 没有可续传的文件，全新导出
        if output_file.exists():
            print("  发现旧 CSV 但无进度文件，将从零开始（旧文件将被覆盖）")
        return 0

    # 有 CSV + 有 .progress，校验一致性
    progress_count = _read_progress(output_file)
    csv_rows = _count_csv_rows(output_file)

    if progress_count == csv_rows:
        print(f"  发现有效进度: 已导出 {progress_count:,} 行，将续传")
        return progress_count
    else:
        print(f"  进度不一致: .progress={progress_count:,}, CSV实际行数={csv_rows:,}")
        print(f"  建议使用 --force 强制重新导出")
        sys.exit(1)


def export(table_name: str, db_name: str, output_file: Path, force: bool = False) -> bool:
    """导出数据到 CSV，支持断点续传"""
    print("\n" + "=" * 60)
    print("导出数据...")
    print("=" * 60)

    skip_rows = _check_resume(output_file, force)
    is_resume = skip_rows > 0

    config = get_hive_config(db_name)
    field_list = ", ".join(FIELDS)
    sql = f"SELECT {field_list} FROM {table_name}"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        conn = hive.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            username=config["username"],
        )
        cursor = conn.cursor()

        # 获取总数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]

        mode_label = "续传" if is_resume else "全新"
        print(f"  表: {db_name}.{table_name}")
        print(f"  SQL: {sql}")
        print(f"  模式: {mode_label}")
        print(f"  输出文件: {output_file}")
        print(f"  总记录数: {total_count:,}")
        if is_resume:
            print(f"  已导出:   {skip_rows:,}")
            print(f"  待导出:   {total_count - skip_rows:,}")
        print(f"  分批大小: {BATCH_SIZE:,}")
        print()

        # 查询全量数据
        cursor.execute(sql)
        cursor.fetchsize = BATCH_SIZE

        # 跳过已导出的行
        exported = 0
        if skip_rows > 0:
            print(f"  跳过已导出的 {skip_rows:,} 行...")
            skipped = 0
            skip_pbar = tqdm(total=skip_rows, desc="跳过", unit="行", unit_scale=True, ncols=80)
            while skipped < skip_rows:
                batch = min(BATCH_SIZE, skip_rows - skipped)
                cursor.fetchmany(batch)
                skipped += batch
                skip_pbar.update(batch)
            skip_pbar.close()
            exported = skip_rows
            print()

        # 写入数据
        is_first_write = not is_resume
        pbar = tqdm(
            total=total_count,
            desc="导出",
            unit="行",
            unit_scale=True,
            ncols=80,
            initial=exported,
        )

        while True:
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break

            with open(output_file, "a" if not is_first_write else "w", encoding="utf-8", newline="") as f:
                if is_first_write:
                    f.write(",".join(FIELDS) + "\n")
                for row in rows:
                    f.write(",".join(_format_value(v) for v in row) + "\n")

            is_first_write = False
            exported += len(rows)
            _write_progress(output_file, exported)
            pbar.update(len(rows))

        pbar.close()
        cursor.close()
        conn.close()

        # 导出完成，删除进度文件
        _remove_progress(output_file)

        file_size = output_file.stat().st_size
        total_time = time.time() - start_time
        speed = (total_count - skip_rows) / total_time if total_time > 0 and total_count > skip_rows else 0

        print()
        print("=" * 60)
        print(f"  导出完成!")
        print(f"  总记录数: {total_count:,}")
        if is_resume:
            print(f"  本次导出: {total_count - skip_rows:,}")
        print(f"  文件大小: {_format_size(file_size)}")
        print(f"  总耗时:   {total_time:.1f}s")
        if speed > 0:
            print(f"  导出速度: {speed:,.0f} 行/秒")
        print(f"  输出路径: {output_file}")
        print("=" * 60)
        return True

    except KeyboardInterrupt:
        # Ctrl+C 中断，保留进度文件以便续传
        print(f"\n\n  中断! 已导出 {exported:,} 行")
        print(f"  进度已保存，重新运行将自动续传")
        print(f"  如需重新导出，请使用 --force 参数")
        _write_progress(output_file, exported)
        return False

    except Exception as e:
        # 异常中断，也保留进度
        _write_progress(output_file, exported)
        print(f"  导出失败: {e}")
        print(f"  已导出 {exported:,} 行，重新运行将自动续传")
        import traceback
        traceback.print_exc()
        return False


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


def main():
    parser = argparse.ArgumentParser(description="Hive 通行流水数据导出（支持断点续传）")
    parser.add_argument("--table", "-t", required=True, help="表名")
    parser.add_argument("--db", "-d", required=True, help="数据库名")
    parser.add_argument("--output", "-o", default=None, help="输出文件路径（默认: outputs/<table>.csv）")
    parser.add_argument("--force", "-f", action="store_true", help="强制从头导出，忽略已有进度")

    args = parser.parse_args()

    table_name = args.table
    db_name = args.db
    output_file = Path(args.output) if args.output else project_root / "outputs" / f"{table_name}.csv"

    config = get_hive_config(db_name)
    if not test_connection(config):
        sys.exit(1)

    success = export(table_name, db_name, output_file, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
