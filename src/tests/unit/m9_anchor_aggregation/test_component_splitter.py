"""
M9 - component_splitter.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.component_splitter import split_components_by_topology
from src.modules.m9_anchor_aggregation.models import ConstructionInput
from src.modules.m9_anchor_aggregation.topology import TopologyGraph


class TestSplitComponentsByTopology:
    def test_single_component(self):
        """线性链应拆成一个 component"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "E"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"B", "C", "D"}),
        )

        components = split_components_by_topology(construction, topology)

        assert len(components) == 1
        assert components[0].units == {"B", "C", "D"}

    def test_two_disconnected_components(self):
        """两个不连通片区应拆成两个 component"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("M", "N"),
            ("N", "O"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"B", "C", "N", "O"}),
        )

        components = split_components_by_topology(construction, topology)

        assert len(components) == 2
        component_ids = {c.component_id for c in components}
        assert len(component_ids) == 2

    def test_same_suffix_different_components(self):
        """
        同后缀但不同连通分量应拆成多个 component
        ID 后缀不能用于判断方向
        """
        edges = [
            ("A10", "B10"),
            ("B10", "C10"),
            ("M10", "N10"),
            ("N10", "O10"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"A10", "B10", "C10", "M10", "N10", "O10"}),
        )

        components = split_components_by_topology(construction, topology)

        assert len(components) == 2
        units_sets = [c.units for c in components]
        assert {"A10", "B10", "C10"} in units_sets
        assert {"M10", "N10", "O10"} in units_sets

    def test_empty_construction_units(self):
        """空施工集合应返回空列表"""
        edges = [("A", "B")]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset(),
        )

        components = split_components_by_topology(construction, topology)

        assert components == []

    def test_unreachable_units(self):
        """拓扑中不连通的单元应各自成为独立 component"""
        edges = [
            ("A", "B"),
            ("C", "D"),
            ("E", "F"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"B", "D", "F"}),
        )

        components = split_components_by_topology(construction, topology)

        assert len(components) == 3