"""
M9 施工锚点聚合模块 - 局部施工窗口生成
基于门户点和 path 命中区间生成局部施工窗口

窗口来源：
1. 门户点拓扑窗口：entry_portal -> exit_portal 之间可达的施工单元
2. path 命中窗口：path 的 first_hit -> last_hit 区间
"""

from collections import defaultdict
from typing import Optional

from src.app.logger import get_logger
from src.modules.m9_anchor_aggregation.models import (
    ConstructionComponent,
    ConstructionWindow,
    PathRecord,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph
from src.modules.m9_anchor_aggregation.config import AnchorAggregationConfig

logger = get_logger(__name__)


def build_windows_by_portals(
    construction_id: str,
    component: ConstructionComponent,
    topology: TopologyGraph,
) -> list[ConstructionWindow]:
    """
    基于门户点生成局部施工窗口

    对每个 entry_portal 和 exit_portal，如果 entry_portal 在施工子图内有向可达 exit_portal，
    则生成 construction_window。

    Args:
        construction_id: 施工工程 ID
        component: 施工片区（已填充门户）
        topology: 有向拓扑图

    Returns:
        list[ConstructionWindow]: 局部施工窗口列表
    """
    windows: list[ConstructionWindow] = []
    construction_units = component.units

    if not component.entry_portals or not component.exit_portals:
        return windows

    for entry in component.entry_portals:
        for exit in component.exit_portals:
            reachable = topology.directed_reachable_within(entry, construction_units)
            if exit in reachable:
                covered = topology.directed_reachable_within(entry, construction_units)
                covered = {u for u in covered if u in construction_units}

                if covered:
                    window = ConstructionWindow(
                        construction_id=construction_id,
                        component_id=component.component_id,
                        window_id=f"{construction_id}_{component.component_id}_portal_{entry}_{exit}",
                        start_unit=entry,
                        end_unit=exit,
                        covered_units=covered,
                        source="portal",
                    )
                    windows.append(window)

    logger.debug(
        f"[window_build] {component.component_id}: "
        f"portal_windows={len(windows)}"
    )

    return windows


def build_windows_by_path_hits(
    construction_id: str,
    components: list[ConstructionComponent],
    path_records: list[PathRecord],
    construction_units: set[str],
    config: AnchorAggregationConfig,
) -> list[ConstructionWindow]:
    """
    基于 path 命中区间补充窗口

    对每条 path：
    - hit_seq = path 中属于 construction_units 的收费单元序列
    - first_hit = hit_seq[0]
    - last_hit = hit_seq[-1]

    将高频或高流量的 first_hit -> last_hit 补充为局部窗口。

    Args:
        construction_id: 施工工程 ID
        components: 施工片区列表（用于判断 first_hit/last_hit 归属）
        path_records: path 记录列表
        construction_units: 施工单元集合
        config: 配置

    Returns:
        list[ConstructionWindow]: 从 path 命中生成的窗口列表
    """
    if not config.construction_window.enable_path_hit_windows:
        return []

    component_by_unit: dict[str, ConstructionComponent] = {}
    for comp in components:
        for unit in comp.units:
            component_by_unit[unit] = comp

    hit_intervals: dict[tuple[str, str], dict[str, int | float]] = defaultdict(
        lambda: {"flow": 0.0, "count": 0}
    )

    for record in path_records:
        hit_units = [u for u in record.path if u in construction_units]
        if not hit_units:
            continue

        first_hit = hit_units[0]
        last_hit = hit_units[-1]

        if first_hit == last_hit:
            continue

        key = (first_hit, last_hit)
        hit_intervals[key]["flow"] += record.flow
        hit_intervals[key]["count"] += 1

    min_flow = config.construction_window.min_path_hit_flow
    min_count = config.construction_window.min_path_hit_count
    max_windows = config.construction_window.max_windows_per_component

    windows: list[ConstructionWindow] = []
    filtered_intervals = [
        (key, stats)
        for key, stats in hit_intervals.items()
        if stats["flow"] >= min_flow and stats["count"] >= min_count
    ]

    filtered_intervals.sort(key=lambda x: x[1]["flow"], reverse=True)
    filtered_intervals = filtered_intervals[:max_windows]

    for (first_hit, last_hit), stats in filtered_intervals:
        comp = component_by_unit.get(first_hit)
        if comp is None:
            comp = component_by_unit.get(last_hit)
        if comp is None:
            comp_id = f"{construction_id}_unknown"
        else:
            comp_id = comp.component_id

        covered = {u for u in construction_units if _is_between(first_hit, last_hit, u)}
        if not covered:
            covered = {first_hit, last_hit}

        window = ConstructionWindow(
            construction_id=construction_id,
            component_id=comp_id,
            window_id=f"{construction_id}_{comp_id}_pathhit_{first_hit}_{last_hit}",
            start_unit=first_hit,
            end_unit=last_hit,
            covered_units=covered,
            source="path_hit",
            source_flow=stats["flow"],
            source_path_count=stats["count"],
        )
        windows.append(window)

    logger.debug(
        f"[window_build] path_hit_windows={len(windows)}"
    )

    return windows


def _is_between(start: str, end: str, unit: str) -> bool:
    """
    判断 unit 是否在 start 和 end 之间

    这是一个简化的判断，假设 start < end 是路径上的相对顺序。
    实际应该用拓扑可达性判断。
    """
    return start <= unit <= end


def deduplicate_construction_windows(
    windows: list[ConstructionWindow],
) -> list[ConstructionWindow]:
    """
    对局部施工窗口去重

    同一 (start_unit, end_unit) 保留 flow 最大的窗口。

    Args:
        windows: 窗口列表（可能有重复）

    Returns:
        list[ConstructionWindow]: 去重后的窗口列表
    """
    unique_windows: dict[tuple[str, str], ConstructionWindow] = {}

    for window in windows:
        key = (window.start_unit, window.end_unit)
        if key not in unique_windows:
            unique_windows[key] = window
        else:
            existing = unique_windows[key]
            if window.source_flow > existing.source_flow:
                unique_windows[key] = window

    result = list(unique_windows.values())
    logger.debug(
        f"[window_build] deduplicated: {len(windows)} -> {len(result)} windows"
    )
    return result


def build_all_construction_windows(
    construction_id: str,
    components: list[ConstructionComponent],
    topology: TopologyGraph,
    path_records: list[PathRecord],
    construction_units: set[str],
    config: AnchorAggregationConfig,
) -> list[ConstructionWindow]:
    """
    构建所有局部施工窗口（门户窗口 + path 命中窗口）

    Args:
        construction_id: 施工工程 ID
        components: 施工片区列表
        topology: 有向拓扑图
        path_records: path 记录列表
        construction_units: 施工单元集合
        config: 配置

    Returns:
        list[ConstructionWindow]: 局部施工窗口列表
    """
    all_windows: list[ConstructionWindow] = []

    for component in components:
        if config.construction_window.enable_portal_windows:
            portal_windows = build_windows_by_portals(
                construction_id=construction_id,
                component=component,
                topology=topology,
            )
            all_windows.extend(portal_windows)

    path_hit_windows = build_windows_by_path_hits(
        construction_id=construction_id,
        components=components,
        path_records=path_records,
        construction_units=construction_units,
        config=config,
    )
    all_windows.extend(path_hit_windows)

    all_windows = deduplicate_construction_windows(all_windows)

    logger.info(
        f"[window_build] construction_id={construction_id}: "
        f"total_windows={len(all_windows)}"
    )

    return all_windows