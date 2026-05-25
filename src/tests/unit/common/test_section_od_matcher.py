"""
test_section_od_matcher.py - 路段级别OD匹配器单元测试
"""

import csv
import os
import tempfile

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.common.section_od_matcher import SectionOdMatcher, deduplicate_name_words
from src.modules.m3_impact_analysis.analysis_schema import (
    AffectedOdPathRecord,
    MidTripExitFlowStatRecord,
    DetourFlowStatRecord,
    ImpactSummaryRecord,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo():
    """Mock M7Repository"""
    with patch("src.common.section_od_matcher.M7Repository") as MockRepo:
        repo = MagicMock()
        MockRepo.return_value = repo
        yield repo


@pytest.fixture
def matcher(mock_repo):
    """SectionOdMatcher with mocked repo"""
    return SectionOdMatcher()


@pytest.fixture
def sample_section_map():
    """模拟 sectionMap: 16位收费单元ID → section_number"""
    return {
        "G000561005000910": 35,
        "G000561006000110": 325,
        "G000561006000210": 42,
        "G000561007000110": 100,
    }


@pytest.fixture
def sample_station_map():
    """模拟 station_map: 14位站ID → section_number"""
    return {
        "61010001010101": 35,
        "61010002010101": 325,
        "61010003010101": 42,
    }


# ============================================================================
# resolve_to_section_number 测试
# ============================================================================


class TestResolveToSectionNumber:
    """测试 resolve_to_section_number 方法"""

    def test_station_map_direct_hit(self, matcher, mock_repo, sample_station_map):
        """14位站ID在 station_map 中直接命中"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202603": sample_station_map}

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            result = matcher.resolve_to_section_number("61010001010101", "20260415")

        assert result == 35

    def test_section_map_direct_hit(self, matcher, mock_repo, sample_section_map):
        """16位收费单元ID在 sectionMap 中直接命中"""
        mock_repo.get_section_map.return_value = sample_section_map
        matcher._station_map_cache = {}

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            result = matcher.resolve_to_section_number("G000561005000910", "20260415")

        assert result == 35

    def test_drill_down_one_level(self, matcher, mock_repo, sample_section_map):
        """station_map 和 sectionMap 都未命中，下钻一层在 sectionMap 中找到"""
        mock_repo.get_section_map.return_value = sample_section_map
        matcher._station_map_cache = {}

        # _query_next_sections_from_db 返回下一层门架
        mock_repo._query_next_sections_from_db.return_value = ["G000561005000910"]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202512"):
            result = matcher.resolve_to_section_number("61999999010101", "20260415")

        assert result == 35
        mock_repo._query_next_sections_from_db.assert_called_once()

    def test_drill_down_two_levels(self, matcher, mock_repo, sample_section_map):
        """下钻返回两层结果，第二层命中"""
        mock_repo.get_section_map.return_value = sample_section_map
        matcher._station_map_cache = {}

        # 第一层门架不在 sectionMap，第二层门架在
        mock_repo._query_next_sections_from_db.return_value = [
            "NOT_IN_MAP_1",
            "G000561006000110",
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202512"):
            result = matcher.resolve_to_section_number("61999999010101", "20260415")

        assert result == 325

    def test_not_found(self, matcher, mock_repo):
        """所有层级都未找到"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {}
        mock_repo._query_next_sections_from_db.return_value = []

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202512"):
            result = matcher.resolve_to_section_number("61999999999999", "20260415")

        assert result is None

    def test_no_topo_version(self, matcher, mock_repo):
        """无法获取拓扑版本时返回 None"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {}

        with patch("src.common.section_od_matcher.get_nearest_version", return_value=None):
            result = matcher.resolve_to_section_number("61999999999999", "20260415")

        assert result is None


# ============================================================================
# match_section_od 测试
# ============================================================================


class TestMatchSectionOd:
    """测试 match_section_od 方法"""

    def test_both_resolved_sorted(self, matcher, mock_repo):
        """两端都解析成功，排序拼接"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202603": {
            "61010001010101": 325,
            "61010002010101": 35,
        }}

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            result = matcher.match_section_od("61010001010101", "61010002010101", "20260415")

        assert result == "35|325"

    def test_only_one_resolved(self, matcher, mock_repo):
        """只有一端解析成功"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202603": {
            "61010001010101": 35,
        }}

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            result = matcher.match_section_od("61010001010101", "61999999999999", "20260415")

        assert result == "35"

    def test_neither_resolved(self, matcher, mock_repo):
        """两端都未解析成功"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {}
        mock_repo._query_next_sections_from_db.return_value = []

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202512"):
            result = matcher.match_section_od("61999999999999", "61999999999998", "20260415")

        assert result is None

    def test_result_cached(self, matcher, mock_repo):
        """相同 (enid, exid, dataDate) 不重复解析"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202603": {
            "61010001010101": 35,
            "61010002010101": 325,
        }}

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            r1 = matcher.match_section_od("61010001010101", "61010002010101", "20260415")
            r2 = matcher.match_section_od("61010001010101", "61010002010101", "20260415")

        assert r1 == r2 == "35|325"
        # station_map 只加载一次（版本缓存）
        assert len(matcher._station_map_cache) == 1


# ============================================================================
# enrich_records 测试
# ============================================================================


class TestEnrichRecords:
    """测试 enrich_records 方法"""

    def test_enrich_affected_od_records(self, matcher, mock_repo):
        """enrich AffectedOdPathRecord 列表"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202604": {
            "61010001010101": 35,
            "61010002010101": 325,
        }}

        records = [
            AffectedOdPathRecord(
                od_section_path_id=1,
                enid="61010001010101",
                exid="61010002010101",
                numpath="35|325",
                fixed_intervalpath="G000561005000910|G000561006000110",
                map_version="202604",
            ),
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            count = matcher.enrich_records(
                records, "enid", "exid",
                dataDate="20260415",
                dataDateGetter=lambda r: r.map_version + "01",
            )

        assert count == 1
        assert records[0].section_od == "35|325"

    def test_enrich_mid_trip_flow_stat_records(self, matcher, mock_repo):
        """enrich MidTripExitFlowStatRecord 列表"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202604": {
            "61010001010101": 35,
            "61010002010101": 325,
        }}

        records = [
            MidTripExitFlowStatRecord(
                od_enid="61010001010101",
                od_exid="61010002010101",
                vehicle_type="1",
            ),
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            count = matcher.enrich_records(
                records, "od_enid", "od_exid",
                dataDate="20260415",
            )

        assert count == 1
        assert records[0].section_od == "35|325"

    def test_enrich_detour_flow_stat_records(self, matcher, mock_repo):
        """enrich DetourFlowStatRecord 列表"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202604": {
            "61010001010101": 35,
            "61010002010101": 325,
        }}

        records = [
            DetourFlowStatRecord(
                od_enid="61010001010101",
                od_exid="61010002010101",
                record_enid="61010003010101",
                record_exid="61010002010101",
                record_type="same_origin_diff_dest",
                vehicle_type="1",
            ),
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            count = matcher.enrich_records(
                records, "od_enid", "od_exid",
                dataDate="20260415",
            )

        assert count == 1
        assert records[0].section_od == "35|325"

    def test_enrich_impact_summary_records(self, matcher, mock_repo):
        """enrich ImpactSummaryRecord 列表"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202604": {
            "61010001010101": 35,
            "61010002010101": 325,
        }}

        records = [
            ImpactSummaryRecord(
                enid="61010001010101",
                exid="61010002010101",
                vehicle_type="1",
            ),
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            count = matcher.enrich_records(
                records, "enid", "exid",
                dataDate="20260415",
            )

        assert count == 1
        assert records[0].section_od == "35|325"

    def test_enrich_partial_match(self, matcher, mock_repo):
        """部分记录无法匹配 section_od"""
        mock_repo.get_section_map.return_value = {}
        matcher._station_map_cache = {"202604": {
            "61010001010101": 35,
        }}
        mock_repo._query_next_sections_from_db.return_value = []

        records = [
            MidTripExitFlowStatRecord(
                od_enid="61010001010101",
                od_exid="61999999999999",
                vehicle_type="1",
            ),
            MidTripExitFlowStatRecord(
                od_enid="61999999999998",
                od_exid="61999999999997",
                vehicle_type="1",
            ),
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            count = matcher.enrich_records(
                records, "od_enid", "od_exid",
                dataDate="20260415",
            )

        # 只有第一条部分匹配（单端）
        assert count == 1
        assert records[0].section_od == "35"
        assert records[1].section_od is None


# ============================================================================
# rewrite_csv_with_section_od 测试
# ============================================================================


class TestRewriteCsvWithSectionOd:
    """测试 rewrite_csv_with_section_od 方法"""

    def test_rewrite_adds_section_od_column(self, matcher):
        """重写 CSV 追加 section_od 列"""
        records = [
            ImpactSummaryRecord(
                enid="61010001010101",
                exid="61010002010101",
                vehicle_type="1",
                section_od="35|325",
            ),
        ]
        base_columns = ["enid", "exid", "vehicle_type"]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            csv_path = f.name

        try:
            matcher.rewrite_csv_with_section_od(csv_path, records, base_columns)

            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert "section_od" in reader.fieldnames
            assert len(rows) == 1
            assert rows[0]["section_od"] == "35|325"
        finally:
            os.unlink(csv_path)

    def test_rewrite_empty_records(self, matcher):
        """空记录列表不写文件"""
        matcher.rewrite_csv_with_section_od("/tmp/nonexistent.csv", [], ["col1"])
        # 不报错即可


# ============================================================================
# _load_station_map 测试
# ============================================================================


class TestLoadStationMap:
    """测试 _load_station_map 方法"""

    def test_loads_and_caches_by_version(self, matcher, mock_repo):
        """按版本加载并缓存 station_map"""
        mock_repo.sql_runner.fetch_all.return_value = [
            {"entollstation": "61010001010101", "extollstation": "61010002010101", "section_number": 35},
            {"entollstation": "61010003010101", "extollstation": "", "section_number": 42},
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            sm1 = matcher._load_station_map("20260415")
            sm2 = matcher._load_station_map("20260415")

        assert sm1["61010001010101"] == 35
        assert sm1["61010002010101"] == 35
        assert sm1["61010003010101"] == 42
        assert sm1 is sm2  # 同一版本返回缓存
        assert mock_repo.sql_runner.fetch_all.call_count == 1  # 只查一次

    def test_first_station_wins_on_duplicate(self, matcher, mock_repo):
        """同一个站ID出现在多行时取第一条"""
        mock_repo.sql_runner.fetch_all.return_value = [
            {"entollstation": "61010001010101", "extollstation": "", "section_number": 35},
            {"entollstation": "61010001010101", "extollstation": "", "section_number": 99},
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202603"):
            sm = matcher._load_station_map("20260415")

        assert sm["61010001010101"] == 35


# ============================================================================
# _get_topo_version 测试
# ============================================================================


class TestGetTopoVersion:
    """测试 _get_topo_version 方法"""

    def test_returns_and_caches_version(self, matcher):
        """返回并缓存拓扑版本"""
        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202512"):
            v1 = matcher._get_topo_version("20260415")
            v2 = matcher._get_topo_version("20260415")

        assert v1 == "202512"
        assert v1 is v2
        assert "202604" in matcher._topo_version_cache


# ============================================================================
# deduplicate_name_words 测试
# ============================================================================


class TestDeduplicateNameWords:
    """测试 deduplicate_name_words 纯函数"""

    def test_empty_list(self):
        assert deduplicate_name_words([]) == ""

    def test_single_name(self):
        assert deduplicate_name_words(["漫川关主线-漫川关匝道"]) == "漫川关主线-漫川关匝道"

    def test_no_duplicates(self):
        """所有词组各出现一次，全部保留"""
        result = deduplicate_name_words(["漫川关主线-漫川关匝道", "山阳主线-商洛匝道"])
        assert result == "漫川关主线-漫川关匝道-山阳主线-商洛匝道"

    def test_remove_frequent_words(self):
        """出现>2次（≥3次）的词组被去除"""
        names = [
            "主线-漫川关匝道",
            "主线-山阳匝道",
            "主线-商洛匝道",
        ]
        result = deduplicate_name_words(names)
        # "主线" 出现3次 >2 → 去除
        assert "主线" not in result
        assert "漫川关匝道" in result
        assert "山阳匝道" in result
        assert "商洛匝道" in result

    def test_two_occurrences_kept(self):
        """出现2次的词组保留"""
        names = [
            "漫川关主线-漫川关匝道",
            "漫川关主线-山阳匝道",
        ]
        result = deduplicate_name_words(names)
        # "漫川关主线" 出现2次 ≤2 → 保留
        assert "漫川关主线" in result
        assert "漫川关匝道" in result
        assert "山阳匝道" in result

    def test_preserves_original_order(self):
        """保持原始出现顺序"""
        names = ["B-A", "C-D"]
        result = deduplicate_name_words(names)
        # 顺序应为 B, A, C, D
        assert result == "B-A-C-D"

    def test_dedup_preserves_first_occurrence(self):
        """去重时保留首次出现"""
        names = ["X-Y", "Z-X"]
        result = deduplicate_name_words(names)
        # X出现2次≤2保留，去重后只保留首次: X, Y, Z
        assert result == "X-Y-Z"

    def test_all_high_freq_fallback(self):
        """所有词组都是高频(>2次)时，回退为全词去重拼接"""
        names = ["A-A-A", "A-A-A"]
        # "A" 出现6次 >2，全部过滤后无剩余 → 回退
        result = deduplicate_name_words(names)
        assert result == "A"


# ============================================================================
# resolve_section_od_name 测试
# ============================================================================


class TestResolveSectionOdName:
    """测试 resolve_section_od_name 方法"""

    def test_basic_resolution(self, matcher, mock_repo):
        """解析 section_od 为区间名称"""
        mock_repo.sql_runner.fetch_all.return_value = [
            {"name": "漫川关主线-漫川关匝道"},
            {"name": "漫川关主线-山阳匝道"},
        ]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            result = matcher.resolve_section_od_name("24", "20260415")

        assert "漫川关主线" in result
        assert "漫川关匝道" in result

    def test_two_parts_joined(self, matcher, mock_repo):
        """两个 section_number 用 ' 到 ' 拼接"""

        def fetch_side_effect(sql):
            if "section_number = 24" in sql:
                return [{"name": "A-B"}]
            elif "section_number = 44" in sql:
                return [{"name": "C-D"}]
            return []

        mock_repo.sql_runner.fetch_all.side_effect = fetch_side_effect

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            result = matcher.resolve_section_od_name("24|44", "20260415")

        assert result == "A-B 到 C-D"

    def test_no_names_returns_number(self, matcher, mock_repo):
        """查不到 name 时返回 section_number 字符串"""
        mock_repo.sql_runner.fetch_all.return_value = []

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            result = matcher.resolve_section_od_name("99", "20260415")

        assert result == "99"

    def test_result_cached(self, matcher, mock_repo):
        """相同 (section_number, version) 结果缓存"""
        mock_repo.sql_runner.fetch_all.return_value = [{"name": "A-B"}]

        with patch("src.common.section_od_matcher.get_nearest_version", return_value="202604"):
            r1 = matcher.resolve_section_od_name("24", "20260415")
            r2 = matcher.resolve_section_od_name("24", "20260415")

        assert r1 == r2
        # 只查询一次 DB
        assert mock_repo.sql_runner.fetch_all.call_count == 1
