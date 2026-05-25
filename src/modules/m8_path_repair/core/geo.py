"""
M8 路径修正 — 经纬度匹配

将修正后的节点路径转换为经纬度点序列。
"""

from typing import Optional


def attach_lonlat(
    corrected_nodes: list[str],
    graph,
) -> list[dict]:
    """
    为修正后的节点路径匹配经纬度。

    Args:
        corrected_nodes: 修正后的节点路径
        graph: RoadGraph 实例（包含 node_info 缓存）

    Returns:
        [
            {"seq": 1, "node_id": "...", "lon": 108.123, "lat": 34.456},
            ...
        ]

    注意：
    - 如果某个节点缺少经纬度，不会中断主流程
    - 缺失的 lon/lat 设为 None
    """
    result = []
    missing_nodes = []

    for seq, node_id in enumerate(corrected_nodes, start=1):
        info = graph.get_node_info(node_id)
        if info is not None:
            lon = info.get("lon")
            lat = info.get("lat")
        else:
            lon = None
            lat = None
            missing_nodes.append(node_id)

        result.append({
            "seq": seq,
            "node_id": node_id,
            "lon": lon,
            "lat": lat,
        })

    return result


def get_missing_geo_nodes(geo_points: list[dict]) -> list[str]:
    """获取缺少经纬度信息的节点列表"""
    return [p["node_id"] for p in geo_points if p["lon"] is None or p["lat"] is None]
