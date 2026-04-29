# M2 收费单元-OD(path)小时流量统计 — 运行说明

> 模块归属：M2 流量与OD迁移统计补全
> 目标表：`dws_section_od_path_flow_hour`
> 更新日期：2026-04-28

---

## 功能概述

本任务从CSV通行记录文件（如 `gstx_exit_with_min_fee202603.csv`，约4880万条、>10GB）逐行流式读取，经过以下处理后写入 `dws_section_od_path_flow_hour` 表：

1. **intervalgroup + intervaltimegroup 同步修复** — 拓扑补全缺失收费单元，新增节点时间等间隔插值
2. **numPath 映射** — 复用 M6 两步去重逻辑，将 section_id 序列映射为 numpath
3. **od_section_path_id 查找/插入** — 命中内存缓存则直接复用，未命中则批量 INSERT（并行模式下每 mini-batch 收集后批量 upsert）
4. **(section_id, stat_hour) 去重计数** — 同一记录内，同一收费单元在同一小时内只计1次流量
5. **内存聚合 + 即时 upsert** — 单进程模式定期批量写入；并行模式每个 mini-batch 后立即 flush，消灭全局聚合字典

同时支持 **shortest_path 失败容错**：当路网数据缺失导致拓扑修复失败时，跳过该记录，并将失败详情写入本地 CSV 日志，供后续调查与补处理。

支持两种运行模式：
- **单进程模式**（`--workers 1`）：原有逻辑，向后兼容
- **多进程并行模式**（`--workers N`）：CSV 分区并行处理，即时刷盘，ON CONFLICT 累加

---

## 前置依赖

| 依赖项 | 说明 |
|--------|------|
| `dwd_section_path` | 收费单元路径明细表，用于 section_number 映射 |
| `dwd_od_section_path_map` | OD-Section-Path 映射表，用于 od_path_id 查找/插入 |
| `dwd_tom_noderelation` | 路网拓扑明细表，用于 shortest_path 查询 |
| CSV 源文件 | `/home/shy/gaosu_data/gstx_exit_with_min_fee{version}.csv` |

---

## 入口文件

| 文件 | 用途 |
|------|------|
| `src/jobs/run_m2_flow_stat.py` | 命令行入口 |

---

## 快速开始

### 1. 测试模式（推荐首次运行）

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
  Flow records: 8,456
  Map inserts: 12
  Output: outputs/m2_flow_stat/m2_flow_stat_v202603.json
```

### 2. 全量运行（单进程模式）

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 1 \
    --batch-size 500000 \
    --upsert-interval 5
```

### 3. 全量运行（多进程并行模式，推荐）

```bash
# 10 Worker 并行（生产环境推荐）
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 10 \
    --mini-batch-size 50000

# 2 Worker 并行（默认）
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603
```

### 4. 自定义 CSV 路径

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --csv-path /data/custom/gstx_exit_with_min_fee202603.csv \
    --workers 10
```

### 5. 指定版本（section + topo）

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --section-version 202603 \
    --topo-version 202512 \
    --workers 10
```

### 6. 小规模并行测试

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 2 \
    --max-records 10000 \
    --save-local
```

---

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--version` | 版本年月（YYYYMM），与CSV文件名一致 | `202603` |
| `--csv-path` | CSV 文件路径，为空则自动拼接默认路径 | "" |
| `--section-version` | `dwd_section_path` 版本 | `202603` |
| `--topo-version` | 路网拓扑版本 | `202512` |
| `--batch-size` | 每批处理记录数（单进程模式） | `50000` |
| `--upsert-interval` | 每 N 批执行一次数据库 upsert（单进程模式） | `5` |
| `--max-records` | 最大处理记录数，0=全量 | `0` |
| `--save-local` | 保存结果到本地 JSON（测试模式） | `False` |
| `--output-dir` | 本地输出目录 | `outputs/m2_flow_stat` |
| `--workers` | Worker 进程数，1=单进程模式，>1=并行模式 | `2` |
| `--mini-batch-size` | 并行模式下每个 mini-batch 的记录数 | `50000` |

---

## 数据处理流程

### 单进程模式

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
```

### 多进程并行模式

```
Main Process
    │
    ├── 预加载共享数据（fork前）:
    │   section_map + od_path_lookup + topology_cache
    │
    ├── build_csv_offset_index() — 预扫描CSV建立行偏移索引
    │
    ├── create_table() — 确保目标表存在
    │
    └── multiprocessing.Pool(N workers) — fork创建Worker进程
         │
         ▼
    Worker i (独立进程)
         │
         ├── 继承共享数据（CoW零拷贝）
         ├── 重置 PG 连接 + SQLAlchemy engine
         ├── 创建独立 Repository + FixFailureLogger
         │
         └── iter_csv_partition(start_offset, end_offset)
              │
              └── 每 mini-batch (50K行):
                   ├── fix_intervalgroup_batch()
                   ├── _map_and_dedupe_static()
                   ├── 缓存命中: 直接聚合
                   ├── 缓存未命中: 收集 → batch_upsert_od_path_map()
                   ├── _aggregate_record() → local_agg
                   └── upsert_flow_records() → ON CONFLICT 累加 → 清空 local_agg

结果汇总:
    所有 Worker 直接写入同一张月表（ON CONFLICT 行级原子累加保证正确性）
    无需 Python 层面结果合并，无需中间临时表
```

#### 并行模式关键设计

| 设计点 | 说明 |
|--------|------|
| CSV 分区 | 预扫描建字节偏移索引，Worker seek 到指定位置读取 |
| 即时刷盘 | 每 mini-batch (5万行) 处理后立即 flush 到 DB，无全局聚合字典 |
| ON CONFLICT 累加 | `flow_cnt = table.flow_cnt + EXCLUDED.flow_cnt`，行级原子操作 |
| DB 并发安全 | 每个 Worker 独立 DB Session；INSERT ON CONFLICT 幂等 |
| fork CoW 共享 | 主进程预加载 section_map/od_path_lookup/topology_cache，fork 后零拷贝 |
| TopologyChecker | `_reset_pg_connection()` 重置连接；`_next_cache` 通过 CoW 只读共享 |
| SQLAlchemy engine | Worker 内 `db_module._engine.dispose()` 重置，避免 fork 连接共享 |
| batch_upsert_od_path_map | 每 mini-batch 收集缓存未命中，批量 INSERT...RETURNING，减少 ~90% DB 往返 |

#### Worker 数量建议

| 瓶颈 | 上限 | 说明 |
|------|------|------|
| CPU | ~100 核 | 10 Worker 占 10% |
| DB 连接 | ~25 Worker | 连接池 30 连接 |
| 内存 | ~100 Worker | 每 Worker ~40MB |
| HDD I/O | ~10 Worker | HDD 顺序读 ~200MB/s |
| **实际推荐** | **10~20 Worker** | HDD 是关键瓶颈，SSD 可开到 25+ |

---

## 输出表说明

| 表名 | 说明 | 主键/唯一键 |
|------|------|------------|
| `dws_section_od_path_flow_hour` | 收费单元-OD(path)小时流量统计 | `UNIQUE (section_id, od_section_path_id, stat_hour)` |
| `dwd_od_section_path_map` | 可能被插入新记录（查不到时自动INSERT） | `(enid, exid, numpath, version_yyyyMM)` |

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

| 索引名 | 列 | 覆盖查询 |
|--------|-----|----------|
| `idx_sopfh_section_odpath` | `(section_id, od_section_path_id)` | Q1: 查询收费单元影响的所有OD(path) |
| `idx_sopfh_odpath_hour` | `(od_section_path_id, stat_hour)` | Q2: 查询OD(path)的时间范围流量 |
| `idx_sopfh_section_hour` | `(section_id, stat_hour)` | Q3: 查询收费单元的时间范围流量 |

---

## 失败处理

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

```sql
-- 查看表整体统计
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT section_id) AS unique_sections,
    COUNT(DISTINCT od_section_path_id) AS unique_od_paths,
    SUM(flow_cnt) AS total_flow,
    MIN(stat_hour) AS min_hour,
    MAX(stat_hour) AS max_hour
FROM dws_section_od_path_flow_hour;

-- Q1: 查询某收费单元影响的所有OD(path)
SELECT DISTINCT m.enid, m.exid, m.numpath
FROM dws_section_od_path_flow_hour f
JOIN dwd_od_section_path_map m ON f.od_section_path_id = m.id
WHERE f.section_id = 'G007061003000210'
ORDER BY m.enid, m.exid;

-- Q2: 查询某OD(path)的多日/小时流量
SELECT stat_hour, SUM(flow_cnt) AS total_flow
FROM dws_section_od_path_flow_hour
WHERE od_section_path_id = 42
  AND stat_hour BETWEEN '2026-03-01 00:00:00' AND '2026-03-31 23:59:59'
GROUP BY stat_hour
ORDER BY stat_hour;

-- Q3: 查询某收费单元的多日/小时流量
SELECT DATE(stat_hour) AS stat_day, SUM(flow_cnt) AS daily_flow
FROM dws_section_od_path_flow_hour
WHERE section_id = 'G007061003000210'
  AND stat_hour >= '2026-03-01'
GROUP BY DATE(stat_hour)
ORDER BY stat_day;

-- 查看修复失败记录数（从运行结果中获取，或查日志文件）
-- 日志路径：outputs/m2_flow_stat/fix_failures/fix_failures_v202603.csv
```

---

## Python API 调用

```python
from src.modules.m2_od_flow.flow_stat_service import FlowStatService
from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams

service = FlowStatService()

# 测试模式
params = FlowStatParams(
    version_yyyyMM="202603",
    max_records=1000,
    save_local=True,
)
result = service.run(params)

# 多进程并行模式
params = FlowStatParams(
    version_yyyyMM="202603",
    num_workers=10,
    mini_batch_size=50_000,
)
result = service.run(params)

print(f"Status: {result.status}")
print(f"Processed: {result.records_processed:,}")
print(f"Flow records: {result.flow_records_written:,}")
print(f"Fix failures: {result.fix_failures}")
print(f"Execution time: {result.execution_time:.1f}s")
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

**单进程模式**：减小 `--batch-size`：

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 1 \
    --batch-size 100000 \
    --upsert-interval 3
```

**并行模式**：减小 `--mini-batch-size` 或减少 `--workers`：

```bash
uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 5 \
    --mini-batch-size 20000
```

### Worker 启动失败

并行模式在 Windows 使用 spawn（需 pickle 序列化），Linux 使用 fork。如遇到 pickle 错误：
- 确保共享数据不含不可序列化对象
- 检查 TopologyChecker 是否在 fork 前正确初始化

---

## 后台运行

### nohup 方式（单进程）

```bash
cd "D:/BaiduSyncdisk/shy_product/shanxi_resilience_enhancement"

# 开始后台运行
nohup uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 1 \
    --batch-size 500000 \
    --upsert-interval 5 > m2_flow_stat.log 2>&1 &

echo "PID: $!"

# 实时查看日志
tail -f m2_flow_stat.log

# 只看关键行
tail -f m2_flow_stat.log | grep -E "Batch|Upserted|completed|Failed"
```

### nohup 方式（多进程并行，推荐）

```bash
cd "D:/BaiduSyncdisk/shy_product/shanxi_resilience_enhancement"

# 10 Worker 并行后台运行
nohup uv run python -m src.jobs.run_m2_flow_stat \
    --version 202603 \
    --workers 10 \
    --mini-batch-size 50000 > m2_flow_stat_parallel.log 2>&1 &

echo "PID: $!"

# 实时查看日志
tail -f m2_flow_stat_parallel.log

# 只看各Worker进度
tail -f m2_flow_stat_parallel.log | grep -E "W[0-9]:|PARALLEL|completed|Failed"
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
├── test_csv_reader.py          # 21 tests — CSV流式读取、偏移索引、分区读取
├── test_flow_stat_service.py   # 27 tests — 业务编排、去重计数、静态函数
├── test_flow_stat_schema.py    # 14 tests — Pydantic模型、WorkerResult
└── test_fix_failure_logger.py  # 8 tests — 失败日志记录
```

运行测试：

```bash
uv run pytest src/tests/unit/m2_od_flow/ -v
```

---

## 相关文档

| 文档 | 路径 |
|------|------|
| 数据表详细说明 | `docs/数据表说明.md` |
| 会话记录与搭建过程 | `docs/会话记录与搭建过程.md` |
| 业务逻辑记录 | `docs/业务逻辑记录.md` |
| DDL 建表语句 | `sql/ddl/dws/create_dws_section_od_path_flow_hour.sql` |
| M6 批量运行说明 | `docs/M6_批量运行说明.md` |
