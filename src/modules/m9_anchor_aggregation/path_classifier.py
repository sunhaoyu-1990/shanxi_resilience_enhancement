"""
M9 施工锚点聚合模块 - path 分类
判断 path 是 pass / bypass / unassigned

分类规则：
- pass: path 按顺序经过 anchor_start -> anchor_end，且命中 covered_units
- bypass: path 按顺序经过 anchor_start -> anchor_end，但未命中 covered_units
- unassigned: path 不经过 anchor_start -> anchor_end 或不匹配任何锚点窗口
"""

from typing import Optional

from src.modules.m9_anchor_aggregation.models import (
    PathRecord,
    AnchorWindow,
    ConstructionWindow,
)


def has_ordered_pair(path_units: list[str], start: str, end: str) -> bool:
    """
    判断 path 是否按顺序经过 start -> end

    注意：path 中可能有重复单元，不能用 index()。
    使用 min(start_positions) < max(end_positions) 判断。

    Args:
        path_units: path 单元列表
        start: 起点单元
        end: 终点单元

    Returns:
        bool: 是否按顺序经过
    """
    start_positions = [i for i, u in enumerate(path_units) if u == start]
    end_positions = [i for i, u in enumerate(path_units) if u == end]
    if not start_positions or not end_positions:
        return False
    return min(start_positions) < max(end_positions)


def extract_hit_units(path_units: list[str], construction_units: set[str]) -> list[str]:
    """
    提取 path 中命中施工单元的序列

    Args:
        path_units: path 单元列表
        construction_units: 施工单元集合

    Returns:
        list[str]: 命中的施工单元列表（按原顺序）
    """
    return [u for u in path_units if u in construction_units]


def classify_path_for_anchor_window(
    path_units: list[str],
    window: AnchorWindow,
) -> Optional[str]:
    """
    对单个锚点窗口判断 path 的类型

    Args:
        path_units: path 单元列表
        window: 锚点窗口

    Returns:
        "pass": 经过锚点且命中施工单元
        "bypass": 经过锚点但未命中施工单元
        None: 不经过锚点
    """
    if not has_ordered_pair(path_units, window.anchor_start, window.anchor_end):
        return None

    hit_units = extract_hit_units(path_units, window.covered_units)
    if hit_units:
        return "pass"
    else:
        return "bypass"


def classify_path_for_construction_windows(
    path_units: list[str],
    windows: list[ConstructionWindow],
    construction_units: set[str],
) -> Optional[tuple[str, str, str]]:
    """
    对多个局部施工窗口判断 path 的类型

    返回第一个匹配的窗口信息：(start_unit, end_unit, route_type)

    Args:
        path_units: path 单元列表
        windows: 局部施工窗口列表
        construction_units: 施工单元集合

    Returns:
        (start_unit, end_unit, route_type) 或 None
    """
    for window in windows:
        if not has_ordered_pair(path_units, window.start_unit, window.end_unit):
            continue

        hit_units = extract_hit_units(path_units, window.covered_units)
        route_type = "pass" if hit_units else "bypass"
        return (window.start_unit, window.end_unit, route_type)

    return None


def get_first_and_last_hit(
    path_units: list[str],
    construction_units: set[str],
) -> tuple[Optional[str], Optional[str], list[str]]:
    """
    获取 path 命中的第一个和最后一个施工单元

    Args:
        path_units: path 单元列表
        construction_units: 施工单元集合

    Returns:
        (first_hit, last_hit, hit_units)
    """
    hit_units = extract_hit_units(path_units, construction_units)
    if not hit_units:
        return (None, None, [])
    return (hit_units[0], hit_units[-1], hit_units)


def classify_all_paths_for_anchor_window(
    path_records: list[PathRecord],
    window: AnchorWindow,
    construction_units: set[str],
) -> list[tuple[PathRecord, Optional[str]]]:
    """
    对锚点窗口批量分类所有 path

    Args:
        path_records: path 记录列表
        window: 锚点窗口
        construction_units: 施工单元集合

    Returns:
        list[(PathRecord, route_type)]: path 记录及其类型
    """
    results: list[tuple[PathRecord, Optional[str]]] = []
    for record in path_records:
        route_type = classify_path_for_anchor_window(record.path, window)
        results.append((record, route_type))
    return results