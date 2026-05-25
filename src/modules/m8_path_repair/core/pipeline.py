"""
M8 路径修正 — 主流程编排

单条路径修正的完整流程：
1. 路径标准化
2. 起终点解析
3. V2 锚点 DP + 分段 KSP（优先）
4. 若 V2 不可行则回退 V1（相邻补全）
5. 后处理（小环识别、重复去重）
6. 经纬度匹配
7. 折返指标计算
8. 质量评分
9. 组装输出结果
"""

from typing import Optional

from .normalizer import normalize_raw_path
from .repair import repair_path_v1, RepairResult
from .anchor import filter_anchor_candidates, select_anchors_by_dp
from .stitcher import stitch_segments_by_ksp, StitchResult
from .postprocess import postprocess_corrected_path, _remove_reciprocal_segments
from .geo import attach_lonlat, get_missing_geo_nodes
from .metrics import (
    calc_repeated_node_count,
    calc_reverse_edge_count,
    calc_backward_progress,
    calc_u_turn_count,
    calc_detour_ratio,
    calc_backtrack_index,
    calc_repair_confidence,
    get_repair_status,
    calc_path_length_meters,
)
from .graph import RoadGraph

from src.app.logger import get_logger

logger = get_logger(__name__)


def repair_single(
    record_id: str,
    enid: str,
    exid: str,
    raw_path: str,
    graph: RoadGraph,
    config: dict,
) -> dict:
    """
    修正单条通行路径。

    Args:
        record_id: 通行记录唯一标识
        enid: 入口节点 ID
        exid: 出口节点 ID
        raw_path: 原始路径字符串（| 分隔）
        graph: RoadGraph 实例
        config: 配置参数

    Returns:
        路径修正结果字典
    """
    # Step 1: 路径标准化
    normalized = normalize_raw_path(raw_path, graph)

    if not normalized.clean_nodes and not normalized.raw_nodes:
        return _build_failed_result(
            record_id, enid, exid, raw_path, "FAILED_EMPTY_PATH",
            reason="原始路径为空且无法构造",
        )

    # Step 2: 起终点处理
    start_node = enid
    end_node = exid

    if not graph.has_node(start_node):
        if normalized.clean_nodes:
            start_node = normalized.clean_nodes[0]
        else:
            return _build_failed_result(
                record_id, enid, exid, raw_path, "FAILED_NO_PATH",
                reason=f"起点 {enid} 不在拓扑中",
            )

    if not graph.has_node(end_node):
        if normalized.clean_nodes:
            end_node = normalized.clean_nodes[-1]
        else:
            return _build_failed_result(
                record_id, enid, exid, raw_path, "FAILED_NO_PATH",
                reason=f"终点 {exid} 不在拓扑中",
            )

    # 检查起终点可达性
    _, sp_cost = graph.shortest_path(start_node, end_node)
    if sp_cost is None:
        return _build_failed_result(
            record_id, enid, exid, raw_path, "FAILED_NO_PATH",
            reason=f"起点 {start_node} 到终点 {end_node} 不可达",
        )

    # Step 3: V2 锚点 DP + 分段 KSP（优先尝试）
    use_v2 = config.get("use_v2_algorithm", True)
    corrected: Optional[list[str]] = None
    repair_result: Optional[RepairResult] = None
    stitch_result: Optional[StitchResult] = None

    if use_v2 and len(normalized.clean_nodes) >= 3:
        corrected, repair_result, stitch_result = _try_v2_repair(
            start_node, end_node, normalized, graph, config
        )

    # 回退 V1
    if corrected is None:
        logger.info("Falling back to V1 repair")
        repair_result = repair_path_v1(
            start_node=start_node,
            end_node=end_node,
            normalized=normalized,
            graph=graph,
            config=config,
        )
        corrected = repair_result.corrected_nodes
        stitch_result = None

    if not corrected or len(corrected) < 2:
        return _build_failed_result(
            record_id, enid, exid, raw_path, "FAILED_NO_PATH",
            reason="修正后路径为空或只有一个节点",
        )

    # Step 4: 后处理
    pp_result = postprocess_corrected_path(corrected, graph, config=config)
    corrected = pp_result.nodes

    # Step 5: 经纬度匹配
    geo_points = attach_lonlat(corrected, graph)
    missing_geo = get_missing_geo_nodes(geo_points)

    # Step 6: 折返指标
    backward_info = calc_backward_progress(
        corrected, end_node, graph,
        threshold_m=config.get("backward_progress_threshold_m", 300.0),
    )

    detour = calc_detour_ratio(corrected, start_node, end_node, graph)
    bti = calc_backtrack_index({
        "reverse_edge_count": calc_reverse_edge_count(corrected),
        "backward_progress_count": backward_info["backward_progress_count"],
        "repeated_node_count": calc_repeated_node_count(corrected),
        "u_turn_count": calc_u_turn_count(geo_points),
        "detour_ratio": detour,
    })

    # Step 7: 质量评分
    raw_node_count = len(normalized.raw_nodes)
    raw_match_ratio = _calc_raw_match_ratio(normalized.raw_nodes, corrected)

    anchor_count = len(stitch_result.segment_details) if stitch_result else 0
    inserted_count = len(repair_result.inserted_nodes) if repair_result else 0
    dropped_count = len(repair_result.dropped_nodes) if repair_result else 0

    confidence = calc_repair_confidence(
        raw_match_ratio=raw_match_ratio,
        dropped_node_count=dropped_count,
        inserted_node_count=inserted_count,
        raw_node_count=raw_node_count,
        detour_ratio=detour,
        backtrack_index=bti,
        anchor_count=anchor_count,
        total_node_count=len(corrected),
    )

    status = get_repair_status(confidence, bti)

    # Step 8: 组装输出
    # 输出路径只保留中间节点（去除 OD 起点和终点）
    # 如果中间节点中包含 enid 或 exid，则去除
    # 过滤掉7位收费单元节点（立交单元）

    # 往复路径过滤（在完整路径上检测）
    remove_reciprocal = config.get("remove_reciprocal_path", False)
    reciprocal_removed = False
    if remove_reciprocal and len(corrected) >= 3:
        corrected_filtered, _ = _remove_reciprocal_segments(corrected)
        if len(corrected_filtered) < len(corrected):
            # 检测到往复，使用过滤后的路径
            reciprocal_removed = True
            corrected = corrected_filtered

    INTERCHANGE_UNIT_LENGTH = 7

    # 去除中间节点中的 enid 和 exid
    corrected_middle = [
        n for n in corrected
        if n != start_node and n != end_node
    ]
    # 再过滤7位立交单元
    filtered_middle = [
        n for n in corrected_middle if len(n) != INTERCHANGE_UNIT_LENGTH
    ]
    filtered_node_count = len(corrected_middle) - len(filtered_middle)
    reciprocal_removed_count = 0

    corrected_path_str = "|".join(filtered_middle)
    path_length = calc_path_length_meters(corrected, graph)

    detail = {
        "start_node": start_node,
        "end_node": end_node,
        "algorithm": "v2" if stitch_result is not None else "v1",
        "invalid_nodes": normalized.invalid_nodes,
        "dropped_nodes": repair_result.dropped_nodes if repair_result else [],
        "inserted_nodes": repair_result.inserted_nodes if repair_result else [],
        "segment_count": len(stitch_result.segment_details) if stitch_result else (
            len(repair_result.segment_details) if repair_result else 0
        ),
        "failed_segments": [],
        "missing_geo_nodes": missing_geo,
        "path_length_meters": round(path_length, 1),
        "shortest_path_meters": round(sp_cost, 1) if sp_cost is not None else None,
        "postprocess": {
            "loops_removed": pp_result.removed_loops,
            "duplicates_removed": pp_result.removed_duplicates,
            "uturns_detected": pp_result.uturn_count,
            "uturn_allowed": pp_result.uturn_allowed,
        },
    }

    if stitch_result:
        detail["total_lcs"] = stitch_result.total_lcs
        detail["total_observed"] = stitch_result.total_observed
        detail["lcs_match_ratio"] = (
            stitch_result.total_lcs / max(stitch_result.total_observed, 1)
        )
        detail["segments"] = [
            {
                "from": s.from_anchor,
                "to": s.to_anchor,
                "lcs": s.lcs_length,
                "score": s.score,
                "k_checked": s.k_candidates_checked,
            }
            for s in stitch_result.segment_details
        ]

    if repair_result:
        detail["failed_segments"] = [
            f"{a}->{b}" for a, b in repair_result.failed_segments
        ]

    # 如果检测到往复，更新状态和置信度
    if reciprocal_removed:
        status = "RECIPROCAL_DETECTED"
        confidence = 0.0
        detail["failure_reason"] = "检测到往复路径（A->...->A），已删除往复段"

    # Step 9: 查询最短路径和绕行路径
    sp_result = graph.shortest_path(start_node, end_node)
    shortest_path_nodes, shortest_path_cost = sp_result

    # 施工路段检查
    construction_sections_raw = config.get("construction_sections", "")
    if construction_sections_raw:
        construction_sections = [s for s in construction_sections_raw.split("|") if s]
    else:
        construction_sections = []

    passes_construction = None
    shortest_through_construction = None
    detour_path = None
    detour_distance = None
    detour_fee = None
    min_fee_path = None
    min_fee = None

    if construction_sections and shortest_path_nodes:
        sp_set = set(shortest_path_nodes)
        const_set = set(construction_sections)
        passes_construction = bool(sp_set & const_set)

        if passes_construction:
            # 经过施工路段的最短距离
            shortest_through_construction = shortest_path_cost

            # 查询K条候选绕行路径
            detour_candidates = graph.k_shortest_paths_avoid_nodes(
                start_node, end_node, construction_sections, k=5
            )

            if detour_candidates:
                try:
                    from src.common.toll_calculator import TollCalculator
                    toll_calc = TollCalculator()
                    vehicle_type = config.get("vehicle_type", 11)

                    # 最短绕行路径（距离最短）
                    detour_path_nodes, detour_distance = detour_candidates[0]

                    # 计算最短绕行路径的费额
                    fee_result = toll_calc.calculate_path_fee(
                        detour_path_nodes, vehicle_type, graph.version
                    )
                    detour_fee = fee_result.fee_yuan if fee_result else None

                    # 去除起终点的中间节点
                    detour_path_middle = [
                        n for n in detour_path_nodes
                        if n != start_node and n != end_node
                    ]
                    detour_path = "|".join(detour_path_middle)

                    # 最小费额绕行路径
                    valid_paths = []
                    for path, cost in detour_candidates:
                        fee_res = toll_calc.calculate_path_fee(
                            path, vehicle_type, graph.version
                        )
                        if fee_res:
                            valid_paths.append((path, cost, fee_res.fee_yuan))

                    if valid_paths:
                        min_fee_path_nodes, _, min_fee = min(
                            valid_paths, key=lambda x: x[2]
                        )
                        min_fee_path_middle = [
                            n for n in min_fee_path_nodes
                            if n != start_node and n != end_node
                        ]
                        min_fee_path = "|".join(min_fee_path_middle)

                except Exception as e:
                    logger.warning(f"绕行路径费额计算失败: {e}")
    else:
        passes_construction = None
        shortest_through_construction = None

    # 去除起终点的最短路径
    sp_middle = [n for n in (shortest_path_nodes or []) if n != start_node and n != end_node]
    shortest_path_str = "|".join(sp_middle)

    return {
        "record_id": record_id,
        "enid": enid,
        "exid": exid,
        "raw_path": raw_path,
        "corrected_path": corrected_path_str,
        "raw_node_count": raw_node_count,
        "corrected_node_count": len(filtered_middle),
        "full_path_node_count": len(corrected),
        "filtered_node_count": filtered_node_count,
        "reciprocal_removed_count": reciprocal_removed_count,
        "inserted_node_count": inserted_count,
        "dropped_node_count": dropped_count,
        "raw_match_ratio": round(raw_match_ratio, 4),
        "detour_ratio": round(detour, 4),
        "reverse_edge_count": calc_reverse_edge_count(corrected),
        "backward_progress_count": backward_info["backward_progress_count"],
        "backward_progress_distance": backward_info["backward_progress_distance"],
        "u_turn_count": calc_u_turn_count(geo_points),
        "repeated_node_count": calc_repeated_node_count(corrected),
        "backtrack_index": bti,
        "repair_confidence": confidence,
        "repair_status": status,
        "corrected_geo_points": geo_points if config.get("detail_geo", True) else [],
        "repair_detail": detail,
        # 最短路径相关字段（可能经过施工路段）
        "shortest_path": shortest_path_str,
        "shortest_path_distance": round(shortest_path_cost, 1) if shortest_path_cost else None,
        "passes_construction": passes_construction,
        "shortest_through_construction": round(shortest_through_construction, 1) if shortest_through_construction else None,
        # 绕行路径（绕开施工路段）
        "detour_path": detour_path,
        "detour_distance": round(detour_distance, 1) if detour_distance else None,
        "detour_fee": round(detour_fee, 2) if detour_fee is not None else None,
        # 最小费额绕行路径
        "min_fee_path": min_fee_path,
        "min_fee": round(min_fee, 2) if min_fee is not None else None,
    }


# ============================================================
# V2 尝试
# ============================================================


def _try_v2_repair(
    start_node: str,
    end_node: str,
    normalized,
    graph: RoadGraph,
    config: dict,
) -> tuple[Optional[list[str]], Optional[RepairResult], Optional[StitchResult]]:
    """
    尝试 V2 锚点 DP + 分段 KSP 修正。

    Returns:
        (corrected_nodes, RepairResult, StitchResult) 或 (None, None, None) 如果不可行
    """
    try:
        from .repair import RepairResult

        # 1. 候选锚点筛选
        candidates = filter_anchor_candidates(
            start_node, end_node, normalized.clean_nodes, graph, config
        )

        if not candidates:
            logger.info("V2: No anchor candidates found")
            return None, None, None

        # 2. DP 选择锚点链
        chain_result = select_anchors_by_dp(
            start_node, end_node, normalized.clean_nodes, candidates, graph, config
        )

        if not chain_result.anchors:
            logger.info("V2: DP failed to find anchor chain")
            return None, None, None

        # 构建完整锚点序列 [start, anchor1, ..., end]
        anchor_nodes = [start_node]
        for anchor in chain_result.anchors:
            anchor_nodes.append(anchor.node)
        anchor_nodes.append(end_node)

        # 3. 分段 KSP 拼接
        stitch_result = stitch_segments_by_ksp(
            anchor_nodes, normalized.clean_nodes, graph, config
        )

        if len(stitch_result.corrected_nodes) < 2:
            logger.info("V2: Stitching produced too short path")
            return None, None, None

        # 4. 计算插入/删除节点
        original_set = set(normalized.clean_nodes)
        corrected_set = set(stitch_result.corrected_nodes)
        inserted = list(corrected_set - original_set)
        dropped = list(normalized.invalid_nodes)
        for idx in chain_result.skipped_indices:
            if idx < len(normalized.clean_nodes):
                node = normalized.clean_nodes[idx]
                if node not in corrected_set:
                    dropped.append(node)

        repair_result = RepairResult(
            corrected_nodes=stitch_result.corrected_nodes,
            inserted_nodes=inserted,
            dropped_nodes=dropped,
            segment_details=[],  # 由 StitchResult 提供
            failed_segments=[],
            status="success",
        )

        logger.info(
            f"V2 repair succeeded: {len(stitch_result.corrected_nodes)} nodes, "
            f"{len(stitch_result.segment_details)} segments, "
            f"LCS ratio={stitch_result.total_lcs}/{stitch_result.total_observed}"
        )

        return stitch_result.corrected_nodes, repair_result, stitch_result

    except Exception as e:
        logger.warning(f"V2 repair failed with exception: {e}")
        return None, None, None


# ============================================================
# 辅助函数
# ============================================================


def _calc_raw_match_ratio(raw_nodes: list[str], corrected_nodes: list[str]) -> float:
    """计算原始节点在修正后路径中的匹配率"""
    if not raw_nodes:
        return 1.0

    corrected_set = set(corrected_nodes)
    match_count = sum(1 for n in raw_nodes if n in corrected_set)
    return match_count / len(raw_nodes)


def _build_failed_result(
    record_id: str,
    enid: str,
    exid: str,
    raw_path: str,
    status: str,
    reason: str = "",
) -> dict:
    """构建失败结果"""
    return {
        "record_id": record_id,
        "enid": enid,
        "exid": exid,
        "raw_path": raw_path,
        "corrected_path": "",
        "raw_node_count": len(raw_path.split("|")) if raw_path else 0,
        "corrected_node_count": 0,
        "inserted_node_count": 0,
        "dropped_node_count": 0,
        "raw_match_ratio": 0.0,
        "detour_ratio": 0.0,
        "reverse_edge_count": 0,
        "backward_progress_count": 0,
        "backward_progress_distance": 0.0,
        "u_turn_count": 0,
        "repeated_node_count": 0,
        "backtrack_index": 0.0,
        "repair_confidence": 0.0,
        "repair_status": status,
        "corrected_geo_points": [],
        "repair_detail": {
            "failure_reason": reason,
        },
    }
