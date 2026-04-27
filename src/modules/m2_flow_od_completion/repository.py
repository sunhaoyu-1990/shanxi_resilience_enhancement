"""
M2 流量与OD迁移统计补全 Repository
负责数据库访问和 SQL 执行
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M2Repository(LoggerMixin):
  """M2 数据访问 Repository"""

  def __init__(self, sql_runner: Optional[SqlRunner] = None):
    self.sql_runner = sql_runner or get_sql_runner()

  def get_section_od_flow_count(self, params: dict) -> int:
    """获取路段-OD流量日统计记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM dws_section_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def get_section_flow_count(self, params: dict) -> int:
    """获取路段流量日统计记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM dws_section_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def build_section_od_flow_day(self, params: dict) -> int:
    """
    构建路段-OD流量日统计记录
    数据来源标识追踪: actual/filled/rule
    """
    logger.info("正在构建路段-OD流量日统计记录...")
    sql_file = "sql/dml/m2/build_section_od_flow_day.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_section_od_flow_count(params)

  def build_section_flow_day(self, params: dict) -> int:
    """
    构建路段总流量日统计记录
    数据来源标识追踪: actual/filled/rule
    """
    logger.info("正在构建路段流量日统计记录...")
    sql_file = "sql/dml/m2/build_section_flow_day.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_section_flow_count(params)

  def get_flow_by_source_flag(self, params: dict) -> list[dict]:
    """按数据来源标识获取流量记录"""
    sql = """
    SELECT
      source_flag,
      COUNT(*) AS record_count,
      SUM(flow_pcu) AS total_flow_pcu,
      AVG(flow_pcu) AS avg_flow_pcu
    FROM dws_section_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY source_flag
    ORDER BY source_flag
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def get_flow_summary(self, params: dict) -> dict:
    """获取流量汇总统计"""
    sql = """
    SELECT
      COUNT(DISTINCT section_id) AS section_count,
      COUNT(DISTINCT od_id) AS od_count,
      COUNT(*) AS total_records,
      SUM(flow_pcu) AS total_flow_pcu,
      AVG(flow_pcu) AS avg_flow_pcu
    FROM dws_section_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    return self.sql_runner.fetch_one(sql, params=params)

  def validate_section_od_flow_day(self) -> dict:
    """对 dws_section_od_flow_day 执行校验检查"""
    logger.info("正在校验 dws_section_od_flow_day...")
    sql_file = "sql/checks/m2/check_section_od_flow_day.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"校验失败: {e}")
      return {"valid": False, "error": str(e)}

  def validate_section_flow_day(self) -> dict:
    """对 dws_section_flow_day 执行校验检查"""
    logger.info("正在校验 dws_section_flow_day...")
    sql_file = "sql/checks/m2/check_section_flow_day.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"校验失败: {e}")
      return {"valid": False, "error": str(e)}

  def check_source_flag_distribution(self, params: dict) -> dict:
    """检查数据来源标识分布情况"""
    sql = """
    SELECT
      source_flag,
      COUNT(*) AS cnt
    FROM dws_section_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY source_flag
    """
    results = self.sql_runner.fetch_all(sql, params=params)
    total = sum(r["cnt"] for r in results)
    distribution = {
      r["source_flag"]: {"count": r["cnt"], "ratio": r["cnt"] / total if total > 0 else 0}
      for r in results
    }
    return {"valid": True, "distribution": distribution, "total": total}
