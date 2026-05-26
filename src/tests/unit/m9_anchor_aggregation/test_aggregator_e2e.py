"""
M9 - 端到端集成测试
"""

import pytest
from src.modules.m9_anchor_aggregation.aggregator import aggregate_construction_paths
from src.modules.m9_anchor_aggregation.models import (
    ConstructionInput,
    PathRecord,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph
from src.modules.m9_anchor_aggregation.config import AnchorAggregationConfig


class TestAggregatorEndToEnd:
    def test_basic_aggregation(self):
        """基础端到端测试"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "E"),
            ("E", "F"),
            ("F", "G"),
            ("G", "H"),
            ("H", "I"),
            ("I", "J"),
            ("J", "K"),
            ("K", "L"),
            ("X", "F"),
            ("Y", "H"),
            ("L", "Y"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"C", "D", "E", "F", "G", "H", "I", "J", "K"}),
        )

        path_records = [
            PathRecord(
                record_id="r001",
                enid="A",
                exid="L",
                path=["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"],
                flow=100.0,
            ),
            PathRecord(
                record_id="r002",
                enid="A",
                exid="L",
                path=["A", "B", "X", "F", "G", "H", "I", "J", "K", "L"],
                flow=50.0,
            ),
            PathRecord(
                record_id="r003",
                enid="X",
                exid="L",
                path=["X", "U", "V", "L"],
                flow=20.0,
            ),
        ]

        config = AnchorAggregationConfig()
        config.valid_anchor.min_pass_flow = 1
        config.valid_anchor.min_bypass_flow = 1

        result = aggregate_construction_paths(
            construction_input=construction,
            path_records=path_records,
            topology=topology,
            config=config,
        )

        assert result.construction_id == "const_001"
        assert len(result.components) >= 1
        assert len(result.assignments) == 3

        total_assigned = sum(
            a.flow for a in result.assignments if a.route_type != "unassigned"
        )
        assert total_assigned <= sum(r.flow for r in path_records)

    def test_unique_assignment(self):
        """每条 path 只能归属一个锚点窗口"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "E"),
            ("E", "F"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"B", "C", "D"}),
        )

        path_records = [
            PathRecord(
                record_id="r001",
                enid="A",
                exid="E",
                path=["A", "B", "C", "D", "E"],
                flow=100.0,
            ),
        ]

        result = aggregate_construction_paths(
            construction_input=construction,
            path_records=path_records,
            topology=topology,
        )

        for record_id in {r.record_id for r in path_records}:
            assignments = [
                a for a in result.assignments
                if a.record_id == record_id and a.route_type != "unassigned"
            ]
            assert len(assignments) <= 1

    def test_two_component_split(self):
        """两个不连通片区应正确拆分"""
        edges = [
            ("A10", "B10"),
            ("B10", "C10"),
            ("M10", "N10"),
            ("N10", "O10"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_002",
            construction_units=frozenset({"A10", "B10", "C10", "M10", "N10", "O10"}),
        )

        path_records = [
            PathRecord(
                record_id="r001",
                enid="A10",
                exid="C10",
                path=["A10", "B10", "C10"],
                flow=50.0,
            ),
            PathRecord(
                record_id="r002",
                enid="M10",
                exid="O10",
                path=["M10", "N10", "O10"],
                flow=30.0,
            ),
        ]

        result = aggregate_construction_paths(
            construction_input=construction,
            path_records=path_records,
            topology=topology,
        )

        assert len(result.components) == 2


class TestBypassDetection:
    def test_bypass_path_not_hitting_construction(self):
        """bypass path 不应命中施工单元"""
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("B", "X"),
            ("X", "D"),
        ]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        construction = ConstructionInput(
            construction_id="const_001",
            construction_units=frozenset({"B", "C"}),
        )

        path_records = [
            PathRecord(
                record_id="r001",
                enid="A",
                exid="D",
                path=["A", "B", "X", "D"],
                flow=100.0,
            ),
        ]

        result = aggregate_construction_paths(
            construction_input=construction,
            path_records=path_records,
            topology=topology,
        )

        bypass_assignments = [
            a for a in result.assignments
            if a.route_type == "bypass"
        ]
        for a in bypass_assignments:
            assert len(a.hit_units) == 0