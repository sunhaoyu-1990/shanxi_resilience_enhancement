"""
impact_summary_service 动态测算综合汇总服务单元测试
覆盖: 步骤1-5 全部逻辑
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
    OdsSummaryRecord,
    SectionSummaryRecord,
)
from src.modules.m3_impact_analysis.impact_summary_service import (
    ImpactSummaryService,
    _safe_sum,
    _safe_mean,
    _safe_div,
    _step1_aggregate_flow1,
    _step2_aggregate_flow2,
    _step2_aggregate_flow3,
    _step4_derive_calculations,
    _compute_retained_nearby,
    _compute_retained_midtrip,
    _step5_aggregate_summaries,
    IMPACT_SUMMARY_CSV_COLUMNS,
    ODS_SUMMARY_CSV_COLUMNS,
    SECTION_SUMMARY_CSV_COLUMNS,
    _CSV_COLUMN_ALIASES,
)


# ============================================================
# 工具函数测试
# ============================================================


class TestSafeSum:
    def test_all_values(self):
        assert _safe_sum([1.0, 2.0, 3.0]) == 6.0

    def test_with_none(self):
        assert _safe_sum([1.0, None, 3.0]) == 4.0

    def test_all_none(self):
        assert _safe_sum([None, None]) == 0.0

    def test_empty_list(self):
        assert _safe_sum([]) == 0


class TestSafeDiv:
    def test_normal(self):
        assert _safe_div(10.0, 5.0) == 2.0

    def test_zero_denominator(self):
        assert _safe_div(10.0, 0.0) == 0.0

    def test_zero_numerator(self):
        assert _safe_div(0.0, 5.0) == 0.0


class TestSafeMean:
    def test_all_values(self):
        assert _safe_mean([10.0, 20.0, 30.0]) == 20.0

    def test_with_none(self):
        assert _safe_mean([10.0, None, 30.0]) == 20.0

    def test_all_none(self):
        assert _safe_mean([None, None]) == 0.0

    def test_empty_list(self):
        assert _safe_mean([]) == 0.0

    def test_single_value(self):
        assert _safe_mean([42.0]) == 42.0


# ============================================================
# 步骤1: Flow1 聚合 + 透视
# ============================================================


class TestStep1AggregateFlow1:
    def _make_record(self, **overrides) -> AffectedOdPathRecord:
        defaults = dict(
            od_section_path_id=1, enid="E1", exid="X1",
            numpath="1|2", fixed_intervalpath="S1|S2",
            affected_section_ids="S1", is_affected=True,
            map_version="202603", vehicle_type="1",
            construction_flow=10, same_period_2025_flow=20,
            fee_yuan=100.0, total_length_meters=5000,
            control_fee_yuan=80.0, control_length_meters=4000,
            section_od="1|2",
        )
        defaults.update(overrides)
        return AffectedOdPathRecord(**defaults)

    def test_basic_aggregation(self):
        """is_affected=True 和 False 分别求和"""
        records = [
            self._make_record(is_affected=True, construction_flow=10, fee_yuan=100.0),
            self._make_record(is_affected=True, construction_flow=5, fee_yuan=50.0),
            self._make_record(is_affected=False, construction_flow=20, fee_yuan=200.0),
        ]
        result = _step1_aggregate_flow1(records)
        assert len(result) == 1
        key = ("E1", "X1", "1", "1|2")
        assert key in result
        agg = result[key]
        assert agg["con_flow"] == 15  # 10 + 5
        assert agg["con_fee"] == 75.0  # (100 + 50) / 2 = 75
        assert agg["other_flow"] == 20
        assert agg["other_fee"] == 200.0

    def test_different_vehicle_types(self):
        """不同车型分开聚合"""
        records = [
            self._make_record(vehicle_type="1", construction_flow=10),
            self._make_record(vehicle_type="11", construction_flow=20),
        ]
        result = _step1_aggregate_flow1(records)
        assert len(result) == 2

    def test_different_section_od(self):
        """不同 section_od 分开聚合"""
        records = [
            self._make_record(section_od="1|2"),
            self._make_record(section_od="3|4"),
        ]
        result = _step1_aggregate_flow1(records)
        assert len(result) == 2

    def test_filter_zero_sp2025_flow(self):
        """施工影响路径2025年同期流量<=0 的行被过滤"""
        records = [
            self._make_record(
                is_affected=True, same_period_2025_flow=0,
                construction_flow=10,
            ),
        ]
        result = _step1_aggregate_flow1(records)
        assert len(result) == 0

    def test_filter_negative_sp2025_flow(self):
        """负的同期流量也被过滤"""
        records = [
            self._make_record(
                is_affected=True, same_period_2025_flow=-5,
                construction_flow=10,
            ),
        ]
        result = _step1_aggregate_flow1(records)
        assert len(result) == 0

    def test_positive_sp2025_flow_kept(self):
        """正的同期流量保留"""
        records = [
            self._make_record(
                is_affected=True, same_period_2025_flow=5,
                construction_flow=10,
            ),
        ]
        result = _step1_aggregate_flow1(records)
        assert len(result) == 1

    def test_none_values_handled(self):
        """None 值在平均中被忽略，全 None 返回 0"""
        records = [
            self._make_record(is_affected=True, fee_yuan=None),
        ]
        result = _step1_aggregate_flow1(records)
        key = ("E1", "X1", "1", "1|2")
        assert result[key]["con_fee"] == 0.0


# ============================================================
# 步骤2: Flow2/Flow3 聚合
# ============================================================


class TestStep2AggregateFlow2:
    def _make_mid_record(self, **overrides) -> MidTripExitFlowStatRecord:
        defaults = dict(
            od_enid="E1", od_exid="X1", vehicle_type="1",
            construction_flow=10, same_period_2025_flow=5,
            loss_fee_yuan=100.0, control_loss_fee_yuan=80.0,
            sp2025_loss_fee_yuan=50.0, sp2025_control_loss_fee_yuan=40.0,
        )
        defaults.update(overrides)
        return MidTripExitFlowStatRecord(**defaults)

    def test_basic_aggregation(self):
        records = [
            self._make_mid_record(construction_flow=10, loss_fee_yuan=100.0),
            self._make_mid_record(construction_flow=5, loss_fee_yuan=50.0),
        ]
        result = _step2_aggregate_flow2(records)
        key = ("E1", "X1", "1")
        assert key in result
        assert result[key]["mid_flow"] == 15.0
        assert result[key]["mid_loss_fee"] == 150.0

    def test_unit_fee_calculation(self):
        """单次通行损失费额 = 损失通行费 / 流量"""
        records = [self._make_mid_record(construction_flow=10, loss_fee_yuan=100.0, control_loss_fee_yuan=80.0)]
        result = _step2_aggregate_flow2(records)
        key = ("E1", "X1", "1")
        assert result[key]["mid_unit_loss_fee"] == 10.0  # 100/10
        assert result[key]["mid_unit_control_loss_fee"] == 8.0  # 80/10

    def test_zero_flow_unit_fee(self):
        """流量为0时，单次费率为0（避免除零）"""
        records = [self._make_mid_record(construction_flow=0, loss_fee_yuan=0.0, control_loss_fee_yuan=0.0)]
        result = _step2_aggregate_flow2(records)
        key = ("E1", "X1", "1")
        assert result[key]["mid_unit_loss_fee"] == 0.0
        assert result[key]["mid_unit_control_loss_fee"] == 0.0


class TestStep2AggregateFlow3:
    def _make_detour_record(self, **overrides) -> DetourFlowStatRecord:
        defaults = dict(
            od_enid="E1", od_exid="X1", record_enid="R1", record_exid="R2",
            record_type="same_dest_diff_origin", vehicle_type="1",
            construction_flow=10.0, same_period_2025_flow=5.0,
            loss_fee_yuan=100.0, control_loss_fee_yuan=80.0,
            sp2025_loss_fee_yuan=50.0, sp2025_control_loss_fee_yuan=40.0,
        )
        defaults.update(overrides)
        return DetourFlowStatRecord(**defaults)

    def test_basic_aggregation(self):
        """多条记录聚合同一个 (od_enid, od_exid, vehicle_type)"""
        records = [
            self._make_detour_record(construction_flow=10.0, loss_fee_yuan=100.0),
            self._make_detour_record(construction_flow=5.0, loss_fee_yuan=50.0),
        ]
        result = _step2_aggregate_flow3(records)
        key = ("E1", "X1", "1")
        assert result[key]["detour_flow"] == 15.0
        assert result[key]["detour_loss_fee"] == 150.0

    def test_unit_fee_calculation(self):
        records = [self._make_detour_record(construction_flow=10.0, control_loss_fee_yuan=80.0)]
        result = _step2_aggregate_flow3(records)
        key = ("E1", "X1", "1")
        assert result[key]["detour_unit_control_loss_fee"] == 8.0


# ============================================================
# 步骤4: 派生计算
# ============================================================


class TestComputeRetainedNearby:
    def test_nearby_increment_le_zero(self):
        """附近上下车增量<=0 → 0"""
        assert _compute_retained_nearby(100, 10, 50, 50, 5, 10) == 0

    def test_combined_increment_lt_zero(self):
        """中途+附近增量<0 → 0"""
        # mid_increment = 10-50 = -40, nearby_increment = 20-10 = 10
        # combined = -40+10 = -30 < 0
        assert _compute_retained_nearby(100, 10, 10, 50, 20, 10) == 0

    def test_combined_exceeds_remaining_nearby_capped(self):
        """合并增量>剩余, 但附近增量>剩余 → 取剩余"""
        # affected=100, detour=10, remaining=90
        # mid_increment=30, nearby_increment=80
        # combined=110 > 90, nearby=80 > 90? No. nearby=80 < 90
        # So return min(80, 90) = 80
        result = _compute_retained_nearby(100, 10, 40, 10, 80, 0)
        assert result == 80

    def test_combined_exceeds_remaining_nearby_exceeds_remaining(self):
        """附近增量>剩余 → 取剩余"""
        result = _compute_retained_nearby(100, 10, 10, 5, 95, 0)
        assert result == 90  # min(95, 90)

    def test_normal_case(self):
        """正常: combined <= remaining → 返回附近增量"""
        result = _compute_retained_nearby(100, 10, 30, 20, 50, 30)
        # mid_increment=10, nearby_increment=20, combined=30
        # remaining=90, combined=30 < 90 → return 20
        assert result == 20


class TestComputeRetainedMidtrip:
    def test_mid_increment_le_zero(self):
        """中途上下站增量<=0 → 0"""
        assert _compute_retained_midtrip(5, 10, 100, 10, 0) == 0

    def test_remaining_le_zero(self):
        """受影响-绕行-保留(附近)<=0 → 0"""
        assert _compute_retained_midtrip(20, 10, 30, 30, 0) == 0

    def test_mid_increment_le_remaining(self):
        """中途增量<=剩余 → 返回中途增量"""
        result = _compute_retained_midtrip(30, 20, 100, 10, 5)
        # mid_increment=10, remaining=100-10-5=85
        # 10 <= 85 → return 10
        assert result == 10

    def test_mid_increment_gt_remaining(self):
        """中途增量>剩余 → 返回剩余"""
        result = _compute_retained_midtrip(100, 10, 30, 10, 5)
        # mid_increment=90, remaining=30-10-5=15
        # 90 > 15 → return 15
        assert result == 15


class TestStep4DeriveCalculations:
    def _make_row(self, **overrides) -> dict:
        defaults = dict(
            con_fee=100.0, con_control_fee=80.0,
            con_flow=10, con_sp2025_flow=100,
            con_length=5000, con_control_length=4000,
            other_fee=200.0, other_control_fee=150.0,
            other_flow=50, other_sp2025_flow=30,
            other_length=8000, other_control_length=6000,
            mid_flow=20.0, mid_sp2025_flow=15.0,
            mid_loss_fee=100.0, mid_control_loss_fee=80.0,
            mid_unit_loss_fee=5.0, mid_unit_control_loss_fee=4.0,
            detour_flow=30.0, detour_sp2025_flow=20.0,
            detour_loss_fee=200.0, detour_control_loss_fee=150.0,
            detour_unit_loss_fee=6.67, detour_unit_control_loss_fee=5.0,
        )
        defaults.update(overrides)
        return defaults

    def test_basic_derivation(self):
        """基本派生计算"""
        row = _step4_derive_calculations(self._make_row())

        # 参考总流量 = con_sp2025_flow = 100
        assert row["ref_total_flow"] == 100
        # 未收影响流量 = con_flow = 10
        assert row["unaffected_flow"] == 10
        # 受影响流量 = max(0, 100-10) = 90
        assert row["affected_flow"] == 90
        # 绕行流量 = min(max(0, 50-30), 90) = min(20, 90) = 20
        assert row["detour_flow_final"] == 20
        # 流失等式
        assert row["lost_flow"] == row["affected_flow"] - row["detour_flow_final"] - row["retained_nearby"] - row["retained_midtrip"]

    def test_flow_equation_holds(self):
        """流量等式: 流失 = 受影响 - 绕行 - 保留(附近) - 保留(中途)"""
        row = _step4_derive_calculations(self._make_row())
        expected_lost = row["affected_flow"] - row["detour_flow_final"] - row["retained_nearby"] - row["retained_midtrip"]
        assert row["lost_flow"] == expected_lost

    def test_zero_affected_flow(self):
        """受影响流量=0时，所有派生流量=0"""
        row = self._make_row(con_sp2025_flow=10, con_flow=10)
        row = _step4_derive_calculations(row)
        assert row["affected_flow"] == 0
        assert row["lost_flow"] == 0

    def test_fee_calculations(self):
        """费用计算正确（万元）"""
        row = _step4_derive_calculations(self._make_row())
        # 原交控通行费 = 参考总流量 × con_control_fee / 10000
        assert abs(row["original_control_fee"] - row["ref_total_flow"] * 80.0 / 10000) < 0.001
        # 流失交控通行费 = 流失流量 × con_control_fee / 10000
        assert abs(row["lost_control_fee"] - row["lost_flow"] * 80.0 / 10000) < 0.001


# ============================================================
# 步骤5: 汇总
# ============================================================


class TestStep5AggregateSummaries:
    def _make_summary_record(self, **overrides) -> ImpactSummaryRecord:
        defaults = dict(
            enid="E1", exid="X1", vehicle_type="1", section_od="1|2",
            con_fee=100.0, con_control_fee=80.0,
            con_flow=10, con_sp2025_flow=100,
            con_length=5000, con_control_length=4000,
            other_fee=200.0, other_control_fee=150.0,
            other_flow=50, other_sp2025_flow=30,
            other_length=8000, other_control_length=6000,
            mid_flow=20.0, mid_sp2025_flow=15.0,
            mid_loss_fee=100.0, mid_control_loss_fee=80.0,
            mid_unit_loss_fee=5.0, mid_unit_control_loss_fee=4.0,
            detour_flow=30.0, detour_sp2025_flow=20.0,
            detour_loss_fee=200.0, detour_control_loss_fee=150.0,
            detour_unit_loss_fee=6.67, detour_unit_control_loss_fee=5.0,
        )
        # 添加派生字段
        row = dict(defaults)
        row.update(overrides)
        row = _step4_derive_calculations(row)
        return ImpactSummaryRecord(**row)

    def test_ods_summary(self):
        """OD汇总表按 (enid, exid) 求和"""
        rec1 = self._make_summary_record(vehicle_type="1", con_sp2025_flow=100)
        rec2 = self._make_summary_record(vehicle_type="11", con_sp2025_flow=200)
        ods, sections = _step5_aggregate_summaries([rec1, rec2])
        assert len(ods) == 1
        assert ods[0].ref_total_flow == 300

    def test_section_summary(self):
        """路段汇总表按 section_od 求和"""
        rec1 = self._make_summary_record(section_od="1|2", con_sp2025_flow=100)
        rec2 = self._make_summary_record(section_od="1|2", con_sp2025_flow=50, vehicle_type="11")
        ods, sections = _step5_aggregate_summaries([rec1, rec2])
        assert len(sections) == 1
        assert sections[0].ref_total_flow == 150

    def test_different_sections(self):
        """不同 section_od 分开汇总"""
        rec1 = self._make_summary_record(section_od="1|2")
        rec2 = self._make_summary_record(section_od="3|4", enid="E2", exid="X2")
        ods, sections = _step5_aggregate_summaries([rec1, rec2])
        assert len(sections) == 2


# ============================================================
# 集成测试: ImpactSummaryService.run()
# ============================================================


class TestImpactSummaryServiceRun:
    def _make_flow1_record(self, **overrides) -> AffectedOdPathRecord:
        defaults = dict(
            od_section_path_id=1, enid="E1", exid="X1",
            numpath="1|2", fixed_intervalpath="S1|S2",
            affected_section_ids="S1", is_affected=True,
            map_version="202603", vehicle_type="1",
            construction_flow=10, same_period_2025_flow=100,
            fee_yuan=100.0, total_length_meters=5000,
            control_fee_yuan=80.0, control_length_meters=4000,
            section_od="1|2",
        )
        defaults.update(overrides)
        return AffectedOdPathRecord(**defaults)

    def _make_mid_record(self, **overrides) -> MidTripExitFlowStatRecord:
        defaults = dict(
            od_enid="E1", od_exid="X1", vehicle_type="1",
            construction_flow=20, same_period_2025_flow=15,
            loss_fee_yuan=100.0, control_loss_fee_yuan=80.0,
            sp2025_loss_fee_yuan=50.0, sp2025_control_loss_fee_yuan=40.0,
        )
        defaults.update(overrides)
        return MidTripExitFlowStatRecord(**defaults)

    def _make_detour_record(self, **overrides) -> DetourFlowStatRecord:
        defaults = dict(
            od_enid="E1", od_exid="X1", record_enid="R1", record_exid="R2",
            record_type="same_dest_diff_origin", vehicle_type="1",
            construction_flow=30.0, same_period_2025_flow=20.0,
            loss_fee_yuan=200.0, control_loss_fee_yuan=150.0,
            sp2025_loss_fee_yuan=100.0, sp2025_control_loss_fee_yuan=80.0,
        )
        defaults.update(overrides)
        return DetourFlowStatRecord(**defaults)

    def test_full_pipeline(self):
        """完整流水线测试"""
        service = ImpactSummaryService()
        with tempfile.TemporaryDirectory() as tmpdir:
            records, ods, sections = service.run(
                raw_records=[
                    self._make_flow1_record(is_affected=True, construction_flow=10, same_period_2025_flow=100),
                    self._make_flow1_record(is_affected=False, construction_flow=50, same_period_2025_flow=30),
                ],
                mid_data=[self._make_mid_record()],
                detour_data=[self._make_detour_record()],
                output_path=os.path.join(tmpdir, "summary.csv"),
                ods_output_path=os.path.join(tmpdir, "ods.csv"),
                section_output_path=os.path.join(tmpdir, "section.csv"),
            )

            assert len(records) == 1
            assert len(ods) == 1
            assert len(sections) == 1

            # 验证 CSV 文件存在
            assert os.path.exists(os.path.join(tmpdir, "summary.csv"))
            assert os.path.exists(os.path.join(tmpdir, "ods.csv"))
            assert os.path.exists(os.path.join(tmpdir, "section.csv"))

            # 验证流量等式
            rec = records[0]
            expected_lost = rec.affected_flow - rec.detour_flow_final - rec.retained_nearby - rec.retained_midtrip
            assert rec.lost_flow == expected_lost

    def test_no_mid_detour_data(self):
        """没有流程2/3数据时，默认为0"""
        service = ImpactSummaryService()
        with tempfile.TemporaryDirectory() as tmpdir:
            records, ods, sections = service.run(
                raw_records=[
                    self._make_flow1_record(is_affected=True, construction_flow=10, same_period_2025_flow=100),
                ],
                mid_data=[],
                detour_data=[],
                output_path=os.path.join(tmpdir, "summary.csv"),
                ods_output_path=os.path.join(tmpdir, "ods.csv"),
                section_output_path=os.path.join(tmpdir, "section.csv"),
            )

            assert len(records) == 1
            rec = records[0]
            assert rec.mid_flow == 0.0
            assert rec.detour_flow == 0.0


# ============================================================
# CSV 列名一致性测试
# ============================================================


class TestCsvColumns:
    def test_summary_columns_match_record_fields(self):
        """CSV 列名数量与 ImpactSummaryRecord 字段一致"""
        schema_fields = list(ImpactSummaryRecord.model_fields.keys())
        assert len(IMPACT_SUMMARY_CSV_COLUMNS) == len(schema_fields)

    def test_ods_columns_match_record_fields(self):
        """OD汇总表列名与 OdsSummaryRecord 字段一致"""
        schema_fields = list(OdsSummaryRecord.model_fields.keys())
        assert len(ODS_SUMMARY_CSV_COLUMNS) == len(schema_fields)

    def test_section_columns_match_record_fields(self):
        """路段汇总表列名与 SectionSummaryRecord 字段一致"""
        schema_fields = list(SectionSummaryRecord.model_fields.keys())
        assert len(SECTION_SUMMARY_CSV_COLUMNS) == len(schema_fields)

    def test_chinese_aliases_coverage(self):
        """所有非标识字段都有中文别名"""
        id_fields = {"enid", "exid", "vehicle_type", "section_od"}
        for field_name in ImpactSummaryRecord.model_fields:
            if field_name not in id_fields:
                assert field_name in _CSV_COLUMN_ALIASES, f"Missing alias for: {field_name}"
