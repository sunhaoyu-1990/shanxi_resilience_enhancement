#!/usr/bin/env python
"""
M0 数据工程 - 任务入口

用法：
    python -m src.jobs.run_m0 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30
    python -m src.jobs.run_m0 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30 --overwrite
"""

import argparse
import sys
from pathlib import Path

# 将项目根目录加入路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import ModuleCode, TaskStatus
from src.common.time_utils import parse_date, generate_batch_no

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
  """解析命令行参数"""
  parser = argparse.ArgumentParser(
    description="M0 数据工程 - 加载并准备源数据",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
示例：
  python -m src.jobs.run_m0 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30
  python -m src.jobs.run_m0 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30 --overwrite
    """,
  )

  parser.add_argument(
    "--scheme-id",
    required=True,
    help="施工方案ID",
  )
  parser.add_argument(
    "--start-date",
    required=True,
    help="开始日期（YYYY-MM-DD）",
  )
  parser.add_argument(
    "--end-date",
    required=True,
    help="结束日期（YYYY-MM-DD）",
  )
  parser.add_argument(
    "--overwrite",
    action="store_true",
    help="覆盖已有数据",
  )
  parser.add_argument(
    "--config-env",
    default="dev",
    choices=["dev", "prod"],
    help="配置环境",
  )

  return parser.parse_args()


def main() -> int:
  """
  M0 任务主入口

  返回：
    退出码（0 成功，非 0 失败）
  """
  # 初始化日志
  setup_logging()

  # 解析参数
  args = parse_args()

  # 记录批次信息
  batch_no = generate_batch_no(prefix="M0")
  logger.info("=" * 60)
  logger.info(f"M0 数据工程任务已启动")
  logger.info(f"批次号：{batch_no}")
  logger.info(f"方案ID：{args.scheme_id}")
  logger.info(f"日期范围：{args.start_date} ~ {args.end_date}")
  logger.info(f"是否覆盖：{args.overwrite}")
  logger.info("=" * 60)

  try:
    # 校验日期
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    if start_date > end_date:
      logger.error(f"开始日期 {start_date} 晚于结束日期 {end_date}")
      return 1

    # 导入并运行 M0 服务
    from src.modules.m0_data_engineering.service import M0Service

    service = M0Service()
    result = service.run(
      schemeId=args.scheme_id,
      startDate=str(start_date),
      endDate=str(end_date),
      overwrite=args.overwrite,
    )

    if result.status == TaskStatus.SUCCESS:
      logger.info("=" * 60)
      logger.info(f"M0 数据工程任务执行成功")
      logger.info(f"已处理记录数：{result.recordsProcessed}")
      logger.info(f"批次号：{batch_no}")
      logger.info("=" * 60)
      return 0
    else:
      logger.error("=" * 60)
      logger.error(f"M0 数据工程任务执行失败")
      logger.error(f"状态：{result.status}")
      if result.errors:
        for error in result.errors:
          logger.error(f"错误信息：{error}")
      logger.error("=" * 60)
      return 1

  except KeyboardInterrupt:
    logger.warning("M0 任务被用户中断")
    return 130
  except Exception as e:
    logger.exception(f"M0 任务异常退出：{e}")
    return 1


if __name__ == "__main__":
  sys.exit(main())
