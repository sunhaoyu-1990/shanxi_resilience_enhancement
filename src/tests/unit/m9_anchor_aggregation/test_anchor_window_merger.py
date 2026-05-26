"""
M9 - anchor_window_merger.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.anchor_window_merger import (
    merge_anchor_candidates_to_windows,
    deduplicate_anchor_windows,
)
from src.modules.m9_anchor_aggregation.models import (
    RawAnchorCandidate,
    ConstructionWindow,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph


class TestMergeAnchorCandidatesToWindows:
    def test_merge_same_anchor(self):
        """相同锚点窗口应合并"""
        candidates = [
            RawAnchorCandidate(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w1",
                anchor_start="B",
                anchor_end="K",
                level=1,
            ),
            RawAnchorCandidate(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w2",
                anchor_start="B",
                anchor_end="K",
                level=2,
            ),
        ]

        windows = {
            "w1": ConstructionWindow(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w1",
                start_unit="C",
                end_unit="E",
                covered_units={"C", "D", "E"},
            ),
            "w2": ConstructionWindow(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w2",
                start_unit="F",
                end_unit="H",
                covered_units={"F", "G", "H"},
            ),
        }

        result = merge_anchor_candidates_to_windows(candidates, windows)

        assert len(result) == 1
        assert result[0].anchor_start == "B"
        assert result[0].anchor_end == "K"
        assert result[0].min_level == 1
        assert len(result[0].source_window_ids) == 2

    def test_different_anchors_not_merged(self):
        """不同锚点窗口不应合并"""
        candidates = [
            RawAnchorCandidate(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w1",
                anchor_start="A",
                anchor_end="E",
                level=1,
            ),
            RawAnchorCandidate(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w2",
                anchor_start="B",
                anchor_end="F",
                level=2,
            ),
        ]

        windows = {
            "w1": ConstructionWindow(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w1",
                start_unit="C",
                end_unit="D",
                covered_units={"C", "D"},
            ),
            "w2": ConstructionWindow(
                construction_id="const_001",
                component_id="comp_1",
                window_id="w2",
                start_unit="E",
                end_unit="F",
                covered_units={"E", "F"},
            ),
        }

        result = merge_anchor_candidates_to_windows(candidates, windows)

        assert len(result) == 2


class TestDeduplicateAnchorWindows:
    def test_deduplicate_by_key(self):
        """相同 key 的锚点窗口应去重"""
        from src.modules.m9_anchor_aggregation.models import AnchorWindow

        windows = [
            AnchorWindow(
                construction_id="const_001",
                anchor_start="B",
                anchor_end="K",
                source_window_ids={"w1"},
                covered_units={"C", "D"},
            ),
            AnchorWindow(
                construction_id="const_001",
                anchor_start="B",
                anchor_end="K",
                source_window_ids={"w2"},
                covered_units={"E", "F"},
            ),
        ]

        result = deduplicate_anchor_windows(windows)

        assert len(result) == 1