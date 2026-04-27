#!/usr/bin/env python
"""
流水线总控模块 - 按顺序执行 M0 ~ M5

Usage:
    python -m src.jobs.run_pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30
    python -m src.jobs.run_pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30 --modules m0 m1 m2
    python -m src.jobs.run_pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30 --stop-on-error
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.app.logger import get_logger, setup_logging
from src.app.enums import ModuleCode, TaskStatus
from src.common.time_utils import parse_date, generate_batch_no

logger = get_logger(__name__)

# 模块执行顺序
MODULE_ORDER = ["m0", "m1", "m2", "m3", "m4", "m5"]


def parse_args() -> argparse.Namespace:
  """解析命令行参数"""
  parser = argparse.ArgumentParser(
    description="流水线总控 - 按顺序执行 M0 ~ M5",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
示例:
  # 运行完整流水线
  python -m src.jobs.run_pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30

  # 只运行指定模块
  python -m src.jobs.run_pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30 --modules m0 m1 m2

  # 出错时继续执行后续模块
  python -m src.jobs.run_pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30 --continue-on-error
    """,
  )

  parser.add_argument("--scheme-id", required=True, help="施工方案ID")
  parser.add_argument("--start-date", required=True, help="开始日期 (YYYY-MM-DD)")
  parser.add_argument("--end-date", required=True, help="结束日期 (YYYY-MM-DD)")
  parser.add_argument(
    "--modules",
    nargs="+",
    choices=MODULE_ORDER,
    default=MODULE_ORDER,
    help=f"要执行的模块（默认全部）: {' '.join(MODULE_ORDER)}",
  )
  parser.add_argument(
    "--overwrite",
    action="store_true",
    help="覆盖已有数据",
  )
  parser.add_argument(
    "--stop-on-error",
    action="store_true",
    default=True,
    help="模块失败时停止流水线（默认: True）",
  )
  parser.add_argument(
    "--continue-on-error",
    action="store_false",
    dest="stop_on_error",
    help="模块失败时继续执行后续模块",
  )
  parser.add_argument(
    "--config-env",
    default="dev",
    choices=["dev", "prod"],
    help="配置环境",
  )

  return parser.parse_args()


class PipelineResult:
  """流水线执行结果"""

  def __init__(self):
    self.module_results: dict[str, dict] = {}
    self.start_time: Optional[datetime] = None
    self.end_time: Optional[datetime] = None
    self.success = False

  @property
  def duration_seconds(self) -> float:
    """获取总耗时（秒）"""
    if self.start_time and self.end_time:
      return (self.end_time - self.start_time).total_seconds()
    return 0.0

  def add_module_result(self, module: str, status: TaskStatus, records: int = 0, errors: list[str] | None = None):
    """添加模块执行结果"""
    self.module_results[module] = {
      "status": status,
      "recordsProcessed": records,
      "errors": errors or [],
    }

  def get_summary(self) -> dict:
    """获取流水线执行摘要"""
    return {
      "totalModules": len(self.module_results),
      "successful": sum(1 for r in self.module_results.values() if r["status"] == TaskStatus.SUCCESS),
      "failed": sum(1 for r in self.module_results.values() if r["status"] == TaskStatus.FAILED),
      "durationSeconds": self.duration_seconds,
      "moduleResults": self.module_results,
    }


def run_module(module_code: ModuleCode, scheme_id: str, start_date: str, end_date: str, overwrite: bool) -> tuple[TaskStatus, int, list[str]]:
  """
  执行单个模块

  Args:
    module_code: 要执行的模块
    scheme_id: 方案ID
    start_date: 开始日期
    end_date: 结束日期
    overwrite: 是否覆盖已有数据

  Returns:
    (status, records_processed, errors) 元组
  """
  logger.info(f"[{module_code.value}] 正在启动模块...")

  try:
    # 导入对应的 Service
    if module_code == ModuleCode.M0:
      from src.modules.m0_data_engineering.service import M0Service
      service = M0Service()
    elif module_code == ModuleCode.M1:
      from src.modules.m1_capacity.service import M1Service
      service = M1Service()
    elif module_code == ModuleCode.M2:
      from src.modules.m2_flow_od_completion.service import M2Service
      service = M2Service()
    elif module_code == ModuleCode.M3:
      from src.modules.m3_impact_analysis.service import M3Service
      service = M3Service()
    elif module_code == ModuleCode.M4:
      from src.modules.m4_path_optimization.service import M4Service
      service = M4Service()
    elif module_code == ModuleCode.M5:
      from src.modules.m5_toll_impact.service import M5Service
      service = M5Service()
    else:
      return TaskStatus.FAILED, 0, [f"未知模块: {module_code}"]

    # 执行 Service
    result = service.run(
      schemeId=scheme_id,
      startDate=start_date,
      endDate=end_date,
      overwrite=overwrite,
    )

    logger.info(f"[{module_code.value}] 模块执行完成，状态: {result.status}")
    return result.status, result.recordsProcessed, result.errors or []

  except Exception as e:
    logger.exception(f"[{module_code.value}] 模块执行失败: {e}")
    return TaskStatus.FAILED, 0, [str(e)]


def main() -> int:
  """流水线主入口"""
  setup_logging()

  args = parse_args()
  pipeline_id = generate_batch_no(prefix="PIPELINE")

  logger.info("=" * 70)
  logger.info(f"流水线总控启动")
  logger.info(f"流水线ID: {pipeline_id}")
  logger.info(f"方案ID: {args.scheme_id}")
  logger.info(f"日期范围: {args.start_date} ~ {args.end_date}")
  logger.info(f"执行模块: {' -> '.join(args.modules)}")
  logger.info(f"覆盖已有数据: {args.overwrite}")
  logger.info(f"出错时停止: {args.stop_on_error}")
  logger.info("=" * 70)

  # 校验日期
  try:
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    if start_date > end_date:
      logger.error(f"开始日期 {start_date} 不能晚于结束日期 {end_date}")
      return 1
  except Exception as e:
    logger.error(f"日期格式无效: {e}")
    return 1

  # 初始化流水线结果
  pipeline_result = PipelineResult()
  pipeline_result.start_time = datetime.now()

  # 按顺序执行模块
  for module_name in args.modules:
    module_code = ModuleCode(module_name)

    status, records, errors = run_module(
      module_code,
      args.scheme_id,
      str(start_date),
      str(end_date),
      args.overwrite,
    )

    pipeline_result.add_module_result(module_name, status, records, errors)

    if status == TaskStatus.FAILED and args.stop_on_error:
      logger.error(f"[{module_name}] 模块执行失败，停止流水线")
      break

  # 完成流水线
  pipeline_result.end_time = datetime.now()

  # 输出摘要
  summary = pipeline_result.get_summary()

  logger.info("=" * 70)
  logger.info("流水线执行摘要")
  logger.info("=" * 70)
  logger.info(f"总模块数: {summary['totalModules']}")
  logger.info(f"成功: {summary['successful']}")
  logger.info(f"失败: {summary['failed']}")
  logger.info(f"总耗时: {summary['durationSeconds']:.2f} 秒")
  logger.info("-" * 70)

  for module_name, result in summary["moduleResults"].items():
    status_symbol = "✓" if result["status"] == TaskStatus.SUCCESS else "✗"
    logger.info(f"  {status_symbol} {module_name.upper()}: {result['status']} ({result['recordsProcessed']} 条记录)")

  logger.info("=" * 70)

  # 返回退出码
  if summary["failed"] > 0:
    logger.error(f"流水线执行完成，其中 {summary['failed']} 个模块失败")
    return 1
  else:
    logger.info("流水线执行成功")
    return 0


if __name__ == "__main__":
  sys.exit(main())
