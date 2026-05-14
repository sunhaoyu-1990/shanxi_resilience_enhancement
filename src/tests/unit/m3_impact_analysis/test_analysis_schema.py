"""
analysis_schema Pydantic 模型单元测试
覆盖: 参数校验、默认值、边界情况
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from pydantic import ValidationError

from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdQueryParams,
    AffectedOdPathRecord,
    AffectedOdQueryResult,
    MidTripExitParams,
    MidTripExitRecord,
    MidTripExitResult,
)


# ============================================================
# AffectedOdQueryParams
# ============================================================


class TestAffectedOdQueryParams:
    """施工影响OD查询参数模型测试"""

    def test_normal_creation(self):
        """正常创建参数"""
        params = AffectedOdQueryParams(
            sectionIds="G001|G002",
            startDate="20260315",
            endDate="20260415",
        )
        assert params.sectionIds == "G001|G002"
        assert params.startDate == "20260315"
        assert params.endDate == "20260415"

    def test_single_section_id(self):
        """单个施工收费单元"""
        params = AffectedOdQueryParams(
            sectionIds="G007061003000210",
            startDate="20260301",
            endDate="20260331",
        )
        assert "G007061003000210" in params.sectionIds
        assert "|" not in params.sectionIds

    def test_missing_required_field(self):
        """缺少必填字段应报错"""
        with pytest.raises(ValidationError):
            AffectedOdQueryParams(startDate="20260301", endDate="20260331")

        with pytest.raises(ValidationError):
            AffectedOdQueryParams(sectionIds="G001", endDate="20260331")

        with pytest.raises(ValidationError):
            AffectedOdQueryParams(sectionIds="G001", startDate="20260301")

    def test_pipe_separated_format(self):
        """管道分隔格式"""
        params = AffectedOdQueryParams(
            sectionIds="A|B|C|D|E",
            startDate="20260101",
            endDate="20260102",
        )
        assert params.sectionIds.split("|") == ["A", "B", "C", "D", "E"]


# ============================================================
# AffectedOdPathRecord
# ============================================================


class TestAffectedOdPathRecord:
    """受影响OD-Path记录模型测试"""

    def test_normal_creation(self):
        """正常创建记录"""
        record = AffectedOdPathRecord(
            od_section_path_id=123,
            enid="EN001",
            exid="EX001",
            numpath="1|2|3",
            fixed_intervalpath="S1|S2|S3",
        )
        assert record.od_section_path_id == 123
        assert record.affected_section_ids == ""
        assert record.construction_flow is None
        assert record.same_period_2025_flow is None

    def test_with_all_fields(self):
        """所有字段赋值"""
        record = AffectedOdPathRecord(
            od_section_path_id=456,
            enid="EN002",
            exid="EX002",
            numpath="4|5",
            fixed_intervalpath="S4|S5",
            affected_section_ids="S4",
            construction_flow=100,
            same_period_2025_flow=80,
        )
        assert record.construction_flow == 100
        assert record.same_period_2025_flow == 80

    def test_missing_required_field(self):
        """缺少必填字段"""
        with pytest.raises(ValidationError):
            AffectedOdPathRecord(enid="EN", exid="EX")

    def test_model_dump(self):
        """模型序列化"""
        record = AffectedOdPathRecord(
            od_section_path_id=1,
            enid="A",
            exid="B",
            numpath="1",
            fixed_intervalpath="X",
            construction_flow=50,
        )
        d = record.model_dump()
        assert d["od_section_path_id"] == 1
        assert d["construction_flow"] == 50
        assert d["same_period_2025_flow"] is None


# ============================================================
# AffectedOdQueryResult
# ============================================================


class TestAffectedOdQueryResult:
    """流程1结果模型测试"""

    def test_default_values(self):
        """默认值"""
        result = AffectedOdQueryResult()
        assert result.status == "pending"
        assert result.affectedOdCount == 0
        assert result.constructionFlowAvailable is False
        assert result.samePeriod2025FlowAvailable is False
        assert result.outputCsvPath is None
        assert result.errors == []
        assert result.warnings == []
        assert result.executionTime is None

    def test_with_values(self):
        """赋值"""
        result = AffectedOdQueryResult(
            status="success",
            affectedOdCount=100,
            constructionFlowAvailable=True,
            outputCsvPath="/tmp/out.csv",
            executionTime=5.5,
        )
        assert result.status == "success"
        assert result.affectedOdCount == 100


# ============================================================
# MidTripExitParams
# ============================================================


class TestMidTripExitParams:
    """中途下站检测参数模型测试"""

    def test_with_csv(self):
        """使用CSV输入"""
        params = MidTripExitParams(
            affectedOdCsv="/tmp/od.csv",
            startDate="20260301",
            endDate="20260305",
        )
        assert params.affectedOdCsv == "/tmp/od.csv"
        assert params.odPairs is None
        assert params.dataDir == "/home/shy/gaosu_data"

    def test_with_od_pairs_string(self):
        """使用OD对字符串输入"""
        params = MidTripExitParams(
            odPairs="EN1:EX1,EN2:EX2",
            startDate="20260301",
            endDate="20260305",
            dataDir="/custom/dir",
        )
        assert params.odPairs == "EN1:EX1,EN2:EX2"
        assert params.affectedOdCsv is None
        assert params.dataDir == "/custom/dir"

    def test_default_data_dir(self):
        """默认数据目录"""
        params = MidTripExitParams(
            odPairs="A:B",
            startDate="20260101",
            endDate="20260102",
        )
        assert params.dataDir == "/home/shy/gaosu_data"

    def test_missing_date(self):
        """缺少日期"""
        with pytest.raises(ValidationError):
            MidTripExitParams(odPairs="A:B")


# ============================================================
# MidTripExitRecord
# ============================================================


class TestMidTripExitRecord:
    """中途下站记录模型测试"""

    def test_normal_creation(self):
        """正常创建"""
        record = MidTripExitRecord(
            od_enid="EN1",
            od_exid="EX1",
            vehicle_id="陕A12345_0",
            trip1_enid="EN1",
            trip1_exid="MID1",
            trip1_entime="2026-03-01 08:00:00",
            trip1_extime="2026-03-01 10:00:00",
            trip2_enid="MID2",
            trip2_exid="EX1",
            trip2_entime="2026-03-01 12:00:00",
            trip2_extime="2026-03-01 14:00:00",
            time_gap_hours=2.0,
            period="construction",
        )
        assert record.vehicle_id == "陕A12345_0"
        assert record.time_gap_hours == 2.0
        assert record.period == "construction"

    def test_default_intervalgroup(self):
        """默认intervalgroup为空"""
        record = MidTripExitRecord(
            od_enid="A", od_exid="B", vehicle_id="V1",
            trip1_enid="A", trip1_exid="M",
            trip1_entime="2026-01-01 00:00:00", trip1_extime="2026-01-01 01:00:00",
            trip2_enid="N", trip2_exid="B",
            trip2_entime="2026-01-01 02:00:00", trip2_extime="2026-01-01 03:00:00",
            time_gap_hours=1.0,
            period="same_period_2025",
        )
        assert record.trip1_intervalgroup == ""
        assert record.trip2_intervalgroup == ""


# ============================================================
# MidTripExitResult
# ============================================================


class TestMidTripExitResult:
    """流程2结果模型测试"""

    def test_default_values(self):
        """默认值"""
        result = MidTripExitResult()
        assert result.status == "pending"
        assert result.totalRecordsScanned == 0
        assert result.matchedRecordsScanned == 0
        assert result.midTripExitCount == 0
        assert result.daysProcessed == 0
        assert result.errors == []
