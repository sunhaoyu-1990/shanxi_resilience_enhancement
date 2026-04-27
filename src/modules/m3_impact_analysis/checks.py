"""
M3 交通影响分析输出数据校验
验证输出表的数据质量和完整性
"""

from typing import Any, Optional

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def _build_where_clause(params: Optional[dict]) -> str:
  """从 params 构建 WHERE 子句"""
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


def check_impacted_flow_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 dws_impacted_od_flow_day 中必填字段是否为空

  参数:
    params: 可选参数，包含 scheme_id, start_date, end_date

  返回:
    包含 'valid' 和 'errors' 键的校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_impacted_od_flow_day"

  # 检查 od_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND od_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 od_id 为 NULL 的记录")

  # 检查 section_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND section_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_id 为 NULL 的记录")

  # 检查 demand_flow_pcu 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND demand_flow_pcu IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 demand_flow_pcu 为 NULL 的记录")

  # 检查 capacity_pcu 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND capacity_pcu IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 capacity_pcu 为 NULL 的记录")

  # 检查 impact_ratio 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND impact_ratio IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 impact_ratio 为 NULL 的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_impacted_flow_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 dws_impacted_od_flow_day 中的数值范围

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_impacted_od_flow_day"

  # 检查 demand_flow_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND demand_flow_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 demand_flow_pcu 为负数的记录")

  # 检查 capacity_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND capacity_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 capacity_pcu 为负数的记录")

  # 检查受影响记录的 impact_ratio 在 [0, 1] 范围内
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE is_impacted = TRUE
      AND (impact_ratio < 0 OR impact_ratio > 1)
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 impact_ratio 超出 [0,1] 范围的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_impacted_flow_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 dws_impacted_od_flow_day 中的唯一性约束

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_impacted_od_flow_day"

  # 检查 od_id + section_id + stat_date 的重复情况
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
    errors.append(f"发现 {result['cnt']} 组 od_id+section_id+stat_date 重复的组合")

  return {
    "table": table,
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_impact_ratio_calculation(params: Optional[dict] = None) -> dict:
  """
  验证影响率计算是否正确

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_impacted_od_flow_day"

  # 检查受影响记录的影响率是否等于 (demand - capacity) / demand
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE is_impacted = TRUE
      AND demand_flow_pcu > 0
      AND ABS(impact_ratio - (demand_flow_pcu - capacity_pcu)::float / demand_flow_pcu) > 0.001
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条影响率计算错误的记录"
    )

  # 检查非受影响记录的影响率是否为 0
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE is_impacted = FALSE AND impact_ratio != 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条未受影响但 impact_ratio 不为 0 的记录"
    )

  return {
    "table": table,
    "check": "impact_ratio_calculation",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_impact_level_consistency(params: Optional[dict] = None) -> dict:
  """
  检查 impact_ratio 与 impact_level 之间的一致性

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_impacted_od_flow_day"

  # 检查 severe: impact_ratio > 0.5
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_level = 'severe' AND (impact_ratio <= 0.5 OR impact_ratio IS NULL)
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'severe' 但 impact_ratio <= 0.5 的记录"
    )

  # 检查 moderate: 0.3 < impact_ratio <= 0.5
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_level = 'moderate'
      AND (impact_ratio <= 0.3 OR impact_ratio > 0.5)
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'moderate' 但 impact_ratio 不在 (0.3, 0.5] 范围内的记录"
    )

  # 检查 mild: 0 < impact_ratio <= 0.3
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_level = 'mild'
      AND (impact_ratio <= 0 OR impact_ratio > 0.3)
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'mild' 但 impact_ratio 不在 (0, 0.3] 范围内的记录"
    )

  # 检查 none: impact_ratio = 0 或 is_impacted = FALSE
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_level = 'none'
      AND is_impacted = TRUE AND impact_ratio != 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'none' 但 is_impacted=TRUE 的记录"
    )

  return {
    "table": table,
    "check": "impact_level_consistency",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_capacity_demand_relationship(params: Optional[dict] = None) -> dict:
  """
  检查 capacity 与 demand 之间的逻辑关系

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  warnings = []
  where_clause = _build_where_clause(params)
  table = "dws_impacted_od_flow_day"

  # 检查 capacity >> demand 的记录（可能存在数据问题）
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE capacity_pcu > demand_flow_pcu * 2
    """
  )
  if result and result.get("cnt", 0) > 0:
    warnings.append(
      f"发现 {result['cnt']} 条 capacity 大于 demand 2 倍的记录 "
      "（可能存在数据质量问题）"
    )

  return {
    "table": table,
    "check": "capacity_demand_relationship",
    "valid": len(warnings) == 0,
    "errors": [],
    "warnings": warnings,
  }


def run_all_checks(params: Optional[dict] = None) -> list[dict]:
  """
  运行所有 M3 校验检查

  参数:
    params: 可选参数，包含 scheme_id, start_date, end_date

  返回:
    校验结果列表
  """
  logger.info("运行 M3 校验检查...")

  results = [
    check_impacted_flow_required_fields(params),
    check_impacted_flow_value_ranges(params),
    check_impacted_flow_uniqueness(params),
    check_impact_ratio_calculation(params),
    check_impact_level_consistency(params),
    check_capacity_demand_relationship(params),
  ]

  failed = [r for r in results if not r["valid"]]
  if failed:
    logger.warning(f"发现 {len(failed)} 项未通过的检查")
    for r in failed:
      logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
  else:
    logger.info("所有 M3 校验检查均已通过")

  return results
