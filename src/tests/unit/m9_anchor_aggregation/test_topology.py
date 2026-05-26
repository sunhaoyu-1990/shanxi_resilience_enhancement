"""
M9 - topology.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.topology import TopologyGraph


class TestTopologyGraph:
    def test_load_from_edges(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        assert "A" in topology.get_all_nodes()
        assert "D" in topology.get_all_nodes()

    def test_get_downstream(self):
        edges = [
            ("A", "B"),
            ("A", "C"),
            ("B", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        downstream = topology.get_downstream("A")
        assert downstream == {"B", "C"}

    def test_get_upstream(self):
        edges = [
            ("A", "B"),
            ("A", "C"),
            ("B", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        upstream = topology.get_upstream("B")
        assert upstream == {"A"}

    def test_has_edge(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        assert topology.has_edge("A", "B") is True
        assert topology.has_edge("B", "A") is False
        assert topology.has_edge("A", "C") is False

    def test_directed_reachable_within(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "E"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        allowed = {"B", "C", "D"}
        reachable = topology.directed_reachable_within("B", allowed)
        assert reachable == {"B", "C", "D"}

    def test_directed_reachable_within_blocked(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        allowed = {"A", "B", "C", "D"}
        reachable = topology.directed_reachable_within("A", allowed)
        assert reachable == {"A", "B", "C", "D"}

    def test_has_directed_path_within(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        allowed = {"A", "B", "C", "D"}

        assert topology.has_directed_path_within("A", "D", allowed) is True
        assert topology.has_directed_path_within("D", "A", allowed) is False
        assert topology.has_directed_path_within("A", "X", allowed) is False

    def test_bfs_expand_downstream(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("A", "E"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        levels = topology.bfs_expand_downstream("A", blocked=set(), max_level=2)

        assert 0 in levels and "A" in levels[0]
        assert 1 in levels and "B" in levels[1] and "E" in levels[1]
        assert 2 in levels and "C" in levels[2]

    def test_bfs_expand_downstream_blocked(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("B", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        levels = topology.bfs_expand_downstream("A", blocked={"B"}, max_level=2)

        assert 0 in levels and "A" in levels[0]
        assert 1 not in levels or "B" not in levels.get(1, set())

    def test_bfs_expand_upstream(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("D", "C"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        levels = topology.bfs_expand_upstream("C", blocked=set(), max_level=2)

        assert 0 in levels and "C" in levels[0]
        assert 1 in levels and "B" in levels[1] and "D" in levels[1]
        assert 2 in levels and "A" in levels[2]

    def test_find_path_between(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        path = topology.find_path_between("A", "D")
        assert path == ["A", "B", "C", "D"]

    def test_find_path_between_not_found(self):
        edges = [
            ("A", "B"),
            ("B", "C"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        path = topology.find_path_between("A", "X")
        assert path is None

    def test_find_path_between_self(self):
        topology = TopologyGraph()
        topology.load_from_edges([])
        assert topology.find_path_between("A", "A") == ["A"]