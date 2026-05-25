"""
M8 路径修正 — 可视化模块

生成路径修正结果的可视化图片，包含：
1. 原始路径与修正路径对比
2. 节点类型标注（锚点、插入、删除）
3. 折返区域高亮
4. 质量指标信息面板

依赖：matplotlib
"""

import math
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from matplotlib.backends.backend_agg import FigureCanvasAgg

from src.app.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 可视化常量
# ============================================================

# 状态颜色
COLOR_ORIGINAL = "#E74C3C"  # 红色 - 原始路径
COLOR_CORRECTED = "#3498DB"  # 蓝色 - 修正路径
COLOR_ANCHOR = "#2ECC71"  # 绿色 - 锚点
COLOR_INSERTED = "#F39C12"  # 橙色 - 插入节点
COLOR_DROPPED = "#95A5A6"  # 灰色 - 删除节点
COLOR_BACKTRACK = "#F1C40F"  # 黄色 - 折返区域
COLOR_START = "#9B59B6"  # 紫色 - 起点
COLOR_END = "#E67E22"  # 橙色 - 终点

# 节点大小
NODE_SIZE_NORMAL = 80
NODE_SIZE_ANCHOR = 150
NODE_SIZE_START_END = 200
NODE_SIZE_INSERTED = 100
NODE_SIZE_DROPPED = 80

# 线条宽度
LINE_WIDTH_ORIGINAL = 2.0
LINE_WIDTH_CORRECTED = 3.0
LINE_WIDTH_BACKTRACK = 5.0

# 字体大小
FONT_SIZE_TITLE = 14
FONT_SIZE_INFO = 10
FONT_SIZE_NODE = 8
FONT_SIZE_LEGEND = 9


# ============================================================
# 主可视化函数
# ============================================================


def visualize_repair_result(
    result: dict,
    graph,
    output_path: Optional[Path] = None,
    figsize: tuple[float, float] = (16, 10),
    title: Optional[str] = None,
) -> Optional[Path]:
    """
    为单条路径修正结果生成可视化图片。

    Args:
        result: repair_single() 返回的结果字典
        graph: RoadGraph 实例
        output_path: 输出图片路径，若为 None 则返回图片对象
        figsize: 图形尺寸 (width, height)
        title: 自定义标题

    Returns:
        输出文件路径，或 None（失败时）
    """
    try:
        # 提取数据
        raw_path = result.get("raw_path", "")
        corrected_path_middle = result.get("corrected_path", "")  # 中间节点
        enid = result.get("enid", "")
        exid = result.get("exid", "")
        status = result.get("repair_status", "UNKNOWN")

        # 重建完整路径：起终点 + 中间节点
        corrected_middle_nodes = [n for n in corrected_path_middle.split("|") if n]
        if enid and corrected_middle_nodes and exid:
            # 完整路径 = enid + 中间节点 + exid
            corrected_nodes = [enid] + corrected_middle_nodes + [exid]
        elif corrected_path_middle:
            # 如果没有起终点，直接用中间节点
            corrected_nodes = corrected_middle_nodes
        else:
            logger.warning("Empty path, cannot visualize")
            return None

        if len(corrected_nodes) < 2:
            logger.warning("Path too short to visualize")
            return None

        raw_nodes = [n for n in raw_path.split("|") if n]

        # 获取经纬度
        raw_geo = _get_geo_points(raw_nodes, graph)
        corrected_geo = _get_geo_points(corrected_nodes, graph)

        if not corrected_geo or all(p["lon"] is None or p["lat"] is None for p in corrected_geo):
            logger.warning("No valid geo coordinates for visualization")
            return None

        # 获取节点分类信息
        node_categories = _classify_nodes(raw_nodes, corrected_nodes, result)

        # 获取折返区域
        backtrack_indices = _find_backtrack_regions(corrected_geo)

        # 绘图
        fig, axes = plt.subplots(1, 2, figsize=figsize, gridspec_kw={"width_ratios": [3, 1]})
        fig.patch.set_facecolor("white")

        # 左图：路径可视化
        ax = axes[0]
        ax.set_facecolor("#FAFAFA")

        _plot_path_map(
            ax=ax,
            raw_geo=raw_geo,
            corrected_geo=corrected_geo,
            raw_nodes=raw_nodes,
            corrected_nodes=corrected_nodes,
            node_categories=node_categories,
            backtrack_indices=backtrack_indices,
            start_node=corrected_nodes[0],
            end_node=corrected_nodes[-1],
        )

        # 右图：信息面板
        ax_info = axes[1]
        ax_info.set_facecolor("#F8F9FA")
        ax_info.axis("off")

        _plot_info_panel(
            ax=ax_info,
            result=result,
            node_categories=node_categories,
            raw_nodes=raw_nodes,
            corrected_nodes=corrected_nodes,
        )

        # 标题
        if title:
            fig.suptitle(title, fontsize=FONT_SIZE_TITLE, fontweight="bold", y=0.98)
        else:
            record_id = result.get("record_id", "Unknown")
            fig.suptitle(
                f"Path Repair Visualization — {record_id}\nStatus: {status}",
                fontsize=FONT_SIZE_TITLE,
                fontweight="bold",
                y=0.98,
            )

        plt.tight_layout(rect=[0, 0, 1, 0.95])

        # 保存或返回
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            logger.info(f"Visualization saved to {output_path}")
            return output_path
        else:
            return None

    except Exception as e:
        logger.exception(f"Visualization failed: {e}")
        plt.close("all")
        return None


def visualize_comparison(
    results: list[dict],
    graph,
    output_dir: Path,
    prefix: str = "path_repair",
    max_count: Optional[int] = None,
) -> list[Path]:
    """
    批量生成路径修正结果可视化图片。

    Args:
        results: repair_single() 返回的结果列表
        graph: RoadGraph 实例
        output_dir: 输出目录
        prefix: 文件名前缀
        max_count: 最大处理数量

    Returns:
        生成的图片路径列表
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if max_count:
        results = results[:max_count]

    output_paths = []
    for i, result in enumerate(results):
        record_id = result.get("record_id", f"row_{i + 1}")
        output_path = output_dir / f"{prefix}_{record_id}.png"

        path = visualize_repair_result(
            result=result,
            graph=graph,
            output_path=output_path,
        )

        if path:
            output_paths.append(path)

    logger.info(f"Generated {len(output_paths)} visualizations to {output_dir}")
    return output_paths


# ============================================================
# 绘图辅助函数
# ============================================================


def _get_geo_points(nodes: list[str], graph) -> list[dict]:
    """获取节点列表的经纬度"""
    geo_points = []
    for node in nodes:
        info = graph.get_node_info(node)
        if info:
            geo_points.append({
                "node_id": node,
                "lon": info.get("lon"),
                "lat": info.get("lat"),
            })
        else:
            geo_points.append({
                "node_id": node,
                "lon": None,
                "lat": None,
            })
    return geo_points


def _classify_nodes(
    raw_nodes: list[str],
    corrected_nodes: list[str],
    result: dict,
) -> dict[str, list[int]]:
    """
    分类节点类型。

    Returns:
        {
            "anchors": [indices in corrected],      # 锚点（原始路径中的节点）
            "inserted": [indices in corrected],    # 插入的节点
            "dropped": [indices in raw],            # 删除的节点
            "start": int,                            # 起点索引
            "end": int,                              # 终点索引
        }
    """
    corrected_set = set(corrected_nodes)
    raw_set = set(raw_nodes)

    anchors = [i for i, n in enumerate(corrected_nodes) if n in raw_set]
    inserted = [i for i, n in enumerate(corrected_nodes) if n not in raw_set]
    dropped = [i for i, n in enumerate(raw_nodes) if n not in corrected_set]

    return {
        "anchors": anchors,
        "inserted": inserted,
        "dropped": dropped,
        "start": 0 if corrected_nodes else None,
        "end": len(corrected_nodes) - 1 if corrected_nodes else None,
    }


def _find_backtrack_regions(geo_points: list[dict]) -> list[tuple[int, int]]:
    """
    识别折返区域。

    Returns:
        [(start_idx, end_idx), ...] 折返区域的起止索引
    """
    if len(geo_points) < 3:
        return []

    regions = []
    in_backtrack = False
    start_idx = 0

    for i in range(len(geo_points) - 2):
        p1, p2, p3 = geo_points[i], geo_points[i + 1], geo_points[i + 2]

        if any(p["lon"] is None for p in [p1, p2, p3]):
            continue

        angle = _calc_angle(
            p1["lon"], p1["lat"],
            p2["lon"], p2["lat"],
            p3["lon"], p3["lat"],
        )

        # 角度接近180度视为折返
        if angle >= 150:
            if not in_backtrack:
                in_backtrack = True
                start_idx = i
        else:
            if in_backtrack:
                regions.append((start_idx, i + 2))
                in_backtrack = False

    if in_backtrack:
        regions.append((start_idx, len(geo_points) - 1))

    return regions


def _calc_angle(lon1: float, lat1: float, lon2: float, lat2: float, lon3: float, lat3: float) -> float:
    """计算三点形成的夹角（度）"""
    # 向量
    v1x, v1y = lon1 - lon2, lat1 - lat2
    v2x, v2y = lon3 - lon2, lat3 - lat2

    # 点积
    dot = v1x * v2x + v1y * v2y
    mag1 = math.sqrt(v1x * v1x + v1y * v1y)
    mag2 = math.sqrt(v2x * v2x + v2y * v2y)

    if mag1 == 0 or mag2 == 0:
        return 0

    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1, min(1, cos_angle))  # 限制范围避免浮点误差

    return math.degrees(math.acos(cos_angle))


def _plot_path_map(
    ax,
    raw_geo: list[dict],
    corrected_geo: list[dict],
    raw_nodes: list[str],
    corrected_nodes: list[str],
    node_categories: dict,
    backtrack_indices: list[tuple[int, int]],
    start_node: str,
    end_node: str,
) -> None:
    """绘制路径地图"""
    # 过滤有效坐标
    valid_raw = [(i, p) for i, p in enumerate(raw_geo) if p["lon"] is not None and p["lat"] is not None]
    valid_corrected = [(i, p) for i, p in enumerate(corrected_geo) if p["lon"] is not None and p["lat"] is not None]

    if not valid_corrected:
        ax.text(0.5, 0.5, "No valid coordinates", ha="center", va="center", transform=ax.transAxes)
        return

    lons = [p["lon"] for _, p in valid_corrected]
    lats = [p["lat"] for _, p in valid_corrected]

    # 自动计算边界
    padding = 0.005
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # 如果有原始路径，加入边界计算
    if valid_raw:
        raw_lons = [p["lon"] for _, p in valid_raw]
        raw_lats = [p["lat"] for _, p in valid_raw]
        min_lon = min(min_lon, min(raw_lons))
        max_lon = max(max_lon, max(raw_lons))
        min_lat = min(min_lat, min(raw_lats))
        max_lat = max(max_lat, max(raw_lats))

    lon_range = max(max_lon - min_lon, 0.01)
    lat_range = max(max_lat - min_lat, 0.01)

    ax.set_xlim(min_lon - padding * lon_range, max_lon + padding * lon_range)
    ax.set_ylim(min_lat - padding * lat_range, max_lat + padding * lat_range)

    # 绘制折返区域高亮
    for start_idx, end_idx in backtrack_indices:
        region_lons = [corrected_geo[i]["lon"] for i in range(start_idx, end_idx + 1) if corrected_geo[i]["lon"] is not None]
        region_lats = [corrected_geo[i]["lat"] for i in range(start_idx, end_idx + 1) if corrected_geo[i]["lat"] is not None]
        if region_lons and region_lats:
            ax.fill(
                region_lons, region_lats,
                color=COLOR_BACKTRACK, alpha=0.2,
                zorder=1,
            )

    # 绘制原始路径（红色虚线）
    if valid_raw:
        raw_x = [p["lon"] for _, p in valid_raw]
        raw_y = [p["lat"] for _, p in valid_raw]
        ax.plot(
            raw_x, raw_y,
            color=COLOR_ORIGINAL, linewidth=LINE_WIDTH_ORIGINAL,
            linestyle="--", alpha=0.6,
            label="Original Path",
            zorder=2,
        )

    # 绘制修正路径（蓝色实线）
    corr_x = [p["lon"] for _, p in valid_corrected]
    corr_y = [p["lat"] for _, p in valid_corrected]
    ax.plot(
        corr_x, corr_y,
        color=COLOR_CORRECTED, linewidth=LINE_WIDTH_CORRECTED,
        linestyle="-",
        label="Corrected Path",
        zorder=3,
    )

    # 绘制节点
    anchors = node_categories["anchors"]
    inserted = node_categories["inserted"]
    dropped = node_categories["dropped"]

    # 插入节点（橙色三角形）
    for idx in inserted:
        p = corrected_geo[idx]
        if p["lon"] is not None and p["lat"] is not None:
            ax.scatter(
                p["lon"], p["lat"],
                marker="^", s=NODE_SIZE_INSERTED,
                color=COLOR_INSERTED, edgecolors="white", linewidth=0.5,
                zorder=5,
            )
            ax.annotate(
                f"{p['node_id'][:8]}..." if len(p['node_id']) > 8 else p['node_id'],
                (p["lon"], p["lat"]),
                textcoords="offset points", xytext=(5, 5),
                fontsize=FONT_SIZE_NODE, color=COLOR_INSERTED,
                zorder=6,
            )

    # 锚点和普通节点
    for idx, p in enumerate(corrected_geo):
        if p["lon"] is None or p["lat"] is None:
            continue
        if idx in dropped:
            continue  # 已删除节点不画

        if idx == 0 or idx == len(corrected_geo) - 1:
            # 起终点用大星形
            marker = "*"
            size = NODE_SIZE_START_END
            color = COLOR_START if idx == 0 else COLOR_END
        elif idx in anchors:
            # 锚点用大方形
            marker = "s"
            size = NODE_SIZE_ANCHOR
            color = COLOR_ANCHOR
        else:
            # 普通节点
            marker = "o"
            size = NODE_SIZE_NORMAL
            color = COLOR_CORRECTED

        ax.scatter(
            p["lon"], p["lat"],
            marker=marker, s=size,
            color=color, edgecolors="white", linewidth=0.5,
            zorder=4,
        )

    # 标注起终点
    if corrected_geo:
        start_p = corrected_geo[0]
        end_p = corrected_geo[-1]
        if start_p["lon"] is not None:
            ax.annotate(
                f"START\n{start_node[:10]}",
                (start_p["lon"], start_p["lat"]),
                textcoords="offset points", xytext=(8, 8),
                fontsize=FONT_SIZE_NODE, fontweight="bold",
                color=COLOR_START,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
                zorder=7,
            )
        if end_p["lon"] is not None:
            ax.annotate(
                f"END\n{end_node[:10]}",
                (end_p["lon"], end_p["lat"]),
                textcoords="offset points", xytext=(8, -15),
                fontsize=FONT_SIZE_NODE, fontweight="bold",
                color=COLOR_END,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
                zorder=7,
            )

    # 图例
    legend_elements = [
        plt.Line2D([0], [0], color=COLOR_ORIGINAL, linewidth=2, linestyle="--", label="Original Path"),
        plt.Line2D([0], [0], color=COLOR_CORRECTED, linewidth=3, label="Corrected Path"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_ANCHOR, markersize=10, label="Anchor Node"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor=COLOR_INSERTED, markersize=10, label="Inserted Node"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor=COLOR_START, markersize=12, label="Start/End"),
        mpatches.Patch(color=COLOR_BACKTRACK, alpha=0.3, label="Backtrack Region"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=FONT_SIZE_LEGEND)

    ax.set_xlabel("Longitude", fontsize=FONT_SIZE_INFO)
    ax.set_ylabel("Latitude", fontsize=FONT_SIZE_INFO)
    ax.set_title("Path Visualization", fontsize=FONT_SIZE_INFO)
    ax.grid(True, alpha=0.3)


def _plot_info_panel(
    ax,
    result: dict,
    node_categories: dict,
    raw_nodes: list[str],
    corrected_nodes: list[str],
) -> None:
    """绘制信息面板"""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    y = 0.95
    line_height = 0.055

    def add_text(text: str, fontsize: float = FONT_SIZE_INFO, color: str = "black", weight: str = "normal"):
        nonlocal y
        ax.text(0.05, y, text, fontsize=fontsize, color=color, fontweight=weight, transform=ax.transAxes, va="top")
        y -= line_height

    # 分隔线
    ax.axhline(y=y + 0.02, color="gray", linewidth=0.5)

    # 基本信息
    add_text("=== Path Information ===", weight="bold")
    add_text(f"Record ID: {result.get('record_id', 'N/A')}")
    add_text(f"Start: {result.get('enid', 'N/A')[:15]}...")
    add_text(f"End: {result.get('exid', 'N/A')[:15]}...")

    # 分隔线
    y -= 0.02
    ax.axhline(y=y, color="gray", linewidth=0.5)
    y -= 0.01

    # 节点统计
    add_text("=== Node Statistics ===", weight="bold")
    add_text(f"Raw Nodes: {result.get('raw_node_count', 0)}")
    add_text(f"Corrected Nodes: {result.get('corrected_node_count', 0)}")
    add_text(f"Inserted: {result.get('inserted_node_count', 0)}", color=COLOR_INSERTED)
    add_text(f"Dropped: {result.get('dropped_node_count', 0)}", color=COLOR_DROPPED)
    add_text(f"Anchors: {len(node_categories['anchors'])}", color=COLOR_ANCHOR)

    # 分隔线
    y -= 0.02
    ax.axhline(y=y, color="gray", linewidth=0.5)
    y -= 0.01

    # 质量指标
    add_text("=== Quality Metrics ===", weight="bold")
    add_text(f"Raw Match Ratio: {result.get('raw_match_ratio', 0):.2%}")
    add_text(f"Detour Ratio: {result.get('detour_ratio', 0):.4f}")

    # 分隔线
    y -= 0.02
    ax.axhline(y=y, color="gray", linewidth=0.5)
    y -= 0.01

    # 折返指标
    add_text("=== Backtrack Metrics ===", weight="bold")
    add_text(f"Reverse Edge: {result.get('reverse_edge_count', 0)}")
    add_text(f"Backward Progress: {result.get('backward_progress_count', 0)}")
    add_text(f"U-Turn Count: {result.get('u_turn_count', 0)}")
    add_text(f"Repeated Node: {result.get('repeated_node_count', 0)}")
    add_text(f"Backtrack Index: {result.get('backtrack_index', 0):.1f}", color="red" if result.get("backtrack_index", 0) > 40 else "black")

    # 分隔线
    y -= 0.02
    ax.axhline(y=y, color="gray", linewidth=0.5)
    y -= 0.01

    # 置信度
    confidence = result.get("repair_confidence", 0)
    status = result.get("repair_status", "UNKNOWN")

    add_text("=== Confidence ===", weight="bold")
    add_text(f"Confidence: {confidence:.1f}%", color="green" if confidence >= 85 else ("orange" if confidence >= 65 else "red"))
    add_text(f"Status: {status}", color="green" if "HIGH" in status else ("orange" if "MEDIUM" in status else "red"))

    # 分隔线
    y -= 0.02
    ax.axhline(y=y, color="gray", linewidth=0.5)
    y -= 0.01

    # 路径详情
    add_text("=== Path Details ===", weight="bold")
    raw_path = result.get("raw_path", "")
    corrected_path_middle = result.get("corrected_path", "")  # 中间节点
    enid = result.get("enid", "")
    exid = result.get("exid", "")

    # 原始路径（截断显示）
    if len(raw_path) > 40:
        raw_display = raw_path[:40] + "..."
    else:
        raw_display = raw_path
    add_text(f"Raw: {raw_display}", fontsize=8)

    # 修正路径中间节点（截断显示）
    if len(corrected_path_middle) > 40:
        corr_display = corrected_path_middle[:40] + "..."
    else:
        corr_display = corrected_path_middle if corrected_path_middle else "(无)"
    add_text(f"Middle: {corr_display}", fontsize=8)

    # 完整路径（起终点 + 中间节点，截断显示）
    if enid and corrected_path_middle and exid:
        full_path = f"{enid}|{corrected_path_middle}|{exid}"
    elif enid and exid:
        full_path = f"{enid}|{exid}"
    else:
        full_path = corrected_path_middle
    if len(full_path) > 40:
        full_display = full_path[:40] + "..."
    else:
        full_display = full_path
    add_text(f"Full: {full_display}", fontsize=8)

    # 绘制置信度条
    y -= 0.04
    ax.text(0.05, y, "Confidence:", fontsize=FONT_SIZE_INFO, transform=ax.transAxes, va="top")
    y -= 0.03

    bar_width = 0.9
    bar_height = 0.025
    bar_color = "green" if confidence >= 85 else ("orange" if confidence >= 65 else "red")

    ax.add_patch(mpatches.Rectangle((0.05, y), bar_width, bar_height, facecolor="lightgray", transform=ax.transAxes))
    ax.add_patch(mpatches.Rectangle((0.05, y), bar_width * (confidence / 100), bar_height, facecolor=bar_color, transform=ax.transAxes))

    ax.set_title("Quality Report", fontsize=FONT_SIZE_INFO)
