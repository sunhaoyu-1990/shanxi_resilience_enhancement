"""
src.common.time_utils 的单元测试
"""

import pytest
from datetime import date, datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.common.time_utils import (
  parse_date,
  format_date,
  expand_date_range,
  generate_batch_no,
  days_between,
)


class TestParseDate:
  """日期解析测试"""

  def test_parse_standard_format(self):
    """测试解析 YYYY-MM-DD 格式"""
    result = parse_date("2026-04-01")
    assert result == date(2026, 4, 1)

  def test_parse_slash_format(self):
    """测试解析 YYYY/MM/DD 格式"""
    result = parse_date("2026/04/01")
    assert result == date(2026, 4, 1)

  def test_parse_compact_format(self):
    """测试解析 YYYYMMDD 格式"""
    result = parse_date("20260401")
    assert result == date(2026, 4, 1)

  def test_parse_invalid_raises_error(self):
    """测试无效日期抛出 ValueError"""
    with pytest.raises(ValueError):
      parse_date("invalid-date")


class TestExpandDateRange:
  """日期范围扩展测试"""

  def test_expand_single_day(self):
    """测试扩展单个日期"""
    dates = list(expand_date_range("2026-04-01", "2026-04-01"))
    assert len(dates) == 1
    assert dates[0] == date(2026, 4, 1)

  def test_expand_multiple_days(self):
    """测试扩展多个日期"""
    dates = list(expand_date_range("2026-04-01", "2026-04-03"))
    assert len(dates) == 3
    assert dates[0] == date(2026, 4, 1)
    assert dates[2] == date(2026, 4, 3)


class TestGenerateBatchNo:
  """批次号生成测试"""

  def test_batch_no_format(self):
    """测试批次号格式"""
    batch_no = generate_batch_no("2026-04-01", prefix="TEST")
    assert batch_no.startswith("TEST_")
    assert "20260401" in batch_no

  def test_batch_no_default_prefix(self):
    """测试默认前缀"""
    batch_no = generate_batch_no("2026-04-01")
    assert batch_no.startswith("BATCH_")


class TestDaysBetween:
  """天数计算测试"""

  def test_same_day(self):
    """测试同日返回 0"""
    result = days_between("2026-04-01", "2026-04-01")
    assert result == 0

  def test_consecutive_days(self):
    """测试连续日期返回 1"""
    result = days_between("2026-04-01", "2026-04-02")
    assert result == 1

  def test_week_apart(self):
    """测试相差一周返回 7"""
    result = days_between("2026-04-01", "2026-04-08")
    assert result == 7
