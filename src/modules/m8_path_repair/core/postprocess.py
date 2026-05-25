"""
M8 路径修正 V2 — 后处理

修正后的路径可能仍存在：
1. 局部小环（A -> B -> A）
2. 短距离重复震荡
3. 连续重复节点

后处理策略：
1. 再次去除相邻重复节点
2. 对 A -> B -> A 形式小环进行识别（允许一次掉头，不强制删除）
3. 多次重复折返时标记为低置信度
"""

from dataclasses import dataclass, field
from typing import Optional

from src.app.logger import get_logger

logger = get_logger(__name__)

# 节点 ID 标准化：去掉后两位（方向后缀，如 "10" 或 "20"）
NODE_ID_STANDARDIZE_LENGTH = 14


@dataclass
class PostprocessResult:
    """后处理结果"""
    nodes: list[str]
    removed_loops: list[str]  # 被移除的小环节点
    removed_duplicates: list[str]  # 被移除的重复节点
    uturn_allowed: bool  # 是否允许了一次掉头
    uturn_count: int  # 检测到的掉头次数


def _normalize_node_id(node_id: str) -> str:
    """
    标准化节点 ID：去掉后两位方向后缀。

    收费单元 ID 格式：前14位是收费单元标识，后两位是方向标识（10/20）。
    同一条收费单元的正反向应视为同一节点。
    """
    if len(node_id) >= NODE_ID_STANDARDIZE_LENGTH:
        return node_id[:NODE_ID_STANDARDIZE_LENGTH]
    return node_id


def _is_same_location(node_a: str, node_b: str) -> bool:
    """判断两个节点是否属于同一收费单元（忽略方向）"""
    return _normalize_node_id(node_a) == _normalize_node_id(node_b)


def postprocess_corrected_path(
    corrected_nodes: list[str],
    graph=None,
    node_info=None,
    config: dict | None = None,
) -> PostprocessResult:
    """
    对修正后路径做后处理。
    """
    config = config or {}
    removed_loops: list[str] = []
    removed_dups: list[str] = []
    uturn_count = 0
    uturn_allowed = False

    if len(corrected_nodes) < 3:
        return PostprocessResult(
            nodes=corrected_nodes,
            removed_loops=[],
            removed_duplicates=[],
            uturn_allowed=False,
            uturn_count=0,
        )

    # Step 1: 去除相邻重复节点
    nodes = _remove_adjacent_duplicates(corrected_nodes, removed_dups)

    # Step 2: 检测并处理小环 A -> B -> A
    max_uturns = config.get("allow_uturn_count", 1)
    nodes, removed_loops, uturn_count, uturn_allowed = _process_small_loops(
        nodes, removed_loops, max_uturns
    )

    return PostprocessResult(
        nodes=nodes,
        removed_loops=removed_loops,
        removed_duplicates=removed_dups,
        uturn_allowed=uturn_allowed,
        uturn_count=uturn_count,
    )


def _remove_adjacent_duplicates(
    nodes: list[str], removed: list[str]
) -> list[str]:
    """去除相邻重复节点（按标准化 ID 比较）"""
    if not nodes:
        return nodes

    result = [nodes[0]]
    for node in nodes[1:]:
        if not _is_same_location(node, result[-1]):
            result.append(node)
        else:
            removed.append(node)

    return result


def _process_small_loops(
    nodes: list[str],
    removed_loops: list[str],
    max_uturns: int = 1,
) -> tuple[list[str], list[str], int, bool]:
    """
    检测 A -> B -> A 形式的小环。

    比较时使用标准化节点 ID（前14位），忽略方向后缀。
    允许 max_uturns 次掉头，超过时才删除。

    Returns:
        (处理后节点, 被移除节点, 掉头次数, 是否允许了掉头)
    """
    if len(nodes) < 3:
        return nodes, removed_loops, 0, False

    result = [nodes[0], nodes[1]]
    uturn_count = 0
    uturn_allowed = False

    for i in range(2, len(nodes)):
        # 检测 A -> B -> A，使用标准化 ID 比较
        if _is_same_location(nodes[i], result[-2]) and len(result) >= 2:
            uturn_count += 1
            if uturn_count <= max_uturns:
                # 允许这次掉头
                result.append(nodes[i])
                if uturn_count == 1:
                    uturn_allowed = True
            else:
                # 超过允许次数：跳过
                removed_loops.append(nodes[i])
        else:
            result.append(nodes[i])

    return result, removed_loops, uturn_count, uturn_allowed


def _remove_reciprocal_segments(nodes: list[str]) -> tuple[list[str], int]:
    """
    删除 A -> ... -> A 形式的往复片段。

    检测从节点 A 出发后又回到节点 A 的情况，删除中间的往返片段。
    例如: [M, N, A, B, C, D, C, B, A, U, Y] -> [M, N, U, Y]

    比较时使用标准化节点 ID（前14位），忽略方向后缀。

    注意：起点节点（位置0）如果标准化后与后续节点相同，起点会被删除。
    这是因为在拓扑路径中，从起点出发又回到"同一位置"（标准化后相同）
    意味着路径从该位置出发，这被视为异常。

    Returns:
        (删除往复片段后的节点列表, 删除的节点数量)
    """
    if len(nodes) < 3:
        return nodes, 0

    # 记录每个节点（标准化后）第一次出现的位置
    first_occurrence: dict[str, int] = {}
    result: list[str] = []
    removed_count = 0

    for node in nodes:
        normalized = _normalize_node_id(node)

        if normalized in first_occurrence:
            # 检测到往复：从第一次出现位置的下一个节点开始删除
            first_idx = first_occurrence[normalized]
            removed_count = len(result) - first_idx
            result = result[:first_idx]  # 保留到第一次出现位置为止（删除该位置之后的所有节点）
            # 不添加当前节点（这是回到 A 的节点）
            continue

        # 第一次遇到该节点
        first_occurrence[normalized] = len(result)
        result.append(node)

    return result, removed_count
