"""
impact_summary_service 综合汇总服务单元测试
覆盖: 流程1聚合(均值/求和/乘法/None处理)、流程2匹配、流程3汇总+匹配、CSV输出
"""

import csv
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest

from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdPathRecord,
    DetourFlowStatRecord,
    ImpactSummaryRecord,
    MidTripExitFlowStatRecord,
)
from src.modules.m3_impact_analysis.impact_summary_service import (
    ImpactSummaryService,
    _safe_mean,
    _safe_sum_int,
    _aggregate_flow1_records,
    _build_mid_trip_lookup,
    _aggregate_and_build_detour_lookup,
    IMPACT_SUMMARY_CSV_COLUMNS,
)


# ============================================================
# 工具函数测试
# ============================================================


class TestSafeMean:
    def test_all_values(self):
        assert _safe_mean([1.0, 2.0, 3.0]) == 2.0

    def test_with_none(self):
        assert _safe_mean([1.0, None, 3.0]) == 2.0

    def test_all_none(self):
        assert _safe_mean([None, None]) == 0.0

    def test_empty_list(self):
        assert _safe_mean([]) == 0.0

    def test_single_value(self):
        assert _safe_mean([5.0]) == 5.0


class TestSafeSumInt:
    def test_all_values(self):
        assert _safe_sum_int([1, 2, 3]) == 6

    def test_with_none(self):
        assert _safe_sum_int([1, None, 3]) == 4

    def test_all_none(self):
        assert _safe_sum_int([None, None]) == 0

    def test_empty_list(self):
        assert _safe_sum_int([]) == 0


# ============================================================
# 流程1聚合测试
# ============================================================


class TestAggregateFlow1Records:
    def _make_record(self, enid="EN1", exid="EX1", vehicle_type="1",
                     is_affected=True, fee_yuan=10.0, control_fee_yuan=8.0,
                     construction_flow=5, same_period_2025_flow=3):
        return AffectedOdPathRecord(
            od_section_path_id=1,
            enid=enid, exid=exid,
            numpath="1", fixed_intervalpath="S1",
            is_affected=is_affected,
            vehicle_type=vehicle_type,
            fee_yuan=fee_yuan,
            control_fee_yuan=control_fee_yuan,
            construction_flow=construction_flow,
            same_period_2025_flow=same_period_2025_flow,
        )

    def test_single_affected_record(self):
        """单条受影响记录：均值=自身值，求和=自身值"""
        recs = [self._make_record(fee_yuan=10.0, control_fee_yuan=8.0,
                                  construction_flow=5, same_period_2025_flow=3)]
        result = _aggregate_flow1_records(recs)

        key = ("EN1", "EX1", "1")
        assert key in result
        assert result[key]["avg_con_fee"] == 10.0
        assert result[key]["avg_con_control_fee"] == 8.0
        assert result[key]["con_construction_flow"] == 5
        assert result[key]["sp2025_con_flow"] == 3
        # 非受影响组应无数据
        assert result[key]["avg_other_fee"] == 0.0
        assert result[key]["sp2025_other_flow"] == 0

    def test_mixed_affected_and_other(self):
        """同一 (enid, exid, vtype) 下有受影响和非受影响记录"""
        recs = [
            self._make_record(is_affected=True, fee_yuan=20.0, control_fee_yuan=16.0,
                              construction_flow=4, same_period_2025_flow=2),
            self._make_record(is_affected=True, fee_yuan=30.0, control_fee_yuan=24.0,
                              construction_flow=6, same_period_2025_flow=4),
            self._make_record(is_affected=False, fee_yuan=15.0, control_fee_yuan=12.0,
                              construction_flow=10, same_period_2025_flow=8),
        ]
        result = _aggregate_flow1_records(recs)

        key = ("EN1", "EX1", "1")
        assert abs(result[key]["avg_con_fee"] - 25.0) < 1e-9
        assert abs(result[key]["avg_con_control_fee"] - 20.0) < 1e-9
        assert result[key]["con_construction_flow"] == 10
        assert result[key]["sp2025_con_flow"] == 6
        assert abs(result[key]["avg_other_fee"] - 15.0) < 1e-9
        assert result[key]["other_construction_flow"] == 10
        assert result[key]["sp2025_other_flow"] == 8

    def test_fee_multiplication(self):
        """均值 × 流量 赋值正确"""
        recs = [
            self._make_record(is_affected=True, fee_yuan=10.0, control_fee_yuan=8.0,
                              construction_flow=5, same_period_2025_flow=3),
        ]
        result = _aggregate_flow1_records(recs)

        key = ("EN1", "EX1", "1")
        # avg_con_fee=10.0, sp2025_con_flow=3
        assert abs(result[key]["sp2025_con_fee"] - 30.0) < 1e-9
        # avg_con_fee=10.0, con_construction_flow=5
        assert abs(result[key]["con_construction_fee"] - 50.0) < 1e-9
        # avg_con_control_fee=8.0, sp2025_con_flow=3
        assert abs(result[key]["sp2025_con_control_fee"] - 24.0) < 1e-9
        assert abs(result[key]["con_construction_control_fee"] - 40.0) < 1e-9

    def test_none_fee_values(self):
        """fee_yuan/control_fee_yuan 为 None 时均值跳过"""
        recs = [
            self._make_record(is_affected=True, fee_yuan=None, control_fee_yuan=None),
            self._make_record(is_affected=True, fee_yuan=20.0, control_fee_yuan=16.0),
        ]
        result = _aggregate_flow1_records(recs)

        key = ("EN1", "EX1", "1")
        assert result[key]["avg_con_fee"] == 20.0
        assert result[key]["avg_con_control_fee"] == 16.0

    def test_all_none_fee_values(self):
        """全部 fee_yuan 为 None 时均值为 0.0"""
        recs = [
            self._make_record(is_affected=True, fee_yuan=None, control_fee_yuan=None),
            self._make_record(is_affected=True, fee_yuan=None, control_fee_yuan=None),
        ]
        result = _aggregate_flow1_records(recs)

        key = ("EN1", "EX1", "1")
        assert result[key]["avg_con_fee"] == 0.0
        assert result[key]["avg_con_control_fee"] == 0.0

    def test_different_vehicle_types_separate(self):
        """不同 vehicle_type 独立聚合"""
        recs = [
            self._make_record(vehicle_type="1", is_affected=True, fee_yuan=10.0),
            self._make_record(vehicle_type="2", is_affected=True, fee_yuan=20.0),
        ]
        result = _aggregate_flow1_records(recs)

        assert result[("EN1", "EX1", "1")]["avg_con_fee"] == 10.0
        assert result[("EN1", "EX1", "2")]["avg_con_fee"] == 20.0


# ============================================================
# 流程2查找表测试
# ============================================================


class TestBuildMidTripLookup:
    def test_builds_lookup(self):
        rec = MidTripExitFlowStatRecord(
            od_enid="EN1", od_exid="EX1", vehicle_type="1",
            construction_flow=10, same_period_2025_flow=5,
            loss_fee_yuan=100.0, control_loss_fee_yuan=80.0,
        )
        lookup = _build_mid_trip_lookup([rec])
        key = ("EN1", "EX1", "1")
        assert key in lookup
        assert lookup[key]["mid_construction_flow"] == 10
        assert lookup[key]["mid_loss_fee_yuan"] == 100.0

    def test_empty_list(self):
        lookup = _build_mid_trip_lookup([])
        assert len(lookup) == 0


# ============================================================
# 流程3查找表测试
# ============================================================


class TestAggregateAndBuildDetourLookup:
    def test_aggregates_same_od_vtype(self):
        """同一 (od_enid, od_exid, vtype) 的多条记录聚合加总"""
        recs = [
            DetourFlowStatRecord(
                od_enid="EN1", od_exid="EX1",
                record_enid="R1", record_exid="EX1",
                record_type="same_dest_diff_origin", vehicle_type="1",
                construction_flow=3.0, same_period_2025_flow=2.0,
                loss_fee_yuan=30.0, control_loss_fee_yuan=24.0,
            ),
            DetourFlowStatRecord(
                od_enid="EN1", od_exid="EX1",
                record_enid="R2", record_exid="EX1",
                record_type="same_dest_diff_origin", vehicle_type="1",
                construction_flow=2.0, same_period_2025_flow=1.0,
                loss_fee_yuan=20.0, control_loss_fee_yuan=16.0,
            ),
        ]
        lookup = _aggregate_and_build_detour_lookup(recs)
        key = ("EN1", "EX1", "1")
        assert abs(lookup[key]["detour_construction_flow"] - 5.0) < 1e-9
        assert abs(lookup[key]["detour_same_period_2025_flow"] - 3.0) < 1e-9
        assert abs(lookup[key]["detour_loss_fee_yuan"] - 50.0) < 1e-9

    def test_different_ods_separate(self):
        """不同 OD 对不聚合"""
        recs = [
            DetourFlowStatRecord(
                od_enid="EN1", od_exid="EX1",
                record_enid="R1", record_exid="EX1",
                record_type="same_dest_diff_origin", vehicle_type="1",
                construction_flow=3.0,
            ),
            DetourFlowStatRecord(
                od_enid="EN2", od_exid="EX1",
                record_enid="R2", record_exid="EX1",
                record_type="same_dest_diff_origin", vehicle_type="1",
                construction_flow=2.0,
            ),
        ]
        lookup = _aggregate_and_build_detour_lookup(recs)
        assert lookup[("EN1", "EX1", "1")]["detour_construction_flow"] == 3.0
        assert lookup[("EN2", "EX1", "1")]["detour_construction_flow"] == 2.0

    def test_empty_list(self):
        lookup = _aggregate_and_build_detour_lookup([])
        assert len(lookup) == 0


# ============================================================
# ImpactSummaryService 集成测试
# ============================================================


class TestImpactSummaryService:
    def _make_flow1_record(self, enid="EN1", exid="EX1", vehicle_type="1",
                           is_affected=True, fee_yuan=10.0, control_fee_yuan=8.0,
                           construction_flow=5, same_period_2025_flow=3):
        return AffectedOdPathRecord(
            od_section_path_id=1,
            enid=enid, exid=exid,
            numpath="1", fixed_intervalpath="S1",
            is_affected=is_affected,
            vehicle_type=vehicle_type,
            fee_yuan=fee_yuan,
            control_fee_yuan=control_fee_yuan,
            construction_flow=construction_flow,
            same_period_2025_flow=same_period_2025_flow,
        )

    def test_full_integration(self):
        """完整流程1+2+3数据合并"""
        flow1 = [
            self._make_flow1_record(
                enid="EN1", exid="EX1", vehicle_type="1",
                is_affected=True, fee_yuan=10.0, control_fee_yuan=8.0,
                construction_flow=5, same_period_2025_flow=3,
            ),
            self._make_flow1_record(
                enid="EN1", exid="EX1", vehicle_type="1",
                is_affected=False, fee_yuan=5.0, control_fee_yuan=4.0,
                construction_flow=10, same_period_2025_flow=8,
            ),
        ]

        mid = [
            MidTripExitFlowStatRecord(
                od_enid="EN1", od_exid="EX1", vehicle_type="1",
                construction_flow=2, same_period_2025_flow=1,
                loss_fee_yuan=20.0, control_loss_fee_yuan=16.0,
            ),
        ]

        detour = [
            DetourFlowStatRecord(
                od_enid="EN1", od_exid="EX1",
                record_enid="R1", record_exid="EX1",
                record_type="same_dest_diff_origin", vehicle_type="1",
                construction_flow=3.0, same_period_2025_flow=2.0,
                loss_fee_yuan=30.0, control_loss_fee_yuan=24.0,
            ),
        ]

        service = ImpactSummaryService()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            output_path = f.name

        try:
            records = service.run(flow1, mid, detour, output_path=output_path)

            assert len(records) == 1
            rec = records[0]
            assert rec.enid == "EN1"
            assert rec.exid == "EX1"
            assert rec.vehicle_type == "1"
            # 流程1聚合
            assert rec.avg_con_fee == 10.0
            assert rec.avg_con_control_fee == 8.0
            assert rec.sp2025_con_flow == 3
            assert rec.con_construction_flow == 5
            # 流程1估算
            assert abs(rec.sp2025_con_fee - 30.0) < 1e-9
            assert abs(rec.con_construction_fee - 50.0) < 1e-9
            # 流程2匹配
            assert rec.mid_construction_flow == 2
            assert rec.mid_loss_fee_yuan == 20.0
            # 流程3匹配
            assert abs(rec.detour_construction_flow - 3.0) < 1e-9
            assert abs(rec.detour_loss_fee_yuan - 30.0) < 1e-9

            # 验证 CSV 输出
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["enid"] == "EN1"
                assert abs(float(rows[0]["avg_con_fee"]) - 10.0) < 1e-9
        finally:
            os.unlink(output_path)

    def test_no_mid_match_defaults_to_zero(self):
        """流程2无匹配时字段赋0"""
        flow1 = [self._make_flow1_record(enid="EN1", exid="EX1")]

        service = ImpactSummaryService()
        records = service.run(flow1, [], [])

        rec = records[0]
        assert rec.mid_construction_flow == 0
        assert rec.mid_same_period_2025_flow == 0
        assert rec.mid_loss_fee_yuan is None

    def test_no_detour_match_defaults_to_zero(self):
        """流程3无匹配时字段赋0"""
        flow1 = [self._make_flow1_record(enid="EN1", exid="EX1")]

        service = ImpactSummaryService()
        records = service.run(flow1, [], [])

        rec = records[0]
        assert rec.detour_construction_flow == 0.0
        assert rec.detour_same_period_2025_flow == 0.0
        assert rec.detour_loss_fee_yuan is None

    def test_empty_flow1_returns_empty(self):
        """流程1无数据时返回空列表"""
        service = ImpactSummaryService()
        records = service.run([], [], [])
        assert records == []


class TestImpactSummarySchema:
    def test_csv_columns_match_schema(self):
        """CSV列名与 ImpactSummaryRecord 字段一致"""
        schema_fields = list(ImpactSummaryRecord.model_fields.keys())
        assert IMPACT_SUMMARY_CSV_COLUMNS == schema_fields
