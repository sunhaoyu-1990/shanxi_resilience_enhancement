"""
时间和日期工具模块
提供日期处理、范围展开和批次号生成等函数
"""

from datetime import date, datetime, timedelta
from typing import Generator, Sequence

from src.app.logger import get_logger

logger = get_logger(__name__)


def parse_date(date_str: str) -> date:
  """
  将日期字符串解析为 date 对象

  Args:
    date_str: 日期字符串，格式支持: YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD

  Returns:
    date 对象

  Raises:
    ValueError: 解析失败时抛出
  """
  if not date_str:
    raise ValueError("日期字符串不能为空")

  formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]
  for fmt in formats:
    try:
      return datetime.strptime(date_str, fmt).date()
    except ValueError:
      continue

  raise ValueError(f"无法解析日期: {date_str}")


def format_date(d: date, fmt: str = "%Y-%m-%d") -> str:
  """
  将 date 对象格式化为字符串

  Args:
    d: date 对象
    fmt: 格式字符串

  Returns:
    格式化后的日期字符串
  """
  return d.strftime(fmt)


def expand_date_range(
  start_date: date | str,
  end_date: date | str,
) -> Generator[date, None, None]:
  """
  将日期范围展开为单个日期序列

  Args:
    start_date: 开始日期
    end_date: 结束日期

  Yields:
    范围内的每个日期（包含首尾）

  Example:
    >>> list(expand_date_range("2026-01-01", "2026-01-03"))
    [datetime.date(2026, 1, 1), datetime.date(2026, 1, 2), datetime.date(2026, 1, 3)]
  """
  if isinstance(start_date, str):
    start_date = parse_date(start_date)
  if isinstance(end_date, str):
    end_date = parse_date(end_date)

  current = start_date
  while current <= end_date:
    yield current
    current += timedelta(days=1)


def expand_date_range_batches(
  start_date: date | str,
  end_date: date | str,
  batch_size_days: int = 7,
) -> Generator[tuple[date, date], None, None]:
  """
  将日期范围按批次展开

  Args:
    start_date: 开始日期
    end_date: 结束日期
    batch_size_days: 每批天数

  Yields:
    每批的 (batch_start, batch_end) 元组

  Example:
    >>> list(expand_date_range_batches("2026-01-01", "2026-01-10", 3))
    [(datetime.date(2026, 1, 1), datetime.date(2026, 1, 3)),
     (datetime.date(2026, 1, 4), datetime.date(2026, 1, 6)),
     (datetime.date(2026, 1, 7), datetime.date(2026, 1, 9)),
     (datetime.date(2026, 1, 10), datetime.date(2026, 1, 10))]
  """
  if isinstance(start_date, str):
    start_date = parse_date(start_date)
  if isinstance(end_date, str):
    end_date = parse_date(end_date)

  current = start_date
  while current <= end_date:
    batch_end = min(current + timedelta(days=batch_size_days - 1), end_date)
    yield (current, batch_end)
    current = batch_end + timedelta(days=1)


def generate_batch_no(
  reference_date: date | str | None = None,
  prefix: str = "BATCH",
) -> str:
  """
  根据日期生成批次号

  Args:
    reference_date: 基准日期（默认为当天）
    prefix: 批次号前缀

  Returns:
    批次号字符串，格式: PREFIX_YYYYMMDD_HHMMSS

  Example:
    >>> generate_batch_no("2026-01-15")
    'BATCH_20260115_143022'
  """
  if reference_date is None:
    ref_dt = datetime.now()
  elif isinstance(reference_date, str):
    ref_dt = datetime.strptime(reference_date, "%Y-%m-%d")
  else:
    ref_dt = datetime.combine(reference_date, datetime.min.time())

  date_part = ref_dt.strftime("%Y%m%d")
  time_part = ref_dt.strftime("%H%M%S")

  return f"{prefix}_{date_part}_{time_part}"


def get_date_list(
  start_date: date | str,
  end_date: date | str,
) -> list[date]:
  """
  获取日期范围内的日期列表

  Args:
    start_date: 开始日期
    end_date: 结束日期

  Returns:
    date 对象列表
  """
  return list(expand_date_range(start_date, end_date))


def is_same_day(d1: date | datetime, d2: date | datetime) -> bool:
  """判断两个日期/时间是否在同一天"""
  if isinstance(d1, datetime):
    d1 = d1.date()
  if isinstance(d2, datetime):
    d2 = d2.date()
  return d1 == d2


def get_week_range(d: date | str) -> tuple[date, date]:
  """
  获取指定日期所在周的开始和结束日期

  Args:
    d: 基准日期

  Returns:
    (week_start, week_end) 元组，周从周一开始
  """
  if isinstance(d, str):
    d = parse_date(d)

  # weekday() 返回 0 表示周一，6 表示周日
  days_since_monday = d.weekday()
  week_start = d - timedelta(days=days_since_monday)
  week_end = week_start + timedelta(days=6)

  return week_start, week_end


def get_month_range(d: date | str) -> tuple[date, date]:
  """
  获取指定日期所在月的开始和结束日期

  Args:
    d: 基准日期

  Returns:
    (month_start, month_end) 元组
  """
  if isinstance(d, str):
    d = parse_date(d)

  month_start = d.replace(day=1)
  if d.month == 12:
    month_end = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
  else:
    month_end = d.replace(month=d.month + 1, day=1) - timedelta(days=1)

  return month_start, month_end


def get_quarter_range(d: date | str) -> tuple[date, date]:
  """
  获取指定日期所在季度的开始和结束日期

  Args:
    d: 基准日期

  Returns:
    (quarter_start, quarter_end) 元组
  """
  if isinstance(d, str):
    d = parse_date(d)

  quarter_start_month = ((d.month - 1) // 3) * 3 + 1
  quarter_start = d.replace(month=quarter_start_month, day=1)

  if quarter_start_month == 10:
    quarter_end = d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
  else:
    quarter_end = d.replace(month=quarter_start_month + 3, day=1) - timedelta(days=1)

  return quarter_start, quarter_end


def days_between(start_date: date | str, end_date: date | str) -> int:
  """
  计算两个日期之间的天数

  Args:
    start_date: 开始日期
    end_date: 结束日期

  Returns:
    天数（绝对值）
  """
  if isinstance(start_date, str):
    start_date = parse_date(start_date)
  if isinstance(end_date, str):
    end_date = parse_date(end_date)

  return abs((end_date - start_date).days)


def add_business_days(start_date: date | str, days: int) -> date:
  """
  向指定日期添加工作日（排除周末）

  Args:
    start_date: 起始日期
    days: 需要添加的工作日数（可为负数）

  Returns:
    结果日期
  """
  if isinstance(start_date, str):
    start_date = parse_date(start_date)

  current = start_date
  delta = 1 if days >= 0 else -1
  remaining = abs(days)

  while remaining > 0:
    current += timedelta(days=delta)
    # 跳过周末（5=周六，6=周日）
    if current.weekday() < 5:
      remaining -= 1

  return current


def timestamp_to_date(ts: datetime) -> date:
  """将 datetime 转换为 date"""
  if isinstance(ts, str):
    ts = datetime.fromisoformat(ts)
  return ts.date() if isinstance(ts, datetime) else ts


def now_date() -> date:
  """获取当前日期"""
  return datetime.now().date()


def now_datetime() -> datetime:
  """获取当前日期时间"""
  return datetime.now()
