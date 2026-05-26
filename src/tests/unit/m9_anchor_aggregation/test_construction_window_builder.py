"""
M9 - construction_window_builder.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.construction_window_builder import (
    build_windows_by_portals,
    build_windows_by_path_hits,
    deduplicate_construction_windows,
)
from src.modules.m9_anchor_aggregation.models import (
    ConstructionComponent,
    PathRecord,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph
from src.modules.m9_anchor_aggregation.config import AnchorAggregationConfig


class TestBuildWindowsByPortals:
    def test_basic_window(self):
        """基础门户窗口生成"""
        edges = [
            ("B", "C"),
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
        component.entry_portals = {"C"}
        component.exit_portals = {"D"}

        windows = build_windows_by_portals("const_001", component, topology)

        assert len(windows) == 1
        assert windows[0].start_unit == "C"
        assert windows[0].end_unit == "D"
        assert windows[0].source == "portal"

    def test_no_portals(self):
        """无门户时不生成窗口"""
        edges = [("C", "D")]
        topology = TopologyGraph()
        topology.load_from_edges(edges)

        component = ConstructionComponent(
            construction_id="const_001",
            component_id="comp_1",
            units={"C", "D"},
        )
        component.entry_portals = set()
        component.exit_portals = set()

        windows = build_windows_by_portals("const_001", component, topology)

        assert len(windows) == 0


class TestBuildWindowsByPathHits:
    def test_basic_path_hit_window(self):
        """基础 path 命中窗口"""
        path_records = [
            PathRecord(
                record_id="r001",
                enid="A",
                exid="L",
                path=["A", "B", "C", "D", "E", "F", "L"],
                flow=100.0,
            ),
        ]
        components = [
            ConstructionComponent(
                construction_id="const_001",
                component_id="comp_1",
                units={"C", "D", "E"},
            ),
        ]
        config = AnchorAggregationConfig()
        config.construction_window.min_path_hit_flow = 1
        config.construction_window.min_path_hit_count = 1

        windows = build_windows_by_path_hits(
            construction_id="const_001",
            components=components,
            path_records=path_records,
            construction_units={"C", "D", "E"},
            config=config,
        )

        assert len(windows) >= 1
        hit_window = next(w for w in windows if w.source == "path_hit")
        assert hit_window.start_unit == "C"
        assert hit_window.end_unit == "E"


class TestDeduplicateConstructionWindows:
    def test_deduplicate_by_start_end(self):
        """相同起止点窗口应去重"""
        from src.modules.m9_anchor_aggregation.models import ConstructionWindow

        windows = [
            ConstructionWindow(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w1",
                start_unit="C",
                end_unit="E",
                source_flow=50.0,
            ),
            ConstructionWindow(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w2",
                start_unit="C",
                end_unit="E",
                source_flow=100.0,
            ),
        ]

        result = deduplicate_construction_windows(windows)

        assert len(result) == 1
        assert result[0].window_id == "w2"
        assert result[0].source_flow == 100.0