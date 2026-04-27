#!/usr/bin/env python
"""
M6 批量运行入口（多版本 / 多表）

支持：
1. 指定版本范围，自动切换 Hive 数据库和表名
2. checkpoint 断点续跑（running 状态自动跳过）
3. 每批次实时 upsert，内存占用小
4. rank 在所有版本、所有批次完成后统一计算

数据库规则：
  - version >= 202601 → dbbase2026
  - version <= 202512 → dbbase2025

用法：
    # 单版本测试（100条）
    uv run python -m src.jobs.run_m6 --version 202603 --batch-size 100 --save-local

    # 单版本全量
    uv run python -m src.jobs.run_m6 --version 202603 --batch-size 500000 --workers 2

    # 多版本连续运行（202512 ~ 202603）
    uv run python -m src.jobs.run_m6_batch --start-version 202512 --end-version 202603 --batch-size 500000 --workers 2

    # 断点续跑（自动跳过已完成的版本）
    uv run python -m src.jobs.run_m6_batch --start-version 202512 --end-version 202603 --batch-size 500000 --workers 2

    # 仅查看运行状态
    uv run python -m src.jobs.run_m6_batch --status

    # 重置指定版本 checkpoint（从头重跑）
    uv run python -m src.jobs.run_m6_batch --reset-version 202603

    # 只计算 rank（已有 freq 数据时使用）
    uv run python -m src.jobs.run_m6_batch --compute-rank --version 202603
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import TaskStatus
from src.modules.m6_od_section_path.repository import M6Repository
from src.modules.m6_od_section_path.schema import M6TaskParams
from src.modules.m6_od_section_path.service import M6Service

logger = get_logger(__name__)


def version_to_database(version: str) -> str:
    """根据版本号自动选择 Hive 数据库。"""
    yy = int(version[:4])
    if yy >= 2026:
        return "dbbase2026"
    else:
        return "dbbase2025"


def version_to_topo_version(data_version: str) -> str:
    """根据数据版本自动选择拓扑版本（topo <= 数据月份）。"""
    yy = int(data_version[:4])
    mm = int(data_version[4:6])
    if yy >= 2026:
        # 2026 年数据用 202512 拓扑
        return "202512"
    elif yy == 2025 and mm >= 7:
        # 2025/07 起有 202507 拓扑
        return "202507"
    else:
        # 更早的数据用最早可用拓扑
        return "202412"


def parse_version_list(start: str, end: str) -> list[str]:
    """生成 [start, end] 范围内的版本列表（按时间升序）。"""
    yy_s, mm_s = int(start[:4]), int(start[4:6])
    yy_e, mm_e = int(end[:4]), int(end[4:6])

    versions = []
    yy, mm = yy_s, mm_s
    while (yy < yy_e) or (yy == yy_e and mm <= mm_e):
        versions.append(f"{yy}{mm:02d}")
        mm += 1
        if mm > 12:
            mm = 1
            yy += 1
    return versions


def run_single_version(
    version: str,
    batch_size: int,
    workers: int,
    skip_completed: bool = True,
) -> bool:
    """
    运行单个版本的 M6 处理。

    Returns:
        True = 成功，False = 失败/Skipped
    """
    repo = M6Repository()
    hive_db = version_to_database(version)
    topo_version = version_to_topo_version(version)
    hive_table = f"gstx_exit_with_min_fee{version}"

    # Checkpoint 续跑逻辑
    if skip_completed:
        cp = repo.get_checkpoint(hive_table, version)
        if cp and cp["status"] == "completed":
            logger.info(f"版本 {version} 已完成，跳过（status=completed）")
            return True
        elif cp and cp["status"] == "running":
            offset = cp["batch_offset"]
            logger.info(f"版本 {version} checkpoint 续跑，从 offset={offset} 继续...")

    # 确保 checkpoint 已初始化
    repo.init_checkpoint([(hive_table, version, topo_version)])

    params = M6TaskParams(
        hive_table=hive_table,
        hive_database=hive_db,
        version_yyyyMM=version,
        section_version=version,
        topo_version=topo_version,
        batch_size=batch_size,
        save_local=False,
    )

    service = M6Service(workers=workers)
    service.checkpoint_table_name = hive_table
    service.checkpoint_enabled = True
    result = service.run(params)

    if result.status == TaskStatus.SUCCESS:
        repo.complete_checkpoint(hive_table, version)
        logger.info(f"版本 {version} 完成（{result.batches} 批次，{result.records_processed:,} 条记录）")
        return True
    else:
        logger.error(f"版本 {version} 失败: {result.errors}")
        return False


def cmd_status() -> None:
    """查看所有 checkpoint 状态。"""
    repo = M6Repository()
    rows = repo.get_all_checkpoints()

    if not rows:
        print("暂无 checkpoint 记录")
        return

    print(f"{'版本':<10} {'表名':<35} {'offset':>10} {'processed':>12} {'status':<12} {'topo':<8} {'updated_at'}")
    print("-" * 100)
    for r in rows:
        print(
            f"{r['version_yyyymm']:<10} "
            f"{r['table_name']:<35} "
            f"{r['batch_offset']:>10} "
            f"{r['records_processed']:>12} "
            f"{r['status']:<12} "
            f"{r['topo_version']:<8} "
            f"{r.get('updated_at', '')}"
        )


def cmd_reset_version(version: str) -> None:
    """重置指定版本的 checkpoint（从头重跑）。"""
    repo = M6Repository()
    # 找到对应的 table_name
    rows = repo.get_all_checkpoints()
    matched = [r for r in rows if r["version_yyyymm"] == version]
    if not matched:
        logger.error(f"未找到版本 {version} 的 checkpoint 记录")
        return
    for r in matched:
        repo.reset_checkpoint(r["table_name"], version)
        logger.info(f"已重置 {r['table_name']}@{version}，offset=0, status=running")


def cmd_compute_rank(version: Optional[str]) -> None:
    """计算 ig_rank 并派生 map 表。"""
    repo = M6Repository()
    if version:
        logger.info(f"计算 ig_rank (version={version})...")
        cnt = repo.compute_ig_rank(version)
        logger.info(f"ig_rank 计算完成: {cnt} 条")
        logger.info(f"派生 map 表 (version={version})...")
        map_cnt = repo.derive_map_from_freq(version)
        logger.info(f"map 表派生完成: {map_cnt} 条")
    else:
        logger.info("计算所有版本的 ig_rank...")
        cnt = repo.compute_ig_rank()
        logger.info(f"ig_rank 计算完成: {cnt} 条")
        logger.info("派生所有版本的 map 表...")
        # derive_map_from_freq 需要 version 参数，这里对所有 version 循环
        rows = repo.get_all_checkpoints()
        for r in rows:
            v = r["version_yyyymm"]
            mc = repo.derive_map_from_freq(v)
            logger.info(f"  {v}: {mc} 条 map")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="M6 批量运行（支持多版本 / 断点续跑）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 版本范围
    parser.add_argument("--start-version", help="起始版本（如 202512）")
    parser.add_argument("--end-version", help="结束版本（如 202603）")
    parser.add_argument("--version", help="单版本运行")

    # 处理参数
    parser.add_argument("--batch-size", type=int, default=500_000,
                        help="每批处理记录数（默认 500000）")
    parser.add_argument("--workers", type=int, default=2,
                        help="并行 worker 数（默认 2，适合 2GB RAM）")

    # 控制命令
    parser.add_argument("--status", action="store_true", help="查看 checkpoint 状态")
    parser.add_argument("--reset-version", metavar="VERSION",
                        help="重置指定版本的 checkpoint（从断点重跑）")
    parser.add_argument("--compute-rank", action="store_true",
                        help="仅计算 ig_rank 并派生 map（已有 freq 数据时使用）")

    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()

    # --status
    if args.status:
        cmd_status()
        return 0

    # --reset-version
    if args.reset_version:
        cmd_reset_version(args.reset_version)
        return 0

    # --compute-rank
    if args.compute_rank:
        cmd_compute_rank(args.version)
        return 0

    # 确定版本列表
    if args.version:
        versions = [args.version]
    elif args.start_version and args.end_version:
        versions = parse_version_list(args.start_version, args.end_version)
    else:
        logger.error("请指定 --version 或 --start-version + --end-version")
        return 1

    logger.info("=" * 60)
    logger.info(f"M6 批量运行")
    logger.info(f"版本范围: {versions[0]} ~ {versions[-1]}（共 {len(versions)} 个版本）")
    logger.info(f"批次大小: {args.batch_size:,}")
    logger.info(f"并行 worker: {args.workers}")
    logger.info("=" * 60)

    # 确保 checkpoint 表存在
    repo = M6Repository()
    repo.create_checkpoint_table()

    success_count = 0
    fail_count = 0
    skip_count = 0

    for version in versions:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"开始处理版本: {version}")
        logger.info(f"{'=' * 50}")

        hive_db = version_to_database(version)
        topo_v = version_to_topo_version(version)
        logger.info(f"  Hive 数据库: {hive_db}")
        logger.info(f"  Hive 表名: gstx_exit_with_min_fee{version}")
        logger.info(f"  拓扑版本: {topo_v}")

        ok = run_single_version(
            version=version,
            batch_size=args.batch_size,
            workers=args.workers,
            skip_completed=True,
        )
        if ok:
            success_count += 1
        else:
            fail_count += 1

    logger.info(f"\n{'=' * 60}")
    logger.info("M6 批量运行完成")
    logger.info(f"  成功: {success_count} 个版本")
    logger.info(f"  失败: {fail_count} 个版本")
    logger.info("=" * 60)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
