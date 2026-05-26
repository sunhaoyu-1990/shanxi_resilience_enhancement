"""
M9 - portal_detector.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.portal_detector import detect_portals
from src.modules.m9_anchor_aggregation.models import ConstructionComponent
from src.modules.m9_anchor_aggregation.topology import TopologyGraph


class TestDetectPortals:
    def test_basic_portals(self):
        """基础门户检测"""
        edges = [
            ("B", "C"),
            ("C", "D"),
            ("X", "C"),
            ("D", "E"),
            ("E", "Y"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"C", "D", "E"},
        )

        result = detect_portals(component, topology)

        assert "C" in result.entry_portals
        assert "E" in result.exit_portals
        assert "B" in result.upstream_frontiers
        assert "Y" in result.downstream_frontiers
        assert "X" in result.upstream_frontiers

    def test_no_entry_portal(self):
        """只有出口的 component - 内部起始节点"""
        edges = [
            ("C", "D"),
            ("D", "E"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"C", "D"},
        )

        result = detect_portals(component, topology)

        assert len(result.entry_portals) == 0
        assert len(result.exit_portals) == 1

    def test_no_exit_portal(self):
        """只有入口的 component - 内部末端节点"""
        edges = [
            ("B", "C"),
            ("C", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"C", "D"},
        )

        result = detect_portals(component, topology)

        assert len(result.exit_portals) == 0
        assert "C" in result.entry_portals

    def test_intermediate_portal(self):
        """中间有外部入口的 component"""
        edges = [
            ("C", "D"),
            ("X", "D"),
            ("D", "E"),
            ("E", "F"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"D", "E"},
        )

        result = detect_portals(component, topology)

        assert "D" in result.entry_portals
        assert "E" in result.exit_portals
        assert "X" in result.upstream_frontiers
        assert "F" in result.downstream_frontiers

    def test_multiple_exits(self):
        """多个出口的 component"""
        edges = [
            ("B", "C"),
            ("C", "D"),
            ("C", "X"),
            ("D", "E"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"C", "D"},
        )

        result = detect_portals(component, topology)

        assert "D" in result.exit_portals
        assert "X" in result.downstream_frontiers

    def test_single_unit_component(self):
        """单节点 component"""
        edges = [
            ("B", "C"),
            ("C", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"C"},
        )

        result = detect_portals(component, topology)

        assert "C" in result.entry_portals
        assert "C" in result.exit_portals
        assert "B" in result.upstream_frontiers
        assert "D" in result.downstream_frontiers