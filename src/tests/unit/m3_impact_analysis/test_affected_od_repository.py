"""
affected_od_repository 数据访问层单元测试
覆盖: SQL查询构建、返回值解析、异常情况
使用 Mock SqlRunner，不连接真实数据库
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from unittest.mock import MagicMock

from src.modules.m3_impact_analysis.affected_od_repository import AffectedOdRepository


def _make_repository(fetch_one_side_effect=None, fetch_all_return=None, bridge_exists=False):
    """构造带 Mock SqlRunner 的 Repository

    Args:
        bridge_exists: 如果True，模拟桥接表存在且有数据（走bridge路径）
    """
    mock_runner = MagicMock()
    if fetch_one_side_effect is not None:
        mock_runner.fetch_one.side_effect = fetch_one_side_effect
    if fetch_all_return is not None:
        mock_runner.fetch_all.return_value = fetch_all_return
    if bridge_exists:
        # _check_bridge_table_exists 做两次 fetch_one:
        # 1) 检查表是否存在 → {"table_exists": True}
        # 2) 检查表是否有数据 → {"cnt": 100}
        mock_runner.fetch_one.side_effect = [
            {"table_exists": True},
            {"cnt": 100},
        ] + (list(fetch_one_side_effect) if fetch_one_side_effect else [])
    else:
        # 桥接表不存在
        mock_runner.fetch_one.return_value = {"table_exists": False}
    repo = AffectedOdRepository(sql_runner=mock_runner)
    return repo, mock_runner


# ============================================================
# get_applicable_versions
# ============================================================


class TestGetApplicableVersions:
    """获取适用版本列表"""

    def test_returns_versions(self):
        """正常返回版本列表"""
        version_rows = [
            {"version_yyyymm": "202512"},
            {"version_yyyymm": "202603"},
        ]
        repo, mock = _make_repository(fetch_all_return=version_rows)
        result = repo.get_applicable_versions(["202602", "202603"])
        assert result == ["202512", "202603"]

    def test_empty_month_list(self):
        """空月份列表返回空"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.get_applicable_versions([])
        assert result == []

    def test_no_applicable_versions(self):
        """月份列表无对应版本"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.get_applicable_versions(["209912"])
        assert result == []

    def test_dedup_versions(self):
        """多个月份映射到同一版本时去重"""
        version_rows = [
            {"version_yyyymm": "202603"},
        ]
        repo, mock = _make_repository(fetch_all_return=version_rows)
        result = repo.get_applicable_versions(["202603", "202604"])
        assert result == ["202603"]

    def test_single_month(self):
        """单月份"""
        version_rows = [{"version_yyyymm": "202603"}]
        repo, mock = _make_repository(fetch_all_return=version_rows)
        result = repo.get_applicable_versions(["202603"])
        assert result == ["202603"]


# ============================================================
# find_affected_od_paths (multi-version)
# ============================================================


class TestFindAffectedOdPaths:
    """查找受影响OD-Path（所有版本）"""

    def test_returns_matching_paths_via_unnest(self):
        """通过unnest回退路径返回匹配的OD-Path"""
        expected = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1|2", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN2", "exid": "EX2", "numpath": "3", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202512"},
        ]
        repo, mock = _make_repository(fetch_all_return=expected)
        result = repo.find_affected_od_paths(["S1", "S2"])
        assert len(result) == 2
        assert result[0]["id"] == 1
        # 验证传了正确的参数（只有section_ids，无versions）
        call_args = mock.fetch_all.call_args
        params = call_args[1].get("params", call_args[0][1] if len(call_args[0]) > 1 else {})
        assert "versions" not in params
        assert "S1" in params["section_ids"]
        assert "S2" in params["section_ids"]

    def test_returns_matching_paths_via_bridge(self):
        """通过桥接表索引返回匹配的OD-Path"""
        expected = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1|2", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
        ]
        repo, mock = _make_repository(fetch_all_return=expected, bridge_exists=True)
        result = repo.find_affected_od_paths(["S1"])
        assert len(result) == 1
        # 验证使用了桥接表路径（SQL含dwd_section_path_bridge）
        call_args = mock.fetch_all.call_args
        sql = call_args[0][0]
        assert "dwd_section_path_bridge" in sql

    def test_empty_section_list(self):
        """空施工段列表"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.find_affected_od_paths([])
        assert result == []

    def test_no_matching_paths(self):
        """无匹配OD-Path"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.find_affected_od_paths(["NOT_EXIST"])
        assert result == []

    def test_multiple_versions(self):
        """多版本返回不同版本的同一路径"""
        expected = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1|2", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202512"},
            {"id": 10, "enid": "EN1", "exid": "EX1", "numpath": "1|2", "fixed_intervalpath": "S1|S2|S3", "version_yyyymm": "202603"},
        ]
        repo, mock = _make_repository(fetch_all_return=expected)
        result = repo.find_affected_od_paths(["S1"])
        assert len(result) == 2
        assert result[0]["version_yyyymm"] == "202512"
        assert result[1]["version_yyyymm"] == "202603"

    def test_bridge_with_version_filter(self):
        """桥接表路径支持版本过滤"""
        expected = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1|2", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
        ]
        repo, mock = _make_repository(fetch_all_return=expected, bridge_exists=True)
        result = repo.find_affected_od_paths(["S1"], version="202603")
        assert len(result) == 1
        # 验证SQL含版本过滤
        call_args = mock.fetch_all.call_args
        sql = call_args[0][0]
        assert "version" in sql.lower()


# ============================================================
# find_all_paths_for_ods
# ============================================================


class TestFindAllPathsForOds:
    """查找受影响OD下所有path（所有版本）"""

    def test_returns_all_paths(self):
        """返回OD对下所有path（含受影响和不受影响的）"""
        expected = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1|2", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "3", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
        ]
        repo, mock = _make_repository(fetch_all_return=expected)
        result = repo.find_all_paths_for_ods([("EN1", "EX1")])
        assert len(result) == 2
        # 验证SQL中包含 VALUES CTE 和 JOIN
        call_args = mock.fetch_all.call_args
        sql = call_args[0][0]
        assert "target_ods" in sql
        assert "VALUES" in sql
        assert "('EN1', 'EX1')" in sql

    def test_empty_od_pairs(self):
        """空OD对列表"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.find_all_paths_for_ods([])
        assert result == []

    def test_multiple_ods_multiple_versions(self):
        """多OD对多版本"""
        expected = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN2", "exid": "EX2", "numpath": "2", "fixed_intervalpath": "S2", "version_yyyymm": "202603"},
            {"id": 3, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202512"},
        ]
        repo, mock = _make_repository(fetch_all_return=expected)
        result = repo.find_all_paths_for_ods([("EN1", "EX1"), ("EN2", "EX2")])
        assert len(result) == 3

    def test_no_paths_found(self):
        """无匹配path"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.find_all_paths_for_ods([("EN99", "EX99")])
        assert result == []

    def test_no_cartesian_expansion(self):
        """验证SQL不会产生笛卡尔积（只有精确的OD对匹配）"""
        repo, mock = _make_repository(fetch_all_return=[])
        repo.find_all_paths_for_ods([("EN1", "EX1"), ("EN2", "EX2")])
        sql = mock.fetch_all.call_args[0][0]
        # 确认SQL使用JOIN而非 ANY + ANY
        assert "JOIN target_ods" in sql
        assert "enid_list" not in sql
        assert "exid_list" not in sql


# ============================================================
# check_dws_table_exists
# ============================================================


class TestCheckDwsTableExists:
    """检查dws表是否存在"""

    def test_table_exists(self):
        """表存在"""
        repo, mock = _make_repository(
            fetch_one_side_effect=[{"table_exists": True}]
        )
        assert repo.check_dws_table_exists("dws_section_od_path_flow_hour_202603") is True

    def test_table_not_exists(self):
        """表不存在"""
        repo, mock = _make_repository(
            fetch_one_side_effect=[{"table_exists": False}]
        )
        assert repo.check_dws_table_exists("dws_section_od_path_flow_hour_209912") is False

    def test_none_result(self):
        """查询返回None"""
        repo, mock = _make_repository(
            fetch_one_side_effect=[None]
        )
        assert repo.check_dws_table_exists("unknown") is False


# ============================================================
# list_available_dws_daily_tables
# ============================================================


class TestListAvailableDwsDailyTables:
    """列出可用日表"""

    def test_finds_daily_tables(self):
        """找到日表"""
        repo, mock = _make_repository(
            fetch_one_side_effect=[
                {"table_exists": True},   # 20260301
                {"table_exists": True},   # 20260302
                {"table_exists": False},  # 20260303 不存在
                {"table_exists": True},   # 20260304
            ]
        )
        start = date(2026, 3, 1)
        end = date(2026, 3, 4)
        result = repo.list_available_dws_daily_tables(start, end)
        assert len(result) == 3
        assert result[0] == ("20260301", "dws_section_od_path_flow_hour_20260301")
        assert result[1] == ("20260302", "dws_section_od_path_flow_hour_20260302")
        assert result[2] == ("20260304", "dws_section_od_path_flow_hour_20260304")

    def test_no_daily_tables(self):
        """无日表"""
        repo, mock = _make_repository(
            fetch_one_side_effect=[
                {"table_exists": False},
                {"table_exists": False},
            ]
        )
        result = repo.list_available_dws_daily_tables(date(2025, 1, 1), date(2025, 1, 2))
        assert result == []

    def test_single_day_range(self):
        """单天范围"""
        repo, mock = _make_repository(
            fetch_one_side_effect=[{"table_exists": True}]
        )
        result = repo.list_available_dws_daily_tables(date(2026, 3, 1), date(2026, 3, 1))
        assert len(result) == 1


# ============================================================
# query_flow_for_section_and_paths
# ============================================================


class TestQueryFlowForSectionAndPaths:
    """查询流量"""

    def test_returns_flow_dict(self):
        """返回流量字典"""
        flow_rows = [
            {"od_section_path_id": 1, "total_flow": 50},
            {"od_section_path_id": 2, "total_flow": 30},
        ]
        repo, mock = _make_repository(fetch_all_return=flow_rows)
        result = repo.query_flow_for_section_and_paths(
            table_name="dws_section_od_path_flow_hour_20260301",
            section_id="S1",
            path_id_list=[1, 2],
            start_timestamp="2026-03-01 00:00:00",
            end_timestamp="2026-03-02 00:00:00",
        )
        assert result == {1: 50, 2: 30}

    def test_empty_result(self):
        """无流量数据"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.query_flow_for_section_and_paths(
            table_name="dws_section_od_path_flow_hour_20260301",
            section_id="S1",
            path_id_list=[999],
            start_timestamp="2026-03-01 00:00:00",
            end_timestamp="2026-03-02 00:00:00",
        )
        assert result == {}

    def test_uses_correct_table_name(self):
        """验证使用正确的表名"""
        repo, mock = _make_repository(fetch_all_return=[])
        repo.query_flow_for_section_and_paths(
            table_name="dws_section_od_path_flow_hour_20250401",
            section_id="S1",
            path_id_list=[1],
            start_timestamp="2025-04-01 00:00:00",
            end_timestamp="2025-04-02 00:00:00",
        )
        sql = mock.fetch_all.call_args[0][0]
        assert "dws_section_od_path_flow_hour_20250401" in sql


# ============================================================
# query_flow_by_vehicle_type
# ============================================================


class TestQueryFlowByVehicleType:
    """查询流量（按vehicle_type分组）"""

    def test_returns_vtype_flow_dict(self):
        """返回{(path_id, vehicle_type): total_flow}字典"""
        flow_rows = [
            {"od_section_path_id": 1, "vehicle_type": "1", "total_flow": 50},
            {"od_section_path_id": 1, "vehicle_type": "2", "total_flow": 30},
            {"od_section_path_id": 2, "vehicle_type": "1", "total_flow": 20},
        ]
        repo, mock = _make_repository(fetch_all_return=flow_rows)
        result = repo.query_flow_by_vehicle_type(
            table_name="dws_section_od_path_flow_hour_20260301",
            section_id="S1",
            path_id_list=[1, 2],
            start_timestamp="2026-03-01 00:00:00",
            end_timestamp="2026-03-02 00:00:00",
        )
        assert result[(1, "1")] == 50
        assert result[(1, "2")] == 30
        assert result[(2, "1")] == 20

    def test_empty_result(self):
        """无流量数据"""
        repo, mock = _make_repository(fetch_all_return=[])
        result = repo.query_flow_by_vehicle_type(
            table_name="dws_section_od_path_flow_hour_20260301",
            section_id="S1",
            path_id_list=[999],
            start_timestamp="2026-03-01 00:00:00",
            end_timestamp="2026-03-02 00:00:00",
        )
        assert result == {}

    def test_sql_groups_by_vehicle_type(self):
        """验证SQL包含vehicle_type分组"""
        repo, mock = _make_repository(fetch_all_return=[])
        repo.query_flow_by_vehicle_type(
            table_name="dws_section_od_path_flow_hour_20260301",
            section_id="S1",
            path_id_list=[1],
            start_timestamp="2026-03-01 00:00:00",
            end_timestamp="2026-03-02 00:00:00",
        )
        sql = mock.fetch_all.call_args[0][0]
        assert "vehicle_type" in sql
        assert "GROUP BY" in sql
