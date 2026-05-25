"""
M8 路径修正 V2 — 可信锚点筛选 + DP 锚点链选择

锚点是原始路径中较可信的节点。修正路径被约束为：
    start_node -> anchor_1 -> anchor_2 -> ... -> anchor_k -> end_node

算法：
1. 对每个原始节点计算 detour_ratio = (d_start_v + d_v_end) / d_start_end
2. detour_ratio <= max_anchor_detour_ratio 的节点作为候选锚点
3. DP 选择最优锚点链（考虑分段最短路径长度、跳过节点数、绕行惩罚）
"""

from dataclasses import dataclass, field
from typing import Optional

from src.app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnchorCandidate:
    """锚点候选"""
    node: str
    raw_index: int  # 在原始 clean_nodes 中的索引
    detour_ratio: float
    dist_from_start: Optional[float] = None
    dist_to_end: Optional[float] = None


@dataclass
class AnchorChainResult:
    """锚点链选择结果"""
    anchors: list[AnchorCandidate]  # 选中的锚点链（不含起终点）
    skipped_indices: list[int]  # 被跳过的原始节点索引
    total_cost: float  # 总成本


def filter_anchor_candidates(
    start_node: str,
    end_node: str,
    clean_nodes: list[str],
    graph,
    config: dict,
) -> list[AnchorCandidate]:
    """
    筛选候选锚点。

    对每个节点 v：
    - d_start_v = shortest_path_cost(start, v)
    - d_v_end = shortest_path_cost(v, end)
    - d_start_end = shortest_path_cost(start, end)
    - detour_ratio = (d_start_v + d_v_end) / d_start_end

    如果 detour_ratio <= max_anchor_detour_ratio，作为候选。
    """
    max_ratio = config.get("max_anchor_detour_ratio", 2.0)

    # 起终点最短路成本
    _, d_start_end = graph.shortest_path(start_node, end_node)
    d_start_end = d_start_end or 0.0
    if d_start_end == 0:
        d_start_end = None
        # 不可达或零距离：放宽条件，保留所有可达节点
        d_start_end = None

    candidates = []
    for idx, node in enumerate(clean_nodes):
        # 跳过起终点本身
        if node == start_node or node == end_node:
            continue

        _, d_start_v = graph.shortest_path(start_node, node)
        _, d_v_end = graph.shortest_path(node, end_node)

        if d_start_v is None or d_v_end is None:
            continue  # 不可达的节点不能作为锚点

        if d_start_end is not None:
            ratio = (d_start_v + d_v_end) / d_start_end
        else:
            ratio = 999.0  # 不可达时设为极大值

        if ratio <= max_ratio:
            candidates.append(AnchorCandidate(
                node=node,
                raw_index=idx,
                detour_ratio=round(ratio, 4),
                dist_from_start=d_start_v,
                dist_to_end=d_v_end,
            ))

    logger.info(
        f"Anchor candidates: {len(candidates)} out of {len(clean_nodes)} nodes "
        f"(max_ratio={max_ratio})"
    )
    return candidates


def select_anchors_by_dp(
    start_node: str,
    end_node: str,
    clean_nodes: list[str],
    candidates: list[AnchorCandidate],
    graph,
    config: dict,
) -> AnchorChainResult:
    """
    使用动态规划选择最优锚点链。

    状态定义：
    - dp[i] = 到达第 i 个候选锚点的最小总成本
    - 转移：dp[j] = min(dp[i] + segment_cost(i, j) + skip_penalty(i, j))

    转移成本：
    1. 分段最短路径长度
    2. 跳过的原始节点数量惩罚
    3. 绕行比惩罚
    """
    if not candidates:
        # 无候选锚点：直接返回空链
        return AnchorChainResult(anchors=[], skipped_indices=[], total_cost=0.0)

    # 将起点和终点也加入候选序列，方便 DP
    # pseudo_candidates = [START] + candidates + [END]
    # 但起点/终点不是 AnchorCandidate，用特殊标记

    n = len(candidates)
    INF = float("inf")

    # dp[i]: 到达 candidates[i] 的最小成本
    dp = [INF] * n
    # parent[i]: dp[i] 的最优前驱索引
    parent = [-1] * n

    # 初始化：从起点直接到每个候选
    _, d_start_end = graph.shortest_path(start_node, end_node)
    if d_start_end is None:
        d_start_end = 1.0  # 防止除零

    for i in range(n):
        c = candidates[i]
        if c.dist_from_start is None:
            continue

        # 起点 -> candidates[i] 的成本
        seg_cost = _segment_cost(
            graph, start_node, c.node, c.dist_from_start, d_start_end
        )
        # 跳过 0..i-1 之间的节点的惩罚
        skip_count = i  # 跳过了前 i 个候选
        skip_penalty = skip_count * config.get("skip_node_penalty", 50.0)
        dp[i] = seg_cost + skip_penalty
        parent[i] = -1  # 从起点直接到达

    # DP 转移
    for j in range(1, n):
        c_j = candidates[j]
        if c_j.dist_from_start is None:
            continue

        for i in range(j):
            if dp[i] == INF:
                continue

            c_i = candidates[i]
            if c_i.node == c_j.node:
                continue

            # candidates[i] -> candidates[j] 的最短路径成本
            _, seg_cost_ij = graph.shortest_path(c_i.node, c_j.node)
            if seg_cost_ij is None:
                continue

            seg_normalized = seg_cost_ij / max(d_start_end, 1.0) * 100.0

            # 跳过的候选数惩罚
            skip_between = j - i - 1
            skip_penalty = skip_between * config.get("skip_node_penalty", 50.0)

            total = dp[i] + seg_normalized + skip_penalty
            if total < dp[j]:
                dp[j] = total
                parent[j] = i

    # 回溯：找到最优终点
    best_end = -1
    best_cost = INF

    for i in range(n):
        if dp[i] == INF:
            continue

        # 加上 candidates[i] -> 终点的成本
        c_i = candidates[i]
        _, d_i_end = graph.shortest_path(c_i.node, end_node)
        if d_i_end is None:
            continue

        seg_normalized = d_i_end / max(d_start_end, 1.0) * 100.0
        skip_after = n - i - 1
        skip_penalty = skip_after * config.get("skip_node_penalty", 50.0)

        total = dp[i] + seg_normalized + skip_penalty
        if total < best_cost:
            best_cost = total
            best_end = i

    if best_end == -1:
        # DP 无法找到任何可行锚点链
        logger.warning("DP failed to find feasible anchor chain, falling back to direct")
        return AnchorChainResult(anchors=[], skipped_indices=[], total_cost=0.0)

    # 回溯构建锚点链
    chain = []
    idx = best_end
    while idx >= 0:
        chain.append(candidates[idx])
        idx = parent[idx]
    chain.reverse()

    # 计算被跳过的原始节点索引
    chain_indices = {c.raw_index for c in chain}
    skipped = [i for i in range(len(clean_nodes)) if i not in chain_indices]

    return AnchorChainResult(
        anchors=chain,
        skipped_indices=skipped,
        total_cost=round(best_cost, 2),
    )


def _segment_cost(
    graph,
    from_node: str,
    to_node: str,
    shortest_cost: float,
    d_start_end: float,
) -> float:
    """归一化分段成本"""
    if d_start_end == 0:
        return shortest_cost
    return (shortest_cost / max(d_start_end, 1.0)) * 100.0
