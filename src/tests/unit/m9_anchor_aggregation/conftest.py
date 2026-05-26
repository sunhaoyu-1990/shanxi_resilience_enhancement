"""
M9 施工锚点聚合模块 - 测试共享 fixtures
"""

import pytest
from src.modules.m9_anchor_aggregation.models import (
    PathRecord,
    TopologyEdge,
    ConstructionInput,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph
from src.modules.m9_anchor_aggregation.config import AnchorAggregationConfig


@pytest.fixture
def sample_topology_edges():
    """小型拓扑图边列表"""
    return [
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


@pytest.fixture
def sample_topology(sample_topology_edges):
    """小型拓扑图"""
    topology = TopologyGraph()
    topology.load_from_edges(sample_topology_edges)
    return topology


@pytest.fixture
def sample_construction_input():
    """示例施工输入"""
    return ConstructionInput(
        construction_id="const_001",
        construction_units=frozenset({"C", "D", "E", "F", "G", "H", "I", "J", "K"}),
        construction_name="测试施工",
        version="202603",
    )


@pytest.fixture
def sample_path_records():
    """示例 path 记录（已知分类结果）"""
    return [
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
        PathRecord(
            record_id="r004",
            enid="A",
            exid="L",
            path=["A", "B", "C", "D", "E", "Z", "Z", "F", "G", "H", "I", "J", "K", "L"],
            flow=30.0,
        ),
        PathRecord(
            record_id="r005",
            enid="B",
            exid="F",
            path=["B", "C", "D", "E", "F"],
            flow=40.0,
        ),
    ]


@pytest.fixture
def sample_config():
    """默认配置"""
    return AnchorAggregationConfig.default()


@pytest.fixture
def long_chain_topology():
    """长链拓扑"""
    edges = [(f"U{i}", f"U{i+1}") for i in range(1, 20)]
    topology = TopologyGraph()
    topology.load_from_edges(edges)
    return topology


@pytest.fixture
def two_component_topology():
    """两个不相连片区的拓扑"""
    edges = [
        ("A10", "B10"),
        ("B10", "C10"),
        ("M10", "N10"),
        ("N10", "O10"),
    ]
    topology = TopologyGraph()
    topology.load_from_edges(edges)
    return topology


@pytest.fixture
def two_component_construction():
    """两个片区的施工输入"""
    return ConstructionInput(
        construction_id="const_002",
        construction_units=frozenset({"A10", "B10", "C10", "M10", "N10", "O10"}),
    )