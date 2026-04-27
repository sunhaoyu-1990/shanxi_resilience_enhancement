"""
数据校验工具模块
提供输入数据和数据库校验的通用函数
"""

from datetime import date, datetime
from typing import Any, Optional

from src.app.exceptions import DataValidationError
from src.app.logger import get_logger
from src.common.sql_runner import get_sql_runner

logger = get_logger(__name__)


def validate_not_empty(value: Any, field_name: str) -> None:
  """
  校验值是否为空

  Args:
    value: 待校验的值
    field_name: 字段名，用于错误信息

  Raises:
    DataValidationError: 值为 None 或空字符串时抛出
  """
  if value is None:
    raise DataValidationError(
      message=f"字段 '{field_name}' 不能为 None",
      field=field_name,
      constraint="not_null",
    )

  if isinstance(value, str) and not value.strip():
    raise DataValidationError(
      message=f"字段 '{field_name}' 不能为空",
      field=field_name,
      constraint="not_empty",
    )


def validate_date_range(
  start_date: date | str | None,
  end_date: date | str | None,
  allow_none: bool = False,
) -> tuple[date, date]:
  """
  校验并解析日期范围

  Args:
    start_date: 开始日期
    end_date: 结束日期
    allow_none: 是否允许 None 值

  Returns:
    (start_date, end_date) 元组，类型为 date 对象

  Raises:
    DataValidationError: 校验失败时抛出
  """
  if start_date is None or end_date is None:
    if allow_none:
      raise DataValidationError(
        message="当 allow_none 为 False 时，日期范围不能为 None",
        constraint="date_range",
      )
    raise DataValidationError(
      message="日期范围不能为 None",
      constraint="date_range",
    )

  # 解析字符串日期
  if isinstance(start_date, str):
    start_date = parse_date(start_date)
  if isinstance(end_date, str):
    end_date = parse_date(end_date)

  if start_date and end_date and start_date > end_date:
    raise DataValidationError(
      message=f"开始日期 ({start_date}) 不能晚于结束日期 ({end_date})",
      constraint="start_before_end",
    )

  return start_date, end_date


def parse_date(date_str: str) -> date:
  """
  将日期字符串解析为 date 对象

  Args:
    date_str: 日期字符串，支持多种格式

  Returns:
    date 对象

  Raises:
    DataValidationError: 解析失败时抛出
  """
  if not date_str:
    raise DataValidationError(message="日期字符串不能为空", constraint="date_format")

  formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"]
  for fmt in formats:
    try:
      dt = datetime.strptime(date_str, fmt)
      return dt.date()
    except ValueError:
      continue

  raise DataValidationError(
    message=f"无法解析日期: {date_str}",
    field="date_str",
    constraint="date_format",
  )


def validate_id_field(value: Any, field_name: str, id_type: str = "id") -> str:
  """
  校验 ID 字段

  Args:
    value: ID 值
    field_name: 字段名
    id_type: ID 类型（如 "section"、"scheme"、"od"）

  Returns:
    校验通过后返回字符串形式的 ID

  Raises:
    DataValidationError: 校验失败时抛出
  """
  validate_not_empty(value, field_name)

  if not isinstance(value, (str, int)):
    raise DataValidationError(
      message=f"无效的 {id_type} 类型: 期望 str 或 int，实际 {type(value).__name__}",
      field=field_name,
      constraint="valid_type",
    )

  return str(value)


def check_table_exists(table_name: str, schema: str = "public") -> bool:
  """
  检查数据库表是否存在

  Args:
    table_name: 表名
    schema: schema 名（默认为 public）

  Returns:
    表存在返回 True，否则返回 False
  """
  try:
    sql_runner = get_sql_runner()
    result = sql_runner.fetch_one(
      """
      SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = :schema
        AND table_name = :table_name
      ) AS exists
      """,
      params={"schema": schema, "table_name": table_name},
    )
    return result.get("exists", False) if result else False
  except Exception as e:
    logger.warning(f"检查表是否存在时出错: {e}")
    return False


def validate_foreign_key(
  table_name: str,
  column_name: str,
  value: Any,
  schema: str = "public",
) -> bool:
  """
  校验外键值是否在关联表中存在

  Args:
    table_name: 关联表名
    column_name: 待检查的列名
    value: 待校验的值
    schema: schema 名

  Returns:
    值存在返回 True，否则返回 False
  """
  if value is None:
    return True  # NULL 允许

  try:
    sql_runner = get_sql_runner()
    result = sql_runner.fetch_one(
      f"""
      SELECT EXISTS (
        SELECT 1 FROM {schema}.{table_name}
        WHERE {column_name} = :value
        LIMIT 1
      ) AS exists
      """,
      params={"value": value},
    )
    return result.get("exists", False) if result else False
  except Exception as e:
    logger.warning(f"校验外键时出错: {e}")
    return False


def validate_numeric_range(
  value: float | int,
  field_name: str,
  min_value: Optional[float] = None,
  max_value: Optional[float] = None,
) -> None:
  """
  校验数值是否在指定范围内

  Args:
    value: 待校验的值
    field_name: 字段名
    min_value: 最小值（包含）
    max_value: 最大值（包含）

  Raises:
    DataValidationError: 校验失败时抛出
  """
  if min_value is not None and value < min_value:
    raise DataValidationError(
      message=f"字段 '{field_name}' 的值 {value} 低于最小值 {min_value}",
      field=field_name,
      constraint=f"min_value:{min_value}",
    )

  if max_value is not None and value > max_value:
    raise DataValidationError(
      message=f"字段 '{field_name}' 的值 {value} 超过最大值 {max_value}",
      field=field_name,
      constraint=f"max_value:{max_value}",
    )


def validate_enum_value(
  value: str,
  field_name: str,
  allowed_values: list[str],
) -> None:
  """
  校验值是否在允许列表中

  Args:
    value: 待校验的值
    field_name: 字段名
    allowed_values: 允许的值列表

  Raises:
    DataValidationError: 校验失败时抛出
  """
  if value not in allowed_values:
    raise DataValidationError(
      message=f"字段 '{field_name}' 的值 '{value}' 不在允许列表中: {allowed_values}",
      field=field_name,
      constraint=f"enum:{allowed_values}",
    )


class SchemaValidator:
  """数据库 schema 合规性校验器"""

  def __init__(self, schema_name: str = "public"):
    self.schema_name = schema_name
    self.sql_runner = get_sql_runner()

  def get_table_columns(self, table_name: str) -> list[dict[str, Any]]:
    """获取表的列信息"""
    return self.sql_runner.fetch_all(
      """
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns
      WHERE table_schema = :schema
      AND table_name = :table_name
      ORDER BY ordinal_position
      """,
      params={"schema": self.schema_name, "table_name": table_name},
    )

  def validate_required_columns(
    self,
    table_name: str,
    required_columns: list[str],
  ) -> list[str]:
    """
    校验表是否包含所有必填列

    Args:
      table_name: 待校验的表名
      required_columns: 必填列名列表

    Returns:
      缺失的列名列表（空列表表示全部存在）
    """
    try:
      existing_columns = self.get_table_columns(table_name)
      existing_names = {col["column_name"] for col in existing_columns}
      missing = [col for col in required_columns if col not in existing_names]

      if missing:
        logger.warning(f"表 {table_name} 缺失列: {missing}")

      return missing
    except Exception as e:
      logger.error(f"校验表列时出错: {e}")
      return required_columns  # 出错时假设全部缺失

  def validate_primary_key(self, table_name: str) -> Optional[list[str]]:
    """获取表的主键列"""
    try:
      result = self.sql_runner.fetch_all(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
        AND tc.table_name = :table_name
        AND tc.table_schema = :schema
        ORDER BY kcu.ordinal_position
        """,
        params={"table_name": table_name, "schema": self.schema_name},
      )
      return [row["column_name"] for row in result] if result else None
    except Exception as e:
      logger.error(f"获取主键时出错: {e}")
      return None
