"""
M9 施工锚点聚合模块 - 施工片区拆分
基于有向拓扑的弱连通分量拆分施工片区

关键原则：
1. 不依赖 ID 后缀识别方向
2. 施工输入只表示施工收费单元集合，不表示顺序
3. 片区拆分完全基于拓扑连通性
"""

from typing import Optional

from src.modules.m9_anchor_aggregation.models import (
    ConstructionInput,
    ConstructionComponent,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph


def _build_undirected_adjacency(
    construction_units: set[str],
    topology: TopologyGraph,
) -> dict[str, set[str]]:
    """
    构建施工单元的无向邻接表

    在施工单元子图上，如果存在 A->B 或 B->A 边，则 A 和 B 无向连通。

    Args:
        construction_units: 施工单元集合
        topology: 有向拓扑图

    Returns:
        dict[str, set[str]]: 无向邻接表
    """
    adj: dict[str, set[str]] = {u: set() for u in construction_units}

    for unit in construction_units:
        for downstream in topology.get_downstream(unit):
            if downstream in construction_units:
                adj[unit].add(downstream)
                adj[downstream].add(unit)

        for upstream in topology.get_upstream(unit):
            if upstream in construction_units:
                adj[unit].add(upstream)
                adj[upstream].add(unit)

    return adj


def _union_find_find(parent: dict[str, str], x: str) -> str:
    """并查集 Find 操作（带路径压缩）"""
    if parent[x] != x:
        parent[x] = _union_find_find(parent, parent[x])
    return parent[x]


def _union_find_union(
    parent: dict[str, str],
    rank: dict[str, int],
    x: str,
    y: str,
) -> None:
    """并查集 Union 操作（按秩合并）"""
    root_x = _union_find_find(parent, x)
    root_y = _union_find_find(parent, y)

    if root_x == root_y:
        return

    if rank[root_x] < rank[root_y]:
        parent[root_x] = root_y
    elif rank[root_x] > rank[root_y]:
        parent[root_y] = root_x
    else:
        parent[root_y] = root_x
        rank[root_x] += 1


def split_components_by_topology(
    construction_input: ConstructionInput,
    topology: TopologyGraph,
) -> list[ConstructionComponent]:
    """
    基于拓扑拆分施工片区

    算法：在施工单元子图上做无向连通分量（Union-Find）。
    如果两个施工单元在拓扑中存在 A->B 或 B->A 边，则它们属于同一片区。

    Args:
        construction_input: 施工输入
        topology: 有向拓扑图

    Returns:
        list[ConstructionComponent]: 施工片区列表
    """
    construction_units = construction_input.construction_units
    construction_id = construction_input.construction_id

    if not construction_units:
        return []

    adj = _build_undirected_adjacency(construction_units, topology)

    parent: dict[str, str] = {u: u for u in construction_units}
    rank: dict[str, int] = {u: 0 for u in construction_units}

    for unit, neighbors in adj.items():
        for neighbor in neighbors:
            _union_find_union(parent, rank, unit, neighbor)

    root_to_units: dict[str, set[str]] = {}
    for unit in construction_units:
        root = _union_find_find(parent, unit)
        if root not in root_to_units:
            root_to_units[root] = set()
        root_to_units[root].add(unit)

    components: list[ConstructionComponent] = []
    for i, (root, units) in enumerate(root_to_units.items()):
        component = ConstructionComponent(
            construction_id=construction_id,
            component_id=f"{construction_id}_comp_{i + 1}",
            units=units,
        )
        components.append(component)

    logger = _get_logger()
    logger.info(
        f"[component_split] construction_id={construction_id}, "
        f"component_count={len(components)}"
    )

    for comp in components:
        logger.debug(
            f"  component {comp.component_id}: {len(comp.units)} units, "
            f"units={sorted(comp.units)}"
        )

    return components


def _get_logger():
    from src.app.logger import get_logger
    return get_logger(__name__)