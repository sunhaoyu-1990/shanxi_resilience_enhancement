#!/usr/bin/env python
"""
M8 路径修正与折返识别 — 任务入口

用法：
    python -m src.jobs.run_m8_path_repair \\
        --input-csv data/raw_paths.csv \\
        --output-csv outputs/repaired_paths.csv

    # 限制处理条数（调试用）
    python -m src.jobs.run_m8_path_repair \\
        --input-csv data/raw_paths.csv \\
        --output-csv outputs/repaired_paths.csv \\
        --limit 100

    # 自定义拓扑版本
    python -m src.jobs.run_m8_path_repair \\
        --input-csv data/raw_paths.csv \\
        --output-csv outputs/repaired_paths.csv \\
        --topology-version 202512
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import TaskStatus
from src.common.time_utils import generate_batch_no

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="M8 路径修正与折返识别",
    )

    parser.add_argument("--input-csv", required=True, help="输入CSV文件路径")
    parser.add_argument("--output-csv", required=True, help="输出CSV文件路径")
    parser.add_argument(
        "--topology-version",
        default="202512",
        help="拓扑数据版本（默认 202512）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制处理条数（调试用，None=全部）",
    )
    parser.add_argument(
        "--config-env",
        default="dev",
        choices=["dev", "prod"],
        help="配置环境",
    )

    return parser.parse_args()


def main() -> int:
    """M8 任务主入口"""
    setup_logging()

    args = parse_args()
    batch_no = generate_batch_no(prefix="M8")

    logger.info("=" * 60)
    logger.info("M8 路径修正与折返识别任务已启动")
    logger.info(f"批次号：{batch_no}")
    logger.info(f"输入文件：{args.input_csv}")
    logger.info(f"输出文件：{args.output_csv}")
    logger.info(f"拓扑版本：{args.topology_version}")
    logger.info(f"处理限制：{args.limit or '无'}")
    logger.info("=" * 60)

    try:
        from src.modules.m8_path_repair.service import PathRepairService
        from src.modules.m8_path_repair.schema import PathRepairParams

        params = PathRepairParams(
            input_csv=args.input_csv,
            output_csv=args.output_csv,
            topology_version=args.topology_version,
            limit=args.limit,
        )

        service = PathRepairService(
            topology_version=args.topology_version,
        )

        try:
            result = service.run_batch_csv(params)
        finally:
            service.close()

        if result.status == "success":
            logger.info("=" * 60)
            logger.info("M8 任务执行成功")
            logger.info(f"总记录数：{result.totalRecords}")
            logger.info(f"成功修正：{result.successRecords}")
            logger.info(f"失败记录：{result.failedRecords}")
            logger.info(f"高置信度：{result.highConfidenceCount}")
            logger.info(f"中置信度：{result.mediumConfidenceCount}")
            logger.info(f"低置信度：{result.lowConfidenceCount}")
            logger.info(f"需人工复核：{result.needReviewCount}")
            logger.info(f"耗时：{result.executionTime:.2f}s")
            logger.info("=" * 60)
            return 0
        else:
            logger.error(f"M8 任务执行失败：{result.status}")
            for err in result.errors:
                logger.error(f"  - {err}")
            return 1

    except Exception as e:
        logger.exception(f"M8 任务执行失败：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
