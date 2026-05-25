"""
M8 路径修正 — 标准化模块单元测试
"""

import pytest

from src.modules.m8_path_repair.core.normalizer import (
    split_raw_path,
    remove_consecutive_duplicates,
    filter_invalid_nodes,
    normalize_raw_path,
)


class MockGraph:
    """用于测试的简单图"""

    def __init__(self, nodes: set[str]):
        self._nodes = nodes

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes


# ============================================================
# split_raw_path
# ============================================================


class TestSplitRawPath:
    def test_normal_path(self):
        result = split_raw_path("A|B|C|D")
        assert result == ["A", "B", "C", "D"]

    def test_empty_string(self):
        assert split_raw_path("") == []

    def test_whitespace_only(self):
        assert split_raw_path("   ") == []

    def test_with_spaces(self):
        result = split_raw_path(" A | B | C ")
        assert result == ["A", "B", "C"]

    def test_single_node(self):
        assert split_raw_path("A") == ["A"]

    def test_empty_segments(self):
        result = split_raw_path("A||B|C")
        assert result == ["A", "B", "C"]


# ============================================================
# remove_consecutive_duplicates
# ============================================================


class TestRemoveConsecutiveDuplicates:
    def test_no_duplicates(self):
        nodes, count = remove_consecutive_duplicates(["A", "B", "C"])
        assert nodes == ["A", "B", "C"]
        assert count == 0

    def test_consecutive_duplicates(self):
        nodes, count = remove_consecutive_duplicates(["A", "B", "B", "C"])
        assert nodes == ["A", "B", "C"]
        assert count == 1

    def test_multiple_duplicates(self):
        nodes, count = remove_consecutive_duplicates(["A", "A", "B", "B", "B", "C"])
        assert nodes == ["A", "B", "C"]
        assert count == 3

    def test_empty_list(self):
        nodes, count = remove_consecutive_duplicates([])
        assert nodes == []
        assert count == 0

    def test_preserves_global_duplicates(self):
        """全局重复不应被去除（可能代表掉头/折返）"""
        nodes, count = remove_consecutive_duplicates(["A", "B", "C", "B", "C", "D"])
        assert nodes == ["A", "B", "C", "B", "C", "D"]
        assert count == 0

    def test_single_element(self):
        nodes, count = remove_consecutive_duplicates(["A"])
        assert nodes == ["A"]
        assert count == 0


# ============================================================
# filter_invalid_nodes
# ============================================================


class TestFilterInvalidNodes:
    def test_all_valid(self):
        graph = MockGraph({"A", "B", "C"})
        valid, invalid = filter_invalid_nodes(["A", "B", "C"], graph)
        assert valid == ["A", "B", "C"]
        assert invalid == []

    def test_some_invalid(self):
        graph = MockGraph({"A", "B", "D"})
        valid, invalid = filter_invalid_nodes(["A", "X", "B", "Y", "D"], graph)
        assert valid == ["A", "B", "D"]
        assert invalid == ["X", "Y"]

    def test_all_invalid(self):
        graph = MockGraph({"A", "B"})
        valid, invalid = filter_invalid_nodes(["X", "Y", "Z"], graph)
        assert valid == []
        assert invalid == ["X", "Y", "Z"]

    def test_empty(self):
        graph = MockGraph({"A"})
        valid, invalid = filter_invalid_nodes([], graph)
        assert valid == []
        assert invalid == []


# ============================================================
# normalize_raw_path (integration)
# ============================================================


class TestNormalizeRawPath:
    def test_full_normalization(self):
        graph = MockGraph({"A", "B", "C", "D"})
        result = normalize_raw_path("A|B|B|C|D", graph)
        assert result.raw_nodes == ["A", "B", "B", "C", "D"]
        assert result.clean_nodes == ["A", "B", "C", "D"]
        assert result.invalid_nodes == []
        assert result.consecutive_duplicate_count == 1

    def test_with_invalid_nodes(self):
        graph = MockGraph({"A", "B", "C", "D"})
        result = normalize_raw_path("A|B|X|C|D", graph)
        assert result.clean_nodes == ["A", "B", "C", "D"]
        assert result.invalid_nodes == ["X"]

    def test_empty_path(self):
        graph = MockGraph({"A"})
        result = normalize_raw_path("", graph)
        assert result.raw_nodes == []
        assert result.clean_nodes == []

    def test_global_duplicates_preserved(self):
        """全局重复节点应保留"""
        graph = MockGraph({"A", "B", "C", "D"})
        result = normalize_raw_path("A|B|C|B|C|D", graph)
        assert result.clean_nodes == ["A", "B", "C", "B", "C", "D"]
        assert result.consecutive_duplicate_count == 0
