"""
src.app.enums 的单元测试
"""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.app.enums import (
  ModuleCode,
  TaskStatus,
  SourceFlag,
  VehicleType,
  ImpactType,
  SchemeStatus,
)


class TestModuleCode:
  """ModuleCode 枚举测试"""

  def test_all_modules_present(self):
    """测试所有 M0-M5 模块都存在"""
    assert ModuleCode.M0.value == "m0"
    assert ModuleCode.M1.value == "m1"
    assert ModuleCode.M2.value == "m2"
    assert ModuleCode.M3.value == "m3"
    assert ModuleCode.M4.value == "m4"
    assert ModuleCode.M5.value == "m5"

  def test_display_name(self):
    """测试显示名称正确"""
    assert "M0" in ModuleCode.M0.display_name
    assert "M1" in ModuleCode.M1.display_name

  def test_sql_dir(self):
    """测试 SQL 目录路径"""
    assert "m0" in ModuleCode.M0.sql_dir
    assert "m1" in ModuleCode.M1.sql_dir


class TestTaskStatus:
  """TaskStatus 枚举测试"""

  def test_status_values(self):
    """测试所有状态值"""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.SUCCESS.value == "success"
    assert TaskStatus.FAILED.value == "failed"

  def test_is_terminal(self):
    """测试终态检测"""
    assert TaskStatus.SUCCESS.is_terminal is True
    assert TaskStatus.FAILED.is_terminal is True
    assert TaskStatus.RUNNING.is_terminal is False

  def test_is_success(self):
    """测试成功状态检测"""
    assert TaskStatus.SUCCESS.is_success is True
    assert TaskStatus.PARTIAL_SUCCESS.is_success is True
    assert TaskStatus.FAILED.is_success is False


class TestSourceFlag:
  """SourceFlag 枚举测试"""

  def test_source_values(self):
    """测试来源标识值"""
    assert SourceFlag.ACTUAL.value == "actual"
    assert SourceFlag.FILLED.value == "filled"
    assert SourceFlag.RULE.value == "rule"
    assert SourceFlag.API.value == "api"


class TestVehicleType:
  """VehicleType 枚举测试"""

  def test_vehicle_types(self):
    """测试车型值"""
    assert VehicleType.PASSENGER_SMALL.value == "passenger_small"
    assert VehicleType.TRUCK_LARGE.value == "truck_large"

  def test_from_code(self):
    """测试从数字代码创建"""
    assert VehicleType.from_code(1) == VehicleType.PASSENGER_SMALL
    assert VehicleType.from_code(6) == VehicleType.TRUCK_LARGE
