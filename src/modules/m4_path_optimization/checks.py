"""
M4 分流路径优化输出数据校验
验证输出表的数据质量和完整性
"""

from typing import Any, Optional

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def _build_where_clause(params: Optional[dict], table_alias: str = "") -> str:
  """从 params 构建 WHERE 子句"""
  if not params:
    return ""
  prefix = f"{table_alias}." if table_alias else ""
  conditions = []
  if params.get("scheme_id"):
    conditions.append(f"{prefix}scheme_id = '{params['scheme_id']}'")
  if params.get("start_date"):
    conditions.append(f"{prefix}stat_date >= '{params['start_date']}'")
  if params.get("end_date"):
    conditions.append(f"{prefix}stat_date <= '{params['end_date']}'")
  if conditions:
    return "WHERE " + " AND ".join(conditions)
  return ""


def check_candidate_path_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 dws_od_candidate_path 中必填字段是否为空

  参数:
    params: 可选参数，包含 scheme_id, start_date, end_date

  返回:
    包含 'valid' 和 'errors' 键的校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_od_candidate_path"

  # 检查 od_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND od_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 od_id 为 NULL 的记录")

  # 检查 path_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND path_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 path_id 为 NULL 的记录")

  # 检查 control_section_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND control_section_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 control_section_id 为 NULL 的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_candidate_path_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 dws_od_candidate_path 中的数值范围

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_od_candidate_path"

  # 检查非原路径的 mileage_diff >= 0
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE original_path_id IS NOT NULL
      AND mileage_diff < 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条备选路径 mileage_diff 为负数的记录")

  # 检查非原路径的 fee_diff >= 0
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE original_path_id IS NOT NULL
      AND fee_diff < 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条备选路径 fee_diff 为负数的记录")

  # 检查 mileage_km > 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND mileage_km <= 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 mileage_km 不大于 0 的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_candidate_path_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 dws_od_candidate_path 中的唯一性约束

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "dws_od_candidate_path"

  # 检查 od_id + path_id + stat_date 的重复情况
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM (
      SELECT od_id, path_id, scheme_id, stat_date, COUNT(*) AS cnt
      FROM {table}
      {where_clause}
      GROUP BY od_id, path_id, scheme_id, stat_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组 od_id+path_id+stat_date 重复的组合")

  return {
    "table": table,
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_diversion_plan_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 ads_od_diversion_plan 中必填字段是否为空

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_od_diversion_plan"

  # 检查 od_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND od_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 od_id 为 NULL 的记录")

  # 检查 original_path_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND original_path_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 original_path_id 为 NULL 的记录")

  # 检查 recommended_path_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND recommended_path_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 recommended_path_id 为 NULL 的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_diversion_plan_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 ads_od_diversion_plan 中的数值范围

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_od_diversion_plan"

  # 检查 diverted_flow_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND diverted_flow_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 diverted_flow_pcu 为负数的记录")

  # 检查 diversion_ratio 在 [0, 1] 范围内
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE diversion_ratio < 0 OR diversion_ratio > 1
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 diversion_ratio 超出 [0,1] 范围的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_diversion_plan_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 ads_od_diversion_plan 中的唯一性约束

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_od_diversion_plan"

  # 检查 od_id + stat_date 的重复情况
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM (
      SELECT od_id, scheme_id, stat_date, COUNT(*) AS cnt
      FROM {table}
      {where_clause}
      GROUP BY od_id, scheme_id, stat_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组 od_id+stat_date 重复的组合")

  return {
    "table": table,
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_path_recommendation_quality(params: Optional[dict] = None) -> dict:
  """
  检查路径推荐质量

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  warnings = []
  where_clause = _build_where_clause(params)

  # 检查推荐的路径是否被标记为不可行
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt
    FROM ads_od_diversion_plan p
    JOIN dws_od_candidate_path c
      ON p.od_id = c.od_id
      AND p.recommended_path_id = c.path_id
      AND p.scheme_id = c.scheme_id
    {where_clause}
    AND c.is_viable = FALSE
    """
  )
  if result and result.get("cnt", 0) > 0:
    warnings.append(
      f"发现 {result['cnt']} 个推荐了不可行路径的方案"
    )

  # 检查绕行距离过长的路径
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt
    FROM ads_od_diversion_plan
    {where_clause}
    WHERE mileage_diff > 50  -- 绕行超过 50km
    """
  )
  if result and result.get("cnt", 0) > 0:
    warnings.append(
      f"发现 {result['cnt']} 个绕行超过 50km 的方案"
    )

  return {
    "table": "ads_od_diversion_plan",
    "check": "recommendation_quality",
    "valid": len(warnings) == 0,
    "errors": [],
    "warnings": warnings,
  }


def run_all_checks(params: Optional[dict] = None) -> list[dict]:
  """
  运行所有 M4 校验检查

  参数:
    params: 可选参数，包含 scheme_id, start_date, end_date

  返回:
    校验结果列表
  """
  logger.info("运行 M4 校验检查...")

  results = [
    check_candidate_path_required_fields(params),
    check_candidate_path_value_ranges(params),
    check_candidate_path_uniqueness(params),
    check_diversion_plan_required_fields(params),
    check_diversion_plan_value_ranges(params),
    check_diversion_plan_uniqueness(params),
    check_path_recommendation_quality(params),
  ]

  failed = [r for r in results if not r["valid"]]
  if failed:
    logger.warning(f"发现 {len(failed)} 项未通过的检查")
    for r in failed:
      logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
  else:
    logger.info("所有 M4 校验检查均已通过")

  return results
