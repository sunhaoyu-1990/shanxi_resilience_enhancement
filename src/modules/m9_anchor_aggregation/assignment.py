"""
M9 施工锚点聚合模块 - path 全局唯一归属
保证每条 path 在同一个 construction_id 下只归属一个锚点窗口

归属优先级（第一版）：
1. min_level（越小越好）
2. len(covered_units)（越小越局部）
3. anchor_start + anchor_end（稳定排序兜底）
"""

from typing import Optional

from src.app.logger import get_logger
from src.modules.m9_anchor_aggregation.models import (
    PathRecord,
    AnchorWindow,
    PathAssignment,
)
from src.modules.m9_anchor_aggregation.path_classifier import (
    has_ordered_pair,
    extract_hit_units,
    get_first_and_last_hit,
)

logger = get_logger(__name__)


def score_anchor_window(window: AnchorWindow) -> tuple:
    """
    计算锚点窗口的优先级分数

    分数越小，优先级越高。

    Args:
        window: 锚点窗口

    Returns:
        tuple: 优先级元组
    """
    return (
        window.min_level,
        len(window.covered_units),
        window.anchor_start,
        window.anchor_end,
    )


def assign_path_to_best_window(
    record: PathRecord,
    anchor_windows: list[AnchorWindow],
    construction_units: set[str],
) -> PathAssignment:
    """
    将单条 path 归属到最佳锚点窗口

    遍历所有锚点窗口，找到所有 path 经过的窗口，按优先级排序后选择最佳窗口。

    Args:
        record: path 记录
        anchor_windows: 锚点窗口列表
        construction_units: 施工单元集合

    Returns:
        PathAssignment: 归属结果
    """
    path_units = record.path
    candidate_windows: list[tuple[AnchorWindow, int, int]] = []

    for window in anchor_windows:
        if not has_ordered_pair(path_units, window.anchor_start, window.anchor_end):
            continue

        hit_units = extract_hit_units(path_units, construction_units)
        route_type = "pass" if hit_units else "bypass"
        candidate_windows.append((window, len(hit_units), route_type))

    if not candidate_windows:
        return PathAssignment(
            construction_id=record.path[0] if record.path else "",
            record_id=record.record_id,
            enid=record.enid,
            exid=record.exid,
            assigned_anchor_start=None,
            assigned_anchor_end=None,
            route_type="unassigned",
            hit_units=[],
            first_hit=None,
            last_hit=None,
            assignment_reason="no_matching_window",
            flow=record.flow,
        )

    candidate_windows.sort(key=lambda x: (score_anchor_window(x[0]), -x[1]))
    best_window = candidate_windows[0][0]

    hit_units = extract_hit_units(path_units, construction_units)
    first_hit, last_hit, all_hit_units = get_first_and_last_hit(path_units, construction_units)
    route_type = candidate_windows[0][2]

    reason = f"matched_window({best_window.anchor_start},{best_window.anchor_end})"
    if route_type == "pass":
        reason += f",hit_units={len(hit_units)}"
    else:
        reason += ",bypass"

    return PathAssignment(
        construction_id=best_window.construction_id,
        record_id=record.record_id,
        enid=record.enid,
        exid=record.exid,
        assigned_anchor_start=best_window.anchor_start,
        assigned_anchor_end=best_window.anchor_end,
        route_type=route_type,
        hit_units=hit_units,
        first_hit=first_hit,
        last_hit=last_hit,
        assignment_reason=reason,
        flow=record.flow,
    )


def assign_all_paths(
    path_records: list[PathRecord],
    anchor_windows: list[AnchorWindow],
    construction_units: set[str],
) -> list[PathAssignment]:
    """
    对所有 path 进行全局唯一归属

    Args:
        path_records: path 记录列表
        anchor_windows: 锚点窗口列表
        construction_units: 施工单元集合

    Returns:
        list[PathAssignment]: 归属结果列表
    """
    assignments: list[PathAssignment] = []
    assigned_count = 0
    bypass_count = 0
    pass_count = 0
    unassigned_count = 0

    for record in path_records:
        assignment = assign_path_to_best_window(
            record=record,
            anchor_windows=anchor_windows,
            construction_units=construction_units,
        )
        assignments.append(assignment)

        if assignment.route_type == "pass":
            pass_count += 1
        elif assignment.route_type == "bypass":
            bypass_count += 1
        else:
            unassigned_count += 1

    logger.info(
        f"[assignment] total_records={len(path_records)}, "
        f"assigned={assigned_count}, "
        f"pass={pass_count}, bypass={bypass_count}, unassigned={unassigned_count}"
    )

    return assignments


def validate_unique_assignment(
    assignments: list[PathAssignment],
) -> list[str]:
    """
    验证归属结果的唯一性

    Args:
        assignments: 归属结果列表

    Returns:
        list[str]: 错误信息列表
    """
    errors: list[str] = []

    record_to_assignments: dict[str, list[PathAssignment]] = {}
    for assignment in assignments:
        if assignment.route_type == "unassigned":
            continue
        key = f"{assignment.construction_id}:{assignment.record_id}"
        if key not in record_to_assignments:
            record_to_assignments[key] = []
        record_to_assignments[key].append(assignment)

    for key, records in record_to_assignments.items():
        if len(records) > 1:
            errors.append(
                f"Duplicate assignment for {key}: "
                f"{len(records)} windows"
            )

    total_assigned_flow = sum(a.flow for a in assignments if a.route_type != "unassigned")
    total_flow = sum(a.flow for a in assignments)
    if total_assigned_flow > total_flow * 1.01:
        errors.append(
            f"Assigned flow ({total_assigned_flow:.2f}) exceeds "
            f"total flow ({total_flow:.2f})"
        )

    return errors