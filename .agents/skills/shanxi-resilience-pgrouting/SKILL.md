---
name: shanxi-resilience-pgrouting
description: 陕交控项目专用 pgRouting 路网优化工具 - 基于 PostgreSQL + PostGIS + pgRouting 构建高速路网拓扑，支持最短路径、Top N 路径、排除节点查询等高性能路径分析功能
---

# 陕交控项目 - pgRouting 路网拓扑优化 Skill

## 前置必读

执行本 Skill 前，**必须**先阅读 `docs/数据表说明.md`，重点关注以下表的字段定义和查询示例：
- `dwd_tom_noderelation` — 路网拓扑结构明细表（源数据）
- `dwd_tom_network_edges` — pgRouting 边表
- `dwd_tom_network_vertices` — pgRouting 节点映射表
- `dim_tom_noderelation_version` — 路网版本配置表

**禁止**凭记忆假设字段名（如 `enRoadNodeId` vs `enroadnodeid`），必须以 `docs/数据表说明.md` 中的数据字典为准。

## 概述

本 Skill 用于高速路网拓扑结构的 pgRouting 性能优化，支持收费单元的上一个/下一个单元查询，以及两收费单元间的路径查询。

## 核心能力

### 1. pgRouting 拓扑构建
- 从 `dwd_tom_noderelation` 转换为 pgRouting 格式
- 构建节点映射表 `dwd_tom_network_vertices`
- 构建边表 `dwd_tom_network_edges`
- 支持多版本数据（202312-202512）

### 2. 路径查询函数

| 函数名 | 功能 | 性能 | 算法 |
|--------|------|------|------|
| `find_shortest_path_pgr` | 单条最短路径 | ~22ms | Dijkstra |
| `find_top_n_paths_pgr` | Top N 路径 | ~81ms | 贪婪算法 |
| `find_shortest_path_excluding` | 排除节点查询 | - | Dijkstra |
| `get_next_sections` | 获取下一个节点 | - | SQL |
| `get_prev_sections` | 获取上一个节点 | - | SQL |

### 3. 贪婪算法实现

**原理**: 每次找最短路径，然后禁用该路径经过的节点，重复 N 次

**SQL 排除条件**:
```sql
NOT (source = ANY(v_exclude_nodes) OR target = ANY(v_exclude_nodes))
```
- 边的任意一端被禁用就排除该边
- 注意：不是 `ALL`，是 `ANY`

## 数据库表结构

### 节点映射表
```sql
dwd_tom_network_vertices (
  id BIGSERIAL PRIMARY KEY,          -- pgRouting 节点ID
  original_node_id VARCHAR(32),      -- 原始节点ID
  version_yyyyMM VARCHAR(6),          -- 版本年月
  node_type INT,                      -- 节点类型
  node_name VARCHAR(100)              -- 节点名称
)
```

### 边表
```sql
dwd_tom_network_edges (
  id BIGSERIAL PRIMARY KEY,          -- pgRouting 边ID
  source BIGINT,                      -- 起点节点
  target BIGINT,                      -- 终点节点
  cost FLOAT,                         -- 正向代价（里程）
  reverse_cost FLOAT,                  -- 反向代价（1e9单向路网）
  version_yyyyMM VARCHAR(6),          -- 版本年月
  original_enRoadNodeId VARCHAR(32), -- 原始入口节点
  original_exRoadNodeId VARCHAR(32), -- 原始出口节点
  miles INT                           -- 里程（米）
)
```

## 使用示例

### 1. 构建拓扑
```bash
uv run python scripts/build_tom_network_pgr.py
```

### 2. 最短路径查询
```sql
SELECT * FROM find_shortest_path_pgr(
    'G007061003000210',    -- 起点
    'G004061002000910',    -- 终点
    '202512'               -- 版本
);
```

### 3. Top N 路径查询
```sql
SELECT * FROM find_top_n_paths_pgr(
    'G007061003000210',
    'G004061002000910',
    '202512',
    5
);
```

### 4. 排除节点查询
```sql
SELECT * FROM find_shortest_path_excluding(
    'G007061003000210',
    'G004061002000910',
    '202512',
    ARRAY['G007061003000420']  -- 排除的节点
);
```

### 5. 相邻节点查询
```sql
-- 获取下一个节点
SELECT * FROM get_next_sections('G007061003000210', '202512');

-- 获取上一个节点
SELECT * FROM get_prev_sections('G007061003000210', '202512');
```

## 关键文件

| 文件路径 | 说明 |
|---------|------|
| `sql/ddl/dwd/create_dwd_tom_network_pgr.sql` | pgRouting 表结构 |
| `sql/pgrouting/build_tom_network_topology.sql` | 拓扑构建函数 |
| `sql/pgrouting/query_functions_pgr.sql` | 最短路径函数 |
| `sql/pgrouting/query_top_n_paths_pgr.sql` | Top N 路径函数 |
| `sql/pgrouting/query_functions_excluding.sql` | 排除节点函数 |
| `sql/pgrouting/helper_functions.sql` | 辅助函数 |
| `scripts/build_tom_network_pgr.py` | 拓扑构建脚本 |

## 性能对比

| 查询类型 | 递归CTE | pgRouting | 提升 |
|---------|---------|-----------|------|
| 30节点最短路径 | ~30s | ~22ms | **1300x** |
| Top 5 路径 | >5min | ~81ms | **3700x** |

## 常见问题

### Q: 为什么只返回1条路径？
A: 检查排除条件是否使用了 `ALL`，应该使用 `ANY`：
```sql
-- 错误：两边端点同时被禁用
WHERE source = ALL(v_exclude_nodes) AND target = ALL(v_exclude_nodes)

-- 正确：任意一端被禁用
WHERE NOT (source = ANY(v_exclude_nodes) OR target = ANY(v_exclude_nodes))
```

### Q: pgRouting 支持 KSP 吗？
A: pgRouting 3.3.1 不支持 KSP，使用贪婪算法作为替代方案。

### Q: 路径里程异常高？
A: 路网中存在环路，贪婪算法可能找到绕路很长的替代路径，这是正常现象。

## 调用方式

```
skill: shanxi-resilience-pgrouting
```

## 项目上下文

- **项目**: 陕交控多路段改扩建韧性提升项目（一期）
- **技术栈**: PostgreSQL 15 + PostGIS 3.5.3 + pgRouting 3.3.1
- **数据规模**: 5个版本，约20,130条拓扑关系
- **测试节点**: 起点 `G007061003000210`，终点 `G004061002000910`
