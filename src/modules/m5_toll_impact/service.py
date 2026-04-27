"""
M5 通行费影响测算服务
通行费影响测算主编排逻辑
"""

import time
from typing import Optional

from src.app.enums import ModuleCode, TaskStatus
from src.app.logger import get_logger, LoggerMixin
from src.modules.m5_toll_impact.repository import M5Repository
from src.modules.m5_toll_impact.schema import M5TaskParams, M5TaskResult


logger = get_logger(__name__)


class M5Service(LoggerMixin):
  """M5 通行费影响测算服务"""

  def __init__(self):
    self.repository = M5Repository()
    self.module_code = ModuleCode.M5

  def run(
    self,
    schemeId: str,
    startDate: str,
    endDate: str,
    overwrite: bool = False,
  ) -> M5TaskResult:
    """
    运行 M5 通行费影响测算

    参数:
      schemeId: 施工方案ID
      startDate: 开始日期
      endDate: 结束日期
      overwrite: 是否覆盖已有数据

    返回:
      包含执行状态的 M5TaskResult
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

    logger.info(f"开始对方案 {schemeId} 进行 M5 通行费影响测算")

    try:
      # 步骤 1: 构建通行费影响结果
      logger.info("步骤 1/4: 构建通行费影响结果...")
      impact_count = self.repository.build_toll_impact_result(params)
      total_records += impact_count
      logger.info(f"  已构建 {impact_count} 条通行费影响记录")

      # 步骤 2: 构建方案汇总
      logger.info("步骤 2/4: 构建方案汇总...")
      summary_count = self.repository.build_scheme_summary(params)
      logger.info(f"  已构建 {summary_count} 条方案汇总记录")

      # 步骤 3: 按类型分析影响
      logger.info("步骤 3/4: 按类型分析影响...")
      impact_by_type = self.repository.get_impact_by_type(params)
      for impact in impact_by_type:
        logger.info(
          f"  影响类型 '{impact['impact_type']}': "
          f"{impact['record_count']} 条记录, "
          f"{impact['total_flow']} PCU, "
          f"{impact['total_impact']:.2f} 元"
        )

      # 步骤 4: 验证输出
      logger.info("步骤 4/4: 验证输出...")
      impact_validation = self.repository.validate_toll_impact_result()
      if not impact_validation.get("valid", False):
        warnings.append(
          f"通行费影响验证警告: {impact_validation.get('error', '未知')}"
        )

      summary_validation = self.repository.validate_scheme_summary()
      if not summary_validation.get("valid", False):
        warnings.append(
          f"方案汇总验证警告: {summary_validation.get('error', '未知')}"
        )

      # 检查费用影响计算
      calc_check = self.repository.check_fee_impact_calculation(params)
      if not calc_check.get("valid", False):
        incorrect = calc_check.get("incorrect_count", 0)
        warnings.append(f"发现 {incorrect} 条费用影响计算错误的记录")

      # 检查高影响 OD 对
      high_impacts = self.repository.get_high_impact_od_pairs(params, threshold=10000)
      if high_impacts:
        logger.warning(f"发现 {len(high_impacts)} 个费用影响超过 10000 元的 OD 对")
        warnings.append(f"发现 {len(high_impacts)} 个高影响 OD 对")

      execution_time = time.time() - start_time

      logger.info(f"M5 通行费影响测算完成，耗时 {execution_time:.2f}s")
      logger.info(f"已处理记录总数: {total_records}")

      return M5TaskResult(
        status=TaskStatus.SUCCESS,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

    except Exception as e:
      execution_time = time.time() - start_time
      logger.exception(f"M5 通行费影响测算失败: {e}")
      errors.append(str(e))

      return M5TaskResult(
        status=TaskStatus.FAILED,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

  def build_toll_impact(self, params: dict) -> int:
    """构建通行费影响结果"""
    logger.info("构建通行费影响结果...")
    return self.repository.build_toll_impact_result(params)

  def build_summary(self, params: dict) -> int:
    """构建方案汇总"""
    logger.info("构建方案汇总...")
    return self.repository.build_scheme_summary(params)

  def get_summary(self, params: dict) -> dict:
    """获取通行费影响汇总统计"""
    return self.repository.get_toll_impact_summary(params)

  def get_by_type(self, params: dict) -> list[dict]:
    """按类型获取通行费影响"""
    return self.repository.get_impact_by_type(params)

  def validate(self) -> dict:
    """验证输出数据质量"""
    impact_validation = self.repository.validate_toll_impact_result()
    summary_validation = self.repository.validate_scheme_summary()
    return {
      "ads_toll_impact_result": impact_validation,
      "ads_scheme_summary": summary_validation,
    }
