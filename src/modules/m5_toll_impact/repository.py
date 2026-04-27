"""
M5 通行费影响测算数据仓库
处理数据库访问和 SQL 执行
"""

from typing import Optional

from src.app.logger import get_logger, LoggerMixin
from src.common.sql_runner import get_sql_runner, SqlRunner

logger = get_logger(__name__)


class M5Repository(LoggerMixin):
  """M5 数据访问仓库"""

  def __init__(self, sql_runner: Optional[SqlRunner] = None):
    self.sql_runner = sql_runner or get_sql_runner()

  def get_toll_impact_count(self, params: dict) -> int:
    """获取通行费影响记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM ads_toll_impact_result
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def get_scheme_summary_count(self, params: dict) -> int:
    """获取方案汇总记录数量"""
    sql = """
    SELECT COUNT(*) AS cnt
    FROM ads_scheme_summary
    WHERE scheme_id = %(scheme_id)s
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return result["cnt"] if result else 0

  def build_toll_impact_result(self, params: dict) -> int:
    """
    构建通行费影响结果
    费用影响计算: diverted_flow * fee_diff
    影响类型: fee_increase/fee_decrease/no_impact
    """
    logger.info("构建通行费影响结果...")
    sql_file = "sql/dml/m5/build_toll_impact_result.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_toll_impact_count(params)

  def build_scheme_summary(self, params: dict) -> int:
    """
    构建方案汇总
    按方案聚合通行费影响
    """
    logger.info("构建方案汇总...")
    sql_file = "sql/dml/m5/build_scheme_summary.sql"
    self.sql_runner.run_sql_file(sql_file, params=params)
    return self.get_scheme_summary_count(params)

  def get_toll_impact_summary(self, params: dict) -> dict:
    """获取通行费影响汇总统计"""
    sql = """
    SELECT
      COUNT(*) AS total_records,
      SUM(diverted_flow_pcu) AS total_diverted_flow,
      SUM(fee_impact_yuan) AS total_fee_impact,
      SUM(CASE WHEN impact_type = 'fee_increase' THEN fee_impact_yuan ELSE 0 END) AS total_fee_increase,
      SUM(CASE WHEN impact_type = 'fee_decrease' THEN ABS(fee_impact_yuan) ELSE 0 END) AS total_fee_decrease,
      AVG(fee_impact_yuan) AS avg_fee_impact,
      AVG(ABS(fee_impact_yuan) / NULLIF(diverted_flow_pcu, 0)) AS avg_impact_per_vehicle
    FROM ads_toll_impact_result
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    """
    return self.sql_runner.fetch_one(sql, params=params)

  def get_impact_by_type(self, params: dict) -> list[dict]:
    """按类型获取通行费影响明细"""
    sql = """
    SELECT
      impact_type,
      COUNT(*) AS record_count,
      SUM(diverted_flow_pcu) AS total_flow,
      SUM(fee_impact_yuan) AS total_impact,
      AVG(ABS(fee_impact_yuan)) AS avg_impact
    FROM ads_toll_impact_result
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
    GROUP BY impact_type
    ORDER BY impact_type
    """
    return self.sql_runner.fetch_all(sql, params=params)

  def get_high_impact_od_pairs(self, params: dict, threshold: float = 1000) -> list[dict]:
    """获取高费用影响 OD 对（绝对值）"""
    sql = """
    SELECT
      od_id,
      original_path_id,
      recommended_path_id,
      diverted_flow_pcu,
      fee_impact_yuan,
      impact_type
    FROM ads_toll_impact_result
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
      AND ABS(fee_impact_yuan) >= %(threshold)s
    ORDER BY ABS(fee_impact_yuan) DESC
    LIMIT 100
    """
    return self.sql_runner.fetch_all(sql, {**params, "threshold": threshold})

  def validate_toll_impact_result(self) -> dict:
    """对 ads_toll_impact_result 执行校验检查"""
    logger.info("验证 ads_toll_impact_result...")
    sql_file = "sql/checks/m5/check_toll_impact_result.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"验证失败: {e}")
      return {"valid": False, "error": str(e)}

  def validate_scheme_summary(self) -> dict:
    """对 ads_scheme_summary 执行校验检查"""
    logger.info("验证 ads_scheme_summary...")
    sql_file = "sql/checks/m5/check_scheme_summary.sql"
    try:
      results = self.sql_runner.fetch_all(sql_file)
      return {"valid": True, "results": results}
    except Exception as e:
      logger.error(f"验证失败: {e}")
      return {"valid": False, "error": str(e)}

  def check_fee_impact_calculation(self, params: dict) -> dict:
    """验证费用影响计算是否正确"""
    sql = """
    SELECT COUNT(*) AS incorrect_count
    FROM ads_toll_impact_result
    WHERE scheme_id = %(scheme_id)s
      AND stat_date >= %(start_date)s
      AND stat_date <= %(end_date)s
      AND ABS(fee_impact_yuan - diverted_flow_pcu * fee_diff) > 0.01
      AND fee_diff IS NOT NULL
    """
    result = self.sql_runner.fetch_one(sql, params=params)
    return {
      "valid": result is None or result.get("incorrect_count", 0) == 0,
      "incorrect_count": result.get("incorrect_count", 0) if result else 0,
    }
