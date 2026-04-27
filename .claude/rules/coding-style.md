# Coding Style
# 陕交控多路段改扩建韧性提升项目编码规范
#
# 基于项目的特殊性，补充 Python/SQL 编码规范

## Immutability (CRITICAL)

始终创建新对象，绝不修改现有对象：

```python
# WRONG: Mutation
def update_user(user, name):
    user.name = name  # MUTATION!
    return user

# CORRECT: Immutability
def update_user(user, name):
    return {
        **user,
        "name": name
    }
```

## File Organization

多个小文件 > 单个大文件：
- 高内聚，低耦合
- 典型 200-400 行，最大 800 行
- 从大组件中提取工具函数
- 按功能/领域组织，而非按类型组织

### Python 文件组织

每个模块（M0~M5）统一结构：
```
m{N}_xxx/
├── __init__.py      # 模块初始化
├── task.py          # （未使用，任务入口统一在 jobs/）
├── service.py       # 业务编排层
├── repository.py    # 数据访问层
├── schema.py        # Pydantic 模型
└── checks.py        # 数据校验
```

### SQL 文件组织

```
sql/
├── ddl/            # 建表（按数据层拆分）
│   ├── dim/
│   ├── dwd/
│   ├── dws/
│   └── ads/
├── dml/            # 数据加工（按模块拆分）
│   └── m0~m5/
└── checks/         # 数据校验
```

## Python 编码规则

### 类型标注

所有正式函数必须有类型标注：

```python
# GOOD
def calculate_capacity(lane_cnt: int, lane_occupied_cnt: int) -> int:
    """计算可用车道数"""
    return lane_cnt - lane_occupied_cnt

# BAD
def calculate_capacity(lane_cnt, lane_occupied_cnt):
    return lane_cnt - lane_occupied_cnt
```

### 错误处理

统一异常体系，不允许裸 `except`：

```python
# GOOD
try:
    result = self.sql_runner.fetch_one(sql)
    return result
except Exception as e:
    logger.exception(f"Query failed: {e}")
    raise DatabaseError(f"Query failed: {e}")

# BAD
try:
    result = self.sql_runner.fetch_one(sql)
    return result
except:
    pass
```

### 日志替代 print

使用统一的日志工具：

```python
# GOOD
from src.app.logger import get_logger
logger = get_logger(__name__)

logger.info("Starting M0 module...")
logger.debug(f"Parameters: {params}")

# BAD
print("Starting M0 module...")
```

### 数据库访问优先通过封装

```python
# GOOD
from src.common.sql_runner import get_sql_runner
from src.app.db import get_db_session

sql_runner = get_sql_runner()
sql_runner.execute_sql(sql, params=params)

# BAD
import psycopg
conn = psycopg.connect(...)
```

### 变量命名

- 变量命名使用 camelCase
- 常量命名使用 UPPER_SNAKE_CASE
- 数据库字段使用 snake_case

```python
scheme_id = "SCH_001"  # 接收外部参数
MAX_RETRY_COUNT = 3    # 常量
section_id = row["section_id"]  # 数据库字段
```

## SQL 编码规则

### 核心统计逻辑优先用原生 SQL

```sql
-- GOOD: 原生 SQL，清晰透明
WITH capacity_calc AS (
  SELECT
    section_id,
    lane_cnt - lane_occupied_cnt AS available_lane_cnt
  FROM dwd_scheme_section_map
  WHERE scheme_id = :scheme_id
)
SELECT
  c.*,
  r.capacity_pcu
FROM capacity_calc c
JOIN dim_capacity_rule r
  ON c.available_lane_cnt = r.available_lane_cnt;
```

### 大 SQL 必须拆成可读的 CTE

```sql
-- GOOD: 使用 CTE 分步计算
WITH step1 AS (
  -- 第一步：...
),
step2 AS (
  -- 第二步：...
),
step3 AS (
  -- 第三步：...
)
SELECT * FROM step3;
```

### 每个 SQL 文件顶部必须注明

```sql
-- ============================================================
-- M1: Build Section Capacity
-- ============================================================
-- 作用: 计算收费单元通行能力
-- 输入表: dwd_scheme_section_map, dim_capacity_rule
-- 输出表: dws_section_capacity_day
-- 粒度: section_id × day
-- 关键字段: section_id, day, available_lane_cnt, capacity_pcu
-- ============================================================
```

### 所有落表 SQL 必须说明主键粒度

```sql
-- 主键: scheme_id + section_id + valid_start_date
CREATE TABLE IF NOT EXISTS dwd_scheme_section_map (
  scheme_id VARCHAR(64) NOT NULL,
  section_id VARCHAR(64) NOT NULL,
  valid_start_date DATE NOT NULL,
  ...
  CONSTRAINT pk_dwd_scheme_section_map PRIMARY KEY (
    scheme_id, section_id, valid_start_date
  )
);
```

### 所有汇总逻辑必须明确时间口径

```sql
-- 时间口径: 自然日，非施工期
-- 统计范围: start_date 到 end_date
SELECT
  section_id,
  day,
  COUNT(*) AS flow_cnt
FROM dwd_single_trip_info
WHERE day BETWEEN :start_date AND :end_date
GROUP BY section_id, day;
```

### 关键字段命名统一

对以下字段命名保持统一：
- `section_number` - 同一单一路径上的收费单元归属同一编号
- `scheme_id` - 施工方案 ID
- `section_id` - 收费单元 ID
- `od_id` - OD 对 ID
- `path_id` - 路径 ID

## Code Quality Checklist

标记工作完成前检查：
- [ ] 代码可读性好，命名清晰
- [ ] 函数小（<50 行）
- [ ] 文件聚焦（<800 行）
- [ ] 无深层嵌套（>4 层）
- [ ] 正确的错误处理
- [ ] 无 console.log/print 语句
- [ ] 无硬编码值
- [ ] 无修改（使用不可变模式）
- [ ] SQL 文件有完整的头部注释
- [ ] 所有表已在文档中登记口径
