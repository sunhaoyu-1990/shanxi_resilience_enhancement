"""
M8 路径修正 V2 — 分段 K 最短路拼接 + LCS 观测匹配评分

给定锚点链：S -> A -> C -> E
对每对相邻锚点：
1. 获取原始观测片段
2. 查询 K 条候选路径
3. 分段评分（LCS 匹配 + 路径长度 + 插入惩罚 + 折返惩罚）
4. 选择最优候选拼接
"""

from dataclasses import dataclass, field
from typing import Optional

from src.app.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StitchedSegment:
    """单段拼接结果"""
    from_anchor: str
    to_anchor: str
    chosen_path: list[str]
    observed_slice: list[str]
    lcs_length: int
    score: float
    k_candidates_checked: int


@dataclass
class StitchResult:
    """完整拼接结果"""
    corrected_nodes: list[str]
    segment_details: list[StitchedSegment]
    total_lcs: int
    total_observed: int


def lcs_length(a: list[str], b: list[str]) -> int:
    """
    计算最长公共子序列长度。
    用于衡量候选路径与原始观测片段的匹配程度。
    """
    if not a or not b:
        return 0

    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    return dp[m][n]


def segment_score(
    candidate_path: list[str],
    observed_slice: list[str],
    candidate_cost: float,
    graph,
    config: dict,
) -> float:
    """
    分段评分：分数越低越好。

    segment_score =
        0.40 * 路径长度归一化
      + 0.30 * 原始节点不匹配惩罚
      + 0.15 * 插入节点数量惩罚
      + 0.10 * 折返惩罚
      + 0.05 * 跳过节点惩罚
    """
    if not observed_slice:
        # 没有观测片段：只看路径长度
        return candidate_cost / 1000.0  # 归一化到米

    # LCS 匹配率
    lcs = lcs_length(candidate_path, observed_slice)
    match_ratio = lcs / max(len(observed_slice), 1)
    mismatch_penalty = 1.0 - match_ratio

    # 插入节点数
    candidate_set = set(candidate_path)
    observed_set = set(observed_slice)
    inserted = len(candidate_set - observed_set)
    insert_penalty = inserted / max(len(candidate_path), 1)

    # 路径长度归一化
    length_normalized = candidate_cost / max(len(candidate_path) * 500.0, 1.0)

    # 折返惩罚：重复节点
    from collections import Counter
    counts = Counter(candidate_path)
    repeat_count = sum(1 for c in counts.values() if c > 1)
    repeat_penalty = repeat_count / max(len(candidate_path), 1)

    # 跳过节点惩罚
    skipped = len(set(observed_slice) - candidate_set)
    skip_penalty = skipped / max(len(observed_slice), 1)

    # 加权
    weights = config.get("segment_score_weights", {
        "path_cost": 0.40,
        "observation_match": 0.30,
        "inserted_nodes": 0.15,
        "backtrack": 0.10,
        "skipped_nodes": 0.05,
    })

    score = (
        weights["path_cost"] * min(length_normalized, 1.0)
        + weights["observation_match"] * mismatch_penalty
        + weights["inserted_nodes"] * min(insert_penalty, 1.0)
        + weights["backtrack"] * min(repeat_penalty, 1.0)
        + weights["skipped_nodes"] * min(skip_penalty, 1.0)
    )

    return score


def stitch_segments_by_ksp(
    anchor_nodes: list[str],  # [start, anchor1, anchor2, ..., end]
    clean_nodes: list[str],
    graph,
    config: dict,
) -> StitchResult:
    """
    根据锚点链分段补全路径。

    Args:
        anchor_nodes: 完整锚点序列（含起终点）
        clean_nodes: 标准化后的原始节点列表
        graph: RoadGraph 实例
        config: 配置参数

    Returns:
        StitchResult 拼接结果
    """
    k = config.get("k_shortest_paths", 5)
    corrected: list[str] = [anchor_nodes[0]]
    segments: list[StitchedSegment] = []
    total_lcs = 0
    total_observed = 0

    for i in range(len(anchor_nodes) - 1):
        from_node = anchor_nodes[i]
        to_node = anchor_nodes[i + 1]

        # 获取原始观测片段
        observed = _get_observed_slice(
            clean_nodes, from_node, to_node, i, anchor_nodes
        )

        # 查询 K 条候选路径
        candidates = graph.k_shortest_paths(from_node, to_node, k)

        if not candidates:
            # 不可达：用最短路径尝试
            sp, sp_cost = graph.shortest_path(from_node, to_node)
            if sp:
                sp_cost = sp_cost or 0.0
                score = segment_score(sp, observed, sp_cost, graph, config)
                segments.append(StitchedSegment(
                    from_anchor=from_node,
                    to_anchor=to_node,
                    chosen_path=sp,
                    observed_slice=observed,
                    lcs_length=lcs_length(sp, observed),
                    score=round(score, 4),
                    k_candidates_checked=0,
                ))
                for node in sp[1:]:
                    if node != corrected[-1]:
                        corrected.append(node)
            else:
                logger.warning(f"KSP failed for {from_node} -> {to_node}")
                segments.append(StitchedSegment(
                    from_anchor=from_node,
                    to_anchor=to_node,
                    chosen_path=[from_node, to_node],
                    observed_slice=observed,
                    lcs_length=0,
                    score=999.0,
                    k_candidates_checked=0,
                ))
                if to_node != corrected[-1]:
                    corrected.append(to_node)
            continue

        # 评分选优
        best_path = None
        best_score = float("inf")
        best_lcs = 0
        best_cost = 0.0

        for path, cost in candidates:
            score = segment_score(path, observed, cost, graph, config)
            if score < best_score:
                best_score = score
                best_path = path
                best_lcs = lcs_length(path, observed)
                best_cost = cost

        if best_path:
            # 拼接（去掉起点避免重复）
            for node in best_path[1:]:
                if node != corrected[-1]:
                    corrected.append(node)

            segments.append(StitchedSegment(
                from_anchor=from_node,
                to_anchor=to_node,
                chosen_path=best_path,
                observed_slice=observed,
                lcs_length=best_lcs,
                score=round(best_score, 4),
                k_candidates_checked=len(candidates),
            ))
            total_lcs += best_lcs
        else:
            if to_node != corrected[-1]:
                corrected.append(to_node)

        total_observed += len(observed)

    return StitchResult(
        corrected_nodes=corrected,
        segment_details=segments,
        total_lcs=total_lcs,
        total_observed=total_observed,
    )


def _get_observed_slice(
    clean_nodes: list[str],
    from_node: str,
    to_node: str,
    anchor_idx: int,
    all_anchors: list[str],
) -> list[str]:
    """
    获取两个锚点在原始路径中索引之间的观测节点片段。
    """
    # 找到 from_node 和 to_node 在 clean_nodes 中的位置
    start_idx = None
    end_idx = None

    for i, node in enumerate(clean_nodes):
        if node == from_node and start_idx is None:
            start_idx = i
        if node == to_node:
            end_idx = i

    if start_idx is None or end_idx is None or start_idx >= end_idx:
        return []

    return clean_nodes[start_idx:end_idx]
