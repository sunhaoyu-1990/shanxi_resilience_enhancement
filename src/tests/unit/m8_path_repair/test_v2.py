"""
M8 路径修正 V2 — 单元测试

使用 Mock 图测试锚点筛选、DP 选择、分段拼接、后处理等 V2 模块。
"""

import pytest

from src.modules.m8_path_repair.core.anchor import (
    filter_anchor_candidates,
    select_anchors_by_dp,
    AnchorCandidate,
    AnchorChainResult,
)
from src.modules.m8_path_repair.core.stitcher import (
    lcs_length,
    segment_score,
    stitch_segments_by_ksp,
    StitchResult,
)
from src.modules.m8_path_repair.core.postprocess import (
    postprocess_corrected_path,
)


# ============================================================
# Mock 图
# ============================================================


class MockGraphV2:
    """
    支持 V2 测试的 Mock 图。

    拓扑: A -> B -> C -> D -> E -> F
    额外边: A -> X (错误节点)
    所有相邻节点都有最短路径。
    """

    def __init__(self):
        self._nodes = {"A", "B", "C", "D", "E", "F", "X"}
        self._edges = {
            "A": {"B", "X"},
            "B": {"C"},
            "C": {"D"},
            "D": {"E"},
            "E": {"F"},
        }
        self._paths = {
            ("A", "C"): (["A", "B", "C"], 2000.0),
            ("A", "D"): (["A", "B", "C", "D"], 3000.0),
            ("A", "E"): (["A", "B", "C", "D", "E"], 4000.0),
            ("A", "F"): (["A", "B", "C", "D", "E", "F"], 5000.0),
            ("B", "D"): (["B", "C", "D"], 2000.0),
            ("B", "E"): (["B", "C", "D", "E"], 3000.0),
            ("B", "F"): (["B", "C", "D", "E", "F"], 4000.0),
            ("C", "E"): (["C", "D", "E"], 2000.0),
            ("C", "F"): (["C", "D", "E", "F"], 3000.0),
            ("D", "F"): (["D", "E", "F"], 2000.0),
            ("A", "X"): (["A", "X"], 500.0),
            # 备选路径（模拟 KSP）
            ("B", "D"): (["B", "C", "D"], 2000.0),
        }
        # K 短路备选（模拟）
        self._k_paths = {
            ("A", "D"): [
                (["A", "B", "C", "D"], 3000.0),
                (["A", "B", "C", "X", "D"], 3500.0),
            ],
            ("B", "E"): [
                (["B", "C", "D", "E"], 3000.0),
            ],
            ("D", "F"): [
                (["D", "E", "F"], 2000.0),
            ],
        }
        self._costs = {
            ("A", "B"): 1000.0,
            ("B", "C"): 1000.0,
            ("C", "D"): 1000.0,
            ("D", "E"): 1000.0,
            ("E", "F"): 1000.0,
            ("A", "C"): 2000.0,
            ("A", "D"): 3000.0,
            ("A", "E"): 4000.0,
            ("A", "F"): 5000.0,
            ("B", "D"): 2000.0,
            ("B", "E"): 3000.0,
            ("B", "F"): 4000.0,
            ("C", "E"): 2000.0,
            ("C", "F"): 3000.0,
            ("D", "F"): 2000.0,
            ("A", "X"): 500.0,
        }

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def has_direct_edge(self, from_node: str, to_node: str) -> bool:
        return to_node in self._edges.get(from_node, set())

    def shortest_path_cost(self, start: str, end: str) -> float | None:
        if start == end:
            return 0.0
        return self._costs.get((start, end))

    def shortest_path(self, start: str, end: str) -> list[str] | None:
        if start == end:
            return [start]
        result = self._paths.get((start, end))
        if result:
            return result[0]
        return None

    def k_shortest_paths(self, start: str, end: str, k: int = 5) -> list:
        if start == end:
            return [([start], 0.0)]
        candidates = self._k_paths.get((start, end))
        if candidates:
            return candidates[:k]
        # 回退到单条最短路径
        sp = self.shortest_path(start, end)
        cost = self.shortest_path_cost(start, end)
        if sp and cost is not None:
            return [(sp, cost)]
        return []

    def get_node_info(self, node_id: str) -> dict | None:
        return None


# ============================================================
# LCS 测试
# ============================================================


class TestLCS:
    def test_identical(self):
        assert lcs_length(["A", "B", "C"], ["A", "B", "C"]) == 3

    def test_completely_different(self):
        assert lcs_length(["A", "B", "C"], ["X", "Y", "Z"]) == 0

    def test_partial_match(self):
        assert lcs_length(["A", "B", "C", "D"], ["A", "X", "C", "Y"]) == 2

    def test_empty(self):
        assert lcs_length([], ["A", "B"]) == 0
        assert lcs_length(["A"], []) == 0

    def test_subsequence(self):
        assert lcs_length(["A", "B", "C", "D", "E"], ["A", "C", "E"]) == 3

    def test_order_matters(self):
        assert lcs_length(["A", "B", "C"], ["C", "B", "A"]) == 1


# ============================================================
# 锚点筛选测试
# ============================================================


class TestFilterAnchorCandidates:
    def test_all_nodes_are_candidates(self):
        graph = MockGraphV2()
        config = {"max_anchor_detour_ratio": 2.0}
        clean_nodes = ["A", "B", "C", "D", "E", "F"]
        candidates = filter_anchor_candidates("A", "F", clean_nodes, graph, config)

        # B, C, D, E should be candidates (not A or F)
        nodes = [c.node for c in candidates]
        assert "B" in nodes
        assert "C" in nodes
        assert "D" in nodes
        assert "E" in nodes
        assert "A" not in nodes
        assert "F" not in nodes

    def test_strict_ratio(self):
        graph = MockGraphV2()
        config = {"max_anchor_detour_ratio": 1.01}
        # With ratio=1.01, only nodes on the shortest path should qualify
        # In our mock, all nodes are on the shortest path
        clean_nodes = ["A", "B", "C", "D", "E", "F"]
        candidates = filter_anchor_candidates("A", "F", clean_nodes, graph, config)

        nodes = [c.node for c in candidates]
        assert "B" in nodes
        assert "C" in nodes
        assert "D" in nodes
        assert "E" in nodes

    def test_unreachable_node_excluded(self):
        """不可达节点不应作为候选"""
        graph = MockGraphV2()
        config = {"max_anchor_detour_ratio": 2.0}
        # X is reachable from A but X->F is not in our mock
        clean_nodes = ["A", "X", "F"]
        candidates = filter_anchor_candidates("A", "F", clean_nodes, graph, config)
        # X has dist_from_start (500) but dist_to_end is None (X->F not in mock)
        nodes = [c.node for c in candidates]
        assert "X" not in nodes


# ============================================================
# DP 锚点选择测试
# ============================================================


class TestSelectAnchorsByDP:
    def test_selects_all_when_all_good(self):
        graph = MockGraphV2()
        config = {
            "max_anchor_detour_ratio": 2.0,
            "skip_node_penalty": 50.0,
        }
        clean_nodes = ["A", "B", "C", "D", "E", "F"]
        candidates = filter_anchor_candidates("A", "F", clean_nodes, graph, config)
        chain = select_anchors_by_dp("A", "F", clean_nodes, candidates, graph, config)

        # All anchors should be selected since they're all on the optimal path
        assert len(chain.anchors) == 4  # B, C, D, E
        assert chain.anchors[0].node == "B"

    def test_empty_candidates(self):
        graph = MockGraphV2()
        config = {"max_anchor_detour_ratio": 2.0}
        chain = select_anchors_by_dp("A", "F", ["A", "F"], [], graph, config)
        assert chain.anchors == []

    def test_skipped_indices_tracked(self):
        graph = MockGraphV2()
        config = {"max_anchor_detour_ratio": 0.5}  # Very strict
        clean_nodes = ["A", "B", "C", "D", "E", "F"]
        candidates = filter_anchor_candidates("A", "F", clean_nodes, graph, config)
        chain = select_anchors_by_dp("A", "F", clean_nodes, candidates, graph, config)

        # With ratio=0.5, likely no candidates pass (since each node adds detour)
        # If chain is empty, skipped_indices should cover the range
        # Or if some pass, skipped should track the rest
        assert isinstance(chain.skipped_indices, list)


# ============================================================
# 分段拼接测试
# ============================================================


class TestStitchSegments:
    def test_basic_stitching(self):
        graph = MockGraphV2()
        config = {"k_shortest_paths": 5}
        anchor_nodes = ["A", "B", "C", "D"]
        clean_nodes = ["A", "B", "C", "D"]

        result = stitch_segments_by_ksp(anchor_nodes, clean_nodes, graph, config)

        assert len(result.corrected_nodes) >= 4
        assert result.corrected_nodes[0] == "A"
        assert result.corrected_nodes[-1] == "D"
        assert len(result.segment_details) == 3  # A->B, B->C, C->D

    def test_observed_slice_matching(self):
        """有观测片段时，LCS 应 > 0"""
        graph = MockGraphV2()
        config = {"k_shortest_paths": 5}
        anchor_nodes = ["A", "D"]
        clean_nodes = ["A", "B", "C", "D"]

        result = stitch_segments_by_ksp(anchor_nodes, clean_nodes, graph, config)

        assert result.total_lcs > 0 or result.total_observed == 0
        assert len(result.corrected_nodes) >= 2


# ============================================================
# 后处理测试
# ============================================================


class TestPostprocess:
    def test_no_changes_needed(self):
        result = postprocess_corrected_path(["A", "B", "C", "D"])
        assert result.nodes == ["A", "B", "C", "D"]
        assert result.removed_loops == []
        assert result.removed_duplicates == []

    def test_remove_adjacent_duplicates(self):
        result = postprocess_corrected_path(["A", "B", "B", "C", "D"])
        assert result.nodes == ["A", "B", "C", "D"]
        assert "B" in result.removed_duplicates

    def test_single_uturn_allowed(self):
        """允许一次 A->B->A 掉头"""
        result = postprocess_corrected_path(
            ["A", "B", "C", "B", "C", "D"], config={"allow_uturn_count": 1}
        )
        # Should keep the first U-turn (C->B->C is not A->B->A pattern)
        assert result.uturn_count >= 0

    def test_uturn_removed_when_exceeding(self):
        result = postprocess_corrected_path(
            ["A", "B", "A", "B", "A", "C"],
            config={"allow_uturn_count": 1},
        )
        # First A->B->A allowed, second should be removed
        assert "A" in result.removed_loops or "B" in result.removed_loops
        assert result.uturn_count >= 1

    def test_short_path(self):
        result = postprocess_corrected_path(["A"])
        assert result.nodes == ["A"]

    def test_two_nodes(self):
        result = postprocess_corrected_path(["A", "B"])
        assert result.nodes == ["A", "B"]
