"""
M1 通行能力评估 Repository
负责数据库访问和 SQL 执行
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M1Repository(LoggerMixin):
  """M1 数据访问 Repository"""

  def __init__(self, sql_runner: Optional[SqlRunner] = None):
    self.sql_runner = sql_runner or get_sql_runner()

  def get_section_capacity_count(self, params: dict) -> int:
    """获取路段通行能力日统计记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM dws_section_capacity_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def build_section_capacity_day(self, params: dict) -> int:
    """
    构建路段通行能力日统计记录
    核心逻辑: available_lane_cnt = lane_cnt - lane_occupied_cnt,
             再与 dim_capacity_rule 维度表进行匹配
    """
    logger.info("正在构建路段通行能力日统计记录...")
    sql_file = "sql/dml/m1/build_section_capacity_day.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_section_capacity_count(params)

  def get_capacity_by_section(self, params: dict) -> list[dict]:
    """按路段获取通行能力记录"""
    sql = """
    SELECT
      section_id,
      section_number,
      COUNT(*) AS day_count,
      AVG(available_lane_cnt) AS avg_available_lane_cnt,
      AVG(capacity_pcu) AS avg_capacity_pcu
    FROM dws_section_capacity_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY section_id, section_number
    ORDER BY section_id
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def get_capacity_summary(self, params: dict) -> dict:
    """获取通行能力汇总统计"""
    sql = """
    SELECT
      COUNT(DISTINCT section_id) AS section_count,
      COUNT(*) AS total_records,
      AVG(available_lane_cnt) AS avg_available_lane_cnt,
      AVG(capacity_pcu) AS avg_capacity_pcu,
      MIN(stat_date) AS min_stat_date,
      MAX(stat_date) AS max_stat_date
    FROM dws_section_capacity_day
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    return self.sql_runner.fetch_one(sql, params=params)

  def validate_section_capacity_day(self) -> dict:
    """对 dws_section_capacity_day 执行校验检查"""
    logger.info("正在校验 dws_section_capacity_day...")
    sql_file = "sql/checks/m1/check_section_capacity_day.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"校验失败: {e}")
      return {"valid": False, "error": str(e)}

  def check_capacity_rule_coverage(self, params: dict) -> dict:
    """检查所有路段是否都有匹配的通行能力规则"""
    sql = """
    SELECT COUNT(*) AS uncovered_count
    FROM dws_section_capacity_day d
    LEFT JOIN dim_capacity_rule r
      ON d.available_lane_cnt = r.available_lane_cnt
    WHERE d.scheme_id = %(scheme_id)s
      AND d.stat_date >= %(start_date)s
      AND d.stat_date <= %(end_date)s
      AND r.available_lane_cnt IS NULL
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return {
      "valid": result is None or result.get("uncovered_count", 0) == 0,
      "uncovered_count": result.get("uncovered_count", 0) if result else 0,
    }
