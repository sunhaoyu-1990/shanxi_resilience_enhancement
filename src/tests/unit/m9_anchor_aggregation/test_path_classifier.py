"""
M9 - path_classifier.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.path_classifier import (
    has_ordered_pair,
    extract_hit_units,
    classify_path_for_anchor_window,
    get_first_and_last_hit,
)
from src.modules.m9_anchor_aggregation.models import AnchorWindow


class TestHasOrderedPair:
    def test_normal_order(self):
        result = has_ordered_pair(["A", "B", "C", "D"], "A", "D")
        assert result is True

    def test_reverse_order(self):
        result = has_ordered_pair(["A", "B", "C", "D"], "D", "A")
        assert result is False

    def test_missing_start(self):
        result = has_ordered_pair(["A", "B", "C"], "X", "C")
        assert result is False

    def test_missing_end(self):
        result = has_ordered_pair(["A", "B", "C"], "A", "X")
        assert result is False

    def test_duplicate_units(self):
        """path 中有重复单元时，仍能正确判断顺序"""
        result = has_ordered_pair(["A", "B", "B", "C", "D"], "B", "D")
        assert result is True

        result = has_ordered_pair(["A", "B", "C", "B", "D"], "B", "D")
        assert result is True

    def test_same_unit_both_positions(self):
        """start == end 时返回 True（因为 min < max 不成立，但 min==max 时位置相同）"""
        result = has_ordered_pair(["A", "B", "C"], "B", "B")
        assert result is False


class TestExtractHitUnits:
    def test_basic_hit(self):
        path = ["A", "B", "C", "D"]
        construction = {"B", "C"}
        result = extract_hit_units(path, construction)
        assert result == ["B", "C"]

    def test_no_hit(self):
        path = ["A", "B", "C"]
        construction = {"X", "Y"}
        result = extract_hit_units(path, construction)
        assert result == []

    def test_sparse_hit(self):
        path = ["A", "B", "C", "D", "E"]
        construction = {"B", "E"}
        result = extract_hit_units(path, construction)
        assert result == ["B", "E"]


class TestClassifyPathForAnchorWindow:
    def test_pass_classification(self):
        window = AnchorWindow(
            construction_id="const_001",
            anchor_start="B",
            anchor_end="E",
            covered_units={"C", "D"},
        )
        path = ["A", "B", "C", "D", "E"]
        result = classify_path_for_anchor_window(path, window)
        assert result == "pass"

    def test_bypass_classification(self):
        window = AnchorWindow(
            construction_id="const_001",
            anchor_start="B",
            anchor_end="F",
            covered_units={"C", "D"},
        )
        path = ["A", "B", "X", "Y", "F"]
        result = classify_path_for_anchor_window(path, window)
        assert result == "bypass"

    def test_unrelated_path(self):
        window = AnchorWindow(
            construction_id="const_001",
            anchor_start="B",
            anchor_end="E",
            covered_units={"C", "D"},
        )
        path = ["A", "X", "Y", "Z"]
        result = classify_path_for_anchor_window(path, window)
        assert result is None


class TestGetFirstAndLastHit:
    def test_basic_hit(self):
        path = ["A", "B", "C", "D", "E"]
        construction = {"B", "C", "D"}
        first, last, hits = get_first_and_last_hit(path, construction)
        assert first == "B"
        assert last == "D"
        assert hits == ["B", "C", "D"]

    def test_no_hit(self):
        path = ["A", "B", "C"]
        construction = {"X", "Y"}
        first, last, hits = get_first_and_last_hit(path, construction)
        assert first is None
        assert last is None
        assert hits == []

    def test_single_hit(self):
        path = ["A", "B", "C"]
        construction = {"B"}
        first, last, hits = get_first_and_last_hit(path, construction)
        assert first == "B"
        assert last == "B"
        assert hits == ["B"]