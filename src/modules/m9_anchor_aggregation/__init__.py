"""
M9 施工锚点聚合模块
基于拓扑施工门户与全局锚点窗口去重的 OD-path 聚合算法

核心功能：
1. 输入施工收费单元集合和 OD-path 流量数据
2. 基于有向拓扑拆分施工片区（不依赖 ID 后缀）
3. 识别施工门户点（入口/出口）
4. 生成局部施工窗口
5. 逐级外扩锚点，找到最近有效锚点
6. 合并全局锚点窗口（去重）
7. path 唯一归属
8. 聚合 pass/bypass 流量
"""

from src.modules.m9_anchor_aggregation.models import (
    PathRecord,
    TopologyEdge,
    ConstructionInput,
    ConstructionComponent,
    ConstructionWindow,
    RawAnchorCandidate,
    AnchorWindow,
    AnchorWindowStat,
    PathAssignment,
)
from src.modules.m9_anchor_aggregation.aggregator import (
    aggregate_construction_paths,
    AggregationResult,
)
from src.modules.m9_anchor_aggregation.config import (
    AnchorAggregationConfig,
    load_config,
)
from src.modules.m9_anchor_aggregation.output import (
    export_results_to_csv,
    format_anchor_window_agg,
)
from src.modules.m9_anchor_aggregation.parser import (
    parse_unit_sequence,
    parse_construction_units,
    load_path_records_from_csv,
    build_unit_inverted_index,
    create_construction_input,
)

__all__ = [
    "PathRecord",
    "TopologyEdge",
    "ConstructionInput",
    "ConstructionComponent",
    "ConstructionWindow",
    "RawAnchorCandidate",
    "AnchorWindow",
    "AnchorWindowStat",
    "PathAssignment",
    "aggregate_construction_paths",
    "AggregationResult",
    "AnchorAggregationConfig",
    "load_config",
    "export_results_to_csv",
    "format_anchor_window_agg",
    "parse_unit_sequence",
    "parse_construction_units",
    "load_path_records_from_csv",
    "build_unit_inverted_index",
    "create_construction_input",
]