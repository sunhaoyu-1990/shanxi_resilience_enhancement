"""
M9 - assignment.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.assignment import (
    score_anchor_window,
    assign_path_to_best_window,
    assign_all_paths,
    validate_unique_assignment,
)
from src.modules.m9_anchor_aggregation.models import (
    PathRecord,
    AnchorWindow,
    PathAssignment,
)


class TestScoreAnchorWindow:
    def test_score_ordering(self):
        """min_level 和 covered_units 越小，分数越低（优先级越高）"""
        window1 = AnchorWindow(
            construction_id="const_001",
            anchor_start="B",
            anchor_end="K",
            covered_units={"C", "D"},
            min_level=1,
        )
        window2 = AnchorWindow(
            construction_id="const_001",
            anchor_start="B",
            anchor_end="K",
            covered_units={"C", "D", "E"},
            min_level=1,
        )
        window3 = AnchorWindow(
            construction_id="const_001",
            anchor_start="B",
            anchor_end="K",
            covered_units={"C", "D"},
            min_level=2,
        )

        assert score_anchor_window(window1) < score_anchor_window(window2)
        assert score_anchor_window(window1) < score_anchor_window(window3)


class TestAssignPathToBestWindow:
    def test_single_match(self):
        record = PathRecord(
            record_id="r001",
            enid="A",
            exid="L",
            path=["A", "B", "C", "D", "E", "L"],
            flow=100.0,
        )
        windows = [
            AnchorWindow(
                construction_id="const_001",
                anchor_start="B",
                anchor_end="E",
                covered_units={"C", "D"},
                min_level=1,
            ),
        ]
        construction_units = {"C", "D"}

        result = assign_path_to_best_window(record, windows, construction_units)

        assert result.route_type == "pass"
        assert result.assigned_anchor_start == "B"
        assert result.assigned_anchor_end == "E"

    def test_bypass_path(self):
        record = PathRecord(
            record_id="r001",
            enid="A",
            exid="L",
            path=["A", "B", "X", "Y", "E", "L"],
            flow=100.0,
        )
        windows = [
            AnchorWindow(
                construction_id="const_001",
                anchor_start="B",
                anchor_end="E",
                covered_units={"C", "D"},
                min_level=1,
            ),
        ]
        construction_units = {"C", "D"}

        result = assign_path_to_best_window(record, windows, construction_units)

        assert result.route_type == "bypass"

    def test_unassigned_when_no_match(self):
        record = PathRecord(
            record_id="r001",
            enid="M",
            exid="N",
            path=["M", "X", "Y", "N"],
            flow=100.0,
        )
        windows = [
            AnchorWindow(
                construction_id="const_001",
                anchor_start="B",
                anchor_end="K",
                covered_units={"C", "D"},
                min_level=1,
            ),
        ]
        construction_units = {"C", "D"}

        result = assign_path_to_best_window(record, windows, construction_units)

        assert result.route_type == "unassigned"


class TestAssignAllPaths:
    def test_all_paths_assigned(self):
        records = [
            PathRecord(
                record_id="r001",
                enid="A",
                exid="L",
                path=["A", "B", "C", "D", "L"],
                flow=100.0,
            ),
            PathRecord(
                record_id="r002",
                enid="A",
                exid="L",
                path=["A", "B", "X", "Y", "L"],
                flow=50.0,
            ),
        ]
        windows = [
            AnchorWindow(
                construction_id="const_001",
                anchor_start="B",
                anchor_end="L",
                covered_units={"C", "D"},
                min_level=1,
            ),
        ]
        construction_units = {"C", "D"}

        results = assign_all_paths(records, windows, construction_units)

        assert len(results) == 2
        assert all(r.route_type != "unassigned" for r in results)


class TestValidateUniqueAssignment:
    def test_no_duplicates(self):
        assignments = [
            PathAssignment(
                construction_id="const_001",
                record_id="r001",
                enid="A",
                exid="L",
                assigned_anchor_start="B",
                assigned_anchor_end="K",
                route_type="pass",
                flow=100.0,
            ),
        ]

        errors = validate_unique_assignment(assignments)
        assert len(errors) == 0

    def test_detect_duplicates(self):
        assignments = [
            PathAssignment(
                construction_id="const_001",
                record_id="r001",
                enid="A",
                exid="L",
                assigned_anchor_start="B",
                assigned_anchor_end="K",
                route_type="pass",
                flow=100.0,
            ),
            PathAssignment(
                construction_id="const_001",
                record_id="r001",
                enid="A",
                exid="L",
                assigned_anchor_start="B",
                assigned_anchor_end="K",
                route_type="bypass",
                flow=100.0,
            ),
        ]

        errors = validate_unique_assignment(assignments)
        assert len(errors) > 0