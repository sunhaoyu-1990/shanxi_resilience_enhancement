"""
M0 数据工程输出校验
验证输出表的数据质量与完整性
"""

from typing import dict, list

from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def check_dim_section_info_required_fields(params: dict = None) -> dict:
  """
  检查 dim_section_info 中必填字段是否为空

  参数:
    params: 可选参数

  返回:
    包含 'valid' 和 'errors' 键的校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  # 检查 section_id 非空
  result = sql_runner.fetch_one(
    "SELECT COUNT(*) AS cnt FROM dim_section_info WHERE section_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_id 为空的记录")

  # 检查 section_number 非空
  result = sql_runner.fetch_one(
    "SELECT COUNT(*) AS cnt FROM dim_section_info WHERE section_number IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 section_number 为空的记录")

  return {
    "table": "dim_section_info",
    "check": "required_fields",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_dim_section_info_uniqueness(params: dict = None) -> dict:
  """
  检查 dim_section_info 中的唯一性约束

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  # 检查 section_id + valid_start_date 是否有重复
  result = sql_runner.fetch_one(
    """
    SELECT COUNT(*) AS cnt FROM (
      SELECT section_id, valid_start_date, COUNT(*) AS cnt
      FROM dim_section_info
      GROUP BY section_id, valid_start_date
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组重复的 section_id+valid_start_date 组合")

  return {
    "table": "dim_section_info",
    "check": "uniqueness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_dwd_scheme_section_map_validity(params: dict = None) -> dict:
  """
  检查方案-路段映射的有效性

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  # 检查 lane_occupied_cnt >= 0
  result = sql_runner.fetch_one(
    "SELECT COUNT(*) AS cnt FROM dwd_scheme_section_map WHERE lane_occupied_cnt < 0"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 lane_occupied_cnt 为负数的记录")

  # 检查日期一致性
  result = sql_runner.fetch_one(
    """
    SELECT COUNT(*) AS cnt FROM dwd_scheme_section_map
    WHERE valid_end_date IS NOT NULL AND valid_end_date < valid_start_date
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条日期范围无效的记录")

  return {
    "table": "dwd_scheme_section_map",
    "check": "validity",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def check_dwd_od_path_map_completeness(params: dict = None) -> dict:
  """
  检查 OD-路径映射的完整性

  参数:
    params: 可选参数

  返回:
    校验结果字典
  """
  sql_runner = get_sql_runner()
  errors = []

  # 检查 od_id 或 path_id 是否为空
  result = sql_runner.fetch_one(
    "SELECT COUNT(*) AS cnt FROM dwd_od_path_map WHERE od_id IS NULL OR path_id IS NULL"
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 条 od_id 或 path_id 为空的记录")

  # 检查 od_id + path_id 是否有重复
  result = sql_runner.fetch_one(
    """
    SELECT COUNT(*) AS cnt FROM (
      SELECT od_id, path_id, COUNT(*) AS cnt
      FROM dwd_od_path_map
      GROUP BY od_id, path_id
      HAVING COUNT(*) > 1
    ) duplicates
    """
  )
  if result and result.get("cnt", 0) > 0:
    errors.append(f"发现 {result['cnt']} 组重复的 od_id+path_id 组合")

  return {
    "table": "dwd_od_path_map",
    "check": "completeness",
    "valid": len(errors) == 0,
    "errors": errors,
  }


def run_all_checks(params: dict = None) -> list[dict]:
  """
  运行所有 M0 校验检查

  参数:
    params: 可选参数

  返回:
    校验结果列表
  """
  logger.info("正在运行 M0 校验检查...")

  results = [
    check_dim_section_info_required_fields(params),
    check_dim_section_info_uniqueness(params),
    check_dwd_scheme_section_map_validity(params),
    check_dwd_od_path_map_completeness(params),
  ]

  failed = [r for r in results if not r["valid"]]
  if failed:
    logger.warning(f"发现 {len(failed)} 项校验未通过")
    for r in failed:
      logger.warning(f"  - {r['table']}.{r['check']}: {r['errors']}")
  else:
    logger.info("所有 M0 校验检查均已通过")

  return results
