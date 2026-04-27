# 项目专用 Skills & Agents 快速索引

> 更新日期：2026-04-27

---

## 📋 Skill 清单

### 1. shanxi-resilience-table-creator ⭐ 推荐
**文件**: `.claude/skills/shanxi-resilience-table-creator/SKILL.md`

**功能**:
- 接收字段字典 + 示例数据
- 自动生成 DDL + DML + Python导入脚本（三件套）
- 执行脚本并验证
- 同步更新 docs/数据表说明.md

**适用场景**:
- 新建任何维表（DIM 层规则表、参数表、配置表）
- 用户提供字段字典和示例数据时

---

### 2. shanxi-resilience-data-importer
**文件**: `.claude/skills/shanxi-resilience-data-importer/SKILL.md`

**功能**:
- 分析 Excel/CSV 外部数据
- 生成 DDL 建表语句
- 生成多版本数据导入 Python 脚本
- 数据完整性验证

**适用场景**:
- 外部数据文件（收费单元路径、收费站等）批量导入
- 多版本数据管理

---

### 3. shanxi-resilience-sql-generator
**文件**: `.claude/skills/shanxi-resilience-sql-generator/SKILL.md`

**功能**:
- DDL 生成（DIM/DWD/DWS/ADS 各层）
- DML 生成（M0-M5 模块）
- 检查 SQL 生成（数据质量验证）
- 标准 SQL 模板（CTE、版本化、时间口径）

**适用场景**:
- 业务 SQL 编写
- 数据质量检查 SQL
- 版本化数据查询

---

### 4. shanxi-resilience-doc-updater
**文件**: `.claude/skills/shanxi-resilience-doc-updater/SKILL.md`

**功能**:
- 更新 `docs/数据表说明.md`（新建表后同步）
- 更新会话记录 `docs/会话记录与搭建过程.md`
- 维护业务逻辑记录 `docs/业务逻辑记录.md`
- 更新项目记忆 `.claude/memory/MEMORY.md`

**适用场景**:
- 建表或修改表结构后
- 业务逻辑实现后
- 阶段工作完成后

---

### 5. shanxi-resilience-pgrouting ⭐
**文件**: `.claude/skills/shanxi-resilience-pgrouting/SKILL.md`

**功能**:
- pgRouting 拓扑构建
- 最短路径查询（~22ms）
- Top N 路径查询（~81ms）
- 排除节点查询

**适用场景**:
- 路网拓扑性能优化
- 施工封闭路径重算

---

### 6. shanxi-resilience-path-query ⭐
**文件**: `.claude/skills/shanxi-resilience-path-query/SKILL.md`

**功能**:
- 相邻节点查询
- 最短路径查询
- Top N 路径查询
- 全路径搜索

**适用场景**:
- OD 对路径计算
- 替代路径分析
- 分流方案生成

---

### 7. shanxi-resilience-unit-test-writer ⭐
**文件**: `.claude/skills/shanxi-resilience-unit-test-writer/SKILL.md`

**功能**:
- 按模块分目录组织测试代码
- 自动生成 pytest 单元测试（正常/边界/异常/去重/累积）
- Mock 辅助方法模板（Repository/Service/Schema 层）
- 运行验证并修复失败

**适用场景**:
- 编写模块单元测试
- 补充测试覆盖
- 新模块开发完成后生成测试

---

### 8. shanxi-resilience-git
**文件**: `.claude/skills/shanxi-resilience-git/SKILL.md`

**功能**:
- 项目 Git 操作规范化管理
- Commit message 模板（约定式提交）
- 分支管理与大文件排除
- GitHub 协作流程
- 常用操作命令速查

**适用场景**:
- 提交代码前检查
- Git 操作规范化
- 新人上手参考

---

## 🚀 Skill 快速调用

```
# 新建维表（最常用）
skill: shanxi-resilience-table-creator

# 外部文件数据导入
skill: shanxi-resilience-data-importer

# SQL 编写
skill: shanxi-resilience-sql-generator

# 文档更新
skill: shanxi-resilience-doc-updater

# pgRouting 优化
skill: shanxi-resilience-pgrouting

# 路径查询
skill: shanxi-resilience-path-query

# 单元测试生成
skill: shanxi-resilience-unit-test-writer

# Git 操作
skill: shanxi-resilience-git
```

---

## 🤖 Agent 清单

### shanxi-resilience-dim-manager ⭐ 新增
**文件**: `.claude/agents/shanxi-resilience-dim-manager.md`

**功能**:
- 维表（DIM）的新建、查询、更新、文档同步
- 管理规则表（detour_ratio_rule、lane_capacity_rule 等）
- 提供标准查询 SQL
- 维护 docs/数据表说明.md

**调用场景**: 新增/修改规则表、查询维表数据

---

### shanxi-resilience-data-engineer
**文件**: `.claude/agents/shanxi-resilience-data-engineer.md`

**功能**:
- 数据导入任务
- ETL 开发
- SQL 编写与优化
- 数据质量检查

**调用场景**: 外部数据导入、ETL 任务开发

---

### shanxi-resilience-path-analyzer
**文件**: `.claude/agents/shanxi-resilience-path-analyzer.md`

**功能**:
- 路网路径分析
- pgRouting 调用
- 替代路径生成

**调用场景**: 路径计算、分流方案分析

---

## 📊 当前数据库维表汇总

| 表名 | 记录数 | 模块 | 说明 |
|------|--------|------|------|
| `dim_construction_segment` | 7 | M0 | 施工区间 |
| `dim_detour_ratio_rule` | 5 | M5 | 通行费增幅→绕行比例 |
| `dim_lane_capacity_rule` | 4 | M1 | 设计时速→单车道能力 |
| `dim_toll_road` | 110 | M0 | 收费路段 |
| `dim_section_path_version` | 6 | M0 | 路径版本配置 |
| `dim_toll_station_version` | 5 | M0 | 收费站版本配置 |
| `dim_tom_noderelation_version` | 5 | M0 | 路网版本配置 |
| `dwd_section_path` | 7,606 | M0 | 收费单元路径 |
| `dwd_toll_station` | 2,838 | M0 | 收费站明细 |
| `dwd_tom_noderelation` | 20,130 | M0 | 路网拓扑 |
| `dwd_tom_network_edges` | 20,130 | M0 | pgRouting 边 |
| `dwd_tom_network_vertices` | 10,922 | M0 | pgRouting 节点 |

---

## 📁 关键文档位置

| 文档 | 路径 | 说明 |
|------|------|------|
| **数据表说明** | `docs/数据表说明.md` | ⭐ 所有表的权威说明，新建表后必须更新 |
| 项目记忆 | `.claude/memory/MEMORY.md` | 项目状态、开发模式 |
| 会话记录 | `docs/会话记录与搭建过程.md` | 完整工作记录 |
| 业务逻辑 | `docs/业务逻辑记录.md` | BL-00x 条目 |
| 项目规则 | `.claude/rules/` | 编码规范 |
