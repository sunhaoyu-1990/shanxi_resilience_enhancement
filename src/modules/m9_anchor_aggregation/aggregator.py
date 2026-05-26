"""
M9 施工锚点聚合模块 - 主入口编排
实现 aggregate_construction_paths 主入口函数

10 步流水线：
1. 解析施工集合（已在 ConstructionInput 中）
2. 构建拓扑（可选，从 DB 加载或注入）
3. 拆施工片区
4. 识别门户点
5. 生成局部施工窗口
6. 锚点外扩
7. 合并全局锚点窗口
8. path 分类
9. path 唯一归属
10. 聚合输出
"""

from typing import Optional

from src.app.logger import get_logger
from src.modules.m9_anchor_aggregation.models import (
    ConstructionInput,
    ConstructionComponent,
    ConstructionWindow,
    AnchorWindow,
    AnchorWindowStat,
    PathAssignment,
    PathRecord,
)
from src.modules.m9_anchor_aggregation.topology import TopologyGraph
from src.modules.m9_anchor_aggregation.config import AnchorAggregationConfig
from src.modules.m9_anchor_aggregation.component_splitter import split_components_by_topology
from src.modules.m9_anchor_aggregation.portal_detector import detect_all_portals
from src.modules.m9_anchor_aggregation.construction_window_builder import (
    build_all_construction_windows,
)
from src.modules.m9_anchor_aggregation.anchor_expander import (
    find_valid_anchor_candidates_for_all_windows,
)
from src.modules.m9_anchor_aggregation.anchor_window_merger import (
    merge_anchor_candidates_to_windows,
    deduplicate_anchor_windows,
)
from src.modules.m9_anchor_aggregation.assignment import (
    assign_all_paths,
)
from src.modules.m9_anchor_aggregation.parser import build_unit_inverted_index

logger = get_logger(__name__)


class AggregationResult:
    """
    聚合结果

    Attributes:
        construction_id: 施工工程 ID
        components: 施工片区列表
        construction_windows: 局部施工窗口列表
        anchor_windows: 锚点窗口列表
        assignments: path 归属列表
        anchor_window_agg: 锚点窗口聚合统计
    """
    def __init__(
        self,
        construction_id: str,
        components: list[ConstructionComponent],
        construction_windows: list[ConstructionWindow],
        anchor_windows: list[AnchorWindow],
        assignments: list[PathAssignment],
        anchor_window_agg: list[AnchorWindowStat],
    ):
        self.construction_id = construction_id
        self.components = components
        self.construction_windows = construction_windows
        self.anchor_windows = anchor_windows
        self.assignments = assignments
        self.anchor_window_agg = anchor_window_agg

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "construction_id": self.construction_id,
            "components": [
                {
                    "construction_id": c.construction_id,
                    "component_id": c.component_id,
                    "units": sorted(c.units),
                    "entry_portals": sorted(c.entry_portals),
                    "exit_portals": sorted(c.exit_portals),
                    "upstream_frontiers": sorted(c.upstream_frontiers),
                    "downstream_frontiers": sorted(c.downstream_frontiers),
                }
                for c in self.components
            ],
            "construction_windows": [
                {
                    "construction_id": w.construction_id,
                    "component_id": w.component_id,
                    "window_id": w.window_id,
                    "start_unit": w.start_unit,
                    "end_unit": w.end_unit,
                    "covered_units": sorted(w.covered_units),
                    "source": w.source,
                    "source_flow": w.source_flow,
                    "source_path_count": w.source_path_count,
                }
                for w in self.construction_windows
            ],
            "anchor_windows": [
                {
                    "construction_id": aw.construction_id,
                    "anchor_start": aw.anchor_start,
                    "anchor_end": aw.anchor_end,
                    "source_component_ids": sorted(aw.source_component_ids),
                    "source_window_ids": sorted(aw.source_window_ids),
                    "covered_units": sorted(aw.covered_units),
                    "min_level": aw.min_level,
                }
                for aw in self.anchor_windows
            ],
            "assignments": [
                {
                    "construction_id": a.construction_id,
                    "record_id": a.record_id,
                    "enid": a.enid,
                    "exid": a.exid,
                    "assigned_anchor_start": a.assigned_anchor_start,
                    "assigned_anchor_end": a.assigned_anchor_end,
                    "route_type": a.route_type,
                    "hit_units": a.hit_units,
                    "first_hit": a.first_hit,
                    "last_hit": a.last_hit,
                    "assignment_reason": a.assignment_reason,
                    "flow": a.flow,
                }
                for a in self.assignments
            ],
            "anchor_window_agg": [
                {
                    "construction_id": s.construction_id,
                    "anchor_start": s.anchor_start,
                    "anchor_end": s.anchor_end,
                    "pass_flow": s.pass_flow,
                    "bypass_flow": s.bypass_flow,
                    "pass_path_count": s.pass_path_count,
                    "bypass_path_count": s.bypass_path_count,
                    "od_count": s.od_count,
                    "total_flow": s.total_flow,
                    "bypass_ratio": s.bypass_ratio,
                }
                for s in self.anchor_window_agg
            ],
        }


def aggregate_construction_paths(
    construction_input: ConstructionInput,
    path_records: list[PathRecord],
    topology: TopologyGraph,
    config: Optional[AnchorAggregationConfig] = None,
) -> AggregationResult:
    """
    施工锚点聚合主入口

    给定施工输入和 OD-path 流量数据，执行完整的聚合流水线。

    Args:
        construction_input: 施工输入（施工单元集合）
        path_records: OD-path 流量记录列表
        topology: 有向拓扑图（从 DB 加载或注入）
        config: 锚点聚合配置，默认使用默认配置

    Returns:
        AggregationResult: 聚合结果
    """
    if config is None:
        config = AnchorAggregationConfig.default()

    construction_id = construction_input.construction_id
    construction_units = construction_input.construction_units

    logger.info(
        f"[aggregator] Starting aggregation for construction_id={construction_id}, "
        f"construction_units={len(construction_units)}, "
        f"path_records={len(path_records)}"
    )

    unit_index = build_unit_inverted_index(path_records)

    logger.info(f"[aggregator] Step 1/10: Splitting components...")
    components = split_components_by_topology(construction_input, topology)

    logger.info(f"[aggregator] Step 2/10: Detecting portals...")
    components = detect_all_portals(components, topology)

    logger.info(f"[aggregator] Step 3/10: Building construction windows...")
    construction_windows = build_all_construction_windows(
        construction_id=construction_id,
        components=components,
        topology=topology,
        path_records=path_records,
        construction_units=construction_units,
        config=config,
    )

    logger.info(f"[aggregator] Step 4/10: Expanding anchors...")
    raw_candidates = find_valid_anchor_candidates_for_all_windows(
        windows=construction_windows,
        path_records=path_records,
        topology=topology,
        config=config,
        unit_index=unit_index,
    )

    window_map = {w.window_id: w for w in construction_windows}
    anchor_windows = merge_anchor_candidates_to_windows(
        candidates=raw_candidates,
        window_map=window_map,
    )
    anchor_windows = deduplicate_anchor_windows(anchor_windows)

    logger.info(f"[aggregator] Step 5/10: Assigning paths...")
    assignments = assign_all_paths(
        path_records=path_records,
        anchor_windows=anchor_windows,
        construction_units=construction_units,
    )

    logger.info(f"[aggregator] Step 6/10: Aggregating stats...")
    anchor_window_agg = _aggregate_anchor_windows(assignments, anchor_windows)

    logger.info(
        f"[aggregator] Completed: components={len(components)}, "
        f"windows={len(construction_windows)}, "
        f"anchor_windows={len(anchor_windows)}, "
        f"assignments={len(assignments)}"
    )

    return AggregationResult(
        construction_id=construction_id,
        components=components,
        construction_windows=construction_windows,
        anchor_windows=anchor_windows,
        assignments=assignments,
        anchor_window_agg=anchor_window_agg,
    )


def _aggregate_anchor_windows(
    assignments: list[PathAssignment],
    anchor_windows: list[AnchorWindow],
) -> list[AnchorWindowStat]:
    """
    按锚点窗口聚合 pass/bypass 流量

    Args:
        assignments: path 归属列表
        anchor_windows: 锚点窗口列表

    Returns:
        list[AnchorWindowStat]: 锚点窗口聚合统计
    """
    anchor_key_to_window: dict[tuple[str, str, str], AnchorWindow] = {}
    for aw in anchor_windows:
        anchor_key_to_window[aw.key] = aw

    agg_data: dict[tuple, dict] = {}
    for assignment in assignments:
        if assignment.route_type == "unassigned":
            continue

        key = (
            assignment.construction_id,
            assignment.assigned_anchor_start,
            assignment.assigned_anchor_end,
        )
        if key not in agg_data:
            agg_data[key] = {
                "pass_flow": 0.0,
                "bypass_flow": 0.0,
                "pass_count": 0,
                "bypass_count": 0,
                "od_pairs": set(),
            }

        if assignment.route_type == "pass":
            agg_data[key]["pass_flow"] += assignment.flow
            agg_data[key]["pass_count"] += 1
        else:
            agg_data[key]["bypass_flow"] += assignment.flow
            agg_data[key]["bypass_count"] += 1

        od_pair = (assignment.enid, assignment.exid)
        agg_data[key]["od_pairs"].add(od_pair)

    stats: list[AnchorWindowStat] = []
    for key, data in agg_data.items():
        stat = AnchorWindowStat(
            construction_id=key[0],
            anchor_start=key[1],
            anchor_end=key[2],
            pass_flow=data["pass_flow"],
            bypass_flow=data["bypass_flow"],
            pass_path_count=data["pass_count"],
            bypass_path_count=data["bypass_count"],
            od_count=len(data["od_pairs"]),
        )
        stats.append(stat)

    stats.sort(key=lambda x: (x.construction_id, x.anchor_start, x.anchor_end))

    logger.info(
        f"[aggregation] anchor_window_count={len(stats)}, "
        f"total_pass_flow={sum(s.pass_flow for s in stats):.0f}, "
        f"total_bypass_flow={sum(s.bypass_flow for s in stats):.0f}"
    )

    return stats