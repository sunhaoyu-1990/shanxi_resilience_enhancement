"""M7 数据挖掘模块单元测试"""

from src.modules.m7_data_mining.schema import (
    ODPair,
    ODFlowPair,
    LostVehicleParams,
    LostVehicleResult,
    DetourSectionParams,
    DetourSectionResult,
)
from src.modules.m7_data_mining.checks import (
    check_od_pair_format,
    check_date_range,
    check_numpath_format,
)


class TestODPair:
    """ODPair 模型测试"""

    def test_enid_format(self):
        """enid/exid 格式（长字符串）"""
        od = ODPair(origin="G000561001000110", destination="G007061001000120")
        assert not od.is_section_number_format

    def test_section_number_format(self):
        """section_number 格式（短字符串）"""
        od = ODPair(origin="2", destination="146")
        assert od.is_section_number_format

    def test_section_number_format_multi_digit(self):
        """section_number 格式（多位数字）"""
        od = ODPair(origin="378", destination="152")
        assert od.is_section_number_format

    def test_mixed_format(self):
        """混合格式（一长一短）视为非 section_number 格式"""
        od = ODPair(origin="G000561001000110", destination="146")
        assert not od.is_section_number_format

    def test_boundary_length_9(self):
        """长度恰好9视为 section_number 格式"""
        od = ODPair(origin="123456789", destination="987654321")
        assert od.is_section_number_format

    def test_boundary_length_10(self):
        """长度10视为 enid/exid 格式"""
        od = ODPair(origin="1234567890", destination="0987654321")
        assert not od.is_section_number_format


class TestODFlowPair:
    """ODFlowPair 模型测试"""

    def test_basic(self):
        pair = ODFlowPair(origin="2", destination="146", flow_x=100)
        assert pair.flow_x == 100
        assert pair.is_section_number_format

    def test_enid_format(self):
        pair = ODFlowPair(
            origin="G000561001000110",
            destination="G007061001000120",
            flow_x=50,
        )
        assert not pair.is_section_number_format


class TestLostVehicleParams:
    """LostVehicleParams 测试"""

    def test_defaults(self):
        params = LostVehicleParams(
            odList=[ODPair(origin="2", destination="146")],
            startDate="2026-03-01",
            endDate="2026-03-31",
        )
        assert params.dataDir == "/home/shy/gaosu_data"
        assert params.sectionVersion == "202401"
        assert params.topN == 0
        assert params.outputPath == "outputs/m7/lost_vehicles.csv"


class TestDetourSectionParams:
    """DetourSectionParams 测试"""

    def test_defaults(self):
        params = DetourSectionParams(
            odFlowList=[ODFlowPair(origin="2", destination="146", flow_x=100)],
        )
        assert params.baseTablePath == "research/analysis/基础表.csv"
        assert params.outputPath == "outputs/m7/detour_sections.csv"


class TestChecks:
    """校验函数测试"""

    def test_od_pair_format_valid(self):
        errors = check_od_pair_format("A", "B")
        assert errors == []

    def test_od_pair_format_empty(self):
        errors = check_od_pair_format("", "B")
        assert len(errors) > 0

    def test_date_range_valid(self):
        errors = check_date_range("2026-03-01", "2026-03-31")
        assert errors == []

    def test_date_range_invalid_format(self):
        errors = check_date_range("2026/03/01", "2026-03-31")
        assert len(errors) > 0

    def test_date_range_reversed(self):
        errors = check_date_range("2026-03-31", "2026-03-01")
        assert len(errors) > 0

    def test_numpath_valid(self):
        errors = check_numpath_format("2|4|358|46")
        assert errors == []

    def test_numpath_empty(self):
        errors = check_numpath_format("")
        assert len(errors) > 0

    def test_numpath_invalid(self):
        errors = check_numpath_format("2|abc|46")
        assert len(errors) > 0
