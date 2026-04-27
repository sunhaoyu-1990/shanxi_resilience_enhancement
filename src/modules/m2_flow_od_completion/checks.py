"""
M2 流量与OD迁移统计补全输出数据校验
验证输出表的数据质量和完整性
"""

from typing import Any, Optional

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def _build_where_clause(params: Optional[dict]) -> str:
  """根据参数构建 WHERE 子句"""
  if not params:
    return ""
  conditions = []
  if params.get("scheme_id"):
    conditions.append(f"scheme_id = '{params['scheme_id']}'")
  if params.get("start_date"):
    conditions.append(f"stat_date >= '{params['start_date']}'")
  if params.get("end_date"):
    conditions.append(f"stat_date <= '{params['end_date']}'")
  if conditions:
    return "WHERE " + " AND ".join(conditions)
  return ""


def check_section_od_flow_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_od_flow_day 中必填字段是否为空

  Args:
    params: 可选参数，包含 scheme_id, start_date, end_date

  Returns:
    包含 'valid' 和 'errors' 键的校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_section_od_flow_day"

  # 检查 od_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND od_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 od_id 为空的记录")

  # 检查 section_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND section_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_id 为空的记录")

  # 检查 flow_pcu 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND flow_pcu IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 flow_pcu 为空的记录")

  # 检查 source_flag 不为空且合法
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND source_flag IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 source_flag 为空的记录")

  valid_flags = ("actual", "filled", "rule")
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    AND source_flag NOT IN ('actual', 'filled', 'rule')
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 source_flag 非法的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_od_flow_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_od_flow_day 中的数值范围

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_section_od_flow_day"

  # 检查 flow_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND flow_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 flow_pcu 为负数的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_od_flow_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_od_flow_day 中的唯一性约束

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_section_od_flow_day"

  # 检查 od_id + section_id + stat_date 组合是否重复
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM (
      SELECT od_id, section_id, scheme_id, stat_date, COUNT(*) AS cnt
      FROM {table}
      {where_clause}
      GROUP BY od_id, section_id, scheme_id, stat_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组 od_id+section_id+stat_date 组合重复")

  return {
    "table": table,
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_flow_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_flow_day 中必填字段是否为空

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_section_flow_day"

  # 检查 section_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND section_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_id 为空的记录")

  # 检查 total_flow_pcu 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND total_flow_pcu IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 total_flow_pcu 为空的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_flow_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_flow_day 中的数值范围

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_section_flow_day"

  # 检查 total_flow_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND total_flow_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 total_flow_pcu 为负数的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_section_flow_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 dws_section_flow_day 中的唯一性约束

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_section_flow_day"

  # 检查 section_id + stat_date 组合是否重复
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM (
      SELECT section_id, scheme_id, stat_date, COUNT(*) AS cnt
      FROM {table}
      {where_clause}
      GROUP BY section_id, scheme_id, stat_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组 section_id+stat_date 组合重复")

  return {
    "table": table,
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_source_flag_balance(params: Optional[dict] = None) -> dict:
  """
  检查数据来源标识在记录中的平衡性

  Args:
    params: 可选参数

  Returns:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  warnings = []
  where_clause = _build_where_clause(params)

  # 检查 'rule' 填充记录是否过多（表明过度依赖规则）
  result = sql_runner.fetch_one(
    f"""
    SELECT
      COUNT(*) AS total,
      SUM(CASE WHEN source_flag = 'rule' THEN 1 ELSE 0 END) AS rule_count
    FROM dws_section_od_flow_day
    {where_clause}
    """
  )
  if result and result.get("total", 0) > 0:
    rule_ratio = result.get("rule_count", 0) / result.get("total", 1)
    if rule_ratio > 0.5:
      warnings.append(
        f"'rule' 填充记录占比过高: {rule_ratio:.1%} "
        f"({result['rule_count']}/{result['total']})"
      )

  return {
    "table": "dws_section_od_flow_day",
    "check": "source_flag_balance",
    "valid": len(warnings) == 0,
    "errors": [],
    "warnings": warnings,
  }


def run_all_checks(params: Optional[dict] = None) -> list[dict]:
  """
  运行所有 M2 校验检查

  Args:
    params: 可选参数，包含 scheme_id, start_date, end_date

  Returns:
    校验结果列表
  """
  logger.info("正在运行 M2 校验检查...")

  results = [
    check_section_od_flow_required_fields(params),
    check_section_od_flow_value_ranges(params),
    check_section_od_flow_uniqueness(params),
    check_section_flow_required_fields(params),
    check_section_flow_value_ranges(params),
    check_section_flow_uniqueness(params),
    check_source_flag_balance(params),
  ]

  failed = [r for r in results if not r["valid"]]
  if failed:
    logger.warning(f"发现 {len(failed)} 项校验未通过")
    for r in failed:
      logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
  else:
    logger.info("所有 M2 校验检查均已通过")

  return results
