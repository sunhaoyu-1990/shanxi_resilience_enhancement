---
name: shanxi-resilience-sql-generator
description: 陕交控项目专用SQL生成工具 - 按照项目规范生成DDL/DML/SQL检查语句，支持数据仓库分层（DIM/DWD/DWS/ADS），自动添加中文注释和版本字段
---

# 陕交控项目SQL生成工具

专门用于陕交控多路段改扩建韧性提升项目的SQL生成工作。

## 前置必读

执行本 Skill 前，**必须**先阅读 `docs/数据表说明.md`，该文件是本项目所有数据库表的权威说明，包含：
- 表清单总览（分层、记录数、简介）
- 各表数据字典（字段名、类型、可空、描述）
- 唯一约束与主键定义
- 查询示例与索引设计
- 版本管理规则（version_yyyymm）
- source_flag 枚举值

编写 DML/检查 SQL 时，**禁止**凭记忆假设表结构或字段名，必须以 `docs/数据表说明.md` 中的数据字典为准。新建表时同步更新该文件。

## 核心功能

### 1. DDL 生成
自动生成建表语句：
- DIM 层维表
- DWD 层明细表
- DWS 层汇总表
- ADS 层应用结果表
- 版本配置表

### 2. DML 生成
生成数据加工SQL：
- 按模块（M0-M5）组织
- CTE 分步计算
- 参数化查询
- 数据质量检查

### 3. 检查SQL生成
生成数据验证SQL：
- 主键唯一性检查
- 必填字段非空检查
- 枚举值范围检查
- 业务逻辑验证

### 4. SQL 模板
提供标准SQL模板：
- 版本化数据查询
- 时间口径统计
- 空间查询（PostGIS）
- 溯源标记（source_flag）

## SQL 头部注释模板

```sql
-- ============================================================
-- M{N}: {SQL 文件功能描述}
-- ============================================================
-- 作用: {这个 SQL 做什么}
-- 输入表: {依赖的表名列表}
-- 输出表: {写入的表名}
-- 粒度: {一行代表什么，例如 section_id × day}
-- 关键字段: {关键字段列表，例如 section_id, day, ...}
-- ============================================================
```

## 数据仓库分层规范

### DIM 层（维表层）
```sql
CREATE TABLE IF NOT EXISTS dim_{name} (
    {id} varchar(20) NOT NULL,
    {attributes} ...,
    source_flag varchar(16) DEFAULT 'actual',
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dim_{name} PRIMARY KEY ({id})
);
```

### DWD 层（明细事实层）
```sql
CREATE TABLE IF NOT EXISTS dwd_{name} (
    {id} varchar(20) NOT NULL,
    version_yyyyMM varchar(6) NOT NULL,
    {attributes} ...,
    source_flag varchar(16) DEFAULT 'actual',
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dwd_{name} PRIMARY KEY ({id}, version_yyyyMM)
);
```

### DWS 层（汇总事实层）
```sql
CREATE TABLE IF NOT EXISTS dws_{name} (
    {dimension_keys} ...,
    {metrics} ...,
    source_flag varchar(16) DEFAULT 'computed',
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dws_{name} PRIMARY KEY ({dimension_keys})
);
```

### ADS 层（应用结果层）
```sql
CREATE TABLE IF NOT EXISTS ads_{name} (
    {key} ...,
    {results} ...,
    scheme_id varchar(64) NOT NULL,
    source_flag varchar(16) DEFAULT 'computed',
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_ads_{name} PRIMARY KEY (scheme_id, {key})
);
```

## 关键字段命名规范

| 字段名 | 说明 |
|--------|------|
| `section_number` | 同一单一路径上的收费单元归属同一编号 |
| `scheme_id` | 施工方案 ID |
| `section_id` | 收费单元 ID |
| `od_id` | OD 对 ID |
| `path_id` | 路径 ID |
| `version_yyyyMM` | 版本年月（YYYYMM） |
| `source_flag` | 数据来源标识 |

## SourceFlag 枚举值

| 值 | 说明 |
|----|------|
| `actual` | 真实采集数据 |
| `filled` | 统计补全数据 |
| `rule` | 规则生成数据 |
| `api` | 外部接口数据 |
| `computed` | 计算派生数据 |

## 使用示例

### 生成 DDL
```bash
skill: shanxi-resilience-sql-generator
args: "ddl --layer dwd --name toll_station --pk 'id,version_yyyyMM'"
```

### 生成 DML
```bash
skill: shanxi-resilience-sql-generator
args: "dml --module m1 --input dwd_toll_station --output dws_section_capacity"
```

### 生成检查SQL
```bash
skill: shanxi-resilience-sql-generator
args: "check --table dwd_toll_station --pk 'id,version_yyyyMM'"
```

## 索引创建规范

### 常用索引
- 版本字段：`idx_{table}_version`
- 类型字段：`idx_{table}_type`
- 状态字段：`idx_{table}_status`
- 时间字段：`idx_{table}_day`
- 外键字段：`idx_{table}_{fk_column}`

### 索引示例
```sql
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_version ON dwd_toll_station(version_yyyyMM);
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_type ON dwd_toll_station(TYPE);
CREATE INDEX IF NOT EXISTS idx_dwd_toll_station_status ON dwd_toll_station(status);
```

## 数据质量检查SQL模板

### 主键唯一性检查
```sql
SELECT {pk_columns}, COUNT(*) AS cnt
FROM {table_name}
GROUP BY {pk_columns}
HAVING COUNT(*) > 1;
```

### 必填字段非空检查
```sql
SELECT
    COUNT(*) FILTER (WHERE {column1} IS NULL) AS null_{column1},
    COUNT(*) FILTER (WHERE {column2} IS NULL) AS null_{column2}
FROM {table_name};
```

### 枚举值范围检查
```sql
SELECT DISTINCT {column}
FROM {table_name}
WHERE {column} NOT IN ('{value1}', '{value2}', ...);
```