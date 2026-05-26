"""
M9 施工锚点聚合模块 - 数据模型
定义核心数据结构（dataclass / Pydantic BaseModel）
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PathRecord:
    """
    OD-path 流量记录

    Attributes:
        record_id: path 记录唯一 ID
        enid: 入口收费站/单元 ID
        exid: 出口收费站/单元 ID
        path: 已解析的 section_id 有序序列
        flow: 流量值
        stat_time: 统计时间（可选）
        vehicle_type: 车型（可选）
    """
    record_id: str
    enid: str
    exid: str
    path: list[str]
    flow: float
    stat_time: Optional[str] = None
    vehicle_type: Optional[str] = None


@dataclass(frozen=True)
class TopologyEdge:
    """
    有向拓扑边

    Attributes:
        from_unit: 上游收费单元 ID
        to_unit: 下游收费单元 ID
        length_km: 边长度（公里，可选）
    """
    from_unit: str
    to_unit: str
    length_km: Optional[float] = None


@dataclass(frozen=True)
class ConstructionInput:
    """
    施工输入

    Attributes:
        construction_id: 施工工程 ID
        construction_units: 施工收费单元无序集合
        construction_name: 施工名称（可选）
        version: 路网版本（可选）
    """
    construction_id: str
    construction_units: frozenset[str]
    construction_name: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ConstructionComponent:
    """
    施工片区
    基于拓扑从施工单元集合中拆分出的连通施工区域

    Attributes:
        construction_id: 施工工程 ID
        component_id: 施工片区 ID
        units: 片区内施工单元集合
        entry_portals: 入口门户集合（存在外部上游进入的施工单元）
        exit_portals: 出口门户集合（存在外部下游驶出的施工单元）
        upstream_frontiers: 最近外部上游节点
        downstream_frontiers: 最近外部下游节点
    """
    construction_id: str
    component_id: str
    units: set[str] = field(default_factory=set)
    entry_portals: set[str] = field(default_factory=set)
    exit_portals: set[str] = field(default_factory=set)
    upstream_frontiers: set[str] = field(default_factory=set)
    downstream_frontiers: set[str] = field(default_factory=set)


@dataclass
class ConstructionWindow:
    """
    局部施工窗口
    一个入口门户到一个出口门户之间的局部施工影响范围

    Attributes:
        construction_id: 施工工程 ID
        component_id: 来源施工片区 ID
        window_id: 局部窗口 ID
        start_unit: 局部施工窗口起点施工单元
        end_unit: 局部施工窗口终点施工单元
        covered_units: 该窗口覆盖的施工单元集合
        source: 来源标识（"portal" | "path_hit" | "mixed"）
        source_flow: 若来自历史 path 命中，记录对应流量
        source_path_count: 若来自历史 path 命中，记录 path 数
    """
    construction_id: str
    component_id: str
    window_id: str
    start_unit: str
    end_unit: str
    covered_units: set[str] = field(default_factory=set)
    source: str = "portal"
    source_flow: float = 0.0
    source_path_count: int = 0


@dataclass(frozen=True)
class RawAnchorCandidate:
    """
    原始锚点候选

    Attributes:
        construction_id: 施工工程 ID
        component_id: 来源施工片区 ID
        window_id: 来源局部施工窗口 ID
        anchor_start: 锚点起点
        anchor_end: 锚点终点
        level: 拓展层级
        distance_km: 总距离（公里，可选）
    """
    construction_id: str
    component_id: str
    window_id: str
    anchor_start: str
    anchor_end: str
    level: int
    distance_km: Optional[float] = None


@dataclass
class AnchorWindow:
    """
    锚点窗口
    多个局部施工窗口外扩合并后的全局锚点窗口

    Attributes:
        construction_id: 施工工程 ID
        anchor_start: 锚点起点
        anchor_end: 锚点终点
        source_component_ids: 来源施工片区 ID 集合
        source_window_ids: 来源局部施工窗口 ID 集合
        covered_units: 合并后的覆盖施工单元集合
        min_level: 最小拓展层级
    """
    construction_id: str
    anchor_start: str
    anchor_end: str
    source_component_ids: set[str] = field(default_factory=set)
    source_window_ids: set[str] = field(default_factory=set)
    covered_units: set[str] = field(default_factory=set)
    min_level: int = 0

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.construction_id, self.anchor_start, self.anchor_end)


@dataclass
class AnchorWindowStat:
    """
    锚点窗口聚合统计

    Attributes:
        construction_id: 施工工程 ID
        anchor_start: 锚点起点
        anchor_end: 锚点终点
        pass_flow: 经过施工流量
        bypass_flow: 绕行流量
        pass_path_count: 经过施工 path 数
        bypass_path_count: 绕行 path 数
        od_count: 涉及 OD 数量
    """
    construction_id: str
    anchor_start: str
    anchor_end: str
    pass_flow: float = 0.0
    bypass_flow: float = 0.0
    pass_path_count: int = 0
    bypass_path_count: int = 0
    od_count: int = 0

    @property
    def total_flow(self) -> float:
        return self.pass_flow + self.bypass_flow

    @property
    def bypass_ratio(self) -> float:
        if self.total_flow <= 0:
            return 0.0
        return self.bypass_flow / self.total_flow


@dataclass
class PathAssignment:
    """
    path 归属明细

    Attributes:
        construction_id: 施工工程 ID
        record_id: 原始 path 记录 ID
        enid: 入口
        exid: 出口
        assigned_anchor_start: 归属锚点起点
        assigned_anchor_end: 归属锚点终点
        route_type: 路由类型（"pass" | "bypass" | "unassigned"）
        hit_units: path 命中的施工单元列表
        first_hit: 第一个命中的施工单元
        last_hit: 最后一个命中的施工单元
        assignment_reason: 归属原因
        flow: 流量
    """
    construction_id: str
    record_id: str
    enid: str
    exid: str
    assigned_anchor_start: Optional[str]
    assigned_anchor_end: Optional[str]
    route_type: str
    hit_units: list[str] = field(default_factory=list)
    first_hit: Optional[str] = None
    last_hit: Optional[str] = None
    assignment_reason: str = ""
    flow: float = 0.0