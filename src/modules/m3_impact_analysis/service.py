"""
M3 交通影响分析服务
交通影响分析主编排逻辑
"""

import time
from typing import Optional

from src.app.enums import ModuleCode, TaskStatus
from src.app.logger import get_logger, LoggerMixin
from src.modules.m3_impact_analysis.repository import M3Repository
from src.modules.m3_impact_analysis.schema import M3TaskParams, M3TaskResult


logger = get_logger(__name__)


class M3Service(LoggerMixin):
  """M3 交通影响分析服务"""

  def __init__(self):
    self.repository = M3Repository()
    self.module_code = ModuleCode.M3

  def run(
    self,
    schemeId: str,
    startDate: str,
    endDate: str,
    overwrite: bool = False,
  ) -> M3TaskResult:
    """
    运行 M3 交通影响分析

    参数:
      schemeId: 施工方案ID
      startDate: 开始日期
      endDate: 结束日期
      overwrite: 是否覆盖已有数据

    返回:
      包含执行状态的 M3TaskResult
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

    logger.info(f"开始对方案 {schemeId} 进行 M3 交通影响分析")

    try:
      # 步骤 1: 构建受影响的 OD 流量日记录
      logger.info("步骤 1/3: 构建受影响的 OD 流量日记录...")
      record_count = self.repository.build_impacted_od_flow_day(params)
      total_records += record_count
      logger.info(f"  已构建 {record_count} 条受影响流量记录")

      # 步骤 2: 按等级分析影响
      logger.info("步骤 2/3: 按等级分析影响...")
      impact_by_level = self.repository.get_impact_by_level(params)
      for level in impact_by_level:
        logger.info(
          f"  影响等级 '{level['impact_level']}': "
          f"{level['od_count']} 个OD, "
          f"{level['total_demand']} PCU 需求"
        )

      # 步骤 3: 验证输出
      logger.info("步骤 3/3: 验证输出...")
      validation = self.repository.validate_impacted_od_flow_day()
      if not validation.get("valid", False):
        warnings.append(f"验证警告: {validation.get('error', '未知')}")

      # 检查影响率计算
      ratio_check = self.repository.check_impact_ratio_calculation(params)
      if not ratio_check.get("valid", False):
        incorrect = ratio_check.get("incorrect_count", 0)
        warnings.append(f"发现 {incorrect} 条影响率计算错误的记录")

      # 检查高影响 OD 对
      high_impact = self.repository.get_high_impact_od_pairs(params, threshold=0.5)
      if high_impact:
        logger.warning(f"发现 {len(high_impact)} 个影响率超过50%的 OD 对")
        warnings.append(f"发现 {len(high_impact)} 个严重影响 OD 对")

      execution_time = time.time() - start_time

      logger.info(f"M3 交通影响分析完成，耗时 {execution_time:.2f}s")
      logger.info(f"已处理记录总数: {total_records}")

      return M3TaskResult(
        status=TaskStatus.SUCCESS,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

    except Exception as e:
      execution_time = time.time() - start_time
      logger.exception(f"M3 交通影响分析失败: {e}")
      errors.append(str(e))

      return M3TaskResult(
        status=TaskStatus.FAILED,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

  def build_impacted_flow(self, params: dict) -> int:
    """构建受影响的 OD 流量日记录"""
    logger.info("构建受影响的 OD 流量记录...")
    return self.repository.build_impacted_od_flow_day(params)

  def get_summary(self, params: dict) -> list[dict]:
    """按日期获取影响汇总"""
    return self.repository.get_impact_summary(params)

  def get_by_level(self, params: dict) -> list[dict]:
    """按等级获取影响数量"""
    return self.repository.get_impact_by_level(params)

  def get_high_impact_pairs(self, params: dict, threshold: float = 0.3) -> list[dict]:
    """获取高影响 OD 对"""
    return self.repository.get_high_impact_od_pairs(params, threshold=threshold)

  def validate(self) -> dict:
    """验证输出数据质量"""
    return self.repository.validate_impacted_od_flow_day()
