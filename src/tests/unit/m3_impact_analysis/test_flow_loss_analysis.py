"""
flow_loss_analysis 流失分析服务单元测试
覆盖: 车型归一化、分类、TOP15选取、OD_name映射
"""

import csv
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest

from src.modules.m3_impact_analysis.flow_loss_analysis import (
    normalize_vehicle_type,
    classify_vehicle,
    FlowLossAnalysisService,
)
from src.modules.m3_impact_analysis.analysis_schema import (
    ImpactSummaryRecord,
    SectionSummaryRecord,
)


class TestNormalizeVehicleType:
    def test_passenger_types(self):
        assert normalize_vehicle_type(1) == "客1"
        assert normalize_vehicle_type(2) == "客2"
        assert normalize_vehicle_type(3) == "客3"
        assert normalize_vehicle_type(4) == "客4"

    def test_truck_types_11_16(self):
        assert normalize_vehicle_type(11) == "货1"
        assert normalize_vehicle_type(16) == "货6"

    def test_special_merge_21_to_11(self):
        """21-26 合并到 11-16"""
        assert normalize_vehicle_type(21) == "货1"
        assert normalize_vehicle_type(22) == "货2"
        assert normalize_vehicle_type(26) == "货6"

    def test_unknown_type(self):
        assert normalize_vehicle_type(99) == "99"


class TestClassifyVehicle:
    def test_passenger(self):
        assert classify_vehicle("客1") == "客车"
        assert classify_vehicle("客4") == "客车"

    def test_truck(self):
        assert classify_vehicle("货1") == "货车"
        assert classify_vehicle("货6") == "货车"

    def test_special(self):
        assert classify_vehicle("未知") == "专项"


class TestFlowLossAnalysisService:
    def _make_summary_record(self, section_od: str, lost_flow: int = 100, **overrides) -> ImpactSummaryRecord:
        defaults = dict(
            enid="E1", exid="X1", vehicle_type="1", section_od=section_od,
            con_fee=100.0, con_control_fee=80.0,
            con_flow=10, con_sp2025_flow=200,
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
            original_path_fee=0.08,
            ref_total_flow=200, unaffected_flow=10,
            affected_flow=190, detour_flow_final=20,
            retained_nearby=10, retained_midtrip=10,
            lost_flow=lost_flow,
            original_control_fee=1.6, unaffected_control_fee=0.08,
            detour_control_fee_final=0.3,
            retained_nearby_control_fee=0.04,
            retained_midtrip_control_fee=0.04,
            lost_control_fee=lost_flow * 80.0 / 10000,
        )
        defaults.update(overrides)
        return ImpactSummaryRecord(**defaults)

    def _make_section_record(self, section_od: str, lost_flow: int = 100) -> SectionSummaryRecord:
        return SectionSummaryRecord(
            section_od=section_od,
            ref_total_flow=200,
            unaffected_flow=10,
            affected_flow=190,
            detour_flow_final=20,
            retained_nearby=10,
            retained_midtrip=10,
            lost_flow=lost_flow,
            original_control_fee=1.6,
            unaffected_control_fee=0.08,
            detour_control_fee_final=0.3,
            retained_nearby_control_fee=0.04,
            retained_midtrip_control_fee=0.04,
            lost_control_fee=0.8,
        )

    def test_top15_selection(self):
        """TOP15 按流失流量降序选取"""
        service = FlowLossAnalysisService()
        section_records = [
            self._make_section_record(f"OD{i:03d}", lost_flow=i * 10)
            for i in range(1, 20)
        ]
        summary_records = [
            self._make_summary_record(f"OD{i:03d}", lost_flow=i * 10)
            for i in range(1, 20)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.run(
                summary_records=summary_records,
                section_records=section_records,
                output_dir=tmpdir,
            )
            # TOP15 应取流失流量最高的15个
            assert result["top15_count"] == 15
            assert len(result["top15_od_pairs"]) > 0
            # 映射表应存在
            assert os.path.exists(os.path.join(tmpdir, "TOP1-15_OD编号映射表.csv"))
            # 综合评估表应存在
            assert os.path.exists(os.path.join(tmpdir, "TOP1-15_流失综合评估表.csv"))

    def test_empty_records(self):
        """空记录不报错"""
        service = FlowLossAnalysisService()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.run(
                summary_records=[],
                section_records=[],
                output_dir=tmpdir,
            )
            assert result["top15_count"] == 0

    def test_od_name_mapping_with_matcher(self):
        """传入 matcher + dataDate 后，映射表包含 OD_name 列"""
        mock_matcher = MagicMock()
        mock_matcher.resolve_section_od_name.side_effect = lambda od, _: f"名称_{od}"

        service = FlowLossAnalysisService(section_od_matcher=mock_matcher)
        section_records = [
            self._make_section_record("OD001", lost_flow=200),
            self._make_section_record("OD002", lost_flow=100),
        ]
        summary_records = [
            self._make_summary_record("OD001", lost_flow=200),
            self._make_summary_record("OD002", lost_flow=100),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.run(
                summary_records=summary_records,
                section_records=section_records,
                output_dir=tmpdir,
                dataDate="20260415",
            )
            # od_name_mapping 应包含解析结果
            assert result["od_name_mapping"]["OD001"] == "名称_OD001"
            assert result["od_name_mapping"]["OD002"] == "名称_OD002"

            # CSV 包含 OD_name 列
            mapping_path = os.path.join(tmpdir, "TOP1-15_OD编号映射表.csv")
            assert os.path.exists(mapping_path)
            with open(mapping_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert "OD_name" in reader.fieldnames
            assert rows[0]["OD_name"] == "名称_OD001"

    def test_no_matcher_no_od_name_column(self):
        """不传 matcher 时映射表无 OD_name 列"""
        service = FlowLossAnalysisService()
        section_records = [
            self._make_section_record("OD001", lost_flow=200),
        ]
        summary_records = [
            self._make_summary_record("OD001", lost_flow=200),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = service.run(
                summary_records=summary_records,
                section_records=section_records,
                output_dir=tmpdir,
            )
            assert result["od_name_mapping"] == {}

            mapping_path = os.path.join(tmpdir, "TOP1-15_OD编号映射表.csv")
            with open(mapping_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert "OD_name" not in reader.fieldnames
