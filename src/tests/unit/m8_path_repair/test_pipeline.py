"""
M8 路径修正 — 端到端集成测试

使用 Mock 图模拟完整修正流程，不依赖真实数据库。
"""

import pytest

from src.modules.m8_path_repair.core.graph import RoadGraph
from src.modules.m8_path_repair.core.pipeline import repair_single, _calc_raw_match_ratio


class FullMockGraph:
    """
    完整模拟图：支持所有需要的接口。

    拓扑:
    A -> B -> C -> D -> E
    A -> C (捷径)
    """

    def __init__(self):
        self._nodes = {"A", "B", "C", "D", "E"}
        self._edges: dict[str, set[str]] = {
            "A": {"B", "C"},
            "B": {"C"},
            "C": {"D"},
            "D": {"E"},
        }
        self._node_info: dict[str, dict] = {
            "A": {"node_id": "A", "lon": 108.0, "lat": 34.0},
            "B": {"node_id": "B", "lon": 108.1, "lat": 34.1},
            "C": {"node_id": "C", "lon": 108.2, "lat": 34.2},
            "D": {"node_id": "D", "lon": 108.3, "lat": 34.3},
            "E": {"node_id": "E", "lon": 108.4, "lat": 34.4},
        }
        self._paths: dict[tuple[str, str], list[str]] = {
            ("A", "D"): ["A", "B", "C", "D"],
            ("A", "E"): ["A", "B", "C", "D", "E"],
            ("B", "D"): ["B", "C", "D"],
            ("B", "E"): ["B", "C", "D", "E"],
            ("C", "E"): ["C", "D", "E"],
        }
        self._costs: dict[tuple[str, str], float] = {
            ("A", "B"): 1000.0,
            ("B", "C"): 1000.0,
            ("C", "D"): 1000.0,
            ("D", "E"): 1000.0,
            ("A", "C"): 2000.0,
            ("A", "D"): 3000.0,
            ("A", "E"): 4000.0,
            ("B", "D"): 2000.0,
            ("B", "E"): 3000.0,
            ("C", "E"): 2000.0,
        }

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def has_direct_edge(self, from_node: str, to_node: str) -> bool:
        return to_node in self._edges.get(from_node, set())

    def get_out_neighbors(self, node_id: str) -> set[str]:
        return self._edges.get(node_id, set())

    def get_node_info(self, node_id: str) -> dict | None:
        return self._node_info.get(node_id)

    def shortest_path(self, start: str, end: str) -> list[str] | None:
        if start == end:
            return [start]
        return self._paths.get((start, end))

    def shortest_path_cost(self, start: str, end: str) -> float | None:
        if start == end:
            return 0.0
        return self._costs.get((start, end))

    def k_shortest_paths(self, start: str, end: str, k: int = 5) -> list:
        path = self.shortest_path(start, end)
        cost = self.shortest_path_cost(start, end)
        if path and cost is not None:
            return [(path, cost)]
        return []

    def topo_check(self, from_node: str, to_node: str) -> bool:
        return self.has_direct_edge(from_node, to_node)

    def close(self) -> None:
        pass


class TestRepairSingle:
    def setup_method(self):
        self.graph = FullMockGraph()
        self.config = {
            "max_gap_search_window": 6,
            "backward_progress_threshold_m": 300.0,
            "detail_geo": True,
        }

    def test_normal_path(self):
        """正常路径 A|B|C|D → 不应修改"""
        result = repair_single("test_001", "A", "D", "A|B|C|D", self.graph, self.config)
        assert result["corrected_path"] == "A|B|C|D"
        assert result["repair_status"] in ("HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE")
        assert result["repair_confidence"] > 50

    def test_missing_nodes(self):
        """缺失节点 A|D → 应补全为 A|B|C|D"""
        result = repair_single("test_002", "A", "D", "A|D", self.graph, self.config)
        assert result["corrected_path"] == "A|B|C|D"
        assert result["inserted_node_count"] == 2  # B, C

    def test_with_geo_points(self):
        """修正结果应包含经纬度"""
        result = repair_single("test_003", "A", "E", "A|B|C|D|E", self.graph, self.config)
        geo = result["corrected_geo_points"]
        assert len(geo) == 5
        assert geo[0]["node_id"] == "A"
        assert geo[0]["lon"] == 108.0
        assert geo[4]["node_id"] == "E"

    def test_start_end_constraints(self):
        """修正路径必须以 enid 开始，exid 结束"""
        result = repair_single("test_004", "A", "E", "B|C|D", self.graph, self.config)
        assert result["corrected_path"].startswith("A")
        assert result["corrected_path"].endswith("E")

    def test_output_has_all_fields(self):
        """输出结果应包含所有必填字段"""
        result = repair_single("test_005", "A", "D", "A|B|C|D", self.graph, self.config)
        required_fields = [
            "record_id", "enid", "exid", "raw_path", "corrected_path",
            "raw_node_count", "corrected_node_count",
            "inserted_node_count", "dropped_node_count",
            "raw_match_ratio", "detour_ratio",
            "reverse_edge_count", "backward_progress_count",
            "u_turn_count", "repeated_node_count",
            "backtrack_index", "repair_confidence", "repair_status",
            "corrected_geo_points", "repair_detail",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"


class TestRawMatchRatio:
    def test_perfect_match(self):
        assert _calc_raw_match_ratio(["A", "B", "C"], ["A", "B", "C"]) == 1.0

    def test_partial_match(self):
        assert _calc_raw_match_ratio(["A", "B", "X"], ["A", "B", "C", "D"]) == pytest.approx(2 / 3)

    def test_no_match(self):
        assert _calc_raw_match_ratio(["X", "Y", "Z"], ["A", "B", "C"]) == 0.0

    def test_empty_raw(self):
        assert _calc_raw_match_ratio([], ["A", "B"]) == 1.0
