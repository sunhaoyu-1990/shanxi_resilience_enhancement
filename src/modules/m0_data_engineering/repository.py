"""
M0 数据工程仓储层
处理数据库访问与 SQL 执行
"""

from typing import Generator, Optional

from sqlalchemy.orm import Session

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M0Repository(LoggerMixin):
  """M0 数据访问仓储"""

  def __init__(self, sql_runner: Optional[SqlRunner] = None):
    self.sql_runner = sql_runner or get_sql_runner()

  def get_section_count(self) -> int:
    """获取维度表中路段数量"""
    result = self.sql_runner.fetch_one(
      "SELECT COUNT(*) AS cnt FROM dim_section_info"
    )
    return result["cnt"] if result else 0

  def get_scheme_section_map_count(self) -> int:
    """获取方案-路段映射数量"""
    result = self.sql_runner.fetch_one(
      "SELECT COUNT(*) AS cnt FROM dwd_scheme_section_map"
    )
    return result["cnt"] if result else 0

  def get_od_path_map_count(self) -> int:
    """获取 OD-路径映射数量"""
    result = self.sql_runner.fetch_one(
      "SELECT COUNT(*) AS cnt FROM dwd_od_path_map"
    )
    return result["cnt"] if result else 0

  def load_ods_section_info(self, params: dict) -> None:
    """从原始数据加载 ODS 路段信息"""
    logger.info("正在加载 ODS 路段信息...")
    sql_file = "sql/dml/m0/build_dim_section_info.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)

  def build_dim_section_info(self, params: dict) -> int:
    """构建维度路段信息"""
    logger.info("正在构建维度路段信息...")
    sql_file = "sql/dml/m0/build_dim_section_info.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_section_count()

  def build_dim_station_info(self, params: dict) -> None:
    """构建维度收费站信息"""
    logger.info("正在构建维度收费站信息...")
    # TODO: 待实现

  def build_dim_road_topology(self, params: dict) -> None:
    """构建路网拓扑"""
    logger.info("正在构建路网拓扑...")
    # TODO: 待实现

  def build_dim_scheme_info(self, params: dict) -> None:
    """构建方案维度"""
    logger.info("正在构建方案维度...")
    # TODO: 待实现

  def build_dwd_scheme_section_map(self, params: dict) -> int:
    """构建方案-路段映射"""
    logger.info("正在构建方案-路段映射...")
    sql_file = "sql/dml/m0/build_dwd_scheme_section_map.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_scheme_section_map_count()

  def build_dwd_od_path_map(self, params: dict) -> int:
    """构建 OD-路径映射"""
    logger.info("正在构建 OD-路径映射...")
    sql_file = "sql/dml/m0/build_dwd_od_path_map.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_od_path_map_count()

  def build_dwd_single_trip_info(self, params: dict) -> None:
    """构建单车行程信息"""
    logger.info("正在构建单车行程信息...")
    # TODO: 待实现

  def validate_dim_section_info(self) -> dict:
    """对 dim_section_info 执行校验检查"""
    logger.info("正在校验 dim_section_info...")
    sql_file = "sql/checks/m0/check_dim_section_info.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"校验失败: {e}")
      return {"valid": False, "error": str(e)}
