---
name: shanxi-resilience-path-query
description: 陕交控项目专用路网路径查询工具 - 提供相邻节点查询、最短路径、Top N 替代路径、排除节点查询等功能，支持递归 CTE 和 pgRouting 两种实现方式
---

# 陕交控项目 - 路网路径查询 Skill

## 前置必读

执行本 Skill 前，**必须**先阅读 `docs/数据表说明.md`，重点关注以下表的字段定义和查询示例：
- `dwd_tom_noderelation` — 路网拓扑结构明细表
- `dwd_tom_network_edges` — pgRouting 边表
- `dwd_tom_network_vertices` — pgRouting 节点映射表
- `dwd_section_path` — 收费单元路径明细表（section_number 核心字段）

编写路径查询 SQL 时，**禁止**凭记忆假设字段名或节点类型枚举值，必须以 `docs/数据表说明.md` 中的数据字典为准。

## 概述

本 Skill 用于高速路网的路径查询，包括相邻节点查询、两节点间路径查询等功能。

## 查询类型

### 1. 相邻节点查询

查询某个收费单元的直接前驱或后继节点。

```sql
-- 获取下一个节点
SELECT * FROM get_next_sections('G007061003000210', '202512');

-- 获取上一个节点
SELECT * FROM get_prev_sections('G007061003000210', '202512');

-- 或者使用递归CTE版本
SELECT * FROM get_next_nodes('G007061003000210', '202512');
SELECT * FROM get_prev_nodes('G007061003000210', '202512');
```

### 2. 最短路径查询

使用 pgRouting 快速查找最短路径。

```sql
-- pgRouting 版本（推荐，~22ms）
SELECT * FROM find_shortest_path_pgr(
    'G007061003000210',    -- 起点
    'G004061002000910',    -- 终点
    '202512'               -- 版本
);

-- 递归CTE版本（~30s）
SELECT * FROM find_path_simple(
    'G007061003000210',
    'G004061002000910',
    '202512'
);
```

### 3. Top N 路径查询

查找多条替代路径。

```sql
-- pgRouting 贪婪算法（推荐，~81ms）
SELECT * FROM find_top_n_paths_pgr(
    'G007061003000210',
    'G004061002000910',
    '202512',
    5
);

-- 递归CTE版本
SELECT * FROM find_top_n_paths(
    'G007061003000210',
    'G004061002000910',
    '202512',
    5,      -- 返回条数
    30      -- 最大深度
);
```

### 4. 排除节点查询

查询时排除某些节点（用于施工封闭等情况）。

```sql
SELECT * FROM find_shortest_path_excluding(
    'G007061003000210',
    'G004061002000910',
    '202512',
    ARRAY['G007061003000420']  -- 排除的节点
);
```

### 5. 全路径查询

查找两节点间的所有可能路径。

```sql
-- 递归CTE
SELECT * FROM find_all_paths(
    'G007061003000210',
    'G004061002000910',
    '202512',
    20  -- 最大深度
);

-- 带剪枝优化
SELECT * FROM find_shortest_path(
    'G007061003000210',
    'G004061002000910',
    '202512',
    15,  -- 最大深度
    5    -- 最大路径数
);

-- 双向搜索优化
SELECT * FROM find_all_paths_bidirectional(
    'G007061003000210',
    'G004061002000910',
    '202512',
    20,
    10
);
```

## 返回格式

### 路径查询返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| path_id | INT | 路径ID（多条时） |
| node_path | VARCHAR[] | 节点ID数组 |
| total_miles | BIGINT | 总里程（米） |
| node_count | BIGINT | 节点数 |

### 相邻节点返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| node_id | VARCHAR | 节点ID |
| node_type | INT | 节点类型（1-普通,2-省界,3-收费站） |
| node_name | VARCHAR | 节点名称 |
| miles | INT | 里程（米） |

## 节点类型说明

| 类型值 | 说明 |
|--------|------|
| 1 | 普通收费单元 |
| 2 | 省界收费单元 |
| 3 | 收费站 |

## 版本说明

支持查询的版本：202312, 202409, 202411, 202507, 202512

```sql
-- 查询可用版本
SELECT * FROM dim_tom_noderelation_version;
```

## 测试用例

起点: `G007061003000210`
终点: `G004061002000910`
版本: `202512`

```sql
-- 快速验证路径查询
SELECT * FROM find_shortest_path_pgr(
    'G007061003000210',
    'G004061002000910',
    '202512'
);
```

## 性能建议

| 场景 | 推荐函数 | 性能 |
|------|---------|------|
| 只需要最短路径 | `find_shortest_path_pgr` | ⚡⚡⚡ ~22ms |
| 需要多条替代路径 | `find_top_n_paths_pgr` | ⚡⚡ ~81ms |
| 排除节点查询 | `find_shortest_path_excluding` | ⚡⚡ |
| 获取相邻节点 | `get_next_sections` | ⚡⚡⚡ |
| 全路径搜索 | `find_all_paths` | ⚡ (慢) |

## 关键文件

| 文件路径 | 说明 |
|---------|------|
| `sql/pgrouting/helper_functions.sql` | 相邻节点查询 |
| `sql/pgrouting/query_functions_pgr.sql` | pgRouting 路径查询 |
| `sql/pgrouting/query_top_n_paths_pgr.sql` | Top N 路径 |
| `sql/pgrouting/query_functions_excluding.sql` | 排除节点查询 |
| `sql/views/create_v_tom_network.sql` | 递归CTE 路径查询 |
| `docs/高速路网拓扑结构表使用指南.md` | 完整使用文档 |

## 调用方式

```
skill: shanxi-resilience-path-query
```

## 注意事项

1. **版本选择**: 查询时建议指定 `version_yyyyMM`，避免跨版本数据混淆
2. **递归深度**: 递归CTE 查询的 `p_max_depth` 建议 10-20
3. **性能**: 长路径（30+节点）优先使用 pgRouting 函数
4. **环路**: 路网中存在环路，部分替代路径里程可能异常高
