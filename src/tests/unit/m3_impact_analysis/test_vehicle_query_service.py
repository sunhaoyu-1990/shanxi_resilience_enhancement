"""
vehicle_query_service 高频车辆查询服务单元测试
覆盖: 日期解析、OD对解析、核心逻辑
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest

from src.modules.m3_impact_analysis.vehicle_query_service import (
    parse_date_range,
    parse_od_pairs,
    get_daily_files,
    VehicleQueryService,
)


class TestParseDateRange:
    def test_valid_range(self):
        start, end = parse_date_range("20260301-20260331")
        assert start == "20260301"
        assert end == "20260331"

    def test_with_spaces(self):
        start, end = parse_date_range("20260301 - 20260331")
        assert start == "20260301"
        assert end == "20260331"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="日期范围格式错误"):
            parse_date_range("20260301")

    def test_invalid_date_length(self):
        with pytest.raises(ValueError, match="日期格式错误"):
            parse_date_range("2026031-20260331")

    def test_start_after_end(self):
        with pytest.raises(ValueError, match="开始日期不能晚于结束日期"):
            parse_date_range("20260331-20260301")


class TestParseOdPairs:
    def test_single_od(self):
        result = parse_od_pairs(["E1:X1"])
        assert result == {("E1", "X1")}

    def test_multiple_ods(self):
        result = parse_od_pairs(["E1:X1", "E2:X2"])
        assert result == {("E1", "X1"), ("E2", "X2")}

    def test_duplicate_ods(self):
        result = parse_od_pairs(["E1:X1", "E1:X1"])
        assert len(result) == 1

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="OD 对格式错误"):
            parse_od_pairs(["E1X1"])

    def test_empty_enid(self):
        with pytest.raises(ValueError, match="enid 和 exid 不能为空"):
            parse_od_pairs([":X1"])

    def test_with_spaces(self):
        result = parse_od_pairs([" E1 : X1 "])
        assert result == {("E1", "X1")}


class TestGetDailyFiles:
    def test_no_files(self):
        """不存在的目录返回空"""
        files = get_daily_files("20260301", "20260302", "/nonexistent_dir")
        assert len(files) == 0

    def test_with_existing_dir(self):
        """有文件的目录返回文件列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建月目录和文件
            month_dir = os.path.join(tmpdir, "202603")
            os.makedirs(month_dir)
            for day in ["20260301", "20260302"]:
                filepath = os.path.join(month_dir, f"data_{day}.csv")
                with open(filepath, "w") as f:
                    f.write("header\n")

            files = get_daily_files("20260301", "20260302", tmpdir)
            assert len(files) == 2


class TestVehicleQueryService:
    def test_run_no_files(self):
        """无数据文件时返回空"""
        service = VehicleQueryService()
        result = service.run(
            top_od_pairs=[("E1", "X1")],
            start_date="20260301",
            end_date="20260302",
            data_dir="/nonexistent_dir",
            output_dir=os.path.join(tempfile.gettempdir(), "test_vq"),
        )
        assert result == {}
