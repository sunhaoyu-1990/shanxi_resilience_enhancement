"""
M3 交通影响分析数据仓库
处理数据库访问和 SQL 执行
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M3Repository(LoggerMixin):
  """M3 数据访问仓库"""

  def __init__(self, sql_runner: Optional[SqlRunner] = None):
    self.sql_runner = sql_runner or get_sql_runner()

  def get_impacted_flow_count(self, params: dict) -> int:
    """获取受影响 OD 流量记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM dws_impacted_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def build_impacted_od_flow_day(self, params: dict) -> int:
    """
    构建受影响 OD 流量日记录
    影响率计算规则: 如果 capacity < demand, 则 impact_ratio = (demand - capacity) / demand
    """
    logger.info("构建受影响 OD 流量日记录...")
    sql_file = "sql/dml/m3/build_impacted_od_flow_day.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_impacted_flow_count(params)

  def get_impact_summary(self, params: dict) -> list[dict]:
    """按日期获取影响汇总"""
    sql = """
    SELECT
      stat_date,
      COUNT(*) AS od_count,
      SUM(CASE WHEN is_impacted THEN 1 ELSE 0 END) AS impacted_count,
      SUM(demand_flow_pcu) AS total_demand,
      SUM(capacity_pcu) AS total_capacity,
      AVG(CASE WHEN is_impacted THEN impact_ratio ELSE 0 END) AS avg_impact_ratio
    FROM dws_impacted_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY stat_date
    ORDER BY stat_date
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def get_impact_by_level(self, params: dict) -> list[dict]:
    """按影响等级获取影响数量"""
    sql = """
    SELECT
      impact_level,
      COUNT(*) AS od_count,
      SUM(demand_flow_pcu) AS total_demand,
      SUM(demand_flow_pcu - capacity_pcu) AS excess_demand
    FROM dws_impacted_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY impact_level
    ORDER BY
      CASE impact_level
        WHEN 'severe' THEN 1
        WHEN 'moderate' THEN 2
        WHEN 'mild' THEN 3
        WHEN 'none' THEN 4
        ELSE 5
      END
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def get_high_impact_od_pairs(self, params: dict, threshold: float = 0.3) -> list[dict]:
    """获取高影响率 OD 对"""
    sql = """
    SELECT
      od_id,
      section_id,
      section_number,
      demand_flow_pcu,
      capacity_pcu,
      impact_ratio
    FROM dws_impacted_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
      AND impact_ratio >= %(threshold)s
    ORDER BY impact_ratio DESC
    LIMIT 100
    """
    return self.sql_runner.fetch_all(sql, {**params, "threshold": threshold})

  def validate_impacted_od_flow_day(self) -> dict:
    """对 dws_impacted_od_flow_day 执行校验检查"""
    logger.info("验证 dws_impacted_od_flow_day...")
    sql_file = "sql/checks/m3/check_impacted_od_flow_day.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"验证失败: {e}")
      return {"valid": False, "error": str(e)}

  def check_impact_ratio_calculation(self, params: dict) -> dict:
    """验证影响率计算是否正确"""
    sql = """
    SELECT COUNT(*) AS incorrect_count
    FROM dws_impacted_od_flow_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
      AND is_impacted = TRUE
      AND (
        impact_ratio < 0
        OR impact_ratio > 1
        OR ABS(impact_ratio - (demand_flow_pcu - capacity_pcu)::float / NULLIF(demand_flow_pcu, 0)) > 0.001
      )
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return {
      "valid": result is None or result.get("incorrect_count", 0) == 0,
      "incorrect_count": result.get("incorrect_count", 0) if result else 0,
    }
