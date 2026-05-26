"""
M9 - parser.py 单元测试
"""

import pytest
from src.modules.m9_anchor_aggregation.parser import (
    parse_unit_sequence,
    parse_construction_units,
    build_unit_inverted_index,
    create_construction_input,
)


class TestParseUnitSequence:
    def test_normal_sequence(self):
        result = parse_unit_sequence("A|B|C")
        assert result == ["A", "B", "C"]

    def test_empty_string(self):
        result = parse_unit_sequence("")
        assert result == []

    def test_consecutive_delimiters(self):
        result = parse_unit_sequence("A||B|C")
        assert result == ["A", "B", "C"]

    def test_leading_trailing_delimiter(self):
        result = parse_unit_sequence("|A|B|C|")
        assert result == ["A", "B", "C"]

    def test_whitespace_trimming(self):
        result = parse_unit_sequence(" A | B | C ")
        assert result == ["A", "B", "C"]

    def test_no_remove_empty_false(self):
        result = parse_unit_sequence("A||B|C", remove_empty=False)
        assert result == ["A", "", "B", "C"]


class TestParseConstructionUnits:
    def test_basic_construction(self):
        result = parse_construction_units("C|D|E|F|G")
        assert result == frozenset({"C", "D", "E", "F", "G"})

    def test_unordered(self):
        result = parse_construction_units("C|E|G|D|F")
        assert result == frozenset({"C", "D", "E", "F", "G"})

    def test_duplicates_in_input(self):
        result = parse_construction_units("C|D|C|E")
        assert result == frozenset({"C", "D", "E"})

    def test_empty_construction(self):
        result = parse_construction_units("")
        assert result == frozenset()

    def test_custom_delimiter(self):
        result = parse_construction_units("C,D,E,F", delimiter=",")
        assert result == frozenset({"C", "D", "E", "F"})


class TestBuildUnitInvertedIndex:
    def test_basic_index(self):
        records = [
            create_path_record("r001", ["A", "B", "C"]),
            create_path_record("r002", ["B", "D"]),
            create_path_record("r003", ["E", "F"]),
        ]
        index = build_unit_inverted_index(records)

        assert "A" in index and 0 in index["A"]
        assert "B" in index and 0 in index["B"] and 1 in index["B"]
        assert "E" in index and 2 in index["E"]

    def test_empty_records(self):
        index = build_unit_inverted_index([])
        assert index == {}


class TestCreateConstructionInput:
    def test_basic_input(self):
        result = create_construction_input("const_001", "C|D|E")
        assert result.construction_id == "const_001"
        assert result.construction_units == frozenset({"C", "D", "E"})

    def test_with_name_and_version(self):
        result = create_construction_input(
            "const_001",
            "C|D|E",
            construction_name="测试施工",
            version="202603",
        )
        assert result.construction_name == "测试施工"
        assert result.version == "202603"


def create_path_record(record_id: str, path: list[str]) -> "PathRecord":
    """Helper to create PathRecord for testing"""
    from src.modules.m9_anchor_aggregation.models import PathRecord
    return PathRecord(
        record_id=record_id,
        enid="A",
        exid="Z",
        path=path,
        flow=1.0,
    )