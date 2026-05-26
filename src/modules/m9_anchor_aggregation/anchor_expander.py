"""
M9 施工锚点聚合模块 - 锚点外扩
对每个局部施工窗口，从窗口起终点向外生成候选锚点

基本逻辑：
- 窗口 start_unit 的外部上游方向：沿 upstream_adj 外扩
- 窗口 end_unit 的外部下游方向：沿 downstream_adj 外扩

有效性条件：
- pass_flow >= min_pass_flow
- bypass_flow >= min_pass_flow
- pass_path_count >= min_pass_path_count
- bypass_path_count >= min_bypass_path_count

停止条件：
- stop_at_first_valid=True: 找到第一个有效 level 后停止
- 达到 max_expand_level 后停止
"""

from typing import Optional

from src.app.logger import get_logger
from src.modules.m9_anchor_aggregation.models import (
    ConstructionWindow,
    RawAnchorCandidate,
    PathRecord,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph
from src.modules.m9_anchor_aggregation.config import AnchorAggregationConfig

logger = get_logger(__name__)


def expand_upstream_levels(
    start: str,
    topology: TopologyGraph,
    blocked: set[str],
    max_level: int,
) -> dict[int, set[str]]:
    """
    BFS 向上游扩展，返回每层节点

    Args:
        start: 起始节点
        topology: 有向拓扑图
        blocked: 阻塞节点（施工单元，不访问）
        max_level: 最大扩展层级

    Returns:
        dict[int, set[str]]: {level: nodes_at_level}
    """
    return topology.bfs_expand_upstream(start, blocked, max_level)


def expand_downstream_levels(
    end: str,
    topology: TopologyGraph,
    blocked: set[str],
    max_level: int,
) -> dict[int, set[str]]:
    """
    BFS 向下游扩展，返回每层节点

    Args:
        end: 起始节点
        topology: 有向拓扑图
        blocked: 阻塞节点（施工单元，不访问）
        max_level: 最大扩展层级

    Returns:
        dict[int, set[str]]: {level: nodes_at_level}
    """
    return topology.bfs_expand_downstream(end, blocked, max_level)


def _check_anchor_validity(
    anchor_start: str,
    anchor_end: str,
    path_records: list[PathRecord],
    construction_units: set[str],
    unit_index: dict[str, set[int]],
    config: AnchorAggregationConfig,
) -> tuple[bool, float, float, int, int]:
    """
    检查锚点有效性

    Args:
        anchor_start: 锚点起点
        anchor_end: 锚点终点
        path_records: path 记录列表
        construction_units: 施工单元集合
        unit_index: 单元倒排索引
        config: 配置

    Returns:
        (is_valid, pass_flow, bypass_flow, pass_count, bypass_count)
    """
    min_pass = config.valid_anchor.min_pass_flow
    min_bypass = config.valid_anchor.min_bypass_flow
    min_pass_cnt = config.valid_anchor.min_pass_path_count
    min_bypass_cnt = config.valid_anchor.min_bypass_path_count

    candidate_indices = unit_index.get(anchor_start, set()) & unit_index.get(anchor_end, set())

    pass_flow = 0.0
    bypass_flow = 0.0
    pass_count = 0
    bypass_count = 0

    for idx in candidate_indices:
        record = path_records[idx]
        path_units = record.path

        if not _has_ordered_pair(path_units, anchor_start, anchor_end):
            continue

        hit_units = [u for u in path_units if u in construction_units]
        if hit_units:
            pass_flow += record.flow
            pass_count += 1
        else:
            bypass_flow += record.flow
            bypass_count += 1

    is_valid = (
        pass_flow >= min_pass
        and bypass_flow >= min_bypass
        and pass_count >= min_pass_cnt
        and bypass_count >= min_bypass_cnt
    )

    return is_valid, pass_flow, bypass_flow, pass_count, bypass_count


def _has_ordered_pair(path_units: list[str], start: str, end: str) -> bool:
    """
    判断 path 是否按顺序经过 start -> end

    注意：path 中可能有重复单元，不能用 index()。
    """
    start_positions = [i for i, u in enumerate(path_units) if u == start]
    end_positions = [i for i, u in enumerate(path_units) if u == end]
    if not start_positions or not end_positions:
        return False
    return min(start_positions) < max(end_positions)


def find_valid_anchor_candidates_for_window(
    window: ConstructionWindow,
    path_records: list[PathRecord],
    topology: TopologyGraph,
    config: AnchorAggregationConfig,
    unit_index: dict[str, set[int]],
) -> list[RawAnchorCandidate]:
    """
    对单个局部施工窗口，找最近有效锚点候选

    逐级外扩，每级检查 (anchor_start, anchor_end) 是否满足有效性条件。
    找到第一个有效 level 后停止（如果 stop_at_first_valid=True）。

    Args:
        window: 局部施工窗口
        path_records: path 记录列表
        topology: 有向拓扑图
        config: 配置
        unit_index: 单元倒排索引

    Returns:
        list[RawAnchorCandidate]: 有效锚点候选列表
    """
    max_level = config.anchor_expand.max_expand_level
    stop_at_first = config.anchor_expand.stop_at_first_valid

    blocked = window.covered_units

    upstream_levels = expand_upstream_levels(window.start_unit, topology, blocked, max_level)
    downstream_levels = expand_downstream_levels(window.end_unit, topology, blocked, max_level)

    candidates: list[RawAnchorCandidate] = []
    found_valid = False

    for level in range(max_level + 1):
        anchor_starts = upstream_levels.get(level, set())
        anchor_ends = downstream_levels.get(level, set())

        if not anchor_starts or not anchor_ends:
            continue

        for anchor_start in anchor_starts:
            for anchor_end in anchor_ends:
                is_valid, pass_flow, bypass_flow, pass_cnt, bypass_cnt = _check_anchor_validity(
                    anchor_start=anchor_start,
                    anchor_end=anchor_end,
                    path_records=path_records,
                    construction_units=window.covered_units,
                    unit_index=unit_index,
                    config=config,
                )

                candidate = RawAnchorCandidate(
                    construction_id=window.construction_id,
                    component_id=window.component_id,
                    window_id=window.window_id,
                    anchor_start=anchor_start,
                    anchor_end=anchor_end,
                    level=level,
                )
                candidates.append(candidate)

                if is_valid:
                    logger.debug(
                        f"[anchor_expand] window_id={window.window_id}: "
                        f"level={level}, anchor=({anchor_start}, {anchor_end}), "
                        f"valid, pass_flow={pass_flow:.0f}, bypass_flow={bypass_flow:.0f}"
                    )
                    if stop_at_first:
                        found_valid = True
                        break

            if found_valid and stop_at_first:
                break

        if found_valid and stop_at_first:
            break

    valid_count = len([c for c in candidates if _is_candidate_valid(
        c, path_records, window.covered_units, unit_index, config
    )])
    logger.info(
        f"[anchor_expand] window_id={window.window_id}: "
        f"candidates={len(candidates)}, valid={valid_count}"
    )

    return candidates


def _is_candidate_valid(
    candidate: RawAnchorCandidate,
    path_records: list[PathRecord],
    construction_units: set[str],
    unit_index: dict[str, set[int]],
    config: AnchorAggregationConfig,
) -> bool:
    """判断候选锚点是否有效"""
    _, pass_flow, bypass_flow, pass_cnt, bypass_cnt = _check_anchor_validity(
        candidate.anchor_start,
        candidate.anchor_end,
        path_records,
        construction_units,
        unit_index,
        config,
    )
    return pass_flow >= config.valid_anchor.min_pass_flow


def find_valid_anchor_candidates_for_all_windows(
    windows: list[ConstructionWindow],
    path_records: list[PathRecord],
    topology: TopologyGraph,
    config: AnchorAggregationConfig,
    unit_index: dict[str, set[int]],
) -> list[RawAnchorCandidate]:
    """
    对所有局部施工窗口，找有效锚点候选

    Args:
        windows: 局部施工窗口列表
        path_records: path 记录列表
        topology: 有向拓扑图
        config: 配置
        unit_index: 单元倒排索引

    Returns:
        list[RawAnchorCandidate]: 所有窗口的有效锚点候选列表
    """
    all_candidates: list[RawAnchorCandidate] = []

    for window in windows:
        candidates = find_valid_anchor_candidates_for_window(
            window=window,
            path_records=path_records,
            topology=topology,
            config=config,
            unit_index=unit_index,
        )
        all_candidates.extend(candidates)

    logger.info(
        f"[anchor_expand] total candidates={len(all_candidates)} "
        f"from {len(windows)} windows"
    )

    return all_candidates