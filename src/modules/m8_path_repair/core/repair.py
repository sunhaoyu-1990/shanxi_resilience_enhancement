"""
M8 路径修正 — V1 核心修正逻辑

V1 策略（相邻补全方案）：
1. 遍历相邻节点对 (A, B)
2. 如果 A→B 有直接拓扑边 → 保留
3. 如果 A→B 不可达但 shortest_path(A, B) 存在 → 用最短路径补全
4. 如果 A→B 不可达 → 在后续 max_gap_search_window 个节点中找第一个可达的
5. 如果都不可达 → 标记异常
"""

from dataclasses import dataclass, field

from .normalizer import NormalizedPath

from src.app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RepairSegment:
    """单段修正详情"""
    from_node: str
    to_node: str
    segment_nodes: list[str]  # 该段的完整节点序列
    is_direct_edge: bool  # 是否有直接边
    is_shortest_path_fill: bool  # 是否通过最短路径补全
    is_skip: bool  # 是否跳过了中间节点


@dataclass
class RepairResult:
    """V1 路径修正结果"""
    corrected_nodes: list[str] = field(default_factory=list)
    inserted_nodes: list[str] = field(default_factory=list)  # 新插入的节点
    dropped_nodes: list[str] = field(default_factory=list)  # 被删除的节点
    segment_details: list[RepairSegment] = field(default_factory=list)
    failed_segments: list[tuple[str, str]] = field(default_factory=list)  # 失败的段
    status: str = "success"  # success | low_confidence | failed


def repair_path_v1(
    start_node: str,
    end_node: str,
    normalized: NormalizedPath,
    graph,
    config: dict,
) -> RepairResult:
    """
    V1 路径修正核心逻辑。

    遍历 clean_nodes，对每对相邻节点进行连通性检查和补全。

    Args:
        start_node: 起点节点
        end_node: 终点节点
        normalized: 标准化后的路径
        graph: RoadGraph 实例
        config: 配置参数

    Returns:
        RepairResult 修正结果
    """
    max_gap_window = config.get("max_gap_search_window", 6)

    nodes = normalized.clean_nodes
    invalid_nodes = list(normalized.invalid_nodes)

    if not nodes:
        return RepairResult(
            corrected_nodes=[start_node, end_node],
            dropped_nodes=invalid_nodes,
            status="low_confidence",
        )

    # 确保起终点在路径中
    if start_node not in nodes:
        nodes = [start_node] + nodes
    if end_node not in nodes:
        nodes = nodes + [end_node]

    # 修正后的路径
    corrected: list[str] = []
    inserted: list[str] = []
    dropped: list[str] = list(invalid_nodes)
    segments: list[RepairSegment] = []
    failed: list[tuple[str, str]] = []

    corrected.append(nodes[0])
    i = 0

    while i < len(nodes) - 1:
        curr = nodes[i]
        next_node = nodes[i + 1]

        # 情况 1: 有直接边
        if graph.has_direct_edge(curr, next_node):
            if next_node not in corrected or corrected[-1] != next_node:
                corrected.append(next_node)
            segments.append(RepairSegment(
                from_node=curr,
                to_node=next_node,
                segment_nodes=[curr, next_node],
                is_direct_edge=True,
                is_shortest_path_fill=False,
                is_skip=False,
            ))
            i += 1
            continue

        # 情况 2: 尝试最短路径补全
        path = graph.shortest_path(curr, next_node)
        if path and len(path) > 1:
            # 添加最短路径中间节点（不包括起点）
            for node in path[1:]:
                if node != corrected[-1]:
                    corrected.append(node)
                    if node not in nodes:
                        inserted.append(node)

            segments.append(RepairSegment(
                from_node=curr,
                to_node=next_node,
                segment_nodes=path,
                is_direct_edge=False,
                is_shortest_path_fill=True,
                is_skip=False,
            ))
            i += 1
            continue

        # 情况 3: 在当前节点之后 max_gap_window 个节点中找可达的
        found = False
        for j in range(i + 2, min(i + 1 + max_gap_window, len(nodes))):
            target = nodes[j]
            path = graph.shortest_path(curr, target)
            if path and len(path) > 1:
                # 跳过 i+1 到 j-1 之间的节点
                for skipped in nodes[i + 1:j]:
                    if skipped not in dropped:
                        dropped.append(skipped)

                for node in path[1:]:
                    if node != corrected[-1]:
                        corrected.append(node)
                        if node not in nodes:
                            inserted.append(node)

                segments.append(RepairSegment(
                    from_node=curr,
                    to_node=target,
                    segment_nodes=path,
                    is_direct_edge=False,
                    is_shortest_path_fill=True,
                    is_skip=True,
                ))
                i = j
                found = True
                break

        if found:
            continue

        # 情况 4: 全部不可达，标记失败并跳过
        failed.append((curr, next_node))
        logger.warning(f"Repair failed for segment {curr} -> {next_node}")
        if next_node not in corrected:
            corrected.append(next_node)
        i += 1

    # 确保终点在路径末尾
    if corrected[-1] != end_node:
        corrected.append(end_node)

    # 去重相邻重复节点
    deduped = [corrected[0]]
    for node in corrected[1:]:
        if node != deduped[-1]:
            deduped.append(node)
    corrected = deduped

    status = "success"
    if failed:
        status = "low_confidence"
    elif len(dropped) > len(nodes) * 0.3:
        status = "low_confidence"

    return RepairResult(
        corrected_nodes=corrected,
        inserted_nodes=inserted,
        dropped_nodes=dropped,
        segment_details=segments,
        failed_segments=failed,
        status=status,
    )
