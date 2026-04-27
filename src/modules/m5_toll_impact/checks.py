"""
M5 通行费影响测算输出数据校验
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


def check_toll_impact_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 ads_toll_impact_result 中必填字段是否为空

  参数:
    params: 可选参数，包含 scheme_id, start_date, end_date

  返回:
    包含 'valid' 和 'errors' 键的校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_toll_impact_result"

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

  # 检查 impact_type 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND impact_type IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 impact_type 为 NULL 的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_toll_impact_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 ads_toll_impact_result 中的数值范围

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_toll_impact_result"

  # 检查 diverted_flow_pcu >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND diverted_flow_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 diverted_flow_pcu 为负数的记录")

  # 检查费用金额 >= 0（费用应为非负）
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND original_fee_yuan < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 original_fee_yuan 为负数的记录")

  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND diverted_fee_yuan < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 diverted_fee_yuan 为负数的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_toll_impact_uniqueness(params: Optional[dict] = None) -> dict:
  """
  检查 ads_toll_impact_result 中的唯一性约束

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_toll_impact_result"

  # 检查 od_id + 路径组合 + stat_date 的重复情况
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM (
      SELECT od_id, original_path_id, recommended_path_id, scheme_id, stat_date, COUNT(*) AS cnt
      FROM {table}
      {where_clause}
      GROUP BY od_id, original_path_id, recommended_path_id, scheme_id, stat_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组 od_id+路径+stat_date 重复的组合")

  return {
    "table": table,
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_toll_impact_calculation(params: Optional[dict] = None) -> dict:
  """
  验证费用影响计算是否正确

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_toll_impact_result"

  # 检查 fee_impact = diverted_flow * (diverted_fee - original_fee)
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE ABS(fee_impact_yuan - diverted_flow_pcu * (diverted_fee_yuan - original_fee_yuan)) > 0.01
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条 fee_impact 计算错误的记录"
    )

  # 检查 impact_type 与 fee_impact 符号的一致性
  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_type = 'fee_increase' AND fee_impact_yuan <= 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'fee_increase' 但 fee_impact 不为正的记录"
    )

  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_type = 'fee_decrease' AND fee_impact_yuan >= 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'fee_decrease' 但 fee_impact 不为负的记录"
    )

  result = sql_runner.fetch_one(
    f"""
    SELECT COUNT(*) AS cnt FROM {table} {where_clause}
    WHERE impact_type = 'no_impact' AND fee_impact_yuan != 0
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(
      f"发现 {result['cnt']} 条标记为 'no_impact' 但 fee_impact 不为 0 的记录"
    )

  return {
    "table": table,
    "check": "calculation",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_scheme_summary_required_fields(params: Optional[dict] = None) -> dict:
  """
  检查 ads_scheme_summary 中必填字段是否为空

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_scheme_summary"

  # 检查 scheme_id 不为空
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND scheme_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 scheme_id 为 NULL 的记录")

  return {
    "table": table,
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_scheme_summary_value_ranges(params: Optional[dict] = None) -> dict:
  """
  检查 ads_scheme_summary 中的数值范围

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []
  where_clause = _build_where_clause(params)
  table = "ads_scheme_summary"

  # 检查计数 >= 0
  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND impacted_section_cnt < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 impacted_section_cnt 为负数的记录")

  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND impacted_od_cnt < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 impacted_od_cnt 为负数的记录")

  result = sql_runner.fetch_one(
    f"SELECT COUNT(*) AS cnt FROM {table} {where_clause} AND total_diverted_flow_pcu < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 total_diverted_flow_pcu 为负数的记录")

  return {
    "table": table,
    "check": "value_ranges",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_scheme_summary_reconciliation(params: Optional[dict] = None) -> dict:
  """
  检查方案汇总能否与通行费影响明细对账

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  warnings = []
  where_clause = _build_where_clause(params)

  if not params or not params.get("scheme_id"):
    return {
      "table": "ads_scheme_summary",
      "check": "reconciliation",
      "valid": True,
      "errors": [],
      "warnings": ["未提供 scheme_id，跳过对账检查"],
    }

  # 检查 total_fee_increase + total_fee_decrease = |net_fee_impact|
  result = sql_runner.fetch_one(
    f"""
    SELECT
      total_fee_increase_yuan,
      total_fee_decrease_yuan,
      net_fee_impact_yuan
    FROM ads_scheme_summary
    WHERE scheme_id = '{params['scheme_id']}'
    LIMIT 1
    """
  )
  if result:
    net_from_components = (
      result.get("total_fee_increase_yuan", 0) - result.get("total_fee_decrease_yuan", 0)
    )
    actual_net = result.get("net_fee_impact_yuan", 0)
    if abs(net_from_components - actual_net) > 0.01:
      warnings.append(
        f"方案汇总: net_fee_impact ({actual_net}) 与 "
        f"fee_increase - fee_decrease ({net_from_components}) 不一致"
      )

  return {
    "table": "ads_scheme_summary",
    "check": "reconciliation",
    "valid": len(warnings) == 0,
    "errors": [],
    "warnings": warnings,
  }


def run_all_checks(params: Optional[dict] = None) -> list[dict]:
  """
  运行所有 M5 校验检查

  参数:
    params: 可选参数，包含 scheme_id, start_date, end_date

  返回:
    校验结果列表
  """
  logger.info("运行 M5 校验检查...")

  results = [
    check_toll_impact_required_fields(params),
    check_toll_impact_value_ranges(params),
    check_toll_impact_uniqueness(params),
    check_toll_impact_calculation(params),
    check_scheme_summary_required_fields(params),
    check_scheme_summary_value_ranges(params),
    check_scheme_summary_reconciliation(params),
  ]

  failed = [r for r in results if not r["valid"]]
  if failed:
    logger.warning(f"发现 {len(failed)} 项未通过的检查")
    for r in failed:
      logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
  else:
    logger.info("所有 M5 校验检查均已通过")

  return results
