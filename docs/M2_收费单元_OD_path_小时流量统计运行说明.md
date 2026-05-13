# M2 收费单元-OD(path)小时流量统计 — 运行说明

> 模块归属：M2 流量与OD迁移统计补全
> 目标表：`dws_section_od_path_flow_hour_{version}`（月表 `_{YYYYMM}` 或日表 `_{YYYYMMDD}`）
> 更新日期：2026-04-30

---

## 功能概述

本任务从CSV通行记录文件逐行流式读取，经过以下处理后写入 `dws_section_od_path_flow_hour_{version}` 表：

1. **intervalgroup + intervaltimegroup 同步修复** — 拓扑补全缺失收费单元，新增节点时间等间隔插值
2. **numPath 映射** — 复用 M6 两步去重逻辑，将 section_id 序列映射为 numpath
3. **od_section_path_id 查找/插入** — 命中内存缓存则直接复用，未命中则 INSERT 新记录到 `dwd_od_section_path_map`
4. **(section_id, stat_hour) 去重计数** — 同一记录内，同一收费单元在同一小时内只计1次流量
5. **内存聚合 + 定期批量 upsert** — 按 `(section_id, od_section_path_id, stat_hour)` 聚合，每 N 批写入数据库

支持两种数据源模式：

| 模式 | 数据源 | 输出表 | 触发条件 |
|------|--------|--------|----------|
| **月文件模式** | 单个大月文件（>10GB） | `dws_section_od_path_flow_hour_{YYYYMM}` | `--data-dir` 为空（默认） |
| **日文件模式** | 月份目录下按天拆分的日文件 | `dws_section_od_path_flow_hour_{YYYYMMDD}`（每天一张表） | `--data-dir` 非空 |

同时支持 **shortest_path 失败容错**：当路网数据缺失导致拓扑修复失败时，跳过该记录，并将失败详情写入本地 CSV 日志，供后续调查与补处理。

---

## 前置依赖

| 依赖项 | 说明 |
|--------|------|
| `dwd_section_path` | 收费单元路径明细表，用于 section_number 映射 |
| `dwd_od_section_path_map` | OD-Section-Path 映射表，用于 od_path_id 查找/插入 |
| `dwd_tom_noderelation` | 路网拓扑明细表，用于 shortest_path 查询 |
| CSV 源文件（月文件模式） | `/home/shy/gaosu_data/gstx_exit_with_min_fee{version}.csv` |
| CSV 源文件（日文件模式） | `/home/shy/gaosu_data/{YYYYMM}/data_{YYYYMMDD}.csv`（如 `data_20260301.csv`） |

---

## 入口文件

| 文件 | 用途 |
|------|------|
| `src/jobs/run_m2_flow_stat.py` | 命令行入口 |

---

## 快速开始

### 1. 测试模式 — 月文件（推荐首次运行）

处理1000条记录，保存本地 JSON 结果，不污染数据库：

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --max-records 1000 \
    --save-local
```

输出示例：

```
Done! 1,000 records processed in 3.2s
  Mode: monthly
  Flow records: 8,456
  Map inserts: 12
  Output: outputs/m2_flow_stat/m2_flow_stat_v202603.json
```

### 2. 测试模式 — 日文件

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --max-records 1000 \
    --save-local
```

输出示例：

```
Done! 1,000 records processed in 3.2s
  Mode: daily
  Flow records: 8,456
  Map inserts: 12
  Output: outputs/m2_flow_stat/m2_flow_stat_v202603.json
```

### 3. 全量运行 — 月文件模式

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --batch-size 50000 \
    --upsert-interval 5
```

### 4. 全量运行 — 日文件单进程

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --workers 1
```

### 5. 全量运行 — 日文件并行（推荐）

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --workers 4 \
    --mini-batch-size 50000
```

### 6. 自定义 CSV 路径（月文件模式）

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --csv-path /data/custom/gstx_exit_with_min_fee202603.csv \
    --batch-size 50000
```

### 7. 指定版本（section + topo）

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --section-version 202603 \
    --topo-version 202512 \
    --batch-size 50000
```

---

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--version` | 版本年月（YYYYMM），与CSV文件名/目录名一致 | `202603` |
| `--csv-path` | CSV 文件路径（月文件模式专用），为空则自动拼接默认路径 | `""` |
| `--data-dir` | 日文件数据目录，设定后走日文件模式。目录结构：`{data_dir}/{version}/data_*.csv` | `""` |
| `--section-version` | `dwd_section_path` 版本 | `202603` |
| `--topo-version` | 路网拓扑版本 | `202512` |
| `--batch-size` | 每批处理记录数（单进程模式） | `50000` |
| `--upsert-interval` | 每 N 批执行一次数据库 upsert（单进程模式） | `5` |
| `--max-records` | 最大处理记录数，0=全量 | `0` |
| `--save-local` | 保存结果到本地 JSON（测试模式） | `False` |
| `--output-dir` | 本地输出目录 | `outputs/m2_flow_stat` |
| `--workers` | Worker 进程数，1=单进程，>1=并行模式 | `2` |
| `--mini-batch-size` | 并行模式下每个 mini-batch 的记录数 | `50000` |

### 模式选择逻辑

```
--data-dir 非空？
  ├─ 是 → 日文件模式
  │      ├─ --workers 1 → _run_sequential_daily()
  │      └─ --workers N → _run_parallel_daily()（Round-Robin 分配日文件）
  └─ 否 → 月文件模式
         ├─ --workers 1 → _run_sequential()
         └─ --workers N → _run_parallel()（字节偏移分区）
```

---

## 数据处理流程

### 月文件模式

```
CSV文件(>10GB)
    ↓ 逐行流式读取（csv.reader + 列索引，只取8个字段）
    ↓
fix_intervalgroup_batch() — 同步修复 intervalgroup + intervaltimegroup
    - Case 1: 拓扑连通，直接保留
    - Case 2: 拓扑断裂，shortest_path 补全，新增节点时间等间隔插值
    - Case 3a: 方向反转修复
    - Case 3b: 反向路径补全
    - Case 4: 末尾断裂，跳过
    - 失败时: IntervalFixResult.error = "path_fill_failed:X1->X2"
    ↓
_map_and_dedupe() — 复用 M6 两步去重，生成 numpath
    - Step 1: 相邻 section_number 去重
    - Step 2: 成对去重（offset 0/1 取较短结果）
    ↓
_get_or_create_od_path_id() — 查找或插入 od_section_path_id
    - 内存缓存命中 → 直接返回
    - 未命中 → INSERT ... ON CONFLICT DO UPDATE RETURNING id
    ↓
截断到小时 + (section_id, stat_hour) 去重
    - fixed_ig 与 fixed_itg 一一对应
    - stat_hour = time_str[:14] + "00:00"
    - 同一记录内，同一 (section_id, stat_hour) 只计1次
    ↓
内存聚合 + 定期 upsert
    - {(section_id, od_path_id, stat_hour): count}
    - 每 upsert_interval 批写入数据库
    - 输出表: dws_section_od_path_flow_hour_{YYYYMM}
```

### 日文件模式

```
{data_dir}/{YYYYMM}/  目录
    ↓ discover_daily_files() 扫描 data_{YYYYMMDD}.csv，按日期排序
    ↓
逐文件处理（单进程顺序 / 多进程 Round-Robin 分配）
    ↓ 每个日文件：
    ↓   1. 从文件名提取 day_version（如 "20260301"）
    ↓   2. 主进程执行 create_table(day_version)（并行模式下避免多 Worker 同时 DDL）
    ↓   3. _detect_has_header() 自动检测文件是否含表头
    ↓   4. 逐行流式读取（与月文件模式相同的核心处理流程）
    ↓   5. upsert 到日表 dws_section_od_path_flow_hour_{YYYYMMDD}
    ↓   6. 保存 checkpoint（日文件模式的 completed_files 列表）
    ↓
每张日表独立：
    - dws_section_od_path_flow_hour_20260301
    - dws_section_od_path_flow_hour_20260302
    - ... （31 张表）
```

#### 日文件模式的双版本机制

| 操作 | 使用的版本 | 说明 |
|------|-----------|------|
| `dwd_od_section_path_map` 查找/插入 | 月版 `{YYYYMM}`（如 `202603`） | OD 路径映射按月管理 |
| `dws_section_od_path_flow_hour_{version}` 建表/upsert | 日版 `{YYYYMMDD}`（如 `20260301`） | 流量统计按天输出 |
| checkpoint 标识 | 月版 `{YYYYMM}` | 按 worker + 月版本存储进度 |

#### 日文件 has_header 自动检测

由于 `split_by_month.py` 早期版本生成的日文件可能不含表头，日文件模式自动调用 `_detect_has_header()` 检测首行是否包含 `enid`/`exid`/`intervalgroup` 等关键字：
- 首行含关键字 → 有表头，`has_header=True`，跳过首行
- 首行不含关键字 → 无表头，`has_header=False`，按文件实际列顺序映射
- 空文件 → 默认 `has_header=True`（安全降级）

> 注意：`split_by_month.py` 已修复，新拆分的日文件会写入表头。检测逻辑为兼容旧文件的兜底方案。

---

## 输出表说明

### 月文件模式

| 表名 | 说明 | 主键/唯一键 |
|------|------|------------|
| `dws_section_od_path_flow_hour_{YYYYMM}` | 收费单元-OD(path)小时流量统计（月表） | `UNIQUE (section_id, od_section_path_id, stat_hour)` |
| `dwd_od_section_path_map` | 可能被插入新记录（查不到时自动INSERT） | `(enid, exid, numpath, version_yyyyMM)` |

### 日文件模式

| 表名 | 说明 | 主键/唯一键 |
|------|------|------------|
| `dws_section_od_path_flow_hour_{YYYYMMDD}` | 收费单元-OD(path)小时流量统计（日表，每天一张） | `UNIQUE (section_id, od_section_path_id, stat_hour)` |
| `dwd_od_section_path_map` | 可能被插入新记录（查不到时自动INSERT，使用月版） | `(enid, exid, numpath, version_yyyyMM)` |

日表示例（202603月份会生成31张表）：

```
dws_section_od_path_flow_hour_20260301
dws_section_od_path_flow_hour_20260302
...
dws_section_od_path_flow_hour_20260331
```

### dws_section_od_path_flow_hour 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGSERIAL | 自增主键 |
| `section_id` | VARCHAR(64) | 收费单元ID |
| `od_section_path_id` | BIGINT | OD-Section-Path映射表ID |
| `stat_hour` | TIMESTAMP | 统计小时（带日期），如 `2026-03-01 12:00:00` |
| `flow_cnt` | INTEGER | 通行流量 |
| `source_flag` | VARCHAR(32) | 默认 `computed` |
| `created_at` | TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | 更新时间 |

### 索引设计

每张表（月表或日表）均包含以下索引：

| 索引名 | 列 | 覆盖查询 |
|--------|-----|----------|
| `idx_sopfh_section_odpath` | `(section_id, od_section_path_id)` | Q1: 查询收费单元影响的所有OD(path) |
| `idx_sopfh_odpath_hour` | `(od_section_path_id, stat_hour)` | Q2: 查询OD(path)的时间范围流量 |
| `idx_sopfh_section_hour` | `(section_id, stat_hour)` | Q3: 查询收费单元的时间范围流量 |

---

## 失败处理

### 日文件缺失

日文件模式下，如果某天的文件不存在（如 `data_20260315.csv` 缺失），程序会发出 warning 但不中断，继续处理其余文件。

### shortest_path 修复失败

当 `intervalgroup` 补全过程中 `shortest_path()` 返回 `None` 时：

1. **跳过记录** — 不中断处理，继续下一条
2. **计数上报** — `FlowStatResult.fix_failures` 记录失败总数
3. **本地 CSV 日志** — 失败详情写入 `{output_dir}/fix_failures/fix_failures_v{version}.csv`

CSV 日志字段：

| 字段 | 说明 |
|------|------|
| `enid` | 入口收费站ID |
| `exid` | 出口收费站ID |
| `intervalgroup` | 原始收费单元序列 |
| `intervaltimegroup` | 原始时间序列 |
| `envehicleid` | 入口车辆ID |
| `exvehicleid` | 出口车辆ID |
| `entime` | 入口时间 |
| `extime` | 出口时间 |
| `failure_reason` | 失败原因，如 `path_fill_failed:A->B` |

日志文件支持**追加模式**：多次运行同一版本不会重复写 header。

---

## 验证结果

运行后可用 SQL 核对数据：

### 月文件模式

```sql
-- 查看月表整体统计
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT section_id) AS unique_sections,
    COUNT(DISTINCT od_section_path_id) AS unique_od_paths,
    SUM(flow_cnt) AS total_flow,
    MIN(stat_hour) AS min_hour,
    MAX(stat_hour) AS max_hour
FROM dws_section_od_path_flow_hour_202603;

-- Q1: 查询某收费单元影响的所有OD(path)
SELECT DISTINCT m.enid, m.exid, m.numpath
FROM dws_section_od_path_flow_hour_202603 f
JOIN dwd_od_section_path_map m ON f.od_section_path_id = m.id
WHERE f.section_id = 'G007061003000210'
ORDER BY m.enid, m.exid;

-- Q2: 查询某OD(path)的多日/小时流量
SELECT stat_hour, SUM(flow_cnt) AS total_flow
FROM dws_section_od_path_flow_hour_202603
WHERE od_section_path_id = 42
  AND stat_hour BETWEEN '2026-03-01 00:00:00' AND '2026-03-31 23:59:59'
GROUP BY stat_hour
ORDER BY stat_hour;

-- Q3: 查询某收费单元的多日/小时流量
SELECT DATE(stat_hour) AS stat_day, SUM(flow_cnt) AS daily_flow
FROM dws_section_od_path_flow_hour_202603
WHERE section_id = 'G007061003000210'
  AND stat_hour >= '2026-03-01'
GROUP BY DATE(stat_hour)
ORDER BY stat_day;

-- 查看修复失败记录数（从运行结果中获取，或查日志文件）
-- 日志路径：outputs/m2_flow_stat/fix_failures/fix_failures_v202603.csv
```

### 日文件模式

```sql
-- 查看某日表统计
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT section_id) AS unique_sections,
    COUNT(DISTINCT od_section_path_id) AS unique_od_paths,
    SUM(flow_cnt) AS total_flow,
    MIN(stat_hour) AS min_hour,
    MAX(stat_hour) AS max_hour
FROM dws_section_od_path_flow_hour_20260301;

-- 查看全月所有日表汇总
SELECT
    '20260301' AS day, COUNT(*) AS records, SUM(flow_cnt) AS total_flow
FROM dws_section_od_path_flow_hour_20260301
UNION ALL
SELECT
    '20260302' AS day, COUNT(*) AS records, SUM(flow_cnt) AS total_flow
FROM dws_section_od_path_flow_hour_20260302
-- ... 逐日 UNION ALL
ORDER BY day;

-- 一键查看所有日表（使用 PL/pgSQL 动态查询）
DO $$
DECLARE
    tbl TEXT;
    cnt INTEGER;
BEGIN
    FOR tbl IN
        SELECT tablename FROM pg_tables
        WHERE tablename LIKE 'dws_section_od_path_flow_hour_202603%'
        ORDER BY tablename
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I', tbl) INTO cnt;
        RAISE NOTICE '%  →  % rows', tbl, cnt;
    END LOOP;
END $$;

-- 验证日表 SUM(flow_cnt) 之和 vs 月表 SUM(flow_cnt)（一致性校验）
-- 分别运行月文件模式和日文件模式后对比：
SELECT SUM(flow_cnt) AS monthly_total FROM dws_section_od_path_flow_hour_202603;
-- vs
-- 上述全月所有日表 total_flow 之和
```

---

## Python API 调用

```python
from src.modules.m2_od_flow.flow_stat_service import FlowStatService
from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams

service = FlowStatService()

# 月文件模式 — 测试
params = FlowStatParams(
    version_yyyyMM="202603",
    max_records=1000,
    save_local=True,
)
result = service.run(params)
print(f"Status: {result.status}")
print(f"Processed: {result.records_processed:,}")
print(f"Flow records: {result.flow_records_written:,}")

# 日文件模式 — 单进程
params = FlowStatParams(
    version_yyyyMM="202603",
    data_dir="/home/shy/gaosu_data",
    num_workers=1,
)
result = service.run(params)

# 日文件模式 — 4 Worker 并行
params = FlowStatParams(
    version_yyyyMM="202603",
    data_dir="/home/shy/gaosu_data",
    num_workers=4,
    mini_batch_size=50000,
)
result = service.run(params)
```

---

## 故障处理

### CSV 文件不存在

```
Failed! CSV file not found: /home/shy/gaosu_data/gstx_exit_with_min_fee202603.csv
```

检查文件路径，或通过 `--csv-path` 指定正确路径。

### 数据库连接失败

检查 `.env` 文件中的数据库配置：

```bash
# .env
DB_HOST=192.168.0.75
DB_PORT=5432
DB_NAME=shanxi_resilience_db
DB_USER=sunhaoyu
DB_PASSWORD=xxx
```

### 修复失败记录过多

查看失败日志：

```bash
# 统计失败记录数
wc -l outputs/m2_flow_stat/fix_failures/fix_failures_v202603.csv

# 查看失败原因分布
cut -d',' -f10 outputs/m2_flow_stat/fix_failures/fix_failures_v202603.csv | sort | uniq -c
```

常见原因：
- 路网拓扑版本与数据版本不匹配 → 检查 `--topo-version`
- 新增收费单元不在路网中 → 需要更新路网数据

### 内存溢出

月文件模式减小 `--batch-size`：

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --batch-size 100000 \
    --upsert-interval 3
```

日文件模式减小 `--mini-batch-size`：

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --workers 2 \
    --mini-batch-size 20000
```

### 日文件断点续跑

日文件并行模式支持从 checkpoint 恢复。如果中途被中断，重新运行同一命令即可自动跳过已完成的文件：

```bash
# 首次运行（假设处理到一半被中断）
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --workers 4

# 重新运行，自动从 checkpoint 恢复
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --workers 4
```

checkpoint 文件路径：`outputs/m2_flow_stat/checkpoints/w{worker_id}_v{version}_daily.json`

---

## 后台运行

### nohup 方式 — 月文件

```bash
cd "D:/BaiduSyncdisk/shy_product/shanxi_resilience_enhancement"

# 开始后台运行
nohup uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --batch-size 50000 \
    --upsert-interval 5 > m2_flow_stat.log 2>&1 &

echo "PID: $!"

# 实时查看日志
tail -f m2_flow_stat.log

# 只看关键行
tail -f m2_flow_stat.log | grep -E "Batch|Upserted|completed|Failed"
```

### nohup 方式 — 日文件并行

```bash
nohup uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --data-dir /home/shy/gaosu_data \
    --workers 4 \
    --mini-batch-size 50000 > m2_daily_flow_stat.log 2>&1 &

echo "PID: $!"

# 实时查看日志
tail -f m2_daily_flow_stat.log

# 只看关键行（日文件模式会输出每个文件的处理进度）
tail -f m2_daily_flow_stat.log | grep -E "Processing daily|completed|Worker|Upserted|Failed"
```

### 停止后台进程

```bash
ps aux | grep run_m2_flow_stat
kill <PID>
```

---

## 单元测试

M2 模块单元测试按目录组织：

```
src/tests/unit/m2_od_flow/
├── test_interval_fixer.py      # 34 tests — intervalgroup修复、时间插值
├── test_csv_reader.py          # 51 tests — CSV流式读取、日文件发现、has_header检测、iter_daily_csv_batches
├── test_flow_stat_service.py   # 47 tests — 业务编排、去重计数、日文件分发、日版提取
├── test_flow_stat_schema.py    # 20 tests — Pydantic模型（含data_dir、completed_files）
├── test_checkpoint.py          # 26 tests — offset模式与daily模式断点
└── test_fix_failure_logger.py  # 8 tests — 失败日志记录
```

运行测试：

```bash
uv run pytest src/tests/unit/m2_od_flow/ -v
```

新增日文件模式相关测试覆盖：

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|----------|
| `TestDiscoverDailyFiles` | 9 | 日文件发现、缺失文件warning、空目录 |
| `TestDetectHasHeader` | 8 | 有/无表头检测、空文件降级、编码兼容 |
| `TestIterDailyCsvBatches` | 6 | 日文件批量迭代、day_str提取 |
| `TestDailyCheckpointSaveLoad` | 10 | 日模式断点保存/加载/清除 |
| `TestDailyAndOffsetCoexistence` | 2 | 日模式与月模式断点共存 |
| `TestExtractDayVersion` | 8 | 从文件名提取日版本字符串 |
| `TestAssignDailyFiles` | 9 | Round-Robin 分配逻辑 |
| `TestRunDispatch` | 5 | run() 三路分发逻辑 |
| `TestFlushToDb` | 6 | _flush_to_db 日版/月版参数 |
| `TestColumnConstants` | 6 | CSV_COLUMNS_IN_FILE_ORDER 常量 |

---

## 相关文档

| 文档 | 路径 |
|------|------|
| 数据表详细说明 | `docs/数据表说明.md` |
| 会话记录与搭建过程 | `docs/会话记录与搭建过程.md` |
| 业务逻辑记录 | `docs/业务逻辑记录.md` |
| DDL 建表语句 | `sql/ddl/dws/create_dws_section_od_path_flow_hour.sql` |
| M6 批量运行说明 | `docs/M6_批量运行说明.md` |
