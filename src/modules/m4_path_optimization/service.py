"""
M4 分流路径优化服务
分流路径优化主编排逻辑
"""

import time
from typing import Optional

from src.app.enums import ModuleCode, TaskStatus
from src.app.logger import get_logger, LoggerMixin
from src.modules.m4_path_optimization.repository import M4Repository
from src.modules.m4_path_optimization.schema import M4TaskParams, M4TaskResult


logger = get_logger(__name__)


class M4Service(LoggerMixin):
  """M4 分流路径优化服务"""

  def __init__(self):
    self.repository = M4Repository()
    self.module_code = ModuleCode.M4

  def run(
    self,
    schemeId: str,
    startDate: str,
    endDate: str,
    overwrite: bool = False,
  ) -> M4TaskResult:
    """
    运行 M4 分流路径优化

    参数:
      schemeId: 施工方案ID
      startDate: 开始日期
      endDate: 结束日期
      overwrite: 是否覆盖已有数据

    返回:
      包含执行状态的 M4TaskResult
    """
    start_time = time.time()
    params = {
      "scheme_id": schemeId,
      "start_date": startDate,
      "end_date": endDate,
      "overwrite": overwrite,
    }

    total_records = 0
    errors = []
    warnings = []

    logger.info(f"开始对方案 {schemeId} 进行 M4 分流路径优化")

    try:
      # 步骤 1: 构建候选分流路径
      logger.info("步骤 1/4: 构建候选分流路径...")
      candidate_count = self.repository.build_od_candidate_path(params)
      total_records += candidate_count
      logger.info(f"  已构建 {candidate_count} 条候选路径记录")

      # 步骤 2: 构建分流方案
      logger.info("步骤 2/4: 构建分流方案...")
      plan_count = self.repository.build_od_diversion_plan(params)
      total_records += plan_count
      logger.info(f"  已构建 {plan_count} 条分流方案记录")

      # 步骤 3: 按状态分析分流情况
      logger.info("步骤 3/4: 按状态分析分流情况...")
      plans_by_status = self.repository.get_plan_by_status(params)
      for status in plans_by_status:
        logger.info(
          f"  状态 '{status['plan_status']}': "
          f"{status['plan_count']} 个方案, "
          f"{status['total_flow']} PCU 已分流"
        )

      # 步骤 4: 验证输出
      logger.info("步骤 4/4: 验证输出...")
      candidate_validation = self.repository.validate_od_candidate_path()
      if not candidate_validation.get("valid", False):
        warnings.append(
          f"候选路径验证警告: {candidate_validation.get('error', '未知')}"
        )

      plan_validation = self.repository.validate_od_diversion_plan()
      if not plan_validation.get("valid", False):
        warnings.append(
          f"分流方案验证警告: {plan_validation.get('error', '未知')}"
        )

      # 检查路径对比指标
      metrics_check = self.repository.check_path_comparison_metrics(params)
      if not metrics_check.get("valid", False):
        incorrect = metrics_check.get("incorrect_count", 0)
        warnings.append(f"发现 {incorrect} 条路径对比指标错误的记录")

      execution_time = time.time() - start_time

      logger.info(f"M4 分流路径优化完成，耗时 {execution_time:.2f}s")
      logger.info(f"已处理记录总数: {total_records}")

      return M4TaskResult(
        status=TaskStatus.SUCCESS,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

    except Exception as e:
      execution_time = time.time() - start_time
      logger.exception(f"M4 分流路径优化失败: {e}")
      errors.append(str(e))

      return M4TaskResult(
        status=TaskStatus.FAILED,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

  def build_candidate_paths(self, params: dict) -> int:
    """构建候选分流路径"""
    logger.info("构建候选路径...")
    return self.repository.build_od_candidate_path(params)

  def build_diversion_plans(self, params: dict) -> int:
    """构建分流方案"""
    logger.info("构建分流方案...")
    return self.repository.build_od_diversion_plan(params)

  def get_summary(self, params: dict) -> dict:
    """获取分流汇总统计"""
    return self.repository.get_diversion_summary(params)

  def get_by_status(self, params: dict) -> list[dict]:
    """按状态获取分流方案"""
    return self.repository.get_plan_by_status(params)

  def validate(self) -> dict:
    """验证输出数据质量"""
    candidate_validation = self.repository.validate_od_candidate_path()
    plan_validation = self.repository.validate_od_diversion_plan()
    return {
      "dws_od_candidate_path": candidate_validation,
      "ads_od_diversion_plan": plan_validation,
    }
