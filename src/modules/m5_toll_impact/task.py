"""
M5 通行费影响测算任务入口
解析命令行参数并执行 M5 服务
"""

import argparse
import sys
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import ModuleCode, TaskStatus
from src.common.time_utils import parse_date, generate_batch_no
from src.modules.m5_toll_impact.service import M5Service

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
  """解析命令行参数"""
  parser = argparse.ArgumentParser(
    description="M5 通行费影响测算 - 计算分流方案的费用影响",
  )

  parser.add_argument("--scheme-id", required=True, help="施工方案ID")
  parser.add_argument("--start-date", required=True, help="开始日期 (YYYY-MM-DD)")
  parser.add_argument("--end-date", required=True, help="结束日期 (YYYY-MM-DD)")
  parser.add_argument("--overwrite", action="store_true", help="覆盖已有数据")

  return parser.parse_args()


def main() -> int:
  """M5 任务主入口"""
  setup_logging()

  args = parse_args()
  batch_no = generate_batch_no(prefix="M5")

  logger.info("=" * 60)
  logger.info(f"M5 通行费影响测算任务已启动")
  logger.info(f"批次号: {batch_no}")
  logger.info(f"方案ID: {args.scheme_id}")
  logger.info(f"日期范围: {args.start_date} ~ {args.end_date}")
  logger.info(f"覆盖已有数据: {args.overwrite}")
  logger.info("=" * 60)

  try:
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    service = M5Service()
    result = service.run(
      schemeId=args.scheme_id,
      startDate=str(start_date),
      endDate=str(end_date),
      overwrite=args.overwrite,
    )

    if result.status == TaskStatus.SUCCESS:
      logger.info("=" * 60)
      logger.info(f"M5 通行费影响测算任务成功完成")
      logger.info(f"已处理记录数: {result.recordsProcessed}")
      logger.info(f"执行时间: {result.executionTime:.2f}s")
      if result.warnings:
        logger.warning(f"警告: {result.warnings}")
      logger.info("=" * 60)
      return 0
    else:
      logger.error("=" * 60)
      logger.error(f"M5 通行费影响测算任务失败")
      logger.error(f"错误: {result.errors}")
      logger.error("=" * 60)
      return 1

  except Exception as e:
    logger.exception(f"M5 任务执行异常: {e}")
    return 1


if __name__ == "__main__":
  sys.exit(main())
