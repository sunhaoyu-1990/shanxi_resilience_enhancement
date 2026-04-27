"""
M4 分流路径优化数据仓库
处理数据库访问和 SQL 执行
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M4Repository(LoggerMixin):
  """M4 数据访问仓库"""

  def __init__(self, sql_runner: Optional[SqlRunner] = None):
    self.sql_runner = sql_runner or get_sql_runner()

  def get_candidate_path_count(self, params: dict) -> int:
    """获取候选路径记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM dws_od_candidate_path
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def get_diversion_plan_count(self, params: dict) -> int:
    """获取分流方案记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM ads_od_diversion_plan
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def build_od_candidate_path(self, params: dict) -> int:
    """
    为受影响的 OD 对构建候选分流路径
    路径对比指标: mileage_diff, fee_diff, control_section_id
    """
    logger.info("构建 OD 候选路径...")
    sql_file = "sql/dml/m4/build_od_candidate_path.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_candidate_path_count(params)

  def build_od_diversion_plan(self, params: dict) -> int:
    """
    为受影响的 OD 对构建分流方案
    基于 mileage_diff, fee_diff 等指标选择最优路径
    """
    logger.info("构建 OD 分流方案...")
    sql_file = "sql/dml/m4/build_od_diversion_plan.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_diversion_plan_count(params)

  def get_diversion_summary(self, params: dict) -> dict:
    """获取分流方案汇总统计"""
    sql = """
    SELECT
      COUNT(DISTINCT od_id) AS od_count,
      COUNT(*) AS total_plans,
      SUM(diverted_flow_pcu) AS total_diverted_flow,
      AVG(mileage_diff) AS avg_mileage_diff,
      AVG(fee_diff) AS avg_fee_diff,
      AVG(diversion_ratio) AS avg_diversion_ratio
    FROM ads_od_diversion_plan
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    return self.sql_runner.fetch_one(sql, params=params)

  def get_plan_by_status(self, params: dict) -> list[dict]:
    """按状态分组获取分流方案"""
    sql = """
    SELECT
      plan_status,
      COUNT(*) AS plan_count,
      SUM(diverted_flow_pcu) AS total_flow
    FROM ads_od_diversion_plan
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY plan_status
    ORDER BY plan_status
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def get_candidate_path_details(self, params: dict) -> list[dict]:
    """获取包含对比指标的候选路径详情"""
    sql = """
    SELECT
      od_id,
      path_id,
      mileage_km,
      mileage_diff,
      fee_yuan,
      fee_diff,
      is_viable,
      path_rank
    FROM dws_od_candidate_path
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    ORDER BY od_id, path_rank
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def validate_od_candidate_path(self) -> dict:
    """对 dws_od_candidate_path 执行校验检查"""
    logger.info("验证 dws_od_candidate_path...")
    sql_file = "sql/checks/m4/check_od_candidate_path.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"验证失败: {e}")
      return {"valid": False, "error": str(e)}

  def validate_od_diversion_plan(self) -> dict:
    """对 ads_od_diversion_plan 执行校验检查"""
    logger.info("验证 ads_od_diversion_plan...")
    sql_file = "sql/checks/m4/check_od_diversion_plan.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"验证失败: {e}")
      return {"valid": False, "error": str(e)}

  def check_path_comparison_metrics(self, params: dict) -> dict:
    """检查路径对比指标是否计算正确"""
    sql = """
    SELECT COUNT(*) AS incorrect_count
    FROM dws_od_candidate_path
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
      AND mileage_diff < 0
      AND original_path_id IS NOT NULL
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return {
      "valid": result is None or result.get("incorrect_count", 0) == 0,
      "incorrect_count": result.get("incorrect_count", 0) if result else 0,
    }
