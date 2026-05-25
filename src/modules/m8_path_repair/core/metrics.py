"""
M8 路径修正 — 折返指标与质量评分

计算以下指标：
1. repeated_node_count — 重复出现的节点数量
2. reverse_edge_count — 反向边数量（A→B 后又 B→A）
3. backward_progress_count — 到终点距离反增次数
4. backward_progress_distance — 到终点距离反增累计距离
5. u_turn_count — 几何掉头次数（连续三点方向角变化接近 180°）
6. detour_ratio — 绕行比
7. backtrack_index — 综合折返指数 0-100

以及：
- repair_confidence — 修正置信度 0-100
- repair_status — 修正状态枚举
"""

import math
from typing import Optional


# ============================================================
# 折返指标计算
# ============================================================


def calc_repeated_node_count(path: list[str]) -> int:
    """计算重复出现的节点数量（出现次数 > 1 的节点总数）"""
    from collections import Counter

    counts = Counter(path)
    return sum(1 for c in counts.values() if c > 1)


def calc_reverse_edge_count(path: list[str]) -> int:
    """
    如果路径中出现 A->B 和 B->A，则计为反向边。
    返回反向边对的数量。
    """
    if len(path) < 3:
        return 0

    edges_seen: set[tuple[str, str]] = set()
    reverse_count = 0
    for i in range(len(path) - 1):
        edge = (path[i], path[i + 1])
        reverse_edge = (path[i + 1], path[i])
        if reverse_edge in edges_seen:
            reverse_count += 1
        edges_seen.add(edge)

    return reverse_count


def calc_backward_progress(
    path: list[str],
    end_node: str,
    graph,
    threshold_m: float = 300.0,
) -> dict:
    """
    计算沿路径前进过程中，到终点最短距离是否反增。

    Args:
        path: 修正后的节点路径
        end_node: 终点节点
        graph: RoadGraph 实例
        threshold_m: 反增判定阈值（米），低于此值视为噪声

    Returns:
        {
            "backward_progress_count": int,
            "backward_progress_distance": float
        }
    """
    if len(path) < 2:
        return {"backward_progress_count": 0, "backward_progress_distance": 0.0}

    # 预计算每个节点到终点的最短距离
    dist_to_end: dict[str, Optional[float]] = {}
    for node in path:
        if node == end_node:
            dist_to_end[node] = 0.0
        else:
            _, dist = graph.shortest_path(node, end_node)
            dist_to_end[node] = dist

    backward_count = 0
    backward_dist = 0.0

    for i in range(len(path) - 1):
        d_curr = dist_to_end.get(path[i])
        d_next = dist_to_end.get(path[i + 1])

        if d_curr is not None and d_next is not None:
            diff = d_next - d_curr
            if diff > threshold_m:
                backward_count += 1
                backward_dist += diff

    return {
        "backward_progress_count": backward_count,
        "backward_progress_distance": round(backward_dist, 1),
    }


def _bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """计算两个点之间的方位角（度，0-360）"""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    d_lon = lon2 - lon1

    x = math.sin(d_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)

    bearing_rad = math.atan2(x, y)
    return (math.degrees(bearing_rad) + 360) % 360


def _angle_diff(angle1: float, angle2: float) -> float:
    """计算两个方向角的最小夹角（度）"""
    diff = abs(angle1 - angle2) % 360
    return min(diff, 360 - diff)


def calc_u_turn_count(
    geo_points: list[dict], angle_threshold: float = 150.0
) -> int:
    """
    根据连续三点方位角变化识别近似掉头。

    Args:
        geo_points: [{"node_id": str, "lon": float, "lat": float}, ...]
        angle_threshold: 夹角阈值，超过此值视为掉头

    Returns:
        掉头次数
    """
    if len(geo_points) < 3:
        return 0

    uturn_count = 0
    for i in range(len(geo_points) - 2):
        p1 = geo_points[i]
        p2 = geo_points[i + 1]
        p3 = geo_points[i + 2]

        if p1["lon"] is None or p2["lon"] is None or p3["lon"] is None:
            continue

        b1 = _bearing(p1["lon"], p1["lat"], p2["lon"], p2["lat"])
        b2 = _bearing(p2["lon"], p2["lat"], p3["lon"], p3["lat"])
        diff = _angle_diff(b1, b2)

        if diff >= angle_threshold:
            uturn_count += 1

    return uturn_count


def calc_detour_ratio(
    path: list[str],
    start_node: str,
    end_node: str,
    graph,
) -> float:
    """
    计算绕行比 = 修正路径总长度 / 起终点最短路长度
    """
    if len(path) < 2:
        return 1.0

    # 计算修正路径总长度
    total_length = 0.0
    for i in range(len(path) - 1):
        _, cost = graph.shortest_path(path[i], path[i + 1])
        if cost is not None:
            total_length += cost

    # 起终点最短路长度
    _, shortest = graph.shortest_path(start_node, end_node)
    if shortest is None or shortest == 0:
        return 1.0

    return round(total_length / shortest, 4)


def calc_path_length_meters(path: list[str], graph) -> float:
    """计算路径总长度（米）"""
    total = 0.0
    for i in range(len(path) - 1):
        _, cost = graph.shortest_path(path[i], path[i + 1])
        if cost is not None:
            total += cost
    return total


def calc_backtrack_index(metrics: dict) -> float:
    """
    计算 0~100 的综合折返指数。

    建议公式：
    BTI = 30 * reverse_score + 25 * backward_score + 20 * repeat_score
         + 15 * uturn_score + 10 * detour_score
    """
    reverse_score = min(metrics.get("reverse_edge_count", 0) / 2.0, 1.0)
    backward_score = min(metrics.get("backward_progress_count", 0) / 3.0, 1.0)
    repeat_score = min(metrics.get("repeated_node_count", 0) / 3.0, 1.0)
    uturn_score = min(metrics.get("u_turn_count", 0) / 2.0, 1.0)
    detour_ratio = metrics.get("detour_ratio", 1.0)
    detour_score = min(max(detour_ratio - 1.2, 0.0) / 1.0, 1.0)

    bti = (
        30.0 * reverse_score
        + 25.0 * backward_score
        + 20.0 * repeat_score
        + 15.0 * uturn_score
        + 10.0 * detour_score
    )

    return round(min(bti, 100.0), 1)


# ============================================================
# 质量评分
# ============================================================

REPAIR_STATUS_HIGH = "HIGH_CONFIDENCE"
REPAIR_STATUS_MEDIUM = "MEDIUM_CONFIDENCE"
REPAIR_STATUS_LOW = "LOW_CONFIDENCE"
REPAIR_STATUS_REVIEW = "NEED_MANUAL_REVIEW"
REPAIR_STATUS_FAILED_NO_PATH = "FAILED_NO_PATH"
REPAIR_STATUS_FAILED_AMBIGUOUS = "FAILED_AMBIGUOUS_SE"
REPAIR_STATUS_FAILED_EMPTY = "FAILED_EMPTY_PATH"


def calc_repair_confidence(
    raw_match_ratio: float,
    dropped_node_count: int,
    inserted_node_count: int,
    raw_node_count: int,
    detour_ratio: float,
    backtrack_index: float,
    anchor_count: int = 0,
    total_node_count: int = 0,
) -> float:
    """
    计算 0~100 的修正置信度。

    confidence = 100
    - 删除节点比例惩罚
    - 插入节点比例惩罚
    - 绕行比惩罚
    - 折返指数惩罚
    - 锚点不足惩罚
    """
    confidence = 100.0

    if raw_node_count > 0:
        dropped_ratio = dropped_node_count / raw_node_count
        inserted_ratio = inserted_node_count / raw_node_count
    else:
        dropped_ratio = 0.0
        inserted_ratio = 0.0

    confidence -= dropped_ratio * 25.0
    confidence -= inserted_ratio * 15.0
    confidence -= max(detour_ratio - 1.2, 0.0) * 30.0
    confidence -= backtrack_index * 0.5

    # 锚点不足惩罚
    if total_node_count > 0 and anchor_count < total_node_count * 0.3:
        confidence -= 10.0

    return round(max(min(confidence, 100.0), 0.0), 1)


def get_repair_status(confidence: float, backtrack_index: float) -> str:
    """
    根据置信度和折返指数返回修正状态。
    """
    if confidence >= 85:
        return REPAIR_STATUS_HIGH
    elif confidence >= 65:
        return REPAIR_STATUS_MEDIUM
    elif confidence >= 40:
        return REPAIR_STATUS_LOW
    else:
        return REPAIR_STATUS_REVIEW
