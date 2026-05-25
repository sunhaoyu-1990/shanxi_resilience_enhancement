---
name: shanxi-resilience-data-importer
description: 陕交控项目专用数据导入工具 - 处理收费单元路径、收费站信息、收费路段等基础数据的Excel/CSV多版本导入，严格遵循数据字典，自动生成建表语句和导入脚本
---

# 陕交控项目数据导入工具

专门用于陕交控多路段改扩建韧性提升项目的数据导入工作。

## 前置必读

执行本 Skill 前，**必须**先阅读 `docs/数据表说明.md`，该文件是本项目所有数据库表的权威说明，包含：
- 表清单总览（分层、记录数、简介）
- 各表数据字典（字段名、类型、可空、描述）
- 唯一约束与主键定义
- 版本管理规则（version_yyyymm）
- source_flag 枚举值

建表和导入数据时，**禁止**凭记忆假设字段名或类型，必须以 `docs/数据表说明.md` 中的数据字典为准。导入完成后同步更新该文件的记录数。

## 核心功能

### 1. 数据分析
自动分析 Excel/CSV 数据文件，识别：
- 数据结构和字段列表
- 数据类型和值范围
- 多版本数据的差异
- 数据字典匹配

### 2. 建表语句生成
按照项目规范生成 SQL DDL：
- DIM 层维表
- DWD 层明细表
- 版本配置表
- 索引和约束
- 字段注释（中文）

### 3. 导入脚本生成
生成 Python 导入脚本：
- 使用项目统一的数据库连接
- 支持多版本数据批量导入
- 数据类型正确转换
- 数据完整性验证
- 使用 uv run 执行

### 4. 支持的数据类型

| 数据类型 | 说明 |
|---------|------|
| 收费单元路径 | 多版本 Excel，带数据字典 |
| 收费站信息 | 多版本 CSV，带数据字典 |
| 收费路段 | 单版本 Excel |
| 其他基础数据 | 通用导入框架 |

## 使用示例

### 分析数据文件
```bash
# 自动分析并生成导入方案
skill: shanxi-resilience-data-importer
args: "analyze --path research/data/基础数据/xxx"
```

### 生成建表语句
```bash
# 生成 DDL SQL
skill: shanxi-resilience-data-importer
args: "ddl --data-type toll_station --output sql/ddl/"
```

### 完整导入流程
```bash
# 一键分析、建表、导入、验证
skill: shanxi-resilience-data-importer
args: "full --path research/data/基础数据/收费站信息表"
```

## 项目规范遵循

### 文件位置
- DDL: `sql/ddl/{dim,dwd}/`
- 导入脚本: `scripts/import_*.py`
- 分析脚本: `scripts/analyze_*.py`

### 命名规范
- 表名: `{dim,dwd}_{snake_case_name}`
- 主键: `pk_{table_name}`
- 索引: `idx_{table_name}_{column_name}`
- 脚本: `import_{snake_case_name}.py`

### SQL 规范
- 字段注释使用中文
- 必须标注 source_flag
- 必须有 created_at, updated_at
- 主键粒度明确说明

## 数据验证检查清单

- [ ] 主键唯一性
- [ ] 必填字段非空
- [ ] 枚举值范围正确
- [ ] 数值范围合理
- [ ] 日期格式正确
- [ ] 数据量与预期一致
- [ ] 版本配置正确

## 常见数据模式

### 模式1: 多版本CSV
```
tollstation202312.csv
tollstation202409.csv
tollstation202411.csv
数据字典.xlsx
```

### 模式2: 多版本Excel
```
202401单元唯一路径.xlsx
202409单元唯一路径.xlsx
数据字典.xlsx
```

### 模式3: 单版本数据
```
收费路段.xls
```