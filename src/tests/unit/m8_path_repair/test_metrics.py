"""
M8 路径修正 — 折返指标与质量评分单元测试
"""

import pytest
import math

from src.modules.m8_path_repair.core.metrics import (
    calc_repeated_node_count,
    calc_reverse_edge_count,
    calc_backward_progress,
    calc_u_turn_count,
    calc_detour_ratio,
    calc_backtrack_index,
    calc_repair_confidence,
    get_repair_status,
    _bearing,
    _angle_diff,
)


class MockGraph:
    """用于测试的简单图，返回固定的最短路径成本"""

    def __init__(self, cost_map: dict[tuple[str, str], float]):
        self._cost_map = cost_map

    def shortest_path_cost(self, start: str, end: str) -> float | None:
        if start == end:
            return 0.0
        return self._cost_map.get((start, end))


# ============================================================
# calc_repeated_node_count
# ============================================================


class TestRepeatedNodeCount:
    def test_no_repeats(self):
        assert calc_repeated_node_count(["A", "B", "C", "D"]) == 0

    def test_one_repeat(self):
        assert calc_repeated_node_count(["A", "B", "C", "B", "D"]) == 1

    def test_multiple_repeats(self):
        assert calc_repeated_node_count(["A", "B", "A", "B", "C"]) == 2

    def test_all_same(self):
        assert calc_repeated_node_count(["A", "A", "A"]) == 1

    def test_empty(self):
        assert calc_repeated_node_count([]) == 0


# ============================================================
# calc_reverse_edge_count
# ============================================================


class TestReverseEdgeCount:
    def test_no_reverse(self):
        assert calc_reverse_edge_count(["A", "B", "C", "D"]) == 0

    def test_one_reverse(self):
        assert calc_reverse_edge_count(["A", "B", "C", "B", "D"]) == 1

    def test_multiple_reverses(self):
        # A->B, B->A(reverse!), A->B, B->A(reverse!), A->B, B->A doesn't exist yet
        # Edges: (A,B), (B,A), (A,B), (B,A), (A,B)
        # Reverse counts: at i=1: (B,A) vs seen{(A,B)} → 1
        #                  at i=2: (A,B) vs seen{(A,B),(B,A)} → 1 (B,A was seen)
        #                  at i=3: (B,A) vs seen{(A,B),(B,A)} → 1 (A,B was seen)
        # Total: 3
        assert calc_reverse_edge_count(["A", "B", "A", "B", "A"]) == 3

    def test_short_path(self):
        assert calc_reverse_edge_count(["A", "B"]) == 0


# ============================================================
# calc_backward_progress
# ============================================================


class TestBackwardProgress:
    def test_no_backward(self):
        # A -> B -> C -> D, each closer to D
        graph = MockGraph({
            ("A", "D"): 3000.0,
            ("B", "D"): 2000.0,
            ("C", "D"): 1000.0,
            ("D", "D"): 0.0,
        })
        result = calc_backward_progress(["A", "B", "C", "D"], "D", graph)
        assert result["backward_progress_count"] == 0
        assert result["backward_progress_distance"] == 0.0

    def test_one_backward(self):
        # A -> B -> X -> D, X is farther from D than B
        graph = MockGraph({
            ("A", "D"): 3000.0,
            ("B", "D"): 2000.0,
            ("X", "D"): 2500.0,  # X is farther than B
            ("D", "D"): 0.0,
        })
        result = calc_backward_progress(["A", "B", "X", "D"], "D", graph, threshold_m=300.0)
        assert result["backward_progress_count"] == 1
        assert result["backward_progress_distance"] == 500.0


# ============================================================
# _bearing and _angle_diff
# ============================================================


class TestBearing:
    def test_north(self):
        # 从 (0, 0) 到 (0, 1) 应该是接近 0°（北）
        b = _bearing(0, 0, 0, 1)
        assert abs(b - 0) < 1 or abs(b - 360) < 1

    def test_east(self):
        # 从 (0, 0) 到 (1, 0) 应该是接近 90°（东）
        b = _bearing(0, 0, 1, 0)
        assert abs(b - 90) < 1

    def test_south(self):
        # 从 (0, 0) 到 (0, -1) 应该是接近 180°（南）
        b = _bearing(0, 0, 0, -1)
        assert abs(b - 180) < 1

    def test_west(self):
        # 从 (0, 0) 到 (-1, 0) 应该是接近 270°（西）
        b = _bearing(0, 0, -1, 0)
        assert abs(b - 270) < 1


class TestAngleDiff:
    def test_same_angle(self):
        assert _angle_diff(45, 45) == 0

    def test_opposite(self):
        assert _angle_diff(0, 180) == 180

    def test_small_diff(self):
        assert _angle_diff(0, 10) == 10

    def test_wrap_around(self):
        assert _angle_diff(350, 10) == 20


# ============================================================
# calc_u_turn_count
# ============================================================


class TestUTurnCount:
    def test_straight_line(self):
        points = [
            {"node_id": "A", "lon": 0, "lat": 0},
            {"node_id": "B", "lon": 1, "lat": 0},
            {"node_id": "C", "lon": 2, "lat": 0},
        ]
        assert calc_u_turn_count(points) == 0

    def test_u_turn(self):
        # A -> B (向东) -> C (向西，掉头)
        points = [
            {"node_id": "A", "lon": 0, "lat": 0},
            {"node_id": "B", "lon": 1, "lat": 0},
            {"node_id": "C", "lon": 0, "lat": 0},  # 回到原点，180° 掉头
        ]
        assert calc_u_turn_count(points) == 1

    def test_insufficient_points(self):
        points = [
            {"node_id": "A", "lon": 0, "lat": 0},
            {"node_id": "B", "lon": 1, "lat": 0},
        ]
        assert calc_u_turn_count(points) == 0

    def test_missing_coords(self):
        points = [
            {"node_id": "A", "lon": None, "lat": None},
            {"node_id": "B", "lon": 1, "lat": 0},
            {"node_id": "C", "lon": 2, "lat": 0},
        ]
        assert calc_u_turn_count(points) == 0


# ============================================================
# calc_detour_ratio
# ============================================================


class TestDetourRatio:
    def test_direct_path(self):
        # 修正路径长度 = 1000, 最短路 = 1000, 比值 = 1.0
        graph = MockGraph({
            ("A", "B"): 1000.0,
        })
        ratio = calc_detour_ratio(["A", "B"], "A", "B", graph)
        assert ratio == 1.0

    def test_detour_path(self):
        # 修正路径 A->B->C = 1500, 最短路 A->C = 1000, 比值 = 1.5
        graph = MockGraph({
            ("A", "B"): 750.0,
            ("B", "C"): 750.0,
            ("A", "C"): 1000.0,
        })
        ratio = calc_detour_ratio(["A", "B", "C"], "A", "C", graph)
        assert ratio == 1.5


# ============================================================
# calc_backtrack_index
# ============================================================


class TestBacktrackIndex:
    def test_no_issues(self):
        metrics = {
            "reverse_edge_count": 0,
            "backward_progress_count": 0,
            "repeated_node_count": 0,
            "u_turn_count": 0,
            "detour_ratio": 1.0,
        }
        assert calc_backtrack_index(metrics) == 0.0

    def test_some_issues(self):
        metrics = {
            "reverse_edge_count": 1,
            "backward_progress_count": 1,
            "repeated_node_count": 1,
            "u_turn_count": 1,
            "detour_ratio": 1.5,
        }
        bti = calc_backtrack_index(metrics)
        # 15 + 8.33 + 6.67 + 7.5 + 3 = ~40.5
        assert 30 <= bti <= 50

    def test_max_capped(self):
        metrics = {
            "reverse_edge_count": 10,
            "backward_progress_count": 10,
            "repeated_node_count": 10,
            "u_turn_count": 10,
            "detour_ratio": 5.0,
        }
        bti = calc_backtrack_index(metrics)
        assert bti <= 100.0


# ============================================================
# calc_repair_confidence
# ============================================================


class TestRepairConfidence:
    def test_perfect(self):
        conf = calc_repair_confidence(
            raw_match_ratio=1.0,
            dropped_node_count=0,
            inserted_node_count=0,
            raw_node_count=4,
            detour_ratio=1.0,
            backtrack_index=0.0,
        )
        assert conf == 100.0

    def test_with_drops(self):
        conf = calc_repair_confidence(
            raw_match_ratio=0.75,
            dropped_node_count=1,
            inserted_node_count=0,
            raw_node_count=4,
            detour_ratio=1.0,
            backtrack_index=0.0,
        )
        # 100 - 0.25*25 = 93.75
        assert 90 <= conf <= 95

    def test_with_high_detour(self):
        conf = calc_repair_confidence(
            raw_match_ratio=1.0,
            dropped_node_count=0,
            inserted_node_count=0,
            raw_node_count=4,
            detour_ratio=2.0,
            backtrack_index=0.0,
        )
        # 100 - 0.8*30 = 76
        assert 70 <= conf <= 80

    def test_with_high_backtrack(self):
        conf = calc_repair_confidence(
            raw_match_ratio=1.0,
            dropped_node_count=0,
            inserted_node_count=0,
            raw_node_count=4,
            detour_ratio=1.0,
            backtrack_index=60.0,
        )
        # 100 - 30 = 70
        assert 65 <= conf <= 75


# ============================================================
# get_repair_status
# ============================================================


class TestRepairStatus:
    def test_high(self):
        assert get_repair_status(90, 5) == "HIGH_CONFIDENCE"

    def test_medium(self):
        assert get_repair_status(75, 25) == "MEDIUM_CONFIDENCE"

    def test_low(self):
        assert get_repair_status(50, 45) == "LOW_CONFIDENCE"

    def test_review(self):
        assert get_repair_status(30, 60) == "NEED_MANUAL_REVIEW"

    def test_boundary_high(self):
        assert get_repair_status(85, 10) == "HIGH_CONFIDENCE"

    def test_boundary_medium(self):
        assert get_repair_status(65, 30) == "MEDIUM_CONFIDENCE"
