"""
M1 通行能力评估服务
通行能力评估主编排逻辑
"""

import time
from typing import Optional

from src.app.enums import ModuleCode, TaskStatus
from src.app.logger import get_logger, LoggerMixin
from src.modules.m1_capacity.repository import M1Repository
from src.modules.m1_capacity.schema import M1TaskParams, M1TaskResult


logger = get_logger(__name__)


class M1Service(LoggerMixin):
  """M1 通行能力评估服务"""

  def __init__(self):
    self.repository = M1Repository()
    self.module_code = ModuleCode.M1

  def run(
    self,
    schemeId: str,
    startDate: str,
    endDate: str,
    overwrite: bool = False,
  ) -> M1TaskResult:
    """
    执行 M1 通行能力评估

    Args:
      schemeId: 施工方案ID
      startDate: 开始日期
      endDate: 结束日期
      overwrite: 是否覆盖已有数据

    Returns:
      包含执行状态的 M1TaskResult
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

    logger.info(f"开始为方案 {schemeId} 执行 M1 通行能力评估")

    try:
      # 步骤 1: 构建路段通行能力日统计记录
      logger.info("步骤 1/2: 构建路段通行能力日统计记录...")
      record_count = self.repository.build_section_capacity_day(params)
      total_records += record_count
      logger.info(f"  已构建 {record_count} 条通行能力记录")

      # 步骤 2: 验证输出数据
      logger.info("步骤 2/2: 验证输出数据...")
      validation = self.repository.validate_section_capacity_day()
      if not validation.get("valid", False):
        warnings.append(f"验证警告: {validation.get('error', '未知错误')}")

      # 检查通行能力规则覆盖率
      coverage = self.repository.check_capacity_rule_coverage(params)
      if not coverage.get("valid", False):
        uncovered = coverage.get("uncovered_count", 0)
        warnings.append(f"发现 {uncovered} 个路段无匹配的通行能力规则")

      execution_time = time.time() - start_time

      logger.info(f"M1 通行能力评估完成，耗时 {execution_time:.2f}秒")
      logger.info(f"处理记录总数: {total_records}")

      return M1TaskResult(
        status=TaskStatus.SUCCESS,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

    except Exception as e:
      execution_time = time.time() - start_time
      logger.exception(f"M1 通行能力评估失败: {e}")
      errors.append(str(e))

      return M1TaskResult(
        status=TaskStatus.FAILED,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

  def build_capacity(self, params: dict) -> int:
    """构建路段通行能力日统计记录"""
    logger.info("正在构建路段通行能力记录...")
    return self.repository.build_section_capacity_day(params)

  def get_summary(self, params: dict) -> dict:
    """获取通行能力汇总统计"""
    return self.repository.get_capacity_summary(params)

  def get_by_section(self, params: dict) -> list[dict]:
    """按路段获取通行能力记录"""
    return self.repository.get_capacity_by_section(params)

  def validate(self) -> dict:
    """验证输出数据质量"""
    return self.repository.validate_section_capacity_day()
