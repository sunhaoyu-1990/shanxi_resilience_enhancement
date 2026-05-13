---
name: shanxi-resilience-table-creator
description: 陕交控项目一键建表工具 - 根据字段字典和示例数据，自动生成 DDL + DML + Python导入脚本三件套，并同步更新 docs/数据表说明.md
---

# 陕交控项目一键建表工具

## 前置必读

执行本 Skill 前，**必须**先阅读 `docs/数据表说明.md`，该文件是本项目所有数据库表的权威说明。新建表前必须确认：
- 新表名不与已有表重复（检查表清单总览）
- 字段命名与已有表保持一致（如 `version_yyyymm` 而非 `version_yyyyMM`）
- 遵循已有的分层规范（DIM/DWD/DWS/ADS）
- 新建表完成后**必须**同步更新 `docs/数据表说明.md`

**禁止**凭记忆假设已有表的字段名或类型，必须以 `docs/数据表说明.md` 中的数据字典为准。

## 触发场景

用户提供以下任意形式的输入时自动激活：
- "新增一个 xxx 表"
- "需要建一张 xxx 的对应表"
- "字段字典如下：..."
- "需要添加的数据为：..."

---

## 执行流程

### Step 1 — 分析输入

从用户输入中提取：
- **表名**（snake_case，自动推断）
- **所属数据层**：优先 DIM（维表 / 规则表），业务宽表用 DWD/DWS/ADS
- **所属模块**：M0~M5（根据字段语义判断）
- **字段列表**：名称、类型、约束、描述
- **主键策略**：
  - 纯规则表（id 是业务编号） → `id VARCHAR(20) PRIMARY KEY`
  - 有复合自然唯一键 → `id SERIAL PRIMARY KEY` + `UNIQUE(...)` 约束
- **示例数据**：逐行解析

### Step 2 — 生成 DDL

文件路径：`sql/ddl/{layer}/create_{table_name}.sql`

必须包含：
```sql
-- ============================================================
-- M{N}: Create {Layer} Table - {描述}
-- ============================================================
-- 作用: ...
-- 输入表: 无（手动配置）
-- 输出表: {table_name}
-- 粒度: 每条规则一行
-- 关键字段: {pk_fields}
-- ============================================================

CREATE TABLE IF NOT EXISTS {table_name} (
  -- 主键
  ...
  -- 业务字段
  ...
  -- 元数据
  remark      TEXT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  -- 约束
  CONSTRAINT pk_{table_name} PRIMARY KEY (...),
  CONSTRAINT chk_... CHECK (...)
);

CREATE INDEX IF NOT EXISTS idx_{abbr}_xxx ON {table_name}(...);

COMMENT ON TABLE {table_name} IS '...';
COMMENT ON COLUMN {table_name}.{col} IS '...';
```

PostgreSQL 类型映射：
- `float(8)` → `FLOAT8`
- `int(11)` → `INTEGER`
- `int(1)` → `INTEGER`（配合 CHECK 约束）
- `varchar(N)` → `VARCHAR(N)`
- `date` → `DATE`
- 生成列：`DATE GENERATED ALWAYS AS (date_col + int_col) STORED`

### Step 3 — 生成 DML

文件路径：`sql/dml/m{N}/insert_{table_name}.sql`

```sql
-- ============================================================
-- M{N}: Insert Data - {描述}
-- ============================================================
-- 作用: ...
-- 输入表: 无
-- 输出表: {table_name}
-- ...
-- ============================================================

INSERT INTO {table_name} ({columns})
VALUES
    (...),
    (...)
ON CONFLICT ({pk_or_unique}) DO NOTHING;
```

冲突策略：
- `id` 为 VARCHAR 主键 → `ON CONFLICT (id) DO NOTHING`
- SERIAL 主键 + UNIQUE 约束 → `ON CONFLICT ON CONSTRAINT uq_{table_name} DO NOTHING`

### Step 4 — 生成 Python 导入脚本

文件路径：`scripts/import_{table_name}.py`

固定结构（参考 `scripts/import_toll_road.py`）：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{表描述}建表与数据导入脚本
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg
from psycopg.rows import dict_row

RULE_DATA = [...]  # 示例数据元组列表

INSERT_SQL = """INSERT INTO ... VALUES (...) ON CONFLICT ... DO NOTHING"""

class {ClassName}Importer:
    def __init__(self): ...
    def _read_env(self) -> dict: ...   # 从 .env 读配置
    def get_conn(self): ...            # psycopg.connect
    def test_connection(self) -> bool: ...
    def create_table(self) -> bool: ...  # DROP + 读 DDL 文件 + CREATE
    def import_data(self) -> int: ...    # executemany
    def verify_data(self) -> bool: ...   # 统计 + 质量检查

def main():
    importer = {ClassName}Importer()
    if not importer.test_connection(): sys.exit(1)
    if not importer.create_table(): sys.exit(1)
    importer.import_data()
    importer.verify_data()

if __name__ == "__main__":
    main()
```

`verify_data()` 必须包含：
- 总记录数
- 核心字段的分布统计或明细展示
- 主键唯一性检查（无重复则 ✅）

### Step 5 — 执行脚本

```bash
cd /d/BaiduSyncdisk/shy_product/shanxi_resilience_enhancement
uv run python scripts/import_{table_name}.py
```

### Step 6 — 更新文档

执行成功后，更新 `docs/数据表说明.md`：
1. 更新文件顶部日期
2. 在"二、表清单总览"表格中插入新行（保持字母序）
3. 在"三、各表详细说明"中插入新章节（简介、主键、数据字典、查询示例）
4. 后续章节编号 +1

---

## 质量检查清单

- [ ] DDL 含完整头部注释（作用/输入/输出/粒度/关键字段）
- [ ] 主键策略正确（SERIAL vs VARCHAR）
- [ ] CHECK 约束覆盖枚举值、范围
- [ ] 索引覆盖常用查询字段
- [ ] COMMENT ON COLUMN 覆盖所有字段
- [ ] DML ON CONFLICT 策略与主键一致
- [ ] Python 脚本四方法齐全
- [ ] `verify_data()` 含唯一性检查
- [ ] docs/数据表说明.md 已更新

---

## 快速参考

### 数据库连接
- Host: `192.168.0.75:5432`
- DB: `shanxi_resilience_db`
- User: `sunhaoyu`
- `.env` 路径：`project_root / ".env"`

### 已有规则类维表
| 表名 | 模块 | 主键 |
|------|------|------|
| `dim_construction_segment` | M0 | SERIAL + UNIQUE |
| `dim_detour_ratio_rule` | M5 | VARCHAR id |
| `dim_lane_capacity_rule` | M1 | VARCHAR id |
