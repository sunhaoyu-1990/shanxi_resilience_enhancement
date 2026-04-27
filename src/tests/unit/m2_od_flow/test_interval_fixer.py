"""
interval_fixer 的单元测试 — 含 intervaltimegroup 同步修复

测试覆盖：
1. _interpolate_times — 等间隔时间插值
2. fix_intervalgroup — 四种修复情况 + 时间同步
3. fix_intervalgroup_batch — 批量修复含 intervaltimegroup
4. IntervalFixResult — fixed_timegroup 字段
5. split_intervalgroup / join_intervalgroup / reverse_section_id
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.interval_fixer import (
    _interpolate_times,
    fix_intervalgroup,
    fix_intervalgroup_batch,
    split_intervalgroup,
    join_intervalgroup,
    reverse_section_id,
    IntervalFixResult,
    TopologyChecker,
)


# ============================================================================
# _interpolate_times
# ============================================================================

class TestInterpolateTimes:
    """等间隔时间插值测试"""

    def test_interpolate_two_points(self):
        """2个点在 14:00~14:30 之间等间隔"""
        result = _interpolate_times("2026-03-15 14:00:00", "2026-03-15 14:30:00", 2)
        assert len(result) == 2
        assert result[0] == "2026-03-15 14:10:00"
        assert result[1] == "2026-03-15 14:20:00"

    def test_interpolate_one_point(self):
        """1个点在两端正中间"""
        result = _interpolate_times("2026-03-15 10:00:00", "2026-03-15 10:20:00", 1)
        assert len(result) == 1
        assert result[0] == "2026-03-15 10:10:00"

    def test_interpolate_zero_count(self):
        """0个点返回空列表"""
        result = _interpolate_times("2026-03-15 10:00:00", "2026-03-15 10:30:00", 0)
        assert result == []

    def test_interpolate_negative_count(self):
        """负数返回空列表"""
        result = _interpolate_times("2026-03-15 10:00:00", "2026-03-15 10:30:00", -1)
        assert result == []

    def test_interpolate_empty_left(self):
        """左边界为空返回空列表"""
        result = _interpolate_times("", "2026-03-15 10:30:00", 2)
        assert result == []

    def test_interpolate_empty_right(self):
        """右边界为空返回空列表"""
        result = _interpolate_times("2026-03-15 10:00:00", "", 2)
        assert result == []

    def test_interpolate_cross_midnight(self):
        """跨天插值"""
        result = _interpolate_times("2026-03-15 23:50:00", "2026-03-16 00:10:00", 1)
        assert len(result) == 1
        assert result[0] == "2026-03-16 00:00:00"

    def test_interpolate_three_points(self):
        """3个点等间隔分布"""
        result = _interpolate_times("2026-03-15 00:00:00", "2026-03-15 01:00:00", 3)
        assert len(result) == 3
        assert result[0] == "2026-03-15 00:15:00"
        assert result[1] == "2026-03-15 00:30:00"
        assert result[2] == "2026-03-15 00:45:00"

    def test_interpolate_invalid_time_format(self):
        """无效时间格式 — 回退到左边界"""
        result = _interpolate_times("2026-03-15 10:00:00", "invalid", 2)
        assert len(result) == 2
        assert all(t == "2026-03-15 10:00:00" for t in result)


# ============================================================================
# fix_intervalgroup — without intervaltimegroup (backward compat)
# ============================================================================

class TestFixIntervalgroupBasic:
    """不传 intervaltimegroup 时的基本修复（向后兼容）"""

    def _make_topo(self, adj_map: dict[str, set[str]]) -> MagicMock:
        """Build a mock TopologyChecker from adjacency map"""
        topo = MagicMock(spec=TopologyChecker)
        topo.topo_check.side_effect = lambda a, b: b in adj_map.get(a, set())
        topo.shortest_path.return_value = None
        return topo

    def test_no_fix_needed(self):
        """完整的相邻序列无需修复"""
        topo = self._make_topo({"A": {"B"}, "B": {"C"}, "C": {"D"}})
        result = fix_intervalgroup("A|B|C|D", topo)
        assert result.fixed == "A|B|C|D"
        assert not result.has_changes()

    def test_short_sequence_unchanged(self):
        """2个及以下单元不修复"""
        topo = self._make_topo({})
        result = fix_intervalgroup("A|B", topo)
        assert result.fixed == "A|B"

    def test_empty_input(self):
        """空输入返回空"""
        topo = self._make_topo({})
        result = fix_intervalgroup("", topo)
        assert result.fixed == ""

    def test_no_timegroup_backward_compat(self):
        """不传 intervaltimegroup 时 fixed_timegroup 为空"""
        topo = self._make_topo({"A": {"B"}, "B": {"C"}})
        result = fix_intervalgroup("A|B|C", topo)
        assert result.fixed_timegroup == ""


# ============================================================================
# fix_intervalgroup — with intervaltimegroup
# ============================================================================

class TestFixIntervalgroupWithTime:
    """传入 intervaltimegroup 时的时间同步修复"""

    def _make_topo(self, adj_map: dict[str, set[str]], paths: dict = None) -> MagicMock:
        """Build mock TopologyChecker with adj_map and optional paths"""
        topo = MagicMock(spec=TopologyChecker)
        topo.topo_check.side_effect = lambda a, b: b in adj_map.get(a, set())
        if paths:
            topo.shortest_path.side_effect = lambda a, b: paths.get((a, b))
        else:
            topo.shortest_path.return_value = None
        return topo

    def test_no_fix_time_preserved(self):
        """完整序列 — 时间直接对应，不做修改"""
        topo = self._make_topo({"A": {"B"}, "B": {"C"}})
        result = fix_intervalgroup(
            "A|B|C",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 10:10:00|2026-03-15 10:20:00",
        )
        assert result.fixed == "A|B|C"
        assert result.fixed_timegroup == "2026-03-15 10:00:00|2026-03-15 10:10:00|2026-03-15 10:20:00"

    def test_path_fill_time_interpolated(self):
        """情况2: path_fill — 中间节点时间等间隔插值"""
        adj_map = {"A": {"X"}, "X": {"B"}, "B": {"C"}}
        # A→B broken, but shortest_path returns [A, X, B]
        paths = {("A", "B"): ["A", "X", "B"]}
        topo = self._make_topo(adj_map, paths)

        result = fix_intervalgroup(
            "A|B|C",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 10:20:00|2026-03-15 10:30:00",
        )
        assert "X" in result.fixed
        # fixed_timegroup should have entries matching fixed sections
        times = split_intervalgroup(result.fixed_timegroup)
        sections = split_intervalgroup(result.fixed)
        assert len(times) == len(sections)
        # X is between A(10:00) and B(10:20), with 2 new nodes (X, B)
        # interpolated at 1/3 and 2/3: 10:06:40 and 10:13:20
        x_idx = sections.index("X")
        assert times[x_idx] == "2026-03-15 10:06:40"

    def test_reverse_fix_time_preserved(self):
        """情况3a: reverse_fix — 时间沿用原始节点的"""
        # A→G007 broken, A→G007_rev(upward) OK, G007_rev→C OK
        # G007061003000220(downward) → reverse → G007061003000210(upward)
        B = "G007061003000220"  # downward
        B_rev = "G007061003000210"  # upward (reverse of B)
        adj_map = {"A": {B_rev}, B_rev: {"C"}}
        topo = self._make_topo(adj_map)

        result = fix_intervalgroup(
            f"A|{B}|C",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 10:10:00|2026-03-15 10:20:00",
        )
        assert B_rev in result.fixed
        # B_rev should keep B's original time 10:10
        times = split_intervalgroup(result.fixed_timegroup)
        sections = split_intervalgroup(result.fixed)
        b_rev_idx = sections.index(B_rev)
        assert times[b_rev_idx] == "2026-03-15 10:10:00"

    def test_duplicate_section_first_time_kept(self):
        """重复section只保留首次出现的时间"""
        topo = self._make_topo({"A": {"B"}, "B": {"C"}, "C": {"A"}})
        result = fix_intervalgroup(
            "A|B|C|A",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 10:10:00|2026-03-15 10:20:00|2026-03-15 10:30:00",
        )
        sections = split_intervalgroup(result.fixed)
        # A appears twice in input, only once in output
        assert sections.count("A") == 1
        times = split_intervalgroup(result.fixed_timegroup)
        # A's time should be the first occurrence 10:00:00
        a_idx = sections.index("A")
        assert times[a_idx] == "2026-03-15 10:00:00"

    def test_times_shorter_than_sections_padded(self):
        """times 比 sections 短时，缺失时间用空字符串填充，split后可能少于sections数"""
        topo = self._make_topo({"A": {"B"}, "B": {"C"}})
        result = fix_intervalgroup(
            "A|B|C",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 10:10:00",
        )
        # Should not crash — empty time slots are padded but may be stripped by split
        times = split_intervalgroup(result.fixed_timegroup)
        sections = split_intervalgroup(result.fixed)
        # At minimum, the existing times should be preserved
        assert len(times) >= 2

    def test_empty_timegroup(self):
        """空 intervaltimegroup — fixed_timegroup 为空"""
        topo = self._make_topo({"A": {"B"}, "B": {"C"}})
        result = fix_intervalgroup("A|B|C", topo, intervaltimegroup="")
        assert result.fixed_timegroup == ""

    def test_fixed_timegroup_length_matches_fixed(self):
        """修复后 fixed_timegroup 和 fixed 长度必须一致"""
        adj_map = {"A": {"X"}, "X": {"Y"}, "Y": {"B"}, "B": {"C"}}
        paths = {("A", "B"): ["A", "X", "Y", "B"]}
        topo = self._make_topo(adj_map, paths)

        result = fix_intervalgroup(
            "A|B|C",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 10:30:00|2026-03-15 10:40:00",
        )
        sections = split_intervalgroup(result.fixed)
        times = split_intervalgroup(result.fixed_timegroup)
        assert len(sections) == len(times), (
            f"Mismatch: {len(sections)} sections vs {len(times)} times"
        )

    def test_interpolated_times_within_bounds(self):
        """插值时间必须在左右边界之间"""
        adj_map = {"A": {"X"}, "X": {"B"}, "B": {"C"}}
        paths = {("A", "B"): ["A", "X", "B"]}
        topo = self._make_topo(adj_map, paths)

        result = fix_intervalgroup(
            "A|B|C",
            topo,
            intervaltimegroup="2026-03-15 10:00:00|2026-03-15 11:00:00|2026-03-15 11:10:00",
        )
        times = split_intervalgroup(result.fixed_timegroup)
        # X's time should be between 10:00 and 11:00
        sections = split_intervalgroup(result.fixed)
        if "X" in sections:
            x_idx = sections.index("X")
            x_time = times[x_idx]
            assert "10:" in x_time  # Should be around 10:30


# ============================================================================
# fix_intervalgroup_batch
# ============================================================================

class TestFixIntervalgroupBatch:
    """批量修复测试"""

    def _make_topo(self) -> MagicMock:
        topo = MagicMock(spec=TopologyChecker)
        topo.topo_check.return_value = True
        topo.shortest_path.return_value = None
        return topo

    def test_batch_passes_intervaltimegroup(self):
        """批量修复自动传递 intervaltimegroup"""
        topo = self._make_topo()
        records = [
            {"tradeid": "t1", "intervalgroup": "A|B|C", "intervaltimegroup": "2026-03-15 10:00:00|2026-03-15 10:10:00|2026-03-15 10:20:00"},
            {"tradeid": "t2", "intervalgroup": "X|Y|Z", "intervaltimegroup": "2026-03-15 11:00:00|2026-03-15 11:10:00|2026-03-15 11:20:00"},
        ]
        results = fix_intervalgroup_batch(records, topology=topo)
        assert len(results) == 2
        assert results[0].tradeid == "t1"
        assert results[0].fixed_timegroup != ""
        assert results[1].fixed_timegroup != ""

    def test_batch_missing_timegroup_field(self):
        """记录中无 intervaltimegroup 字段 — fixed_timegroup 为空"""
        topo = self._make_topo()
        records = [
            {"tradeid": "t1", "intervalgroup": "A|B|C"},
        ]
        results = fix_intervalgroup_batch(records, topology=topo)
        assert results[0].fixed_timegroup == ""

    def test_batch_empty_records(self):
        """空记录列表"""
        topo = self._make_topo()
        results = fix_intervalgroup_batch([], topology=topo)
        assert results == []


# ============================================================================
# IntervalFixResult
# ============================================================================

class TestIntervalFixResult:
    """IntervalFixResult 数据结构测试"""

    def test_fixed_timegroup_default_empty(self):
        """默认 fixed_timegroup 为空"""
        result = IntervalFixResult(tradeid="t1", original="A|B", fixed="A|B")
        assert result.fixed_timegroup == ""

    def test_to_dict_includes_timegroup_when_present(self):
        """to_dict 包含 fixed_timegroup（当非空时）"""
        result = IntervalFixResult(
            tradeid="t1", original="A|B", fixed="A|B",
            fixed_timegroup="2026-03-15 10:00:00|2026-03-15 10:10:00",
        )
        d = result.to_dict()
        assert "fixed_timegroup" in d
        assert d["fixed_timegroup"] == "2026-03-15 10:00:00|2026-03-15 10:10:00"

    def test_to_dict_omits_timegroup_when_empty(self):
        """to_dict 不含 fixed_timegroup（当为空时）"""
        result = IntervalFixResult(tradeid="t1", original="A|B", fixed="A|B")
        d = result.to_dict()
        assert "fixed_timegroup" not in d


# ============================================================================
# Utility functions
# ============================================================================

class TestSplitJoinIntervalgroup:
    """split/join 工具函数测试"""

    def test_split_normal(self):
        assert split_intervalgroup("A|B|C") == ["A", "B", "C"]

    def test_split_empty(self):
        assert split_intervalgroup("") == []

    def test_split_whitespace(self):
        assert split_intervalgroup("  ") == []

    def test_split_with_spaces(self):
        assert split_intervalgroup(" A | B | C ") == ["A", "B", "C"]

    def test_join_normal(self):
        assert join_intervalgroup(["A", "B", "C"]) == "A|B|C"

    def test_roundtrip(self):
        original = "X1|X2|X3"
        assert join_intervalgroup(split_intervalgroup(original)) == original


class TestReverseSectionId:
    """reverse_section_id 测试"""

    def test_upward_to_downward(self):
        assert reverse_section_id("G007061003000210") == "G007061003000220"

    def test_downward_to_upward(self):
        assert reverse_section_id("G007061003000220") == "G007061003000210"

    def test_non_directional_returns_none(self):
        assert reverse_section_id("G007061003000230") is None

    def test_too_short_returns_none(self):
        assert reverse_section_id("X") is None

    def test_none_returns_none(self):
        assert reverse_section_id(None) is None
