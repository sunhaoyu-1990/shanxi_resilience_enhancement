"""
affected_od_service 业务编排层单元测试
覆盖: 完整流程、日期解析、2025同期映射、去重逻辑、多版本、is_affected标记、
      affected_section_ids合并、异常处理、CSV输出
使用 Mock Repository，不连接真实数据库
"""

import csv
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

import pytest
from datetime import date
from unittest.mock import patch

from src.modules.m3_impact_analysis.affected_od_service import (
    AffectedOdService,
    _parse_date,
    _get_month_list,
    _dedup_by_latest_version,
    _mark_affected_sections,
)
from src.common.time_utils import to_same_period
from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdQueryParams,
    AffectedOdPathRecord,
)


# ============================================================
# 辅助函数
# ============================================================


class TestParseDate:
    """日期解析"""

    def test_normal(self):
        assert _parse_date("20260315") == date(2026, 3, 15)

    def test_jan_1(self):
        assert _parse_date("20260101") == date(2026, 1, 1)

    def test_dec_31(self):
        assert _parse_date("20261231") == date(2026, 12, 31)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            _parse_date("2026-03-15")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _parse_date("")


class TestToSamePeriod:
    """同期映射 (参数化年份)"""

    def test_normal_date_2025(self):
        assert to_same_period(date(2026, 3, 15), 2025) == date(2025, 3, 15)

    def test_normal_date_2024(self):
        assert to_same_period(date(2026, 3, 15), 2024) == date(2024, 3, 15)

    def test_feb_28(self):
        assert to_same_period(date(2024, 2, 28), 2025) == date(2025, 2, 28)

    def test_feb_29_leap_year_maps_to_feb_28(self):
        """闰年2月29日映射到目标年2月28日（平年无2月29日）"""
        result = to_same_period(date(2024, 2, 29), 2025)
        assert result == date(2025, 3, 1) - __import__("datetime").timedelta(days=1)
        assert result.month == 2
        assert result.day == 28

    def test_dec_31(self):
        assert to_same_period(date(2026, 12, 31), 2025) == date(2025, 12, 31)

    def test_jan_1(self):
        assert to_same_period(date(2026, 1, 1), 2025) == date(2025, 1, 1)

    def test_cross_year_same_period(self):
        """跨年映射：2026施工期 → 2024同期"""
        assert to_same_period(date(2025, 12, 20), 2024) == date(2024, 12, 20)
        assert to_same_period(date(2026, 1, 10), 2024) == date(2024, 1, 10)


class TestGetMonthList:
    """月份列表生成"""

    def test_single_month(self):
        assert _get_month_list(date(2026, 3, 1), date(2026, 3, 31)) == ["202603"]

    def test_cross_month(self):
        result = _get_month_list(date(2026, 3, 15), date(2026, 4, 15))
        assert result == ["202603", "202604"]

    def test_cross_year(self):
        result = _get_month_list(date(2025, 12, 20), date(2026, 1, 10))
        assert result == ["202512", "202601"]

    def test_same_day(self):
        assert _get_month_list(date(2026, 5, 1), date(2026, 5, 1)) == ["202605"]


class TestDedupByLatestVersion:
    """多版本去重"""

    def test_takes_latest_version(self):
        rows = [
            {"enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202512"},
            {"enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2|S3", "version_yyyymm": "202603"},
        ]
        result = _dedup_by_latest_version(rows)
        assert len(result) == 1
        assert result[0]["version_yyyymm"] == "202603"
        assert result[0]["fixed_intervalpath"] == "S1|S2|S3"

    def test_different_paths_kept(self):
        rows = [
            {"enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
        ]
        result = _dedup_by_latest_version(rows)
        assert len(result) == 2

    def test_empty_list(self):
        assert _dedup_by_latest_version([]) == []

    def test_same_version_merges_affected_sections(self):
        rows = [
            {"enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603", "affected_section_ids": "S1"},
            {"enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603", "affected_section_ids": "S2"},
        ]
        result = _dedup_by_latest_version(rows)
        assert len(result) == 1
        merged = result[0]["affected_section_ids"].split("|")
        assert "S1" in merged
        assert "S2" in merged


class TestMarkAffectedSections:
    """标记受影响section和is_affected"""

    def test_affected_path(self):
        row = {"fixed_intervalpath": "S1|S2|S3"}
        affected_str, is_affected = _mark_affected_sections(row, ["S2"])
        assert is_affected is True
        assert affected_str == "S2"

    def test_unaffected_path(self):
        row = {"fixed_intervalpath": "S4|S5"}
        affected_str, is_affected = _mark_affected_sections(row, ["S1", "S2"])
        assert is_affected is False
        assert affected_str == ""

    def test_multiple_affected_sections_preserves_input_order(self):
        row = {"fixed_intervalpath": "S3|S1|S2"}
        affected_str, is_affected = _mark_affected_sections(row, ["S1", "S2", "S3"])
        assert is_affected is True
        assert affected_str == "S1|S2|S3"


# ============================================================
# AffectedOdService 完整流程
# ============================================================


def _make_service(
    affected_paths=None,
    all_paths=None,
    daily_tables=None,
    vtype_flow_result=None,
    table_exists=True,
):
    """构造带 Mock Repository 的 Service

    Args:
        vtype_flow_result: dict[(path_id, vehicle_type), flow]，默认 {(1, "1"): 50}
    """
    service = AffectedOdService()
    mock_repo = MagicMock()

    if affected_paths is None:
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1|2", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202603",
            },
        ]
    mock_repo.find_affected_od_paths.return_value = affected_paths

    if all_paths is None:
        all_paths = affected_paths  # 默认：受影响path = 所有path
    mock_repo.find_all_paths_for_ods.return_value = all_paths

    if daily_tables is None:
        daily_tables = [("20260301", "dws_section_od_path_flow_hour_20260301")]
    mock_repo.list_available_dws_daily_tables.return_value = daily_tables

    if vtype_flow_result is None:
        vtype_flow_result = {(1, "1"): 50}
    mock_repo.query_flow_by_vehicle_type.return_value = vtype_flow_result

    mock_repo.check_dws_table_exists.return_value = table_exists

    service.repository = mock_repo
    return service, mock_repo


class TestAffectedOdServiceRun:
    """完整流程测试"""

    def test_basic_flow(self):
        """基本流程：1个施工段 → 1条受影响OD-Path → 有流量"""
        service, mock = _make_service()
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "success"
        assert result.affectedOdCount >= 1
        assert result.constructionFlowAvailable is True

    def test_multiple_sections_in_input(self):
        """多个施工段输入"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1|2", "fixed_intervalpath": "S1|S2|S3",
                "version_yyyymm": "202603",
            },
            {
                "id": 2, "enid": "EN2", "exid": "EX2",
                "numpath": "3", "fixed_intervalpath": "S2|S4",
                "version_yyyymm": "202603",
            },
        ]
        all_paths = affected_paths + [
            {
                "id": 3, "enid": "EN1", "exid": "EX1",
                "numpath": "5", "fixed_intervalpath": "S5|S6",
                "version_yyyymm": "202603",
            },
        ]
        service, mock = _make_service(affected_paths=affected_paths, all_paths=all_paths)
        params = AffectedOdQueryParams(
            sectionIds="S1|S2", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "success"
        # 验证find_affected_od_paths被调用了正确的参数
        call_args = mock.find_affected_od_paths.call_args
        assert "S1" in call_args[0][0]
        assert "S2" in call_args[0][0]

    def test_is_affected_flag(self):
        """is_affected标记：受影响和不受影响的path"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1|2", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202603",
            },
        ]
        all_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1|2", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202603",
            },
            {
                "id": 2, "enid": "EN1", "exid": "EX1",
                "numpath": "3", "fixed_intervalpath": "S4|S5",
                "version_yyyymm": "202603",
            },
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 50, (2, "1"): 30}
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            # path 1 是受影响的（经过S1），path 2 不受影响
            affected_map = {r["od_section_path_id"]: r for r in rows}
            assert affected_map["1"]["is_affected"] == "True"
            assert affected_map["2"]["is_affected"] == "False"

    def test_affected_section_ids_order(self):
        """affected_section_ids按输入顺序拼接"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1", "fixed_intervalpath": "S2|S1|S3",
                "version_yyyymm": "202603",
            },
        ]
        service, mock = _make_service(affected_paths=affected_paths, all_paths=affected_paths)
        params = AffectedOdQueryParams(
            sectionIds="S1|S2|S3", startDate="20260301", endDate="20260301",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert rows[0]["affected_section_ids"] == "S1|S2|S3"

    def test_map_version_in_output(self):
        """CSV输出包含map_version列"""
        service, mock = _make_service()
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert "map_version" in rows[0]
            assert rows[0]["map_version"] == "202603"

    def test_multi_version_dedup(self):
        """多版本去重：同enid+exid+numpath取最新版本"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1|2", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202512",
            },
            {
                "id": 10, "enid": "EN1", "exid": "EX1",
                "numpath": "1|2", "fixed_intervalpath": "S1|S2|S3",
                "version_yyyymm": "202603",
            },
        ]
        all_paths = affected_paths  # 简化：受影响=所有
        service, mock = _make_service(
            affected_paths=affected_paths,
            all_paths=all_paths,
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260225", endDate="20260306",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            # 去重后应只有1条，版本为202603
            assert len(rows) == 1
            assert rows[0]["map_version"] == "202603"

    def test_no_affected_paths(self):
        """无受影响OD-Path"""
        service, mock = _make_service(affected_paths=[])
        params = AffectedOdQueryParams(
            sectionIds="NOT_EXIST", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "success"
        assert result.affectedOdCount == 0

    def test_empty_dwd_table(self):
        """dwd_od_section_path_map表无数据（find_affected_od_paths返回空）"""
        service, mock = _make_service(affected_paths=[])
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "success"
        assert result.affectedOdCount == 0

    def test_no_dws_tables(self):
        """dws表不存在"""
        service, mock = _make_service(daily_tables=[], table_exists=False)
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "success"
        assert result.constructionFlowAvailable is False

    def test_csv_output_exists(self):
        """CSV文件正确生成"""
        service, mock = _make_service()
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            assert os.path.exists(out)
            with open(out, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) >= 1
            assert "od_section_path_id" in rows[0]
            assert "construction_flow" in rows[0]
            assert "is_affected" in rows[0]
            assert "map_version" in rows[0]

    def test_2025_same_period_not_available(self):
        """2025同期表不存在时正确处理"""
        service, mock = _make_service(table_exists=False)
        # 施工期间日表返回数据，但2025同期日表和月表都不存在
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_section_od_path_flow_hour_20260301")]
                if start.year == 2026
                else []
            )
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.samePeriod2025FlowAvailable is False

    def test_exception_handling(self):
        """Repository异常时返回failed"""
        service, mock = _make_service()
        mock.find_affected_od_paths.side_effect = RuntimeError("DB down")
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert result.status == "failed"
        assert len(result.errors) > 0

    def test_flow_query_missing_paths(self):
        """部分path无流量数据时，construction_flow为None"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1",
                "fixed_intervalpath": "S1", "version_yyyymm": "202603",
            },
            {
                "id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2",
                "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603",
            },
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=affected_paths,
            vtype_flow_result={(1, "1"): 100}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_section_od_path_flow_hour_20260301")]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # 验证记录结构：path 1 有流量，path 2 无流量
            path_ids_seen = {r["od_section_path_id"] for r in rows}
            assert "1" in path_ids_seen
            assert "2" in path_ids_seen
            # path 1 的 construction_flow 应为正数（来自 vtype_flow_result）
            path1_flows = [r["construction_flow"] for r in rows if r["od_section_path_id"] == "1"]
            assert all(f != "" for f in path1_flows), f"path 1 flows should be non-empty: {path1_flows}"
            # path 2 的 construction_flow 应为空
            path2_flows = [r["construction_flow"] for r in rows if r["od_section_path_id"] == "2"]
            assert all(f == "" for f in path2_flows), f"path 2 flows should be empty: {path2_flows}"

    def test_daily_table_priority(self):
        """日表优先查询"""
        service, mock = _make_service()
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260303",
        )
        result = service.run(params)
        assert mock.list_available_dws_daily_tables.called

    def test_daily_table_flow_accumulation(self):
        """日表模式下，多日流量应累加而非只取第一天"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=affected_paths,
            vtype_flow_result={(1, "1"): 10}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [
                    ("20260301", "dws_20260301"),
                    ("20260302", "dws_20260302"),
                    ("20260303", "dws_20260303"),
                ]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260303",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # 3天 × 10 = 30
            assert rows[0]["construction_flow"] == "30"

    def test_fallback_to_monthly_table(self):
        """无日表时回退到月表"""
        service, mock = _make_service(daily_tables=[])
        mock.check_dws_table_exists.return_value = True
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        assert mock.query_flow_by_vehicle_type.called

    def test_find_affected_od_paths_called_without_version(self):
        """find_affected_od_paths调用时不传版本参数"""
        service, mock = _make_service()
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260225", endDate="20260306",
        )
        result = service.run(params)
        # 验证find_affected_od_paths被调用，且只有section_id_list参数
        assert mock.find_affected_od_paths.called
        call_args = mock.find_affected_od_paths.call_args
        section_ids = call_args[0][0]
        assert "S1" in section_ids
        # 不再传version_list参数
        assert call_args[1].get("version_list") is None or len(call_args[0]) == 1

    def test_unaffected_path_uses_first_section_as_anchor(self):
        """不受影响path取fixed_intervalpath第一个section作为锚点"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202603",
            },
        ]
        all_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202603",
            },
            {
                "id": 2, "enid": "EN1", "exid": "EX1",
                "numpath": "3", "fixed_intervalpath": "S4|S5",
                "version_yyyymm": "202603",
            },
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 50, (2, "1"): 30}
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        # 验证query_flow_by_vehicle_type被调用了S4（不受影响path的第一个section）
        calls = mock.query_flow_by_vehicle_type.call_args_list
        section_ids_used = [c[1].get("section_id", c[0][1] if len(c[0]) > 1 else None) for c in calls]
        assert "S4" in section_ids_used

    def test_od_pairs_passed_to_find_all_paths(self):
        """验证find_all_paths_for_ods接收的是OD对列表而非enid/exid列表"""
        affected_paths = [
            {
                "id": 1, "enid": "EN1", "exid": "EX1",
                "numpath": "1", "fixed_intervalpath": "S1|S2",
                "version_yyyymm": "202603",
            },
            {
                "id": 2, "enid": "EN2", "exid": "EX2",
                "numpath": "2", "fixed_intervalpath": "S1|S3",
                "version_yyyymm": "202603",
            },
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=affected_paths,
            vtype_flow_result={(1, "1"): 50, (2, "1"): 30}
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
        )
        result = service.run(params)
        # 验证find_all_paths_for_ods的第一个参数是OD对列表
        call_args = mock.find_all_paths_for_ods.call_args
        od_pairs_arg = call_args[0][0]
        assert isinstance(od_pairs_arg, list)
        assert ("EN1", "EX1") in od_pairs_arg
        assert ("EN2", "EX2") in od_pairs_arg
        # 不应有笛卡尔积产生的假OD对（如EN1+EX2）
        assert ("EN1", "EX2") not in od_pairs_arg

    def test_min_affected_path_flow_filter(self):
        """Step 10: minAffectedPathFlow过滤：OD对聚合流量<=阈值则is_affected记录全部去掉，不受影响的path无条件保留"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
        ]
        all_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
        ]
        # path 1 (is_affected=True): OD对EN1→EX1聚合流量=3, 低于阈值10 → 该OD下is_affected记录全部去掉
        # path 2 (is_affected=False): 不受影响 → 无条件保留
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 3, (2, "1"): 5}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_20260301")]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minAffectedPathFlow=10,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result, _ = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # path 1 被过滤掉（is_affected=True, OD聚合流量=3 < 10）
            # path 2 保留（is_affected=False, 无条件保留）
            # 但之后 Step 11 要求至少有一条 is_affected=True path，所以 EN1→EX1 的 path 2 也会被去掉
            assert len(rows) == 0
            assert len(result.filteredOdPairs) == 0

    @patch("src.modules.m3_impact_analysis.affected_od_service._batch_calculate_toll_fee")
    def test_min_affected_path_flow_keeps_qualified_affected_path(self, mock_toll):
        """Step 10: minAffectedPathFlow过滤：OD对聚合流量>阈值则is_affected记录保留"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
        ]
        all_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
        ]
        # path 1 (is_affected=True): construction_flow=100 > 10 → 保留
        # path 2 (is_affected=False): 无条件保留
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 100, (2, "1"): 50}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_20260301")]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minAffectedPathFlow=10,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result, _ = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # 两条path都保留（各1条车型记录）
            assert len(rows) == 2

    @patch("src.modules.m3_impact_analysis.affected_od_service._batch_calculate_toll_fee")
    def test_three_step_filter(self, mock_toll):
        """三步过滤完整流程：Step 10 → Step 11 → Step 12"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 3, "enid": "EN2", "exid": "EX2", "numpath": "3", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202603"},
        ]
        all_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
            {"id": 3, "enid": "EN2", "exid": "EX2", "numpath": "3", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202603"},
        ]
        # path 1 (is_affected=True): OD对EN1→EX1聚合流量=100 > 10 → Step 10 保留
        # path 2 (is_affected=False): 无条件保留
        # path 3 (is_affected=True): OD对EN2→EX2聚合流量=3 <= 10 → Step 10 去掉
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 100, (2, "1"): 50, (3, "1"): 3}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_20260301")]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minAffectedPathFlow=10,
            minFlow=100,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result, _ = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # Step 10: EN2→EX2 OD聚合流量=3 <= 10, path 3 被去掉
            # Step 11: EN2→EX2 无 is_affected=True path 存活 → 去掉
            # Step 12: EN1→EX1 OD总流量 = 100+50 = 150 > 100 → 保留两条
            assert len(rows) == 2
            csv_ods = {(r["enid"], r["exid"]) for r in rows}
            assert csv_ods == {("EN1", "EX1")}

    @patch("src.modules.m3_impact_analysis.affected_od_service._batch_calculate_toll_fee")
    def test_min_affected_path_flow_od_aggregation_keeps_zero_flow_paths(self, mock_toll):
        """Step 10 新逻辑：同一OD下多条is_affected=True的path，单条0流量但OD聚合>阈值则全部保留"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 3, "enid": "EN1", "exid": "EX1", "numpath": "3", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202603"},
        ]
        all_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
            {"id": 3, "enid": "EN1", "exid": "EX1", "numpath": "3", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202603"},
        ]
        # path 1 (is_affected=True): construction_flow=15
        # path 3 (is_affected=True): construction_flow=0 (0流量车型)
        # path 2 (is_affected=False): construction_flow=20
        # 旧逻辑：path 3 单条 flow=0 < 10 → 去掉
        # 新逻辑：EN1→EX1 OD聚合 = 15+0 = 15 > 10 → 两条is_affected都保留
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 15, (2, "1"): 20, (3, "1"): 0}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_20260301")]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minAffectedPathFlow=10,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result, _ = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # OD聚合流量=15 > 10, path 1 和 path 3 (is_affected) 都保留, path 2 也保留
            assert len(rows) == 3
            affected_rows = [r for r in rows if r["is_affected"] == "True"]
            assert len(affected_rows) == 2

    def test_min_flow_filter_od_level_aggregation(self):
        """Step 12: minFlow过滤：同一OD下多条path流量聚合后超过阈值，全部保留"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=affected_paths,
            vtype_flow_result={(1, "1"): 5, (2, "1"): 8}
        )
        mock.list_available_dws_daily_tables.side_effect = (
            lambda start, end: (
                [("20260301", "dws_20260301")]
                if start.year == 2026
                else []
            )
        )
        mock.check_dws_table_exists.return_value = False
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minFlow=10,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # OD (EN1,EX1) 总流量 = (5+8)*2 = 26 > 10 → 两条path都保留
            assert len(rows) == 2

    def test_min_flow_zero_no_filter(self):
            assert len(rows) == 2

    def test_min_flow_zero_no_filter(self):
        """minFlow=0不过滤"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN2", "exid": "EX2", "numpath": "2", "fixed_intervalpath": "S1|S3", "version_yyyymm": "202603"},
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=affected_paths,
            vtype_flow_result={(1, "1"): 0}
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minFlow=0,
            minAffectedPathFlow=0,
        )
        result = service.run(params)
        assert result.affectedOdCount == 2

    def test_filtered_od_pairs_requires_affected_path(self):
        """filteredOdPairs只包含有is_affected=True path的OD对，records也同步过滤"""
        affected_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
        ]
        # EN1->EX1 有受影响path(id=1)和不受影响path(id=2)
        # EN2->EX2 只有不受影响path(id=3)
        all_paths = [
            {"id": 1, "enid": "EN1", "exid": "EX1", "numpath": "1", "fixed_intervalpath": "S1|S2", "version_yyyymm": "202603"},
            {"id": 2, "enid": "EN1", "exid": "EX1", "numpath": "2", "fixed_intervalpath": "S4|S5", "version_yyyymm": "202603"},
            {"id": 3, "enid": "EN2", "exid": "EX2", "numpath": "3", "fixed_intervalpath": "S6|S7", "version_yyyymm": "202603"},
        ]
        service, mock = _make_service(
            affected_paths=affected_paths, all_paths=all_paths,
            vtype_flow_result={(1, "1"): 100, (2, "1"): 200, (3, "1"): 300}
        )
        params = AffectedOdQueryParams(
            sectionIds="S1", startDate="20260301", endDate="20260301",
            minFlow=10,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.csv")
            result = service.run(params, output_path=out)
            with open(out, "r") as f:
                rows = list(csv.DictReader(f))
            # CSV只保留EN1->EX1下的path(id=1,2)，不含EN2->EX2(id=3)
            csv_ods = {(r["enid"], r["exid"]) for r in rows}
            assert csv_ods == {("EN1", "EX1")}
            assert len(rows) == 2  # id=1 和 id=2
            # filteredOdPairs也只含EN1->EX1
            od_pairs_set = set(result.filteredOdPairs)
            assert ("EN1", "EX1") in od_pairs_set
            assert ("EN2", "EX2") not in od_pairs_set
