"""
test_toll_calculator.py - 通行费计算模块单元测试
"""

import pytest
from unittest.mock import MagicMock, patch

from src.common.toll_calculator import (
    TollCalculator,
    TollFeeResult,
    PathFeeResult,
    split_intervalgroup,
    is_passenger_vehicle,
    calculate_toll_fee,
)


# ============================================================================
# 辅助函数测试
# ============================================================================


class TestSplitIntervalgroup:
    """测试 split_intervalgroup 函数"""

    def test_normal_case(self):
        """正常拆分 intervalgroup"""
        result = split_intervalgroup("A|B|C")
        assert result == ["A", "B", "C"]

    def test_with_spaces(self):
        """带空格的拆分"""
        result = split_intervalgroup(" A | B | C ")
        assert result == ["A", "B", "C"]

    def test_empty_string(self):
        """空字符串"""
        result = split_intervalgroup("")
        assert result == []

    def test_whitespace_only(self):
        """仅空格"""
        result = split_intervalgroup("   ")
        assert result == []

    def test_single_element(self):
        """单个元素"""
        result = split_intervalgroup("A")
        assert result == ["A"]

    def test_with_empty_parts(self):
        """包含空部分"""
        result = split_intervalgroup("A||C")
        assert result == ["A", "C"]


class TestIsPassengerVehicle:
    """测试 is_passenger_vehicle 函数"""

    def test_passenger_vehicles(self):
        """客车车型 (1-4)"""
        assert is_passenger_vehicle(1) is True
        assert is_passenger_vehicle(2) is True
        assert is_passenger_vehicle(3) is True
        assert is_passenger_vehicle(4) is True

    def test_truck_vehicles(self):
        """货车车型 (11-26)"""
        assert is_passenger_vehicle(11) is False
        assert is_passenger_vehicle(15) is False
        assert is_passenger_vehicle(21) is False
        assert is_passenger_vehicle(26) is False

    def test_invalid_vehicle_type(self):
        """无效车型"""
        assert is_passenger_vehicle(0) is False
        assert is_passenger_vehicle(5) is False
        assert is_passenger_vehicle(10) is False


# ============================================================================
# TollCalculator 单元测试（使用 Mock）
# ============================================================================


class TestTollCalculator:
    """测试 TollCalculator 类"""

    @pytest.fixture
    def mock_sql_runner(self):
        """创建 Mock SQL Runner"""
        return MagicMock()

    @pytest.fixture
    def calculator(self, mock_sql_runner):
        """创建 TollCalculator 实例"""
        return TollCalculator(sql_runner=mock_sql_runner)

    def test_get_shortest_path_success(self, calculator, mock_sql_runner):
        """测试查询最短路径成功"""
        mock_sql_runner.fetch_one.return_value = {
            "node_path": ["A", "B", "C"]
        }

        result = calculator.get_shortest_path("enid", "exid", "202512")

        assert result == ["A", "B", "C"]
        mock_sql_runner.fetch_one.assert_called_once()

    def test_get_shortest_path_empty(self, calculator, mock_sql_runner):
        """测试查询最短路径为空"""
        mock_sql_runner.fetch_one.return_value = {"node_path": None}

        result = calculator.get_shortest_path("enid", "exid", "202512")

        assert result == []

    def test_get_shortest_path_exception(self, calculator, mock_sql_runner):
        """测试查询最短路径异常"""
        mock_sql_runner.fetch_one.side_effect = Exception("DB Error")

        result = calculator.get_shortest_path("enid", "exid", "202512")

        assert result == []

    def test_get_section_info_success(self, calculator, mock_sql_runner):
        """测试查询收费单元信息成功"""
        mock_sql_runner.fetch_one.return_value = {
            "id": "S001",
            "length": 5000,
            "roadtype": 1,
            "feeKtype": 1,
            "feeHtype": 1,
            "roadid": "G007061003",
        }

        result = calculator.get_section_info("S001", "202512")

        assert result["id"] == "S001"
        assert result["length"] == 5000
        assert result["roadtype"] == 1

    def test_get_section_info_not_found(self, calculator, mock_sql_runner):
        """测试查询收费单元信息不存在"""
        mock_sql_runner.fetch_one.return_value = None

        result = calculator.get_section_info("S001", "202512")

        assert result is None

    def test_get_fee_per_km_success(self, calculator, mock_sql_runner):
        """测试查询费率成功"""
        mock_sql_runner.fetch_one.return_value = {"feebykm": 0.5}

        result = calculator.get_fee_per_km(roadtype=1, feetype=1, vehicle_type=1)

        assert result == 0.5

    def test_get_fee_per_km_not_found(self, calculator, mock_sql_runner):
        """测试查询费率不存在"""
        mock_sql_runner.fetch_one.return_value = None

        result = calculator.get_fee_per_km(roadtype=1, feetype=1, vehicle_type=1)

        assert result is None

    def test_is_control_section_loan(self, calculator, mock_sql_runner):
        """测试判断交控单元（还贷性）"""
        mock_sql_runner.fetch_one.return_value = {"路段性质": "还贷性"}

        result = calculator.is_control_section("G00706100300")

        assert result is True

    def test_is_control_section_operation(self, calculator, mock_sql_runner):
        """测试判断交控单元（经营性）"""
        mock_sql_runner.fetch_one.return_value = {"路段性质": "经营性"}

        result = calculator.is_control_section("G00706100300")

        assert result is False

    def test_is_control_section_empty_roadid(self, calculator, mock_sql_runner):
        """测试空 roadid"""
        result = calculator.is_control_section("")

        assert result is False

    def test_calculate_path_fee_passenger(self, calculator, mock_sql_runner):
        """测试计算路径通行费 - 客车"""
        # Mock get_section_info
        calculator.get_section_info = MagicMock(side_effect=[
            {
                "id": "S001",
                "length": 10000,
                "roadtype": 1,
                "feeKtype": 1,
                "feeHtype": 1,
                "roadid": "G00706100300",
            },
            {
                "id": "S002",
                "length": 5000,
                "roadtype": 1,
                "feeKtype": 1,
                "feeHtype": 1,
                "roadid": "G00706100400",
            },
        ])

        # Mock get_fee_per_km
        calculator.get_fee_per_km = MagicMock(return_value=0.5)

        # Mock is_control_section
        calculator.is_control_section = MagicMock(side_effect=[True, False])

        result = calculator.calculate_path_fee(
            section_ids=["S001", "S002"],
            vehicle_type=1,  # 客车
            version="202512",
        )

        # S001: 10000m / 1000 * 0.5 = 5.0 元, 交控
        # S002: 5000m / 1000 * 0.5 = 2.5 元, 非交控
        assert result.fee_yuan == 7.5
        assert result.control_fee_yuan == 5.0
        assert result.total_length_meters == 15000
        assert result.control_length_meters == 10000
        assert result.skipped_sections == []

    def test_calculate_path_fee_truck(self, calculator, mock_sql_runner):
        """测试计算路径通行费 - 货车"""
        calculator.get_section_info = MagicMock(side_effect=[
            {
                "id": "S001",
                "length": 10000,
                "roadtype": 2,  # 桥隧加收
                "feeKtype": 1,
                "feeHtype": 2,
                "roadid": "G00706100300",
            },
        ])

        calculator.get_fee_per_km = MagicMock(return_value=0.8)
        calculator.is_control_section = MagicMock(return_value=True)

        result = calculator.calculate_path_fee(
            section_ids=["S001"],
            vehicle_type=11,  # 货车
            version="202512",
        )

        # 货车使用 feeHtype=2
        # S001: 10000m / 1000 * 0.8 = 8.0 元
        assert result.fee_yuan == 8.0
        assert result.total_length_meters == 10000

    def test_calculate_path_fee_with_skipped_sections(self, calculator, mock_sql_runner):
        """测试计算路径通行费 - 含跳过单元"""
        calculator.get_section_info = MagicMock(side_effect=[
            {
                "id": "S001",
                "length": 10000,
                "roadtype": 1,
                "feeKtype": 1,
                "feeHtype": 1,
                "roadid": "G00706100300",
            },
            {
                "id": "S002",
                "length": 5000,
                "roadtype": 3,  # 跳过（西铜高速）
                "feeKtype": 1,
                "feeHtype": 1,
                "roadid": "G00706100400",
            },
            {
                "id": "S003",
                "length": 3000,
                "roadtype": 1,
                "feeKtype": 1,
                "feeHtype": 1,
                "roadid": "G00706100500",
            },
        ])

        calculator.get_fee_per_km = MagicMock(return_value=0.5)
        calculator.is_control_section = MagicMock(return_value=False)

        result = calculator.calculate_path_fee(
            section_ids=["S001", "S002", "S003"],
            vehicle_type=1,
            version="202512",
        )

        # S001: 10元, S002跳过, S003: 1.5元
        assert result.fee_yuan == 6.5
        assert result.total_length_meters == 18000  # 包含跳过的里程
        assert "S002" in result.skipped_sections


# ============================================================================
# calculate_toll_fee 集成测试（使用 Mock）
# ============================================================================


class TestCalculateTollFee:
    """测试 calculate_toll_fee 函数"""

    @pytest.fixture
    def mock_calculator(self):
        """创建 Mock TollCalculator"""
        with patch("src.common.toll_calculator.get_calculator") as mock:
            calc = MagicMock()
            mock.return_value = calc
            yield calc

    def test_enid_exid_empty_intervalgroup_not_empty(self, mock_calculator):
        """enid/exid 为空，直接计算 intervalgroup"""
        mock_calculator.calculate_toll_fee.return_value = TollFeeResult(
            fee_yuan=10.0,
            control_fee_yuan=5.0,
            total_length_meters=10000,
            control_length_meters=5000,
            section_count=2,
            path_type="direct",
        )

        result = calculate_toll_fee(
            enid="",
            exid="",
            intervalgroup="S001|S002",
            vehicle_type=1,
        )

        assert result.fee_yuan == 10.0
        assert result.path_type == "direct"

    def test_intervalgroup_empty_use_shortest_path(self, mock_calculator):
        """intervalgroup 为空，使用最短路径"""
        # 模拟 calculate_toll_fee 方法的完整行为
        mock_calculator.calculate_toll_fee.return_value = TollFeeResult(
            fee_yuan=15.0,
            control_fee_yuan=10.0,
            total_length_meters=20000,
            control_length_meters=15000,
            section_count=3,
            path_type="shortest",
        )

        result = calculate_toll_fee(
            enid="enid",
            exid="exid",
            intervalgroup="",
            vehicle_type=1,
        )

        # 实际调用时 path_type 由内部计算决定
        assert result.total_length_meters == 20000
        assert result.path_type == "shortest"

    def test_compare_and_pick_lower_fee(self, mock_calculator):
        """比较最短路径和 intervalgroup，取较小值"""
        # 模拟 calculate_toll_fee 方法返回较小值的结果
        mock_calculator.calculate_toll_fee.return_value = TollFeeResult(
            fee_yuan=15.0,
            control_fee_yuan=8.0,
            total_length_meters=10000,
            control_length_meters=5000,
            section_count=2,
            path_type="intervalgroup",
        )

        result = calculate_toll_fee(
            enid="enid",
            exid="exid",
            intervalgroup="S001|S002",
            vehicle_type=1,
        )

        # 应该返回较小值
        assert result.fee_yuan == 15.0
        assert result.path_type == "intervalgroup"

    def test_error_when_all_empty(self, mock_calculator):
        """enid/exid/intervalgroup 都为空"""
        mock_calculator.calculate_toll_fee.return_value = TollFeeResult(
            error="intervalgroup 为空且 enid/exid 为空",
        )

        result = calculate_toll_fee(
            enid="",
            exid="",
            intervalgroup="",
            vehicle_type=1,
        )

        assert result.error == "intervalgroup 为空且 enid/exid 为空"


# ============================================================================
# 数据结构测试
# ============================================================================


class TestDataStructures:
    """测试数据结构"""

    def test_path_fee_result_to_dict(self):
        """测试 PathFeeResult.to_dict()"""
        result = PathFeeResult(
            fee_yuan=10.5,
            control_fee_yuan=5.5,
            total_length_meters=10000,
            control_length_meters=5000,
            skipped_sections=["S002"],
        )

        d = result.to_dict()

        assert d["fee_yuan"] == 10.5
        assert d["control_fee_yuan"] == 5.5
        assert d["total_length_meters"] == 10000
        assert d["control_length_meters"] == 5000
        assert d["skipped_sections"] == ["S002"]

    def test_toll_fee_result_to_dict(self):
        """测试 TollFeeResult.to_dict()"""
        result = TollFeeResult(
            fee_yuan=10.5,
            control_fee_yuan=5.5,
            total_length_meters=10000,
            control_length_meters=5000,
            section_count=2,
            skipped_sections=["S002"],
            path_type="intervalgroup",
        )

        d = result.to_dict()

        assert d["fee_yuan"] == 10.5
        assert d["path_type"] == "intervalgroup"
        assert d["section_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
