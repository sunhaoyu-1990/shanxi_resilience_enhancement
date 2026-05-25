"""
M8 路径修正 — 经纬度匹配单元测试
"""

import pytest

from src.modules.m8_path_repair.core.geo import attach_lonlat, get_missing_geo_nodes


class MockGraph:
    """用于测试的简单图"""

    def __init__(self, node_info: dict[str, dict]):
        self._node_info = node_info

    def has_node(self, node_id: str) -> bool:
        return node_id in self._node_info

    def get_node_info(self, node_id: str) -> dict | None:
        return self._node_info.get(node_id)


class TestAttachLonLat:
    def test_all_nodes_have_coords(self):
        graph = MockGraph({
            "A": {"node_id": "A", "lon": 108.0, "lat": 34.0},
            "B": {"node_id": "B", "lon": 108.1, "lat": 34.1},
            "C": {"node_id": "C", "lon": 108.2, "lat": 34.2},
        })
        result = attach_lonlat(["A", "B", "C"], graph)
        assert len(result) == 3
        assert result[0] == {"seq": 1, "node_id": "A", "lon": 108.0, "lat": 34.0}
        assert result[1] == {"seq": 2, "node_id": "B", "lon": 108.1, "lat": 34.1}
        assert result[2] == {"seq": 3, "node_id": "C", "lon": 108.2, "lat": 34.2}

    def test_missing_coords(self):
        graph = MockGraph({
            "A": {"node_id": "A", "lon": 108.0, "lat": 34.0},
            "B": {"node_id": "B", "lon": None, "lat": None},
            "C": {"node_id": "C", "lon": 108.2, "lat": 34.2},
        })
        result = attach_lonlat(["A", "B", "C"], graph)
        assert result[1]["lon"] is None
        assert result[1]["lat"] is None

    def test_unknown_node(self):
        graph = MockGraph({
            "A": {"node_id": "A", "lon": 108.0, "lat": 34.0},
        })
        result = attach_lonlat(["A", "X", "B"], graph)
        assert result[0]["lon"] == 108.0
        assert result[1]["lon"] is None  # X 不在图中
        assert result[2]["lon"] is None  # B 不在图中

    def test_empty_path(self):
        graph = MockGraph({})
        result = attach_lonlat([], graph)
        assert result == []

    def test_seq_starts_at_one(self):
        graph = MockGraph({
            "A": {"node_id": "A", "lon": 0, "lat": 0},
        })
        result = attach_lonlat(["A"], graph)
        assert result[0]["seq"] == 1


class TestGetMissingGeoNodes:
    def test_no_missing(self):
        points = [
            {"seq": 1, "node_id": "A", "lon": 108.0, "lat": 34.0},
            {"seq": 2, "node_id": "B", "lon": 108.1, "lat": 34.1},
        ]
        assert get_missing_geo_nodes(points) == []

    def test_some_missing(self):
        points = [
            {"seq": 1, "node_id": "A", "lon": 108.0, "lat": 34.0},
            {"seq": 2, "node_id": "B", "lon": None, "lat": None},
            {"seq": 3, "node_id": "C", "lon": 108.2, "lat": 34.2},
        ]
        assert get_missing_geo_nodes(points) == ["B"]

    def test_all_missing(self):
        points = [
            {"seq": 1, "node_id": "A", "lon": None, "lat": None},
            {"seq": 2, "node_id": "B", "lon": None, "lat": None},
        ]
        assert get_missing_geo_nodes(points) == ["A", "B"]
