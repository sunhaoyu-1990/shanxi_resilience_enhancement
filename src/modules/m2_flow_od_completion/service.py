"""
M2 流量与OD迁移统计补全服务
流量补全及OD迁移主编排逻辑
"""

import time
from typing import Optional

from src.app.enums import ModuleCode, TaskStatus
from src.app.logger import get_logger, LoggerMixin
from src.modules.m2_flow_od_completion.repository import M2Repository
from src.modules.m2_flow_od_completion.schema import M2TaskParams, M2TaskResult


logger = get_logger(__name__)


class M2Service(LoggerMixin):
  """M2 流量与OD迁移统计补全服务"""

  def __init__(self):
    self.repository = M2Repository()
    self.module_code = ModuleCode.M2

  def run(
    self,
    schemeId: str,
    startDate: str,
    endDate: str,
    overwrite: bool = False,
  ) -> M2TaskResult:
    """
    执行 M2 流量与OD迁移统计补全

    Args:
      schemeId: 施工方案ID
      startDate: 开始日期
      endDate: 结束日期
      overwrite: 是否覆盖已有数据

    Returns:
      包含执行状态的 M2TaskResult
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

    logger.info(f"开始为方案 {schemeId} 执行 M2 流量与OD迁移统计补全")

    try:
      # 步骤 1: 构建路段-OD流量日统计记录
      logger.info("步骤 1/4: 构建路段-OD流量日统计记录...")
      od_flow_count = self.repository.build_section_od_flow_day(params)
      total_records += od_flow_count
      logger.info(f"  已构建 {od_flow_count} 条路段-OD流量记录")

      # 步骤 2: 构建路段流量日统计记录
      logger.info("步骤 2/4: 构建路段流量日统计记录...")
      section_flow_count = self.repository.build_section_flow_day(params)
      total_records += section_flow_count
      logger.info(f"  已构建 {section_flow_count} 条路段流量记录")

      # 步骤 3: 验证输出数据
      logger.info("步骤 3/4: 验证输出数据...")
      od_flow_validation = self.repository.validate_section_od_flow_day()
      if not od_flow_validation.get("valid", False):
        warnings.append(f"路段-OD流量验证警告: {od_flow_validation.get('error', '未知错误')}")

      section_flow_validation = self.repository.validate_section_flow_day()
      if not section_flow_validation.get("valid", False):
        warnings.append(f"路段流量验证警告: {section_flow_validation.get('error', '未知错误')}")

      # 步骤 4: 检查数据来源标识分布
      logger.info("步骤 4/4: 检查数据来源标识分布...")
      source_distribution = self.repository.check_source_flag_distribution(params)
      for flag, info in source_distribution.get("distribution", {}).items():
        logger.info(f"  数据来源标识 '{flag}': {info['count']} 条记录 ({info['ratio']:.1%})")

      execution_time = time.time() - start_time

      logger.info(f"M2 流量与OD迁移统计补全完成，耗时 {execution_time:.2f}秒")
      logger.info(f"处理记录总数: {total_records}")

      return M2TaskResult(
        status=TaskStatus.SUCCESS,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

    except Exception as e:
      execution_time = time.time() - start_time
      logger.exception(f"M2 流量与OD迁移统计补全失败: {e}")
      errors.append(str(e))

      return M2TaskResult(
        status=TaskStatus.FAILED,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

  def build_section_od_flow(self, params: dict) -> int:
    """构建路段-OD流量日统计记录"""
    logger.info("正在构建路段-OD流量记录...")
    return self.repository.build_section_od_flow_day(params)

  def build_section_flow(self, params: dict) -> int:
    """构建路段流量日统计记录"""
    logger.info("正在构建路段流量记录...")
    return self.repository.build_section_flow_day(params)

  def get_summary(self, params: dict) -> dict:
    """获取流量汇总统计"""
    return self.repository.get_flow_summary(params)

  def get_by_source_flag(self, params: dict) -> list[dict]:
    """按数据来源标识获取流量记录"""
    return self.repository.get_flow_by_source_flag(params)

  def validate(self) -> dict:
    """验证输出数据质量"""
    od_validation = self.repository.validate_section_od_flow_day()
    section_validation = self.repository.validate_section_flow_day()
    return {
      "dws_section_od_flow_day": od_validation,
      "dws_section_flow_day": section_validation,
    }
