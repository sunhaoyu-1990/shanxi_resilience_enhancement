#!/usr/bin/env python
"""
M2 流量与 OD 迁移统计 - 任务入口

用法：
    python -m src.jobs.run_m2 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import ModuleCode, TaskStatus
from src.common.time_utils import parse_date, generate_batch_no

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
  """解析命令行参数"""
  parser = argparse.ArgumentParser(
    description="M2 流量与 OD 迁移统计",
  )

  parser.add_argument("--scheme-id", required=True, help="施工方案ID")
  parser.add_argument("--start-date", required=True, help="开始日期（YYYY-MM-DD）")
  parser.add_argument("--end-date", required=True, help="结束日期（YYYY-MM-DD）")
  parser.add_argument("--overwrite", action="store_true", help="覆盖已有数据")
  parser.add_argument("--config-env", default="dev", choices=["dev", "prod"])

  return parser.parse_args()


def main() -> int:
  """M2 任务主入口"""
  setup_logging()

  args = parse_args()
  batch_no = generate_batch_no(prefix="M2")

  logger.info("=" * 60)
  logger.info(f"M2 流量统计任务已启动")
  logger.info(f"批次号：{batch_no}")
  logger.info(f"方案ID：{args.scheme_id}")
  logger.info(f"日期范围：{args.start_date} ~ {args.end_date}")
  logger.info("=" * 60)

  try:
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    from src.modules.m2_flow_od_completion.service import M2Service

    service = M2Service()
    result = service.run(
      schemeId=args.scheme_id,
      startDate=str(start_date),
      endDate=str(end_date),
      overwrite=args.overwrite,
    )

    if result.status == TaskStatus.SUCCESS:
      logger.info("=" * 60)
      logger.info(f"M2 任务执行成功")
      logger.info(f"已处理记录数：{result.recordsProcessed}")
      logger.info("=" * 60)
      return 0
    else:
      logger.error(f"M2 任务执行失败：{result.status}")
      return 1

  except Exception as e:
    logger.exception(f"M2 任务执行失败：{e}")
    return 1


if __name__ == "__main__":
  sys.exit(main())
