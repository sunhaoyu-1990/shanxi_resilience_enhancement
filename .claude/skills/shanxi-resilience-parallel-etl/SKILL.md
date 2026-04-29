---
name: shanxi-resilience-parallel-etl
description: 陕交控项目批量处理并行化工具 - 将单进程 ETL/统计任务改造为多进程并行模式，含 CSV 分区读取、fork-safe DB、ON CONFLICT 累加、mini-batch 即时刷盘等完整模式
---

# 陕交控项目批量处理并行化工具

## 触发场景

用户需要将单进程数据处理任务并行化时激活：
- "xxx 任务运行太慢，需要多进程"
- "把 xxx 改成并行处理"
- "xxx 模块需要加速"
- "单进程跑不完，帮我并行化"

---

## 整体架构：分区并行 + 即时刷盘

```
                    Main Process
                        |
        +---------------+---------------+
        |               |               |
   CSV 预扫描       启动 Worker Pool    结果汇总
   (行偏移索引)     (multiprocessing.Pool)
        |               |               |
        v               v               v
  +---------+   +---+ +---+ +---+   +----------+
  | 偏移索引  |   | W0| | W1| | WN|   | 验证+摘要 |
  +---------+   +---+ +---+ +---+   +----------+
                  |      |      |
                  v      v      v
              各 Worker 独立读取 CSV 分区
              各 Worker 独立 DB Session
              各 Worker 即时 flush -> ON CONFLICT 累加
```

核心思路：
- **分区读取**：预扫描 CSV 建立行偏移索引，每个 Worker seek 到指定位置读取
- **即时刷盘**：每个 mini-batch 处理完立即 flush 到 DB，消灭全局聚合字典
- **ON CONFLICT 累加**：`flow_cnt = table.flow_cnt + EXCLUDED.flow_cnt` 保证多进程写入正确性
- **小批量流式**：每批 5 万行处理后立即释放内存

---

## 执行流程

### Step 1 — 评估并行化可行性

分析目标模块，确认以下条件：

| 检查项 | 要求 | 说明 |
|--------|------|------|
| 数据源 | CSV / 可 seek 的文件 | 需要支持按偏移分区读取 |
| 聚合粒度 | 可按行独立处理 | 每条记录的处理不依赖其他记录的中间结果 |
| DB 写入 | ON CONFLICT 兼容 | 目标表有 UNIQUE 约束，支持累加语义 |
| 共享数据 | 只读或可 CoW | 预加载的映射表/缓存不需要跨 Worker 修改 |

**不适合并行化的场景**：
- 全局排序后再写入
- 行间有强依赖（如当前行需要上一行的输出）
- 目标表无 UNIQUE 约束且不允许重复写入

### Step 2 — 扩展 csv_reader.py

在模块的 `csv_reader.py` 中新增两个函数：

#### 2.1 `build_csv_offset_index()`

```python
def build_csv_offset_index(
    file_path: str,
    step: int = 50_000,
    encoding: str = "utf-8",
) -> tuple[list[int], int]:
    """
    Scan CSV file and record byte offsets every `step` lines.

    Returns:
        (offsets, line_count): 偏移列表和总行数
        offsets[0] = header_end_offset (首个数据行的起始位置)
    """
    offsets: list[int] = []

    with open(file_path, "rb") as f:
        f.readline()  # skip header
        offsets.append(f.tell())

        line_count = 0
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                break
            line_count += 1
            if line_count % step == 0:
                offsets.append(pos)

    return offsets, line_count
```

关键点：
- 用 **二进制模式** 读取，`f.tell()` 返回可靠字节偏移
- 返回 `(offsets, line_count)` 元组，主进程可据此计算分区
- `step` 对应 mini-batch 大小

#### 2.2 `iter_csv_partition()`

```python
def iter_csv_partition(
    file_path: str,
    start_offset: int,
    end_offset: int,
    batch_size: int = 50_000,
    columns: Optional[list[str]] = None,
    encoding: str = "utf-8",
) -> Generator[list[dict], None, None]:
    """
    Read a partition of a CSV file between two byte offsets.

    Key design:
    - Uses io.TextIOWrapper wrapping binary file for seek/tell support
    - start_offset=0: read from header (already positioned after header read)
    - start_offset>0: seek to position, skip partial line, then read
    - end_offset=0: read to EOF
    - end_offset>0: stop when binary buffer position exceeds end_offset
    """
    import io

    with open(file_path, "rb") as bf:
        f = io.TextIOWrapper(bf, encoding=encoding)

        # Read header for column indices
        header = next(csv.reader(f))
        # ... column index setup ...

        if start_offset > 0:
            bf.seek(start_offset)
            f.detach()  # Prevent wrapper from closing bf
            f = io.TextIOWrapper(bf, encoding=encoding)
            f.readline()  # Skip potentially partial line

        reader = csv.reader(f)
        batch: list[dict] = []

        for row in reader:
            if end_offset > 0:
                current_pos = bf.tell()
                if current_pos > end_offset:
                    break

            record = {col: row[idx] for col, idx in col_indices.items() if idx < len(row)}
            batch.append(record)

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch
```

关键点：
- **io.TextIOWrapper 包裹二进制文件**：csv.reader 需要 text stream，但 text stream 的 `tell()` 在 `next(csv.reader())` 后被禁用。用二进制文件 + TextIOWrapper 可以同时支持 seek 和 csv 解析
- **seek 后 detach + 重建 TextIOWrapper**：避免缓冲区不同步
- **首行跳过**：`start_offset > 0` 时第一行可能是上一个分区的残余行

### Step 3 — 重构 Service 层

#### 3.1 统一入口 + 模式分派

```python
class XxxService:
    def run(self, params: XxxParams) -> XxxResult:
        """Main entry - dispatches based on num_workers"""
        if params.num_workers > 1:
            return self._run_parallel(params)
        return self._run_sequential(params)
```

#### 3.2 模块级共享数据

```python
# Module-level shared data for fork-based multiprocessing.
# Populated by _run_parallel() before forking, read by workers via CoW.
_shared_lookup_map: dict[str, int] = {}
_shared_cache: Optional[SomeCache] = None
```

#### 3.3 模块级 Worker 函数（可被 pickle）

```python
def _worker_process(partition: dict) -> WorkerResult:
    """
    Independent worker entry point.

    Args:
        partition: dict with worker_id, csv_path, start_offset, end_offset,
                   mini_batch_size, version, etc.

    Returns:
        WorkerResult with processing statistics
    """
    # 1. Get shared data (fork CoW or load fresh)
    lookup_map = _shared_lookup_map
    if not lookup_map:
        # Spawn mode - load independently
        lookup_map = load_data_independently(...)

    # 2. Reset DB connections for this process
    _reset_db_connections()

    # 3. Create independent repository
    repository = XxxRepository()

    # 4. Process partition
    for mini_batch in iter_csv_partition(...):
        # fix -> map -> aggregate -> flush
        ...

    return WorkerResult(...)
```

**Worker 函数必须满足**：
- 定义在**模块级别**（不能是类方法或嵌套函数），否则无法被 pickle
- 所有依赖通过参数或模块级全局变量传入
- 不修改共享数据（只读通过 CoW）

#### 3.4 静态化实例方法

Worker 无法使用 `self`，需要将实例方法改为模块级函数：

```python
# 原实例方法
class XxxService:
    def _map_and_dedupe(self, intervalgroup: str) -> Optional[str]:
        numbers = [self.section_map.get(sid) for sid in section_ids]
        ...

# Worker 用的静态版本
def _map_and_dedupe_static(section_map: dict, intervalgroup: str) -> Optional[str]:
    numbers = [section_map.get(sid) for sid in section_ids]
    ...
```

#### 3.5 并行调度器

```python
def _run_parallel(self, params: XxxParams) -> XxxResult:
    """Parallel multi-process execution"""
    global _shared_lookup_map, _shared_cache

    # 1. Pre-load shared data BEFORE forking
    _shared_lookup_map = self.repository.load_lookup_map(...)
    _shared_cache = SomeCache(...)
    _shared_cache._reset_db_connection()  # fork-safe

    # 2. Ensure target table exists
    self.repository.create_table(...)

    # 3. Build CSV offset index
    offsets, total_lines = build_csv_offset_index(csv_path, step=params.mini_batch_size)

    # 4. Split into partitions
    partitions = _split_partitions(offsets, params.num_workers, csv_path, params)

    # 5. Fork context (Linux=CoW, Windows=spawn)
    try:
        ctx = multiprocessing.get_context("fork")
    except ValueError:
        ctx = multiprocessing.get_context("spawn")

    with ctx.Pool(params.num_workers) as pool:
        worker_results = pool.map(_worker_process, partitions)

    # 6. Aggregate results
    total_records = sum(r.records_processed for r in worker_results)
    ...

    # 7. Clean up shared data
    _shared_lookup_map = {}
    if _shared_cache:
        _shared_cache.close()
        _shared_cache = None
```

### Step 4 — 重构 Repository 层

#### 4.1 批量 upsert（减少 DB 往返）

```python
def batch_upsert_xxx_map(
    self,
    records: list[dict],
    version: str,
) -> dict[tuple, int]:
    """
    Batch upsert with INSERT ... ON CONFLICT ... RETURNING id.

    Key design:
    - Deduplicate within batch before SQL
    - Chunk to stay under PostgreSQL 65535 parameter limit
    - Use session.execute(text(sql), params) for RETURNING results
    - Returns {(key_fields): id} mapping
    """
    if not records:
        return {}

    # Deduplicate within batch
    seen: set[tuple] = set()
    unique_records: list[dict] = []
    for r in records:
        key = (r["field1"], r["field2"], version)
        if key not in seen:
            seen.add(key)
            unique_records.append(r)
    records = unique_records

    MAX_PER_CHUNK = 5000  # 65535 / ~10 params per record
    result_map: dict[tuple, int] = {}

    for chunk_start in range(0, len(records), MAX_PER_CHUNK):
        chunk = records[chunk_start:chunk_start + MAX_PER_CHUNK]

        sql = "INSERT INTO xxx (...) VALUES "
        value_rows = []
        params = {}
        for i, r in enumerate(chunk):
            value_rows.append(f"(:f1_{i}, :f2_{i}, ...)")
            params[f"f1_{i}"] = r["field1"]
            params[f"f2_{i}"] = r["field2"]
            ...

        sql += ", ".join(value_rows) + """
        ON CONFLICT (field1, field2, version) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
        RETURNING id, field1, field2
        """

        from src.app.db import get_db_session
        with get_db_session() as session:
            result = session.execute(text(sql), params)
            session.commit()
            for row in result.fetchall():
                result_map[(row[1], row[2])] = row[0]

    return result_map
```

#### 4.2 ON CONFLICT 累加 upsert

```python
def upsert_flow_records(self, records: list[dict], version: str) -> int:
    """Batch upsert with flow_cnt accumulation (multi-worker safe)"""
    table_name = f"xxx_{version}"
    MAX_PER_CHUNK = 10000  # 65535 / 5 params

    for chunk_start in range(0, len(records), MAX_PER_CHUNK):
        chunk = records[chunk_start:chunk_start + MAX_PER_CHUNK]

        sql = f"INSERT INTO {table_name} (...) VALUES "
        # ... build value_rows and params ...

        sql += ", ".join(value_rows) + f"""
        ON CONFLICT (key1, key2, key3)
        DO UPDATE SET
            flow_cnt  = {table_name}.flow_cnt + EXCLUDED.flow_cnt,
            updated_at = CURRENT_TIMESTAMP
        """
        self.sql_runner.execute_sql(sql, params=params, commit=True)
```

### Step 5 — 重构 Schema 层

```python
class XxxParams(BaseModel):
    # ... existing fields ...
    num_workers: int = Field(default=1, description="Worker进程数，1=单进程，>1=并行")
    mini_batch_size: int = Field(default=50_000, description="并行模式下mini-batch大小")

class WorkerResult(BaseModel):
    """Worker进程返回的统计结果"""
    worker_id: int = Field(..., description="Worker编号")
    records_processed: int = Field(default=0)
    flow_records_written: int = Field(default=0)
    map_records_inserted: int = Field(default=0)
    fix_failures: int = Field(default=0)
    batches: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
    execution_time: Optional[float] = Field(default=None)
```

### Step 6 — 更新 CLI 入口

```python
parser.add_argument(
    "--workers", type=int, default=2,
    help="Worker进程数，1=单进程兼容模式，>1=并行模式 (default: 2)",
)
parser.add_argument(
    "--mini-batch-size", type=int, default=50000,
    help="并行模式下mini-batch大小 (default: 50000)",
)
```

### Step 7 — Fork 安全性处理

Worker 进程启动后必须执行的清理操作：

```python
def _worker_process(partition: dict) -> WorkerResult:
    # 1. Reset PG connection (TopologyChecker etc.)
    if _shared_cache:
        _shared_cache._reset_pg_connection()

    # 2. Reset SQLAlchemy engine (avoid fork connection sharing)
    import src.app.db as db_module
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = None
    db_module._SessionFactory = None

    # 3. Create independent repository
    repository = XxxRepository()
    ...
```

### Step 8 — 编写测试

为新增的并行化功能编写单元测试：

```python
class TestBuildCsvOffsetIndex:
    """CSV偏移索引构建测试"""
    def test_basic_offset_index(self): ...
    def test_fewer_than_step(self): ...
    def test_offsets_increasing(self): ...

class TestIterCsvPartition:
    """CSV分区读取测试"""
    def test_full_partition(self): ...
    def test_selected_columns(self): ...
    def test_mini_batch_splitting(self): ...

class TestWorkerResult:
    """Worker结果模型测试"""
    def test_success_result(self): ...
    def test_failed_worker(self): ...
    def test_defaults(self): ...

class TestMapAndDedupeStatic:
    """静态去重函数测试"""
    def test_consistent_with_instance_method(self): ...
```

---

## DB 并发安全机制详解

### ON CONFLICT 累加时序

```
时刻1: Worker1 INSERT (key_A, cnt=5)
       -> 行不存在 -> INSERT 成功 -> cnt = 5 -> COMMIT

时刻2: Worker2 INSERT (key_A, cnt=3)
       -> 行已存在 -> ON CONFLICT -> 等待 Worker1 行锁释放
       -> cnt = 5 + 3 = 8 -> COMMIT
```

### 安全性矩阵

| 操作 | 并发安全性 | 原理 |
|------|-----------|------|
| `upsert_flow_records` (ON CONFLICT 累加) | 安全 | 行级原子操作 |
| `batch_upsert_xxx_map` (ON CONFLICT 幂等) | 安全 | 只更新 updated_at |
| `create_table` (IF NOT EXISTS) | 安全 | 幂等操作 |
| `validate_output` (只读) | 安全 | 无写入 |

### 连接池计算

```
连接池配置: pool_size=10, max_overflow=20, 总计=30
Worker 数量: N (每 Worker 1 连接)
安全上限: N <= 25 (留 5 连接给主进程 + 验证)
```

---

## Worker 数量决策表

| 瓶颈 | HDD 服务器 | SSD 服务器 | 说明 |
|------|-----------|-----------|------|
| CPU | ~100 核可用 | ~100 核可用 | 10 Worker 占 10% |
| DB 连接 | ~25 Worker | ~25 Worker | 连接池 30 |
| 内存 | ~100 Worker | ~100 Worker | 每 Worker ~40MB |
| 磁盘 I/O | **~10 Worker** | ~25 Worker | HDD ~200MB/s 顺序读 |
| **推荐** | **10~20** | **20~25** | 磁盘是关键瓶颈 |

---

## 内存控制对照表

| 参数 | 单进程模式 | 并行模式 | 说明 |
|------|-----------|---------|------|
| batch_size | 500,000 | - | 单进程每批读取量 |
| mini_batch_size | - | 50,000 | 并行每批读取量 |
| upsert_interval | 5 | 1 | 并行模式每批都 flush |
| 全局聚合字典 | 有（定期 flush） | 无 | 并行模式即时清空 |
| 单 Worker 内存 | ~400MB | ~40MB | 5万行 list + 小聚合 |
| N Worker 总内存 | N/A | ~40N + 50MB | 共享数据 ~50MB |

---

## 质量检查清单

- [ ] `build_csv_offset_index()` 返回 `(offsets, line_count)` 元组
- [ ] `iter_csv_partition()` 使用 `io.TextIOWrapper` 包裹二进制文件
- [ ] Worker 函数定义在模块级别（可被 pickle）
- [ ] 共享数据通过 `_shared_*` 模块级变量 + fork CoW 传递
- [ ] Worker 内重置 PG 连接 + SQLAlchemy engine
- [ ] 每个 Worker 创建独立 Repository
- [ ] 批量 upsert 含批次内去重
- [ ] ON CONFLICT 累加语法正确（`table.col + EXCLUDED.col`）
- [ ] chunk 大小 < 65535 / 参数数量
- [ ] `num_workers=1` 行为与改造前一致
- [ ] FlowStatParams 新增 `num_workers` + `mini_batch_size`
- [ ] WorkerResult 模型定义完整
- [ ] CLI 新增 `--workers` + `--mini-batch-size` 参数
- [ ] 测试覆盖：分区读取、WorkerResult、静态函数
