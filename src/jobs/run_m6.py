#!/usr/bin/env python
"""
M6 OD-Section-Path 映射构建 - 任务入口

用法：
    # 测试模式（100条，串行，结果存本地）
    uv run python -m src.jobs.run_m6 \
        --version 202603 \
        --batch-size 100 \
        --save-local

    # 全量模式（50万条/批，2个worker并行，直接落库）
    uv run python -m src.jobs.run_m6 \
        --version 202603 \
        --batch-size 500000 \
        --workers 2
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import TaskStatus
from src.modules.m6_od_section_path.service import M6Service
from src.modules.m6_od_section_path.schema import M6TaskParams


def version_to_database(version: str) -> str:
    yy = int(version[:4])
    if yy >= 2026:
        return 'dbbase2026'
    else:
        return 'dbbase2025'


def version_to_topo_version(data_version: str) -> str:
    yy = int(data_version[:4])
    mm = int(data_version[4:6])
    if yy >= 2026:
        # 2026 年数据用 202512 拓扑
        return '202512'
    elif yy == 2025 and mm >= 7:
        # 2025/07 起有 202507 拓扑
        return '202507'
    else:
        # 更早的数据用最早可用拓扑
        return '202412'

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="M6 OD-Section-Path 映射构建",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 测试模式 - 小批量验证
  uv run python -m src.jobs.run_m6 --version 202603 --batch-size 100 --save-local

  # 全量模式 - 批量处理
  uv run python -m src.jobs.run_m6 --version 202603 --batch-size 500000
        """,
    )
    parser.add_argument(
        "--version",
        default="202603",
        help="版本年月，自动设置 Hive 表名和数据库（默认: 202603）",
    )
    parser.add_argument(
        "--hive-table",
        default=None,
        help="Hive 表名（默认根据 --version 自动生成）",
    )
    parser.add_argument(
        "--hive-database",
        default=None,
        help="Hive 数据库（默认根据 --version 自动切换: dbbase2025/dbbase2026）",
    )
    parser.add_argument(
        "--section-version",
        default=None,
        help="dwd_section_path 表的版本年月（默认: 同 --version）",
    )
    parser.add_argument(
        "--topo-version",
        default=None,
        help="拓扑数据版本（默认根据 --version 自动选择）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500_000,
        help="每批处理记录数（默认: 500000，测试时用100）",
    )
    parser.add_argument(
        "--save-local",
        action="store_true",
        help="保存结果到本地 JSON（测试模式）",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/m6_test",
        help="本地输出目录（默认: outputs/m6_test）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="并行 worker 进程数（默认: 2，适合 2GB RAM；全量模式自动启用并行；测试模式自动用串行）",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()

    # Auto-derive hive table and database from version
    hive_table = args.hive_table or f"gstx_exit_with_min_fee{args.version}"
    hive_database = args.hive_database or version_to_database(args.version)
    section_version = args.section_version or args.version
    topo_version = args.topo_version or version_to_topo_version(args.version)

    logger.info("=" * 60)
    logger.info("M6 OD-Section-Path 映射构建任务已启动")
    logger.info(f"版本: {args.version}")
    logger.info(f"Hive 数据库: {hive_database}")
    logger.info(f"Hive 表: {hive_table}")
    logger.info(f"拓扑版本: {topo_version}")
    logger.info(f"批次大小: {args.batch_size:,}")
    logger.info(f"并行 worker: {args.workers}")
    logger.info(f"测试模式: {args.save_local}")
    logger.info("=" * 60)

    params = M6TaskParams(
        hive_table=hive_table,
        hive_database=hive_database,
        version_yyyyMM=args.version,
        section_version=section_version,
        topo_version=topo_version,
        batch_size=args.batch_size,
        save_local=args.save_local,
        output_dir=args.output_dir,
    )

    # Ensure checkpoint table exists
    from src.modules.m6_od_section_path.repository import M6Repository
    repo = M6Repository()
    repo.create_checkpoint_table()

    service = M6Service(workers=args.workers)
    service.checkpoint_table_name = hive_table
    service.checkpoint_enabled = True
    result = service.run(params)

    if result.status == TaskStatus.SUCCESS:
        logger.info("=" * 60)
        logger.info("M6 任务成功完成")
        logger.info(f"处理记录: {result.records_processed:,}")
        logger.info(f"批次数量: {result.batches}")
        logger.info(f"map 记录: {result.maps_written:,}")
        logger.info(f"freq 记录: {result.freq_written:,}")
        logger.info(f"执行时间: {result.execution_time:.2f}s")
        if result.local_output_path:
            logger.info(f"本地输出: {result.local_output_path}")
        if result.warnings:
            logger.warning(f"警告: {result.warnings}")
        logger.info("=" * 60)
        return 0
    else:
        logger.error(f"M6 任务失败: {result.errors}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
