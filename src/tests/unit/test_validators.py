"""
src.common.validators 的单元测试
"""

import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.common.validators import (
  validate_not_empty,
  validate_date_range,
  validate_numeric_range,
  validate_enum_value,
)
from src.app.exceptions import DataValidationError


class TestValidateNotEmpty:
  """非空校验测试"""

  def test_none_raises_error(self):
    """测试 None 抛出 DataValidationError"""
    with pytest.raises(DataValidationError) as exc_info:
      validate_not_empty(None, "test_field")
    assert "test_field" in str(exc_info.value)

  def test_empty_string_raises_error(self):
    """测试空字符串抛出 DataValidationError"""
    with pytest.raises(DataValidationError):
      validate_not_empty("", "test_field")

  def test_valid_value_passes(self):
    """测试有效值通过"""
    validate_not_empty("value", "test_field")
    validate_not_empty(0, "test_field")
    validate_not_empty([], "test_field")


class TestValidateDateRange:
  """日期范围校验测试"""

  def test_valid_range(self):
    """测试有效日期范围"""
    start, end = validate_date_range("2026-04-01", "2026-04-30")
    assert start == date(2026, 4, 1)
    assert end == date(2026, 4, 30)

  def test_start_after_end_raises_error(self):
    """测试起始日期晚于结束日期时抛出错误"""
    with pytest.raises(DataValidationError):
      validate_date_range("2026-04-30", "2026-04-01")


class TestValidateNumericRange:
  """数值范围校验测试"""

  def test_within_range(self):
    """测试范围内的值通过"""
    validate_numeric_range(50, "test_field", min_value=0, max_value=100)

  def test_below_min_raises_error(self):
    """测试低于最小值抛出错误"""
    with pytest.raises(DataValidationError):
      validate_numeric_range(-1, "test_field", min_value=0)

  def test_above_max_raises_error(self):
    """测试高于最大值抛出错误"""
    with pytest.raises(DataValidationError):
      validate_numeric_range(101, "test_field", max_value=100)


class TestValidateEnumValue:
  """枚举值校验测试"""

  def test_valid_enum(self):
    """测试有效枚举值通过"""
    validate_enum_value("m0", "module", ["m0", "m1", "m2"])

  def test_invalid_enum_raises_error(self):
    """测试无效枚举抛出错误"""
    with pytest.raises(DataValidationError):
      validate_enum_value("m9", "module", ["m0", "m1", "m2"])
