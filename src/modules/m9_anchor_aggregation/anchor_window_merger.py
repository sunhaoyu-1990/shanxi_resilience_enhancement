"""
M9 施工锚点聚合模块 - 锚点窗口合并
将多个局部施工窗口外扩产生的候选锚点，按 (construction_id, anchor_start, anchor_end) 合并

合并规则：
- key = construction_id + anchor_start + anchor_end
- source_component_ids = union
- source_window_ids = union
- covered_units = union
- min_level = min(level)
"""

from collections import defaultdict

from src.app.logger import get_logger
from src.modules.m9_anchor_aggregation.models import (
    ConstructionWindow,
    RawAnchorCandidate,
    AnchorWindow,
)

logger = get_logger(__name__)


def merge_anchor_candidates_to_windows(
    candidates: list[RawAnchorCandidate],
    window_map: dict[str, ConstructionWindow],
) -> list[AnchorWindow]:
    """
    将锚点候选合并为全局锚点窗口

    按 (construction_id, anchor_start, anchor_end) 分组合并。

    Args:
        candidates: 锚点候选列表
        window_map: window_id -> ConstructionWindow 映射

    Returns:
        list[AnchorWindow]: 合并后的锚点窗口列表
    """
    merged: dict[tuple[str, str, str], AnchorWindow] = {}

    for candidate in candidates:
        key = (candidate.construction_id, candidate.anchor_start, candidate.anchor_end)

        if key not in merged:
            window = window_map.get(candidate.window_id)
            covered = window.covered_units if window else set()

            merged[key] = AnchorWindow(
                construction_id=candidate.construction_id,
                anchor_start=candidate.anchor_start,
                anchor_end=candidate.anchor_end,
                source_component_ids={candidate.component_id},
                source_window_ids={candidate.window_id},
                covered_units=covered.copy(),
                min_level=candidate.level,
            )
        else:
            aw = merged[key]
            aw.source_component_ids.add(candidate.component_id)
            aw.source_window_ids.add(candidate.window_id)
            aw.min_level = min(aw.min_level, candidate.level)

            window = window_map.get(candidate.window_id)
            if window:
                aw.covered_units |= window.covered_units

    result = list(merged.values())

    logger.info(
        f"[anchor_merge] raw_candidates={len(candidates)}, "
        f"merged_anchor_windows={len(result)}"
    )

    for aw in result:
        logger.debug(
            f"  anchor=({aw.anchor_start}, {aw.anchor_end}): "
            f"level={aw.min_level}, "
            f"source_windows={len(aw.source_window_ids)}, "
            f"covered_units={len(aw.covered_units)}"
        )

    return result


def deduplicate_anchor_windows(
    anchor_windows: list[AnchorWindow],
) -> list[AnchorWindow]:
    """
    对锚点窗口列表去重（基于 key）

    Args:
        anchor_windows: 锚点窗口列表

    Returns:
        list[AnchorWindow]: 去重后的列表
    """
    seen: dict[tuple[str, str, str], AnchorWindow] = {}

    for aw in anchor_windows:
        key = aw.key
        if key not in seen:
            seen[key] = aw

    result = list(seen.values())
    if len(result) < len(anchor_windows):
        logger.debug(
            f"[anchor_merge] deduplicated: {len(anchor_windows)} -> {len(result)}"
        )
    return result