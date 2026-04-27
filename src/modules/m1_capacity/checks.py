"""
M1 通行能力评估输出数据校验
验证输出表的数据质量和完整性
"""

from typing import Any, Optional

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def check_section_capacity_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_capacity_day 中必填字段是否为空

  Args:
    params: 可选参数，包含 scheme_id, start_date, end_date

  Returns:
    包含 'valid' 和 'errors' 键的校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  where_clause = ""
  if params:
    conditions = []
    if params.get("scheme_id"):
      conditions.append(f"scheme_id = '{params['scheme_id']}'")
    if params.get("start_date"):
      conditions.append(f"stat_date >= '{params['start_date']}'")
    if params.get("end_date"):
      conditions.append(f"stat_date <= '{params['end_date']}'")
    if conditions:
      where_clause = "WHERE " + " AND ".join(conditions)

  # 检查 section_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND section_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_id 为空的记录")

  # 检查 section_number 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND section_number IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_number 为空的记录")

  # 检查 capacity_pcu 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND capacity_pcu IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 capacity_pcu 为空的记录")

  return {
    "table": "dws_section_capacity_day",
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_capacity_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_capacity_day 中的数值范围

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  where_clause = ""
  if params:
    conditions = []
    if params.get("scheme_id"):
      conditions.append(f"scheme_id = '{params['scheme_id']}'")
    if params.get("start_date"):
      conditions.append(f"stat_date >= '{params['start_date']}'")
    if params.get("end_date"):
      conditions.append(f"stat_date <= '{params['end_date']}'")
    if conditions:
      where_clause = "WHERE " + " AND ".join(conditions)

  # 检查 lane_cnt >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND lane_cnt < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 lane_cnt 为负数的记录")

  # 检查 lane_occupied_cnt >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND lane_occupied_cnt < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 lane_occupied_cnt 为负数的记录")

  # 检查 available_lane_cnt >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND available_lane_cnt < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 available_lane_cnt 为负数的记录")

  # 检查 available_lane_cnt <= lane_cnt
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause}
    AND available_lane_cnt > lane_cnt
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 available_lane_cnt 大于 lane_cnt 的记录")

  # 检查 capacity_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM dws_section_capacity_day {where_clause} AND capacity_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 capacity_pcu 为负数的记录")

  return {
    "table": "dws_section_capacity_day",
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_capacity_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_capacity_day 中的唯一性约束

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  where_clause = ""
  if params:
    conditions = []
    if params.get("scheme_id"):
      conditions.append(f"scheme_id = '{params['scheme_id']}'")
    if params.get("start_date"):
      conditions.append(f"stat_date >= '{params['start_date']}'")
    if params.get("end_date"):
      conditions.append(f"stat_date <= '{params['end_date']}'")
    if conditions:
      where_clause = "WHERE " + " AND ".join(conditions)

  # 检查 section_id + stat_date 组合是否重复
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM (
      SELECT section_id, scheme_id, stat_date, COUNT(*) AS cnt
      FROM dws_section_capacity_day
      {where_clause}
      GROUP BY section_id, scheme_id, stat_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组 section_id+stat_date 组合重复")

  return {
    "table": "dws_section_capacity_day",
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_capacity_date_coverage(params: Optional[dict] = None) -> dict:
  """
  检查日期范围内是否都有通行能力记录

  Args:
    params: 可选参数，包含 scheme_id, start_date, end_date

  Returns:
    校验结果字典
  """
  if not params or not params.get("start_date") or not params.get("end_date"):
    return {
      "table": "dws_section_capacity_day",
      "check": "date_coverage",
      "valid": True,
      "errors": [],
      "warnings": ["未提供日期范围，跳过日期覆盖率检查"],
    }

  sql_runner = get_sql_runner()
  errors = []

  # 检查每个路段的日期覆盖是否存在缺口
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(DISTINCT section_id) AS sections_with_gaps
    FROM (
      SELECT
        section_id,
        stat_date,
        LAG(stat_date) OVER (PARTITION BY section_id ORDER BY stat_date) AS prev_date,
        (stat_date - LAG(stat_date) OVER (PARTITION BY section_id ORDER BY stat_date)) AS day_gap
      FROM dws_section_capacity_day
      WHERE scheme_id = '{params['scheme_id']}'
        AND stat_date >= '{params['start_date']}'
        AND stat_date <= '{params['end_date']}'
    ) gaps
    WHERE day_gap > 1
    """
  )
  if result and result.get("sections_with_gaps", 0) > 0:
    errors.append(f"发现 {result['sections_with_gaps']} 个路段存在日期缺口")

  return {
    "table": "dws_section_capacity_day",
    "check": "date_coverage",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_capacity_rule_match(params: Optional[dict] = None) -> dict:
  """
  检查所有路段是否都有匹配的通行能力规则

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  where_clause = ""
  if params:
    conditions = []
    if params.get("scheme_id"):
      conditions.append(f"d.scheme_id = '{params['scheme_id']}'")
    if params.get("start_date"):
      conditions.append(f"d.stat_date >= '{params['start_date']}'")
    if params.get("end_date"):
      conditions.append(f"d.stat_date <= '{params['end_date']}'")
    if conditions:
      where_clause = "WHERE " + " AND ".join(conditions)

  # 检查是否存在无法匹配的通行能力规则
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS unmatched_count
    FROM dws_section_capacity_day d
    LEFT JOIN dim_capacity_rule r
      ON d.available_lane_cnt = r.available_lane_cnt
      AND (d.construction_mode = r.construction_mode OR r.construction_mode IS NULL)
    {where_clause}
    AND r.available_lane_cnt IS NULL
    """
  )
  if result and result.get("unmatched_count", 0) > 0:
    errors.append(f"发现 {result['unmatched_count']} 条无法匹配通行能力规则的记录")

  return {
    "table": "dws_section_capacity_day",
    "check": "capacity_rule_match",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def run_all_checks(params: Optional[dict] = None) -> list[dict]:
  """
  运行所有 M1 校验检查

  Args:
    params: 可选参数，包含 scheme_id, start_date, end_date

  Returns:
    校验结果列表
  """
  logger.info("正在运行 M1 校验检查...")

  results = [
    check_section_capacity_required_fields(params),
    check_section_capacity_value_ranges(params),
    check_section_capacity_uniqueness(params),
    check_section_capacity_date_coverage(params),
    check_capacity_rule_match(params),
  ]

  failed = [r for r in results if not r["valid"]]
  if failed:
    logger.warning(f"发现 {len(failed)} 项校验未通过")
    for r in failed:
      logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
  else:
    logger.info("所有 M1 校验检查均已通过")

  return results
