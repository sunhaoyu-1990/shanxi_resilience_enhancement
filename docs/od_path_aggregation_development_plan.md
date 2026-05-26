# OD-path 施工锚点聚合模块开发计划文档

> 适用对象：Claude Code / 算法工程实现人员  
> 模块名称：`construction_anchor_path_aggregator`  
> 文档目标：将“基于拓扑、施工门户点、局部施工窗口、锚点外扩、全局去重归属”的 OD-path 聚合算法落地为可开发、可测试、可扩展的 Python 模块。

---

## 1. 需求背景

当前系统中存在大量 OD、路径 path 和对应流量 flow 数据。每条记录大致包含：

```text
OD = enid + exid
path = 收费单元 ID 按通行顺序拼接而成，例如 A|B|C|D|E
flow = 当前 OD-path 对应流量
```

由于 path 数量可能非常多，不适合逐条展示，需要围绕施工路段进行路径聚合。核心目标是：

1. 区分经过施工路段的路径和绕行路径；
2. 不展示路径内部细节，只返回用于解释的一对关键锚点；
3. 对经过相同锚点窗口的 path 进行流量聚合；
4. 对施工输入乱序、双向混合、长施工串、中途进入施工路段、不连续施工片区等复杂情况具备鲁棒性；
5. 避免同一条 path 被多个片区、多个局部窗口、多个锚点窗口重复统计。

---

## 2. 最终算法定位

本模块不是传统意义上的聚类算法，而是一个规则驱动的施工影响路径聚合算法。

推荐算法名称：

```text
基于拓扑施工门户与全局锚点窗口去重的 OD-path 聚合算法
```

英文模块名：

```text
Topology-based Construction Portal Anchor Path Aggregation
```

工程模块名：

```text
construction_anchor_path_aggregator
```

---

## 3. 核心设计原则

### 3.1 只信拓扑，不信 ID 后缀

施工单元 ID 的后两位可能是 `10`、`20`，但：

1. 后两位相同不一定属于同一方向；
2. 后两位不同也不代表可以直接识别双向关系；
3. 输入施工路段时，可能包含双向施工的多个单元；
4. 施工输入可能乱序，不表示真实通行顺序。

因此：

```text
施工输入只表示施工收费单元集合，不表示顺序、不表示方向、不表示片区。
```

片区、方向、上下游关系必须全部从有向路网拓扑中推导。

---

### 3.2 长施工串不能只从整段两端外扩锚点

对于长施工串，中间可能有多个立交、匝道、收费站接入点。大量车辆可能从中间进入施工串，部分经过施工路段。

如果只使用施工串整体两端外扩锚点，会导致：

1. 中途进入车辆不经过施工串最上游锚点；
2. 中途驶出车辆不经过施工串最下游锚点；
3. 这部分 path 无法被有效聚合；
4. 即使被更远锚点覆盖，也会丧失局部解释性。

因此必须引入：

```text
施工门户点 construction_portal
局部施工窗口 construction_window
锚点窗口 anchor_window
```

---

### 3.3 不同片区、不同局部窗口拓展到同一锚点时不能重复统计

一个施工工程中可能存在多个不连续施工片区，也可能同一个长施工片区内部产生多个局部施工窗口。

不同来源窗口可能都拓展到相同锚点：

```text
anchor_start -> anchor_end
```

此时必须合并为同一个全局锚点窗口：

```text
construction_id + anchor_start + anchor_end
```

最终流量只能统计一次。

---

### 3.4 同一条 path 在同一个施工工程下只能归属一个最终锚点窗口

同一条 path 可能同时满足多个窗口，例如：

```text
局部窗口 F -> K
整段窗口 C -> K
更大锚点窗口 A -> M
```

最终必须唯一归属。

归属优先级建议：

1. 优先匹配与 path 实际施工命中区间最贴近的局部施工窗口；
2. 其次选择锚点拓展层级更近的窗口；
3. 再选择锚点跨度更短的窗口；
4. 再选择覆盖施工单元更少、更局部的窗口；
5. 最后使用稳定排序兜底。

---

## 4. 术语定义

| 术语 | 英文名 | 含义 |
|---|---|---|
| 施工工程 | construction | 一次输入的施工路段集合，对应一个 construction_id |
| 施工单元集合 | construction_units | 输入施工 path 解析后的收费单元集合，不保证有序 |
| 有向拓扑 | directed_topology | 收费单元之间的上下游有向关系 from_unit -> to_unit |
| 施工片区 | construction_component | 基于拓扑从施工单元集合中拆出的连通施工区域 |
| 施工门户点 | construction_portal | 施工片区内部可被外部车辆进入或驶出的施工单元 |
| 入口门户 | entry_portal | 存在外部上游节点进入的施工单元 |
| 出口门户 | exit_portal | 存在下游外部节点驶出的施工单元 |
| 局部施工窗口 | construction_window | 一个入口门户到一个出口门户之间的局部施工影响范围 |
| 锚点窗口 | anchor_window | 局部施工窗口向外拓展得到的最终聚合关键点对 |
| pass path | pass | 经过锚点窗口，且命中该窗口覆盖施工单元的 path |
| bypass path | bypass | 经过锚点窗口，但未命中该窗口覆盖施工单元的 path |
| 全局去重 | global deduplication | 相同 anchor_start -> anchor_end 只保留一个窗口 |
| 唯一归属 | unique assignment | 每条 path 在一个 construction_id 下只归属一个最终窗口 |

---

## 5. 输入数据要求

### 5.1 OD-path 流量输入

建议字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| record_id | str | 是 | path 记录唯一 ID。如果没有，可以由 enid、exid、path 哈希生成 |
| enid | str | 是 | 入口收费站或入口单元 ID |
| exid | str | 是 | 出口收费站或出口单元 ID |
| path | str | 是 | 以 `|` 拼接的收费单元有序序列 |
| flow | float | 是 | 流量值 |
| stat_time | str/datetime | 否 | 统计时间粒度，可选 |
| vehicle_type | str | 否 | 车型，可选 |
| version | str | 否 | 路网版本，可选 |

示例：

```text
record_id,enid,exid,path,flow
r001,A,Z,A|B|C|D|E|F|G|Z,100
r002,A,Z,A|B|X|Y|G|Z,20
```

---

### 5.2 施工输入

建议字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| construction_id | str | 是 | 施工工程 ID |
| construction_path | str | 是 | 以 `|` 拼接的施工收费单元 ID，允许乱序、双向混合、不连续 |
| construction_name | str | 否 | 施工名称 |
| version | str | 否 | 路网版本 |

示例：

```text
construction_id = const_001
construction_path = C|D|E|F|G|H|I|J|K|P|Q|R
```

注意：

```text
construction_path 不表示施工单元顺序，只表示集合。
```

---

### 5.3 路网拓扑输入

建议字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| from_unit | str | 是 | 上游收费单元 |
| to_unit | str | 是 | 下游收费单元 |
| length_km | float | 否 | 拓扑边长度，用于距离停止条件 |
| road_id | str | 否 | 路线编号 |
| version | str | 否 | 路网版本 |

示例：

```text
from_unit,to_unit,length_km
A,B,2.1
B,C,3.0
C,D,1.5
D,E,2.0
```

---

## 6. 输出数据设计

建议至少输出三类结果：

1. 施工片区拆分结果；
2. 局部施工窗口结果；
3. 最终锚点窗口聚合结果。

---

### 6.1 施工片区表：`construction_component`

| 字段 | 类型 | 说明 |
|---|---|---|
| construction_id | str | 施工工程 ID |
| component_id | str | 施工片区 ID |
| unit_count | int | 片区内施工单元数量 |
| units | list[str] | 片区内施工单元集合 |
| entry_portals | list[str] | 入口门户 |
| exit_portals | list[str] | 出口门户 |
| upstream_frontiers | list[str] | 最近外部上游节点 |
| downstream_frontiers | list[str] | 最近外部下游节点 |

---

### 6.2 局部施工窗口表：`construction_window`

| 字段 | 类型 | 说明 |
|---|---|---|
| construction_id | str | 施工工程 ID |
| component_id | str | 来源施工片区 ID |
| window_id | str | 局部窗口 ID |
| start_unit | str | 局部施工窗口起点施工单元 |
| end_unit | str | 局部施工窗口终点施工单元 |
| covered_units | list[str] | 该窗口覆盖的施工单元 |
| source | str | portal/path_hit/mixed |
| source_flow | float | 若来自历史 path 命中，记录对应流量 |
| source_path_count | int | 若来自历史 path 命中，记录 path 数 |

---

### 6.3 锚点窗口聚合表：`construction_anchor_window_agg`

最终展示和统计主要使用这张表。

| 字段 | 类型 | 说明 |
|---|---|---|
| construction_id | str | 施工工程 ID |
| anchor_start | str | 锚点起点 |
| anchor_end | str | 锚点终点 |
| anchor_level | int | 最近拓展层级 |
| source_component_ids | list[str] | 来源施工片区 |
| source_window_ids | list[str] | 来源局部施工窗口 |
| covered_unit_count | int | 覆盖施工单元数量 |
| pass_flow | float | 经过施工流量 |
| bypass_flow | float | 绕行流量 |
| total_flow | float | pass_flow + bypass_flow |
| bypass_ratio | float | bypass_flow / total_flow |
| pass_path_count | int | 经过施工 path 数 |
| bypass_path_count | int | 绕行 path 数 |
| od_count | int | 涉及 OD 数量 |
| representative_pass_path | str | 代表性经过施工 path，可选 |
| representative_bypass_path | str | 代表性绕行 path，可选 |

---

### 6.4 path 归属明细表：`path_assignment_detail`

用于调试、抽检和解释。

| 字段 | 类型 | 说明 |
|---|---|---|
| construction_id | str | 施工工程 ID |
| record_id | str | 原始 path 记录 ID |
| enid | str | 入口 |
| exid | str | 出口 |
| assigned_anchor_start | str | 归属锚点起点 |
| assigned_anchor_end | str | 归属锚点终点 |
| route_type | str | pass/bypass/unassigned |
| hit_units | list[str] | path 命中的施工单元 |
| first_hit | str | 第一个命中的施工单元 |
| last_hit | str | 最后一个命中的施工单元 |
| assignment_reason | str | 归属原因 |
| flow | float | 流量 |

---

## 7. 配置项设计

建议使用 YAML 配置。

```yaml
construction_anchor_path_aggregation:
  path:
    delimiter: "|"
    remove_empty_unit: true
    deduplicate_consecutive_units: false

  component_split:
    # 注意：这里的 strong_directed_reachability 不是严格 SCC。
    # 含义是：基于有向拓扑识别方向性施工结构，不依赖 ID 后缀。
    mode: strong_directed_reachability
    min_component_unit_count: 1

  construction_hit:
    mode: any_hit
    min_hit_count: 1
    min_hit_ratio: 0.0

  construction_window:
    enable_portal_windows: true
    enable_path_hit_windows: true
    min_path_hit_flow: 1
    min_path_hit_count: 1
    max_windows_per_component: 200

  anchor_expand:
    max_expand_level: 5
    max_expand_distance_km: 30
    stop_at_first_valid: true
    min_marginal_flow_gain_ratio: 0.03

  valid_anchor:
    min_pass_flow: 1
    min_bypass_flow: 1
    min_pass_path_count: 1
    min_bypass_path_count: 1

  global_assignment:
    unique_assignment: true
    priority:
      - hit_window_similarity
      - anchor_level
      - anchor_span
      - covered_unit_count
      - stable_key

  output:
    keep_component_table: true
    keep_construction_window_table: true
    keep_path_assignment_detail: true
    keep_representative_path: true
```

---

## 8. 模块目录建议

建议 Claude Code 按如下结构开发：

```text
src/
  construction_anchor_path_aggregator/
    __init__.py
    models.py
    config.py
    parser.py
    topology.py
    component_splitter.py
    portal_detector.py
    construction_window_builder.py
    anchor_expander.py
    anchor_window_merger.py
    path_classifier.py
    assignment.py
    aggregator.py
    output.py
    utils.py

tests/
  construction_anchor_path_aggregator/
    test_parser.py
    test_topology.py
    test_component_splitter.py
    test_portal_detector.py
    test_construction_window_builder.py
    test_anchor_expander.py
    test_anchor_window_merger.py
    test_path_classifier.py
    test_assignment.py
    test_aggregator_end_to_end.py
```

---

## 9. 数据模型设计

在 `models.py` 中定义核心 dataclass。

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class PathRecord:
    record_id: str
    enid: str
    exid: str
    path: str
    flow: float
    stat_time: Optional[str] = None
    vehicle_type: Optional[str] = None
    version: Optional[str] = None


@dataclass
class TopologyEdge:
    from_unit: str
    to_unit: str
    length_km: Optional[float] = None
    road_id: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ConstructionInput:
    construction_id: str
    construction_path: str
    construction_name: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ConstructionComponent:
    construction_id: str
    component_id: str
    units: Set[str]
    entry_portals: Set[str] = field(default_factory=set)
    exit_portals: Set[str] = field(default_factory=set)
    upstream_frontiers: Set[str] = field(default_factory=set)
    downstream_frontiers: Set[str] = field(default_factory=set)


@dataclass
class ConstructionWindow:
    construction_id: str
    component_id: str
    window_id: str
    start_unit: str
    end_unit: str
    covered_units: Set[str]
    source: str
    source_flow: float = 0.0
    source_path_count: int = 0


@dataclass
class RawAnchorCandidate:
    construction_id: str
    component_id: str
    window_id: str
    anchor_start: str
    anchor_end: str
    level: int
    distance_km: Optional[float] = None


@dataclass
class AnchorWindow:
    construction_id: str
    anchor_start: str
    anchor_end: str
    source_component_ids: Set[str] = field(default_factory=set)
    source_window_ids: Set[str] = field(default_factory=set)
    covered_units: Set[str] = field(default_factory=set)
    min_level: int = 0
    min_distance_km: Optional[float] = None

    @property
    def key(self) -> Tuple[str, str, str]:
        return self.construction_id, self.anchor_start, self.anchor_end


@dataclass
class AnchorWindowStat:
    construction_id: str
    anchor_start: str
    anchor_end: str
    pass_flow: float = 0.0
    bypass_flow: float = 0.0
    pass_path_count: int = 0
    bypass_path_count: int = 0

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
    construction_id: str
    record_id: str
    enid: str
    exid: str
    assigned_anchor_start: Optional[str]
    assigned_anchor_end: Optional[str]
    route_type: str  # pass / bypass / unassigned
    hit_units: List[str]
    first_hit: Optional[str]
    last_hit: Optional[str]
    assignment_reason: str
    flow: float
```

---

## 10. 开发任务拆解

### Task 1：基础解析模块

文件：`parser.py`

功能：

1. 解析 path 字符串；
2. 解析 construction_path 字符串；
3. 可选去空值；
4. 可选相邻重复去重。

函数建议：

```python
def parse_unit_sequence(seq: str, delimiter: str = "|", remove_empty: bool = True) -> list[str]:
    pass


def parse_construction_units(construction_path: str, delimiter: str = "|") -> set[str]:
    pass
```

测试点：

1. 空字符串；
2. 连续分隔符；
3. 首尾分隔符；
4. 重复收费单元；
5. 乱序施工输入。

---

### Task 2：拓扑构建模块

文件：`topology.py`

功能：

1. 从 `TopologyEdge` 构建下游邻接表；
2. 构建上游邻接表；
3. 支持查询上游、下游；
4. 支持限制在某个 allowed_units 集合内做有向可达搜索；
5. 支持计算拓扑扩展层级；
6. 如有 length_km，支持距离累计。

函数建议：

```python
def build_downstream_adj(edges: list[TopologyEdge]) -> dict[str, set[str]]:
    pass


def build_upstream_adj(edges: list[TopologyEdge]) -> dict[str, set[str]]:
    pass


def directed_reachable_within_set(
    start: str,
    allowed_units: set[str],
    downstream_adj: dict[str, set[str]],
) -> set[str]:
    pass


def has_directed_path_within_set(
    start: str,
    end: str,
    allowed_units: set[str],
    downstream_adj: dict[str, set[str]],
) -> bool:
    pass
```

---

### Task 3：施工片区拆分模块

文件：`component_splitter.py`

功能：

1. 输入施工单元集合；
2. 只根据拓扑关系拆分施工片区；
3. 不依赖 ID 后缀；
4. 支持同一后缀下多个不连续片区；
5. 避免严格 SCC 导致单向链被拆成单点。

实现建议：

第一版采用“拓扑弱连通候选区域 + 有向可达结构保留”的方式：

```python
def split_components_by_topology(
    construction_id: str,
    construction_units: set[str],
    downstream_adj: dict[str, set[str]],
    upstream_adj: dict[str, set[str]],
) -> list[ConstructionComponent]:
    pass
```

注意：

```text
拆片区时可以用上下游邻接合并判断拓扑连通；
识别门户点、外扩锚点、path 判定时必须使用有向拓扑。
```

测试用例：

```text
A -> B -> C
D -> E
施工集合 = {A,B,C,D,E}
应拆成两个 component：{A,B,C} 和 {D,E}
```

```text
A10 -> B10 -> C10
M10 -> N10
施工集合 = {A10,B10,C10,M10,N10}
应拆成两个 component，不能因为后缀都是 10 合并。
```

---

### Task 4：施工门户点识别模块

文件：`portal_detector.py`

功能：识别每个施工片区的入口门户、出口门户和最近外部边界。

定义：

```text
入口门户 entry_portal：
  u 属于 component.units，且存在 p 不属于 component.units，p -> u

出口门户 exit_portal：
  u 属于 component.units，且存在 q 不属于 component.units，u -> q
```

函数建议：

```python
def detect_portals(
    component: ConstructionComponent,
    downstream_adj: dict[str, set[str]],
    upstream_adj: dict[str, set[str]],
) -> ConstructionComponent:
    pass
```

返回时填充：

```python
component.entry_portals
component.exit_portals
component.upstream_frontiers
component.downstream_frontiers
```

测试拓扑：

```text
B -> C -> D -> E -> F
X -> D
E -> Y
施工集合 = {C,D,E}
```

预期：

```text
entry_portals = {C,D}
exit_portals = {E}
upstream_frontiers = {B,X}
downstream_frontiers = {F,Y}
```

---

### Task 5：局部施工窗口生成模块

文件：`construction_window_builder.py`

局部施工窗口来源有两种：

1. 门户点拓扑生成；
2. 实际 path 命中区间补充。

---

#### 5.1 门户点生成窗口

对每个 entry_portal 和 exit_portal：

```text
如果 entry_portal 在施工子图内有向可达 exit_portal，则生成 construction_window。
```

函数建议：

```python
def build_windows_by_portals(
    construction_id: str,
    component: ConstructionComponent,
    downstream_adj: dict[str, set[str]],
) -> list[ConstructionWindow]:
    pass
```

窗口 covered_units 第一版可取：

```text
从 start_unit 出发，在 component.units 内可达，且能够到达 end_unit 的施工单元集合。
```

如果实现复杂，第一版可简化为：

```text
covered_units = start_unit 在 component.units 内可达集合 与 可以到达 end_unit 的集合交集。
```

---

#### 5.2 基于 path 命中区间补充窗口

对每条 path：

```text
hit_seq = path 中属于 construction_units 的收费单元序列
first_hit = hit_seq[0]
last_hit = hit_seq[-1]
```

将高频或高流量的 `first_hit -> last_hit` 补充为局部窗口。

函数建议：

```python
def build_windows_by_path_hits(
    construction_id: str,
    components: list[ConstructionComponent],
    path_records: list[PathRecord],
    construction_units: set[str],
    delimiter: str = "|",
    min_path_hit_flow: float = 1,
    min_path_hit_count: int = 1,
) -> list[ConstructionWindow]:
    pass
```

注意：

1. 只为命中施工单元的 pass path 生成窗口；
2. first_hit 和 last_hit 必须属于同一个 component；
3. 如果跨多个 component，应按 component 分别提取命中区间；
4. 异常 path 不应生成过多碎窗口，应受 `min_path_hit_flow` 和 `min_path_hit_count` 控制。

---

### Task 6：锚点外扩模块

文件：`anchor_expander.py`

功能：对每个局部施工窗口，从窗口起终点向外生成候选锚点。

基本逻辑：

```text
窗口 start_unit 的外部上游方向：沿 upstream_adj 外扩；
窗口 end_unit 的外部下游方向：沿 downstream_adj 外扩。
```

函数建议：

```python
def expand_upstream_levels(
    start_unit: str,
    upstream_adj: dict[str, set[str]],
    blocked_units: set[str],
    max_expand_level: int,
) -> dict[int, set[str]]:
    pass


def expand_downstream_levels(
    end_unit: str,
    downstream_adj: dict[str, set[str]],
    blocked_units: set[str],
    max_expand_level: int,
) -> dict[int, set[str]]:
    pass


def generate_anchor_candidates_for_window(
    window: ConstructionWindow,
    upstream_adj: dict[str, set[str]],
    downstream_adj: dict[str, set[str]],
    max_expand_level: int,
) -> list[RawAnchorCandidate]:
    pass
```

注意：

1. 外扩时需要 blocked_units，避免又扩回施工窗口内部；
2. level 0 应优先取最近外部上游/下游节点；
3. 如果窗口 start_unit 本身存在多个外部上游，level 0 可能有多个 anchor_start；
4. 如果窗口 end_unit 存在多个外部下游，level 0 可能有多个 anchor_end；
5. 多个 start 和 end 组合会产生多个候选锚点。

---

### Task 7：锚点有效性预统计与停止条件

文件：`anchor_expander.py` 或 `path_classifier.py`

目标：对每个局部窗口，从近到远外扩，找到最近有效锚点。

有效锚点条件：

```text
pass_flow >= min_pass_flow
bypass_flow >= min_bypass_flow
pass_path_count >= min_pass_path_count
bypass_path_count >= min_bypass_path_count
```

停止条件：

1. 找到最近有效锚点后停止；
2. 达到最大拓展层级后停止；
3. 达到最大拓展距离后停止；
4. 外扩新增流量低于边际收益阈值后停止。

第一版可优先实现：

```text
stop_at_first_valid + max_expand_level
```

后续再补充距离和边际收益。

函数建议：

```python
def stat_anchor_candidate(
    candidate: RawAnchorCandidate,
    covered_units: set[str],
    path_records: list[PathRecord],
    delimiter: str = "|",
) -> AnchorWindowStat:
    pass


def find_valid_anchor_candidates_for_window(
    window: ConstructionWindow,
    path_records: list[PathRecord],
    upstream_adj: dict[str, set[str]],
    downstream_adj: dict[str, set[str]],
    config,
) -> list[RawAnchorCandidate]:
    pass
```

---

### Task 8：全局锚点窗口合并模块

文件：`anchor_window_merger.py`

功能：

1. 接收所有局部窗口生成的有效锚点候选；
2. 按 `construction_id + anchor_start + anchor_end` 合并；
3. 合并来源 component_ids；
4. 合并来源 window_ids；
5. 合并 covered_units；
6. 取最小 level 作为 min_level。

函数建议：

```python
def merge_anchor_candidates_to_windows(
    candidates: list[RawAnchorCandidate],
    window_map: dict[str, ConstructionWindow],
) -> list[AnchorWindow]:
    pass
```

合并规则：

```text
key = construction_id + anchor_start + anchor_end
source_component_ids = union
source_window_ids = union
covered_units = union
min_level = min(level)
```

---

### Task 9：path 分类与命中区间提取模块

文件：`path_classifier.py`

功能：

1. 判断 path 是否按顺序经过 anchor_start -> anchor_end；
2. 提取 path 命中的施工单元序列；
3. 提取 first_hit / last_hit；
4. 对某个 anchor_window 判断 pass/bypass/unmatched。

函数建议：

```python
def has_ordered_pair(path_units: list[str], start: str, end: str) -> bool:
    pass


def extract_hit_units(path_units: list[str], construction_units: set[str]) -> list[str]:
    pass


def classify_path_for_anchor_window(
    path_units: list[str],
    window: AnchorWindow,
) -> str | None:
    """
    return:
      pass
      bypass
      None
    """
    pass
```

`has_ordered_pair` 注意不要简单使用 `index()`，因为 path 中可能存在重复单元。

推荐实现：

```python
def has_ordered_pair(path_units: list[str], start: str, end: str) -> bool:
    start_positions = [i for i, u in enumerate(path_units) if u == start]
    end_positions = [i for i, u in enumerate(path_units) if u == end]
    if not start_positions or not end_positions:
        return False
    return min(start_positions) < max(end_positions)
```

---

### Task 10：全局唯一归属模块

文件：`assignment.py`

目标：每条 path 在同一个 construction_id 下只归属一个最终 anchor_window。

#### 10.1 pass path 归属

对于命中施工单元的 path：

1. 提取 first_hit / last_hit；
2. 优先匹配来源 construction_window 与 first_hit/last_hit 最接近的 anchor_window；
3. 如果多个窗口可选，按优先级排序。

建议排序 key：

```python
(
    hit_window_distance,      # 越小越好
    window.min_level,         # 越小越好
    len(window.covered_units), # 越小越局部
    window.anchor_start,
    window.anchor_end,
)
```

第一版可以简化为：

```python
(
    window.min_level,
    len(window.covered_units),
    window.anchor_start,
    window.anchor_end,
)
```

但需要在代码注释中预留 hit_window_similarity 扩展。

#### 10.2 bypass path 归属

对于没有命中施工单元的 path：

1. 遍历所有有效 anchor_window；
2. 如果 path 经过 anchor_start -> anchor_end，且未命中 covered_units，则是 bypass 候选；
3. 多个候选时按优先级选择一个。

建议排序 key：

```python
(
    window.min_level,
    len(window.covered_units),
    window.anchor_start,
    window.anchor_end,
)
```

函数建议：

```python
def assign_path_to_best_window(
    record: PathRecord,
    anchor_windows: list[AnchorWindow],
    construction_units: set[str],
    delimiter: str = "|",
) -> PathAssignment:
    pass
```

---

### Task 11：聚合输出模块

文件：`aggregator.py` 和 `output.py`

主入口函数建议：

```python
def aggregate_construction_paths(
    construction_input: ConstructionInput,
    path_records: list[PathRecord],
    topology_edges: list[TopologyEdge],
    config,
) -> dict:
    """
    return:
      {
        "components": list[ConstructionComponent],
        "construction_windows": list[ConstructionWindow],
        "anchor_windows": list[AnchorWindow],
        "assignments": list[PathAssignment],
        "anchor_window_agg": list[dict],
      }
    """
    pass
```

聚合逻辑：

```text
1. 解析施工集合；
2. 构建上下游拓扑；
3. 拆施工片区；
4. 识别门户点；
5. 生成局部施工窗口；
6. 对局部窗口生成最近有效锚点候选；
7. 合并全局锚点窗口；
8. 对 path 做唯一归属；
9. 按 anchor_window 聚合 pass/bypass flow；
10. 输出结果表。
```

---

## 11. 端到端主流程伪代码

```python
def aggregate_construction_paths(construction_input, path_records, topology_edges, config):
    # 1. 解析输入
    construction_units = parse_construction_units(
        construction_input.construction_path,
        delimiter=config.path.delimiter,
    )

    # 2. 构建拓扑
    downstream_adj = build_downstream_adj(topology_edges)
    upstream_adj = build_upstream_adj(topology_edges)

    # 3. 拆施工片区
    components = split_components_by_topology(
        construction_id=construction_input.construction_id,
        construction_units=construction_units,
        downstream_adj=downstream_adj,
        upstream_adj=upstream_adj,
    )

    # 4. 识别门户点
    components = [
        detect_portals(c, downstream_adj, upstream_adj)
        for c in components
    ]

    # 5. 生成局部施工窗口
    all_windows = []
    for component in components:
        portal_windows = build_windows_by_portals(
            construction_id=construction_input.construction_id,
            component=component,
            downstream_adj=downstream_adj,
        )
        all_windows.extend(portal_windows)

    path_hit_windows = build_windows_by_path_hits(
        construction_id=construction_input.construction_id,
        components=components,
        path_records=path_records,
        construction_units=construction_units,
        delimiter=config.path.delimiter,
        min_path_hit_flow=config.construction_window.min_path_hit_flow,
        min_path_hit_count=config.construction_window.min_path_hit_count,
    )
    all_windows.extend(path_hit_windows)

    # 6. 局部窗口去重
    all_windows = deduplicate_construction_windows(all_windows)

    # 7. 对每个局部窗口生成最近有效锚点候选
    raw_anchor_candidates = []
    for window in all_windows:
        candidates = find_valid_anchor_candidates_for_window(
            window=window,
            path_records=path_records,
            upstream_adj=upstream_adj,
            downstream_adj=downstream_adj,
            config=config,
        )
        raw_anchor_candidates.extend(candidates)

    # 8. 全局锚点窗口合并
    window_map = {w.window_id: w for w in all_windows}
    anchor_windows = merge_anchor_candidates_to_windows(
        candidates=raw_anchor_candidates,
        window_map=window_map,
    )

    # 9. path 全局唯一归属
    assignments = []
    for record in path_records:
        assignment = assign_path_to_best_window(
            record=record,
            anchor_windows=anchor_windows,
            construction_units=construction_units,
            delimiter=config.path.delimiter,
        )
        assignments.append(assignment)

    # 10. 聚合
    agg_rows = aggregate_assignments(assignments, anchor_windows)

    return {
        "components": components,
        "construction_windows": all_windows,
        "anchor_windows": anchor_windows,
        "assignments": assignments,
        "anchor_window_agg": agg_rows,
    }
```

---

## 12. 关键边界场景与处理规则

### 12.1 施工输入乱序

处理规则：

```text
解析为集合；禁止根据输入顺序推断起终点。
```

---

### 12.2 双向施工混合输入

处理规则：

```text
不按 ID 后缀拆方向；只基于有向拓扑拆片区和门户。
```

---

### 12.3 后两位相同但不同方向或不同片区

处理规则：

```text
拓扑不连通则拆成多个 component。
```

---

### 12.4 长施工串中途进入

处理规则：

```text
通过入口门户和 path first_hit 生成局部施工窗口。
```

---

### 12.5 长施工串中途驶出

处理规则：

```text
通过出口门户和 path last_hit 生成局部施工窗口。
```

---

### 12.6 多个片区拓展到相同锚点

处理规则：

```text
合并成同一个 anchor_window，flow 只统计一次。
```

---

### 12.7 同一路径匹配多个锚点窗口

处理规则：

```text
全局唯一归属，按优先级选择最佳窗口。
```

---

### 12.8 找不到 bypass path

处理规则：

```text
如果配置要求 pass/bypass 对比，则该锚点窗口不是有效窗口。
如果配置允许单纯 pass 统计，则可以输出 pass-only 窗口。
```

第一版建议只输出有效对比窗口：

```text
pass_flow > 0 且 bypass_flow > 0
```

---

### 12.9 锚点无限外扩

处理规则：

```text
达到 max_expand_level 或 max_expand_distance_km 后停止；找到最近有效窗口后停止。
```

---

## 13. 单元测试设计

### 13.1 测试：乱序施工输入

拓扑：

```text
A -> B -> C -> D -> E
```

施工输入：

```text
D|B|C
```

预期：

```text
施工集合 = {B,C,D}
不能按输入顺序认为 D 是起点，C 是终点。
```

---

### 13.2 测试：同后缀不连续片区

拓扑：

```text
A10 -> B10 -> C10
M10 -> N10 -> O10
```

施工输入：

```text
A10|B10|C10|M10|N10|O10
```

预期：

```text
拆成两个 component。
```

---

### 13.3 测试：长施工串中途进入

拓扑：

```text
A -> B -> C -> D -> E -> F -> G -> H -> I -> J -> K -> L
X -> F
Y -> H
```

施工集合：

```text
C|D|E|F|G|H|I|J|K
```

path：

```text
p1: A|B|C|D|E|F|G|H|I|J|K|L, flow=100
p2: X|F|G|H|I|J|K|L, flow=50
p3: X|U|V|L, flow=20
```

预期：

1. p1 是 pass；
2. p2 是中途进入施工串的 pass；
3. p2 不应因为没经过 B 而漏聚；
4. p3 可作为某个 X -> L 窗口的 bypass。

---

### 13.4 测试：不同局部窗口拓展到相同锚点

构造两个窗口都拓展到：

```text
A -> L
```

预期：

```text
只生成一个 AnchorWindow。
source_window_ids 包含两个来源窗口。
flow 不重复统计。
```

---

### 13.5 测试：同一条 path 匹配多个窗口

path：

```text
A|B|C|D|E|F|G|H|I|J|K|L
```

它同时匹配：

```text
B -> L
A -> L
```

预期：

```text
只归属一个窗口，优先归属更近、更局部窗口。
```

---

### 13.6 测试：bypass 判定

施工窗口 covered_units：

```text
{C,D,E}
```

锚点：

```text
B -> F
```

path：

```text
B|X|Y|F
```

预期：

```text
经过 B -> F，未命中 {C,D,E}，route_type = bypass。
```

---

## 14. 验收标准

### 14.1 功能验收

模块应满足：

1. 能解析乱序施工输入；
2. 能基于拓扑拆分不连续施工片区；
3. 不依赖收费单元 ID 后缀识别方向；
4. 能识别长施工串中间入口、出口门户；
5. 能生成局部施工窗口；
6. 能对每个局部窗口进行锚点外扩；
7. 能找到最近有效锚点并停止；
8. 能对相同锚点窗口进行全局去重；
9. 能保证同一 path 在同一 construction_id 下唯一归属；
10. 能输出 pass_flow、bypass_flow、bypass_ratio；
11. 能输出 path 归属明细用于抽检。

---

### 14.2 正确性验收

必须通过以下检查：

1. `sum(assigned_flow)` 不应大于原始 path 总流量；
2. 同一个 `record_id` 在同一个 `construction_id` 下最多出现一次有效归属；
3. 同一个 `construction_id + anchor_start + anchor_end` 只出现一个全局锚点窗口；
4. pass path 必须命中该窗口 covered_units；
5. bypass path 必须不命中该窗口 covered_units；
6. 所有 assigned path 必须经过对应 anchor_start -> anchor_end；
7. 未命中任何窗口的 path 应标记为 `unassigned`，不能强行归类。

---

### 14.3 性能验收

第一版目标：

| 数据规模 | 目标 |
|---|---|
| 10 万条 path | 可在分钟级完成 |
| 100 万条 path | 可通过批处理完成 |
| 单个 construction 的窗口数量 | 应受 max_windows_per_component 控制 |
| 单个 path 归属 | 不应遍历过多无关窗口 |

优化建议：

1. path 预解析并缓存；
2. 为每个 unit 建立倒排索引：unit -> record_ids；
3. anchor_window 预筛选候选 path，避免全量扫描；
4. 大规模数据下优先用批处理和 Pandas/Polars；
5. 数据库版本可后续将 path explode 成明细表，用 SQL 加速匹配。

---

## 15. 性能优化方向

### 15.1 path 解析缓存

不要在每个窗口统计时反复 split path。

建议预处理：

```python
parsed_paths = {
    record_id: [unit1, unit2, unit3, ...]
}
```

---

### 15.2 单元倒排索引

构建：

```python
unit_to_record_ids = {
    unit_id: set(record_id)
}
```

用途：

1. 快速找命中施工单元的 pass 候选；
2. 快速找经过 anchor_start 和 anchor_end 的候选。

---

### 15.3 锚点候选 path 预筛选

对于锚点：

```text
anchor_start -> anchor_end
```

候选 path 必须同时包含 anchor_start 和 anchor_end。

可先取：

```python
candidate_ids = unit_to_record_ids[anchor_start] & unit_to_record_ids[anchor_end]
```

再做有序性判断。

---

### 15.4 窗口数量控制

长施工串可能产生大量 entry_portal × exit_portal 组合。

必须控制：

```yaml
max_windows_per_component: 200
min_path_hit_flow: 1
min_path_hit_count: 1
```

如果窗口过多，优先保留：

1. path_hit_flow 高的窗口；
2. 覆盖更多 pass flow 的窗口；
3. 门户点生成的核心窗口；
4. 整段窗口。

---

## 16. 日志与调试建议

建议输出关键日志：

```text
[component_split] construction_id=xxx, component_count=3
[portal_detect] component_id=xxx, entry_count=5, exit_count=4
[window_build] component_id=xxx, portal_windows=20, path_hit_windows=8
[anchor_expand] window_id=xxx, valid_anchor_count=2, selected_level=1
[anchor_merge] raw_candidates=50, merged_anchor_windows=12
[assignment] total_records=100000, assigned=23000, unassigned=77000
[aggregation] anchor_window_count=12, total_pass_flow=xxx, total_bypass_flow=xxx
```

对于异常情况要 warning：

1. 施工单元不在拓扑中；
2. component 没有入口门户；
3. component 没有出口门户；
4. 局部窗口找不到有效锚点；
5. 锚点外扩达到 max_expand_level 仍无 bypass；
6. 某 path 命中施工但没有归属窗口。

---

## 17. Claude Code 开发提示词建议

可以将下面提示词直接交给 Claude Code：

```text
请根据当前仓库结构，实现 construction_anchor_path_aggregator 模块。

开发目标：
实现一个基于有向路网拓扑、施工门户点、局部施工窗口、锚点外扩、全局锚点窗口去重、path 唯一归属的 OD-path 聚合算法。

请按以下顺序开发：
1. 新建 src/construction_anchor_path_aggregator/ 模块；
2. 实现 models.py 中的数据结构；
3. 实现 parser.py，完成 path 和施工输入解析；
4. 实现 topology.py，完成上下游邻接表和有向可达搜索；
5. 实现 component_splitter.py，基于拓扑拆施工片区，不依赖 ID 后缀；
6. 实现 portal_detector.py，识别 entry_portals、exit_portals、frontiers；
7. 实现 construction_window_builder.py，基于门户点和 path first_hit/last_hit 生成局部施工窗口；
8. 实现 anchor_expander.py，按 level 向上游/下游外扩并找最近有效锚点；
9. 实现 anchor_window_merger.py，按 construction_id + anchor_start + anchor_end 合并锚点窗口；
10. 实现 path_classifier.py 和 assignment.py，保证每条 path 在同一个 construction_id 下唯一归属；
11. 实现 aggregator.py，提供 aggregate_construction_paths 主入口；
12. 编写 tests/construction_anchor_path_aggregator/ 下的单元测试和端到端测试。

请特别注意：
- 施工输入不代表顺序；
- 不能用收费单元 ID 后缀判断方向；
- 长施工串需要从中间门户点生成局部施工窗口；
- 不同片区或不同局部窗口拓展到相同锚点时必须全局去重；
- 同一条 path 不能重复统计；
- path 中可能存在重复收费单元，不能简单使用 index 判断顺序。

请先实现第一版可运行版本，优先保证正确性和可测试性，再考虑性能优化。
```

---

## 18. 第一版开发优先级

### P0：必须实现

1. 数据模型；
2. path/施工输入解析；
3. 拓扑邻接表；
4. 施工片区拆分；
5. 门户点识别；
6. 基于 path_hit 的局部施工窗口；
7. 锚点 level 外扩；
8. pass/bypass 判定；
9. 全局锚点去重；
10. path 唯一归属；
11. 聚合输出；
12. 端到端测试。

### P1：建议实现

1. 门户点 entry × exit 拓扑窗口；
2. max_windows_per_component 控制；
3. 代表路径输出；
4. path_assignment_detail；
5. 日志和 warning。

### P2：后续优化

1. 拓展距离 max_expand_distance_km；
2. 边际收益停止；
3. 大规模性能索引；
4. 数据库 SQL 版本；
5. 多施工工程批处理；
6. 时间粒度、车型维度扩展。

---

## 19. 第一版实现建议

为了尽快落地，第一版可以做如下简化：

1. 片区拆分采用拓扑弱连通，不使用严格 SCC；
2. 局部窗口主要基于 path first_hit / last_hit 生成；
3. 门户点窗口作为辅助补充；
4. 锚点外扩只实现 level 控制，不实现距离控制；
5. 找到第一个满足 pass/bypass 的 level 后停止；
6. 全局锚点窗口按 key 合并；
7. path 归属优先级先用 `min_level + covered_unit_count + stable_key`；
8. 保留接口，后续再补 `hit_window_similarity` 和距离权重。

这样第一版能先跑通主流程，并覆盖你当前最关心的复杂业务场景。

---

## 20. 最终交付物清单

Claude Code 完成后应交付：

```text
src/construction_anchor_path_aggregator/
  models.py
  config.py
  parser.py
  topology.py
  component_splitter.py
  portal_detector.py
  construction_window_builder.py
  anchor_expander.py
  anchor_window_merger.py
  path_classifier.py
  assignment.py
  aggregator.py
  output.py
  utils.py

tests/construction_anchor_path_aggregator/
  test_parser.py
  test_topology.py
  test_component_splitter.py
  test_portal_detector.py
  test_construction_window_builder.py
  test_anchor_expander.py
  test_anchor_window_merger.py
  test_path_classifier.py
  test_assignment.py
  test_aggregator_end_to_end.py
```

主入口函数：

```python
aggregate_construction_paths(
    construction_input: ConstructionInput,
    path_records: list[PathRecord],
    topology_edges: list[TopologyEdge],
    config,
) -> dict
```

---

## 21. 最后总结

本模块的核心不是“按施工路段两端粗暴聚合”，而是：

```text
施工输入集合
  -> 拓扑片区拆分
  -> 施工门户识别
  -> 局部施工窗口生成
  -> 锚点逐级外扩
  -> 最近有效窗口筛选
  -> 全局锚点窗口去重
  -> path 唯一归属
  -> pass/bypass 流量聚合
```

这个设计可以解决：

1. 施工输入乱序；
2. 双向单元混合；
3. ID 后缀不可靠；
4. 同方向多个不连续施工片区；
5. 长施工串中途进入/驶出；
6. 锚点需要动态外扩；
7. 锚点不能无限外扩；
8. 多片区、多窗口拓展到相同锚点不能重复统计；
9. 同一条 path 不能重复归属；
10. 最终展示只保留关键锚点和聚合流量。
