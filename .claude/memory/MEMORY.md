# 陕交控多路段改扩建韧性提升项目（一期）- 项目记忆

## 项目定位

- **项目名称**: 陕交控多路段改扩建韧性提升项目（一期）
- **类型**: 后端算法工程
- **目标**: 围绕一期最小可用版本（MVP）主链路，完成工程化实现
- **核心**: Python + SQL 为主，PostgreSQL + PostGIS 数据库

## 一期范围

固定模块（M0~M5）：

| 模块 | 名称 | 主要职责 |
|------|------|----------|
| M0 | 数据工程 | ODS 数据加载、DIM 维表构建、方案映射、OD-路径映射 |
| M1 | 通行能力评估 | 车道数折算、可用车道数计算、能力规则匹配 |
| M2 | 流量与OD补全 | OD 流量统计、路段流量统计、SourceFlag 溯源 |
| M3 | 交通影响分析 | 供需比计算、影响流量统计、影响等级判定 |
| M4 | 分流路径优化 | 候选路径生成、里程差/收费差计算、分流管控点 |
| M5 | 通行费影响测算 | 通行费增减计算、影响类型判定、方案汇总 |

## 关键字段

- `section_number` - 同一单一路径上的收费单元归属同一编号，用于路径归并和收费单元映射
- `scheme_id` - 施工方案 ID
- `section_id` - 收费单元 ID
- `od_id` - OD 对 ID
- `path_id` - 路径 ID

## 关键业务逻辑

### BL-001: 判断收费单元是否属于交控集团

**详细文档**: `docs/业务逻辑记录.md`

**简要说明**:
1. 提取收费单元 ID 前 11 位
2. 匹配 `research/data/收费路段.xls` 中的"收费路段编号"字段
3. 查看匹配数据的"路段性质"字段
   - `"还贷性"` → 属于交控集团
   - 其他 → 不属于交控集团

**使用模块**: M0, M1, M2 等

## 数据溯源标记 - SourceFlag

| 值 | 含义 |
|-----|------|
| `actual` | 真实采集数据 |
| `filled` | 统计补全数据 |
| `rule` | 规则生成数据 |
| `api` | 外部接口数据 |
| `computed` | 计算派生数据 |

## 数据仓库分层

| 层级 | 用途 |
|------|------|
| ODS | 原始数据层 - 外部数据直接入库 |
| DIM | 维表层 - 不变/缓慢变化维度 |
| DWD | 明细事实层 - 原子事实 |
| DWS | 汇总事实层 - 轻度汇总 |
| ADS | 应用结果层 - 可直接消费 |

## 目录结构

```
shanxi_resilience_enhancement/
├── configs/              # 配置文件（YAML）
├── docs/                 # 项目文档（Org 格式）
├── outputs/              # 临时输出（不提交 Git）
├── research/             # 研究与试验代码（与工程分离）
├── scripts/              # 运维辅助脚本
├── sql/                  # SQL 文件
│   ├── ddl/            # 建表（按数据层拆分）
│   ├── dml/            # 数据加工（按模块拆分）
│   └── checks/         # 数据校验
├── src/                  # 正式工程代码
│   ├── app/            # 应用核心基础设施
│   ├── common/         # 跨模块通用工具
│   ├── modules/        # 核心业务模块（M0~M5）
│   ├── jobs/           # 命令行任务入口
│   ├── services/       # 查询服务
│   └── tests/          # 测试
├── .env                  # 环境变量（不提交 Git）
├── .env.example          # 环境变量模板
├── pyproject.toml        # Python 包配置
├── README.org           # 主文档（Org 格式）
└── README_USE_GUIDE.md  # 使用指南（Markdown）
```

## 模块内文件结构（每个模块统一）

```
m{N}_xxx/
├── __init__.py      # 模块初始化
├── task.py          # （未使用，任务入口统一在 jobs/）
├── service.py       # 业务编排层
├── repository.py    # 数据访问层
├── schema.py        # Pydantic 模型
└── checks.py        # 数据校验
```

## 开发顺序规则

每个模块必须按以下顺序推进：
1. 模块文档
2. 输入输出定义
3. 表结构设计
4. SQL 原型
5. Python 编排
6. 校验 SQL / 数据检查
7. 联调
8. 查询结果输出

## 核心工程原则

1. 先文档，后代码
2. 先表结构与口径，后实现逻辑
3. 先最小可用链路，后增强能力
4. 先保证主链可跑通，后优化性能和抽象层次
5. 所有实现必须可审查、可复现、可迭代

## 绝对禁止事项

1. 禁止绕过项目文档直接新增未定义表结构
2. 禁止在正式目录中加入一次性实验脚本
3. 禁止把复杂业务逻辑硬编码在命令行入口文件中
4. 禁止把数据库连接、账号密码、服务器路径写死在代码里
5. 禁止新增无文档说明的字段、接口、任务
6. 禁止跨模块直接依赖未公开的私有中间表
7. 禁止生成"看起来完整但无法执行"的伪代码冒充正式实现

## SQL 编写规则

1. 核心统计逻辑优先用原生 SQL
2. 大 SQL 必须拆成可读的 CTE
3. 每个 SQL 文件顶部必须注明：作用、输入表、输出表、粒度、关键字段
4. 所有落表 SQL 必须说明主键粒度
5. 所有汇总逻辑必须明确时间口径
6. 对 `section_number`、`scheme_id`、`section_id`、`od_id`、`path_id` 等关键字段命名保持统一

## 当前状态

- ✅ 项目骨架已完整创建（109+ 个文件）
- ✅ 虚拟环境已配置（uv + .venv）
- ✅ configs/ 目录配置文件已汉化
- ✅ README_USE_GUIDE.md 已创建
- ✅ .claude/rules/ 规则体系已建立（agents.md, coding-style.md, testing.md, patterns.md, security.md, git-workflow.md）
- ✅ .claude/memory/MEMORY.md 已创建
- ✅ 基础数据导入完成（收费单元路径、收费站信息、收费路段、路网拓扑，共 ~30,700 条记录）
- ✅ pgRouting 性能优化完成（拓扑构建、路径查询函数）
- ✅ 项目专用 Skills 已创建（6个，含 table-creator）
- ✅ 项目专用 Agents 已创建（3个，含 dim-manager）
- ✅ 施工方案相关维表已建立（dim_construction_segment）
- ✅ 规则类维表已建立（dim_detour_ratio_rule、dim_lane_capacity_rule）
- ✅ 数据表说明文档已创建（docs/数据表说明.md，12张表）
- ✅ M2 intervalgroup 修复模块已完成（滑动窗口算法、拓扑检查、pgRouting最短路径）
- ✅ M6 OD-Section-Path 映射模块已完成（两步去重、聚合落表、测试通过）
- ⏳ 需补充：ODS 层 DDL

## 已实现的路径查询函数

| 函数 | 功能 | 性能 | 算法 |
|------|------|------|------|
| `find_shortest_path_pgr` | 单条最短路径 | ~22ms | pgRouting Dijkstra |
| `find_top_n_paths_pgr` | Top N 路径 | ~81ms | 贪婪算法 |
| `find_shortest_path_excluding` | 排除节点查询 | - | pgRouting Dijkstra |
| `get_next_sections` | 获取下一个节点 | <10ms | SQL |
| `get_prev_sections` | 获取上一个节点 | <10ms | SQL |
| `find_all_paths` | 全路径搜索 | 慢 | 递归CTE |

## 数据库数据汇总

| 表名 | 数据量 | 说明 |
|------|--------|------|
| `dwd_section_path` | 7,606 条 | 收费单元路径（6个版本） |
| `dwd_toll_station` | 2,838 条 | 收费站（5个版本） |
| `dim_toll_road` | 110 条 | 收费路段 |
| `dwd_tom_noderelation` | 20,130 条 | 路网拓扑（5个版本） |
| `dwd_tom_network_vertices` | 10,922 条 | pgRouting 节点 |
| `dwd_tom_network_edges` | 20,130 条 | pgRouting 边 |
| `dim_construction_segment` | 7 条 | 施工区间信息（工程1·方案1） |
| `dim_detour_ratio_rule` | 5 条 | 绕行通行费增幅与绕行比例规则 |
| `dim_lane_capacity_rule` | 4 条 | 各设计时速下单车道通行能力规则 |

## 项目专用 Skills（快速调用）

### 数据导入类
- **`shanxi-resilience-data-importer`** - 数据导入工具
  - 位置: `.claude/skills/shanxi-resilience-data-importer/SKILL.md`
  - 功能: 分析Excel/CSV、生成DDL、生成导入脚本、多版本导入、数据验证
  - 适用: 收费单元路径、收费站信息、收费路段等基础数据导入

### SQL 生成类
- **`shanxi-resilience-sql-generator`** - SQL生成工具
  - 位置: `.claude/skills/shanxi-resilience-sql-generator/SKILL.md`
  - 功能: 生成DDL（DIM/DWD/DWS/ADS）、生成DML（M0-M5）、生成检查SQL、标准模板
  - 适用: 各层建表、业务SQL、数据质量检查

### 文档更新类
- **`shanxi-resilience-doc-updater`** - 文档更新工具
  - 位置: `.claude/skills/shanxi-resilience-doc-updater/SKILL.md`
  - 功能: 更新会话记录、维护业务逻辑记录、登记表口径、更新项目记忆
  - 适用: 文档维护、工作记录、业务逻辑存档

### pgRouting 优化类 ⭐
- **`shanxi-resilience-pgrouting`** - pgRouting 路网优化
  - 位置: `.claude/skills/shanxi-resilience-pgrouting/SKILL.md`
  - 功能: 拓扑构建、最短路径（~22ms）、Top N 路径（~81ms）、排除节点查询
  - 适用: 路网拓扑性能优化、收费单元路径查询

### 路径查询类 ⭐
- **`shanxi-resilience-path-query`** - 路径查询工具
  - 位置: `.claude/skills/shanxi-resilience-path-query/SKILL.md`
  - 功能: 相邻节点查询、最短路径、Top N 路径、全路径搜索
  - 适用: OD 对路径计算、替代路径分析

## 项目专用 Agents

### 数据工程师
- **`shanxi-resilience-data-engineer`** - 数据工程专家
  - 位置: `.claude/agents/shanxi-resilience-data-engineer.md`
  - 功能: 数据导入、表结构设计、SQL 编写、ETL 开发
  - 适用: 数据工程相关任务

### 路径分析专家
- **`shanxi-resilience-path-analyzer`** - 路网路径分析专家
  - 位置: `.claude/agents/shanxi-resilience-path-analyzer.md`
  - 功能: 相邻节点查询、最短路径计算、Top N 路径、排除节点查询
  - 适用: 路网路径分析相关任务

## 可用的 Skills 和 Agents

### 核心 Skills（数据工程专用）
- `senior-data-engineer` - 世界级数据工程专家，构建可扩展的数据管道
- `database-etl-aggregation-debugger` - ETL 数据调试，解决聚合不一致问题
- `csv-data-summarizer` - CSV 数据分析与汇总统计
- `tdd-workflow` - 测试驱动开发工作流

### 开发辅助 Skills
- `code-reviewer` - 全面的代码审查
- `security-review` - 安全审查
- `plan` - 实施计划创建
- `refactor-clean` - 代码清理与重构
- `test-coverage` - 测试覆盖率检查
- `update-docs` - 文档更新
- `update-codemaps` - 代码映射更新

### 核心 Agents
- `planner` - 实施计划专家
- `tdd-guide` - 测试驱动开发指导
- `code-reviewer` - 代码审查专家
- `security-reviewer` - 安全审查专家
- `build-error-resolver` - 构建错误解决
- `doc-updater` - 文档更新专家
- `refactor-cleaner` - 代码清理专家

## 下一步建议

1. 补充 ODS 层 DDL（`sql/ddl/ods/`）
2. 按模块顺序（M0→M1→M2→M3→M4→M5）填充 DML 业务 SQL
3. 完善集成测试
4. 数据库初始化与联调

## 已建立的核心开发模式

### 新建维表标准流程（三件套）
用户给定字段字典 + 示例数据后，固定输出三个文件：

| 文件 | 路径 | 说明 |
|------|------|------|
| DDL | `sql/ddl/dim/create_dim_{name}.sql` | 建表语句，含约束、索引、COMMENT |
| DML | `sql/dml/m{N}/insert_dim_{name}.sql` | 初始数据插入，含 ON CONFLICT |
| 脚本 | `scripts/import_{name}.py` | 建表+插入+验证一体化 Python 脚本 |

### Python 导入脚本标准结构
参考 `scripts/import_toll_road.py`，固定包含四个方法：
- `_read_env()` - 从 `.env` 读取数据库配置
- `test_connection()` - 测试连接
- `create_table()` - DROP + CREATE（读取 DDL 文件）
- `import_data()` - executemany 批量插入
- `verify_data()` - 统计 + 质量检查（dict_row）

### 自增主键 vs 业务复合主键
- 复合唯一键 → 用 `SERIAL` 做主键 + `UNIQUE` 约束做唯一性约束
- 纯规则表（无自然主键）→ 用业务 `id VARCHAR(20)` 做主键

### 生成列用法
- PostgreSQL `DATE + INTEGER = DATE`，可用 `GENERATED ALWAYS AS (...) STORED`
- 示例：`construction_end_time = construction_start_time + construction_duration_days`

## 关键文档位置

| 文档 | 路径 | 说明 |
|------|------|------|
| **数据表说明** | `docs/数据表说明.md` | 所有表的连接信息、数据字典、查询示例，**新建表后必须同步更新** |
| 业务逻辑记录 | `docs/业务逻辑记录.md` | BL-00x 业务逻辑条目 |
| 会话记录 | `docs/会话记录与搭建过程.md` | 完整搭建历史 |
| 项目记忆 | `.claude/memory/MEMORY.md` | 本文件 |

## 数据库连接信息（快速参考）

| 项目 | 值 |
|------|----|
| Host | `192.168.0.75` |
| Port | `5432` |
| DB | `shanxi_resilience_db` |
| User | `sunhaoyu` |

## Hive 数据源（外部数据）

| 项目 | 值 |
|------|----|
| Host | `172.16.5.1` |
| Port | `10000` |
| DB | `dbbase2026` |
| 主要表 | `gstx_exit_with_min_fee202603`（约4880万条，63字段） |

## M6 OD-Section-Path 映射模块 ✅ 已完成

### 功能说明
基于 Hive 表 `gstx_exit_with_min_fee202603` 中已拓扑修复的 intervalgroup，构建 OD-Section-Path 映射表。核心需求：
- 提取每条记录的 `(enid, exid, fixed_ig)` 组合
- 将 intervalgroup 中的收费单元映射为 `section_number` 并去重生成 `numPath`
- 按 `fixed_ig` 分组累加统计量，统计每个 `numPath` 下各 `fixed_ig` 的出现频率
- 同时记录第一步相邻去重后的结果（`step1_numpath`），用于对比 pair 去重效果（仅测试 JSON，不落库）

### 核心文件

| 文件 | 说明 |
|------|------|
| `src/modules/m6_od_section_path/service.py` | 业务编排层（_map_and_dedupe 核心算法，~510行） |
| `src/modules/m6_od_section_path/repository.py` | 数据访问层（PG upsert，幂等写入） |
| `src/modules/m6_od_section_path/schema.py` | Pydantic 模型 |
| `src/jobs/run_m6.py` | 命令行入口 |
| `sql/ddl/dwd/create_dwd_od_section_path_map.sql` | map 表 DDL |
| `sql/ddl/dwd/create_dwd_od_section_path_numpath_freq.sql` | freq 表 DDL |

### 核心算法：两步去重

**Step 1 - 相邻去重**：相邻相同的 section_number 合并。
```
[4, 4, 4, 2, 2, 6, 8, 8, ...] → [4, 2, 6, 8, ...]
```

**Step 2 - 相邻 pair 去重**：从 offset=0 和 offset=1 分别组合 tuple，比较结果选择更短的。
- 遍历 pair：append(a) → append(b)
- 如果当前 pair (a,b) 与下一个 pair (c,d) 完全相同，跳过整个 (c,d)
- 拼接头尾落单元素

示例（deduped = [4,2,6,8,194,8,194,196,...]）：
- offset=0 pairs: (4,2),(6,8),(194,8),(194,196),... → 结果 27 个
- offset=1 pairs: (2,6),(8,194),(8,194),(196,198),... → 结果 25 个（选择此结果）

### 数据库表结构

**dwd_od_section_path_map**（主键: enid, exid, numpath, version_yyyyMM）：
- 只保留 `fixed_intervalpath`，无原始 intervalgroup
- 字段：enid, exid, numpath, fixed_intervalpath, intervalpath_cnt, total_trip_cnt, path_freq_ratio

**dwd_od_section_path_numpath_freq**（主键: enid, exid, numpath, fixed_intervalgroup, version_yyyyMM）：
- 只保留 `fixed_intervalgroup`，无原始 intervalgroup
- 字段：enid, exid, numpath, fixed_intervalgroup, ig_count, ig_rank

### 关键实现细节

1. **按 fixed_ig 聚合选**：map 表的 `fixed_intervalpath` = 该 numpath 下 ig_count 累加最多的 fixed_ig
2. **step1_numpath 仅存于内存**：用于测试 JSON 对比，不写入数据库
3. **offset=1 奇数长度尾部处理**：`i >= len(deduped) and len(deduped) % 2 == 1`
4. **pair dedup 只跳过相同 (a,b)==(c,d)**：反向相同 (d,c) 不跳过，避免过度去重
5. **数据库幂等写入**：使用 ON CONFLICT DO UPDATE，支持多批次累加

### 运行方式

```bash
# 测试模式（100条，结果存本地 JSON）
uv run python -m src.jobs.run_m6 --version 202603 --batch-size 100 --save-local

# 全量模式（50万条/批，直接落库）
uv run python -m src.jobs.run_m6 --version 202603 --batch-size 500000
```

### 测试结果（100条记录）
- map 记录: 15 / freq 记录: 20
- 路径一致性均值: 0.9379
- 高一致性(>=0.9): 13 条 / 低一致性(<0.7): 2 条

### 数据溯源 - SourceFlag

| 值 | 含义 |
|-----|------|
| `hive_computed` | Hive 数据计算生成（默认） |

## 规则类维表汇总（DIM）

### 功能说明
修复 Hive 表 `gstx_exit_with_min_fee202603` 中的 `intervalgroup` 字段，该字段记录车辆通行经过的收费单元ID序列（用"|"分隔），存在两类问题：
1. **遗漏**: 相邻单元在拓扑上不相邻，中间有缺失
2. **错误**: 中间单元方向识别错误（应为反向单元）

### 核心文件

| 文件 | 说明 |
|------|------|
| `src/modules/m2_od_flow/interval_fixer.py` | 核心修复逻辑（~500行） |
| `src/modules/m2_od_flow/hive_repository.py` | Hive 数据访问 |
| `src/app/hive.py` | Hive 连接模块 |
| `outputs/interval_fix/fix_results_v4.json` | 测试结果样例 |

### 核心接口

```python
from src.modules.m2_od_flow.interval_fixer import (
    fix_intervalgroup,       # 单条修复
    fix_intervalgroup_batch, # 批量修复
    TopologyChecker,          # 拓扑查询器
    split_intervalgroup,      # 拆分intervalgroup
    join_intervalgroup,       # 合并intervalgroup
    reverse_section_id,       # 计算反向单元ID
)
from src.modules.m2_od_flow.hive_repository import read_sample_from_hive

# 使用示例
topo = TopologyChecker(version='202512')
topo.load_topology_cache()  # 预加载拓扑（2765条）

result = fix_intervalgroup('X1|X2|X3', topo)
print(result.fixed)  # 修复后的序列

# 批量处理
records = read_sample_from_hive(limit=100)
results = fix_intervalgroup_batch(records, topology=topo)
```

### 算法逻辑

滑动窗口处理四种情况：

| 情况 | X1→X2 | X2→X3 | 处理逻辑 |
|------|-------|-------|----------|
| 1 | ✅ | ✅ | 窗口滑动 |
| 2 | ❌ | ✅ | 补充最短路径 |
| 3 | ❌ | ❌ | 尝试反向，取最短路径 |
| 4 | ✅ | ❌ | 窗口滑动 |

**关键函数**:
- `topo_next(section_id)` → 拓扑后继集合
- `topo_check(from, to)` → 检查是否相邻
- `shortest_path(start, end)` → pgRouting 最短路径

### 数据溯源 - SourceFlag

| 值 | 含义 |
|-----|------|
| `actual` | 真实采集数据 |
| `path_fill` | 路径补全数据 |
| `reverse_fix` | 反向修复数据 |

### 注意事项
- 使用 `uv run python ...` 执行（uv 管理的虚拟环境）
- 批量处理需先调用 `topo.load_topology_cache()` 预加载拓扑
- 反向单元：末2位 10↔20 互换（如 `...310` ↔ `...320`）

## 规则类维表汇总（DIM）

| 表名 | 用途 | 关联模块 |
|------|------|---------|
| `dim_construction_segment` | 施工区间信息（工程/方案/区间/方向） | M0 |
| `dim_detour_ratio_rule` | 通行费增幅区间 → 绕行比例 | M5 |
| `dim_lane_capacity_rule` | 设计时速 → 单车道通行能力(pcu/h) | M1 |
