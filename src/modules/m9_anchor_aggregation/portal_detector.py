"""
M9 施工锚点聚合模块 - 门户点识别
识别每个施工片区的入口门户、出口门户和最近外部边界

定义：
- 入口门户 entry_portal：施工单元 u，存在非施工单元 p 使得 p->u
- 出口门户 exit_portal：施工单元 u，存在非施工单元 q 使得 u->q
- 上游边界 upstream_frontiers：那些 p 节点
- 下游边界 downstream_frontiers：那些 q 节点
"""

from src.app.logger import get_logger
from src.modules.m9_anchor_aggregation.models import ConstructionComponent
from src.modules.m9_anchor_aggregation.topology import TopologyGraph

logger = get_logger(__name__)


def detect_portals(
    component: ConstructionComponent,
    topology: TopologyGraph,
) -> ConstructionComponent:
    """
    检测施工片区的入口/出口门户

    Args:
        component: 施工片区（units 已填充）
        topology: 有向拓扑图

    Returns:
        ConstructionComponent: 填充了 entry_portals, exit_portals,
                             upstream_frontiers, downstream_frontiers
    """
    construction_units = component.units
    entry_portals: set[str] = set()
    exit_portals: set[str] = set()
    upstream_frontiers: set[str] = set()
    downstream_frontiers: set[str] = set()

    for unit in construction_units:
        for upstream_node in topology.get_upstream(unit):
            if upstream_node not in construction_units:
                entry_portals.add(unit)
                upstream_frontiers.add(upstream_node)

        for downstream_node in topology.get_downstream(unit):
            if downstream_node not in construction_units:
                exit_portals.add(unit)
                downstream_frontiers.add(downstream_node)

    component.entry_portals = entry_portals
    component.exit_portals = exit_portals
    component.upstream_frontiers = upstream_frontiers
    component.downstream_frontiers = downstream_frontiers

    logger.info(
        f"[portal_detect] component_id={component.component_id}, "
        f"entry_count={len(entry_portals)}, exit_count={len(exit_portals)}, "
        f"upstream_frontiers={sorted(upstream_frontiers)}, "
        f"downstream_frontiers={sorted(downstream_frontiers)}"
    )

    if not entry_portals:
        logger.warning(
            f"[portal_detect] component {component.component_id} has no entry portals"
        )
    if not exit_portals:
        logger.warning(
            f"[portal_detect] component {component.component_id} has no exit portals"
        )

    return component


def detect_all_portals(
    components: list[ConstructionComponent],
    topology: TopologyGraph,
) -> list[ConstructionComponent]:
    """
    批量检测多个施工片区的门户

    Args:
        components: 施工片区列表
        topology: 有向拓扑图

    Returns:
        list[ConstructionComponent]: 门户已填充的施工片区列表
    """
    return [detect_portals(comp, topology) for comp in components]