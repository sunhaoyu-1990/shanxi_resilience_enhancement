"""
M0 数据工程服务
数据加载与准备的主要编排逻辑
"""

import time
from typing import Optional

from src.app.enums import ModuleCode, TaskStatus, SourceFlag
from src.app.logger import get_logger, LoggerMixin
from src.modules.m0_data_engineering.repository import M0Repository
from src.modules.m0_data_engineering.schema import M0TaskParams, M0TaskResult


logger = get_logger(__name__)


class M0Service(LoggerMixin):
  """M0 数据工程服务"""

  def __init__(self):
    self.repository = M0Repository()
    self.module_code = ModuleCode.M0

  def run(
    self,
    schemeId: str,
    startDate: str,
    endDate: str,
    overwrite: bool = False,
  ) -> M0TaskResult:
    """
    执行 M0 数据工程任务

    参数:
      schemeId: 施工方案ID
      startDate: 开始日期
      endDate: 结束日期
      overwrite: 是否覆盖已有数据

    返回:
      M0TaskResult 包含执行状态
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

    logger.info(f"正在为方案 {schemeId} 启动 M0 数据工程")

    try:
      # 步骤1: 加载 ODS 数据
      logger.info("步骤 1/5: 正在加载 ODS 数据...")
      self.repository.load_ods_section_info(params)

      # 步骤2: 构建维度表
      logger.info("步骤 2/5: 正在构建维度表...")
      section_count = self.repository.build_dim_section_info(params)
      total_records += section_count
      logger.info(f"  已构建 {section_count} 条路段记录")

      # 步骤3: 构建方案-路段映射
      logger.info("步骤 3/5: 正在构建方案-路段映射...")
      map_count = self.repository.build_dwd_scheme_section_map(params)
      total_records += map_count
      logger.info(f"  已构建 {map_count} 条映射记录")

      # 步骤4: 构建 OD-路径映射
      logger.info("步骤 4/5: 正在构建 OD-路径映射...")
      od_map_count = self.repository.build_dwd_od_path_map(params)
      total_records += od_map_count
      logger.info(f"  已构建 {od_map_count} 条 OD-路径记录")

      # 步骤5: 验证输出
      logger.info("步骤 5/5: 正在验证输出...")
      validation = self.repository.validate_dim_section_info()
      if not validation.get("valid", False):
        warnings.append(f"验证警告: {validation.get('error', '未知错误')}")

      execution_time = time.time() - start_time

      logger.info(f"M0 数据工程已在 {execution_time:.2f}秒内完成")
      logger.info(f"总处理记录数: {total_records}")

      return M0TaskResult(
        status=TaskStatus.SUCCESS,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

    except Exception as e:
      execution_time = time.time() - start_time
      logger.exception(f"M0 数据工程执行失败: {e}")
      errors.append(str(e))

      return M0TaskResult(
        status=TaskStatus.FAILED,
        recordsProcessed=total_records,
        errors=errors,
        warnings=warnings,
        executionTime=execution_time,
      )

  def load_ods_data(self, params: dict) -> None:
    """加载 ODS 层数据"""
    logger.info("正在加载 ODS 数据...")
    self.repository.load_ods_section_info(params)

  def build_dimensions(self, params: dict) -> int:
    """构建维度表"""
    logger.info("正在构建维度表...")
    return self.repository.build_dim_section_info(params)

  def build_scheme_mapping(self, params: dict) -> int:
    """构建方案-路段映射"""
    logger.info("正在构建方案-路段映射...")
    return self.repository.build_dwd_scheme_section_map(params)

  def build_od_path_map(self, params: dict) -> int:
    """构建 OD-路径映射"""
    logger.info("正在构建 OD-路径映射...")
    return self.repository.build_dwd_od_path_map(params)

  def check_output(self) -> dict:
    """检查输出数据质量"""
    return self.repository.validate_dim_section_info()
