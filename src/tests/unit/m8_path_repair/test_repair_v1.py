"""
M8 路径修正 — V1 核心修正逻辑单元测试

使用 Mock 图进行测试，不依赖真实数据库。
"""

import pytest

from src.modules.m8_path_repair.core.normalizer import normalize_raw_path, NormalizedPath
from src.modules.m8_path_repair.core.repair import repair_path_v1, RepairResult


class MockGraph:
    """
    用于测试的简单有向图。

    拓扑:
    A -> B -> C -> D -> E -> F
    A -> X (错误边)
    """

    def __init__(self):
        self._nodes = {"A", "B", "C", "D", "E", "F", "X"}
        self._edges: dict[str, set[str]] = {
            "A": {"B", "X"},
            "B": {"C"},
            "C": {"D"},
            "D": {"E"},
            "E": {"F"},
        }
        # 最短路径模拟：返回直接的连通路径
        self._paths: dict[tuple[str, str], list[str]] = {
            ("A", "C"): ["A", "B", "C"],
            ("A", "D"): ["A", "B", "C", "D"],
            ("B", "D"): ["B", "C", "D"],
            ("B", "E"): ["B", "C", "D", "E"],
            ("C", "E"): ["C", "D", "E"],
            ("C", "F"): ["C", "D", "E", "F"],
            ("D", "F"): ["D", "E", "F"],
            ("A", "E"): ["A", "B", "C", "D", "E"],
            ("A", "F"): ["A", "B", "C", "D", "E", "F"],
            ("B", "F"): ["B", "C", "D", "E", "F"],
        }

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def has_direct_edge(self, from_node: str, to_node: str) -> bool:
        return to_node in self._edges.get(from_node, set())

    def shortest_path(self, start: str, end: str) -> list[str] | None:
        if start == end:
            return [start]
        return self._paths.get((start, end))


class TestRepairPathV1:
    def setup_method(self):
        self.graph = MockGraph()
        self.config = {"max_gap_search_window": 6}

    def _normalize(self, raw_path: str) -> NormalizedPath:
        return normalize_raw_path(raw_path, self.graph)

    # ----------------------------------------------------------
    # 正常路径
    # ----------------------------------------------------------

    def test_normal_path(self):
        """A|B|C|D → 应不修改"""
        normalized = self._normalize("A|B|C|D")
        result = repair_path_v1("A", "D", normalized, self.graph, self.config)
        assert result.corrected_nodes == ["A", "B", "C", "D"]
        assert result.inserted_nodes == []
        assert result.dropped_nodes == []
        assert result.status == "success"

    # ----------------------------------------------------------
    # 缺失节点（相邻不可达，用最短路径补全）
    # ----------------------------------------------------------

    def test_missing_nodes(self):
        """A|D → 应补全为 A|B|C|D"""
        normalized = self._normalize("A|D")
        result = repair_path_v1("A", "D", normalized, self.graph, self.config)
        assert result.corrected_nodes == ["A", "B", "C", "D"]
        assert result.status == "success"

    # ----------------------------------------------------------
    # 非法节点
    # ----------------------------------------------------------

    def test_invalid_node(self):
        """A|B|Y|C|D → Y 不在拓扑中，应过滤"""
        normalized = self._normalize("A|B|Y|C|D")
        result = repair_path_v1("A", "D", normalized, self.graph, self.config)
        assert "Y" in result.dropped_nodes
        assert "Y" not in result.corrected_nodes
        assert "A" in result.corrected_nodes
        assert "D" in result.corrected_nodes

    # ----------------------------------------------------------
    # 相邻重复
    # ----------------------------------------------------------

    def test_consecutive_duplicates(self):
        """A|B|B|C|D → 先去重为 A|B|C|D，再修正（不应修改）"""
        normalized = self._normalize("A|B|B|C|D")
        result = repair_path_v1("A", "D", normalized, self.graph, self.config)
        assert result.corrected_nodes == ["A", "B", "C", "D"]

    # ----------------------------------------------------------
    # 断裂路径（需要跳过中间节点）
    # ----------------------------------------------------------

    def test_broken_path_with_skip(self):
        """A|B|X|D → X 是错误节点，A->X 有边但 X->D 不可达"""
        normalized = self._normalize("A|B|X|D")
        result = repair_path_v1("A", "D", normalized, self.graph, self.config)
        # X 应该被跳过，路径应该是 A->B->C->D 或类似
        assert "A" in result.corrected_nodes
        assert "D" in result.corrected_nodes
        assert result.corrected_nodes[0] == "A"
        assert result.corrected_nodes[-1] == "D"

    # ----------------------------------------------------------
    # 起终点强制约束
    # ----------------------------------------------------------

    def test_start_end_constraint(self):
        """修正后路径必须以 start 开始，以 end 结束"""
        normalized = self._normalize("B|C|D|E")
        result = repair_path_v1("A", "F", normalized, self.graph, self.config)
        assert result.corrected_nodes[0] == "A"
        assert result.corrected_nodes[-1] == "F"

    # ----------------------------------------------------------
    # 空路径
    # ----------------------------------------------------------

    def test_empty_path(self):
        normalized = self._normalize("")
        result = repair_path_v1("A", "D", normalized, self.graph, self.config)
        assert result.corrected_nodes == ["A", "D"]
        assert result.status == "low_confidence"
