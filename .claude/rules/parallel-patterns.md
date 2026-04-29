# Parallel Processing Patterns
# 陕交控多路段改扩建韧性提升项目 — 批量处理并行化规范
#
# 基于 M2 多进程并行化改造总结的通用模式，适用于 M0~M5 各模块的批量任务并行化

## 并行化前提评估

并行化改造前必须确认：

| 检查项 | 要求 | 不满足时的替代方案 |
|--------|------|------------------|
| 数据源 | CSV 或可 seek 的文件 | 预导入到临时表后分区查询 |
| 处理独立性 | 每条记录可独立处理 | 拆分为可独立处理的子任务 |
| DB 写入 | 目标表有 UNIQUE 约束 + ON CONFLICT 兼容 | 添加 UNIQUE 约束或用临时表 |
| 共享数据 | 预加载后只读 | Worker 各自加载（牺牲启动时间） |

## 分区策略规范

### CSV 文件分区 — 行偏移索引

```python
# GOOD: 预扫描建偏移索引，Worker seek 到指定位置
offsets, line_count = build_csv_offset_index(csv_path, step=mini_batch_size)
partitions = _split_partitions(offsets, num_workers, csv_path, params)

# BAD: 预拆分文件（额外 I/O，对 10GB+ 文件浪费时间和空间）
split_csv_into_n_files(csv_path, num_workers)  # 禁止
```

### iter_csv_partition 必须使用 io.TextIOWrapper

```python
# GOOD: 二进制文件 + TextIOWrapper，支持 seek/tell
with open(file_path, "rb") as bf:
    f = io.TextIOWrapper(bf, encoding=encoding)
    header = next(csv.reader(f))
    if start_offset > 0:
        bf.seek(start_offset)
        f.detach()  # 防止 wrapper 关闭 bf
        f = io.TextIOWrapper(bf, encoding=encoding)
        f.readline()  # 跳过可能的不完整行

# BAD: text mode 直接 seek（csv.reader 消费后 tell() 被禁用）
with open(file_path, "r") as f:  # 禁止
    header = next(csv.reader(f))
    f.seek(start_offset)  # 不可靠
```

## Worker 函数规范

### 模块级定义（可被 pickle）

```python
# GOOD: 模块级函数，fork/spawn 均可序列化
def _worker_process(partition: dict) -> WorkerResult:
    ...

# BAD: 类方法或嵌套函数（spawn 模式下不可 pickle）
class XxxService:
    def _worker(self, partition):  # 禁止
        ...
```

### 共享数据传递

```python
# GOOD: 模块级变量 + fork CoW
_shared_section_map: dict[str, int] = {}

def _run_parallel(self, params):
    global _shared_section_map
    _shared_section_map = load_data(...)  # fork 前加载
    with ctx.Pool(num_workers) as pool:
        pool.map(_worker_process, partitions)
    _shared_section_map = {}  # 清理

# BAD: 通过参数传递大字典（spawn 模式下每个 Worker 序列化一份）
partitions.append({"section_map": huge_dict})  # 禁止
```

### Fork 安全性清理

每个 Worker 启动后必须执行：

```python
def _worker_process(partition: dict) -> WorkerResult:
    # 1. 重置 PG 连接（TopologyChecker 等）
    if _shared_topo_checker:
        _shared_topo_checker._reset_pg_connection()

    # 2. 重置 SQLAlchemy engine
    import src.app.db as db_module
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = None
    db_module._SessionFactory = None

    # 3. 创建独立 Repository
    repository = XxxRepository()
```

## 内存控制规范

### Mini-batch + 即时刷盘

```python
# GOOD: 小批量 + 每 1 批 flush，无全局聚合字典
for mini_batch in iter_csv_partition(...):
    local_agg = defaultdict(int)
    # ... 处理 ...
    repository.upsert_flow_records(local_agg_records, version)
    # local_agg 自动释放（函数作用域结束）

# BAD: 大批量 + 定期 flush，全局聚合字典无限增长
self._flow_agg = defaultdict(int)  # 全局，不断增长
for batch in iter_csv_batches(batch_size=500_000):
    # ... 处理到 _flow_agg ...
    if batch_count % 5 == 0:  # 5 批才 flush 一次
        self._flush_to_db()
```

### 内存预算公式

```
单 Worker 内存 ≈ mini_batch_size × 单条记录内存 × 2（list + 聚合 dict）
              ≈ 50,000 × 200B × 2 ≈ 20MB

总内存 ≈ num_workers × 单 Worker 内存 + 共享数据大小
      ≈ 10 × 20MB + 50MB ≈ 250MB
```

## DB 并发安全规范

### ON CONFLICT 累加 — 必须用表名限定

```sql
-- GOOD: 表名限定，避免歧义
INSERT INTO dws_section_od_path_flow_hour_202603 (...)
VALUES (...)
ON CONFLICT (section_id, od_section_path_id, stat_hour)
DO UPDATE SET
    flow_cnt  = dws_section_od_path_flow_hour_202603.flow_cnt
                + EXCLUDED.flow_cnt,
    updated_at = CURRENT_TIMESTAMP

-- BAD: 不加表名限定
ON CONFLICT (...) DO UPDATE SET flow_cnt = flow_cnt + EXCLUDED.flow_cnt  -- 禁止
```

### 批量 upsert 参数上限

```python
# PostgreSQL 单查询最多 65535 个参数
# 每条记录 N 个参数 → chunk 大小 ≤ 65535 // N

# 5 个参数的记录: chunk ≤ 13107, 用 10000 留余量
MAX_RECORDS_PER_CHUNK = 10000

# 10 个参数的记录: chunk ≤ 6553, 用 5000 留余量
MAX_PER_CHUNK = 5000
```

### 每个 Worker 独立 DB Session

```python
# GOOD: Worker 内创建独立 Repository
repository = XxxRepository()  # 新 Session

# BAD: 共享 Repository / Session（fork 后连接不可靠）
repository = self.repository  # 禁止：主进程的 Repository
```

### 批量 upsert 批次内去重

```python
# GOOD: 发送 SQL 前先去重，避免 ON CONFLICT 的额外开销
seen: set[tuple] = set()
unique_records: list[dict] = []
for r in records:
    key = (r["enid"], r["exid"], r["numpath"], version)
    if key not in seen:
        seen.add(key)
        unique_records.append(r)
records = unique_records
```

## 实例方法静态化规范

Worker 进程无法使用 `self`，需要将实例方法改为模块级函数：

```python
# 原实例方法
class XxxService:
    def _map_and_dedupe(self, intervalgroup: str) -> Optional[str]:
        numbers = [self.section_map.get(sid) for sid in section_ids]
        ...

# Worker 用的静态版本 — 接受显式参数
def _map_and_dedupe_static(section_map: dict, intervalgroup: str) -> Optional[str]:
    numbers = [section_map.get(sid) for sid in section_ids]
    ...

# 测试中验证一致性
def test_consistent_with_instance_method(self):
    static_result = _map_and_dedupe_static(section_map, input_str)
    instance_result = service._map_and_dedupe(input_str)
    assert static_result == instance_result
```

## 运行环境兼容性

| 平台 | fork 模式 | spawn 模式 | 注意事项 |
|------|----------|-----------|---------|
| Linux (生产) | 默认，CoW 零拷贝 | 可选 | 共享数据只读，Worker 写入触发页级拷贝 |
| Windows (开发) | 不可用 | 默认 | Worker 需自行加载共享数据；所有参数可 pickle |
| macOS | 可用 | 默认 | 与 Linux 行为一致 |

```python
# GOOD: 自动适配平台
try:
    ctx = multiprocessing.get_context("fork")
except ValueError:
    ctx = multiprocessing.get_context("spawn")
```

## Schema 扩展规范

并行化改造时 Schema 必须新增：

```python
class XxxParams(BaseModel):
    # ... 原有字段 ...
    num_workers: int = Field(default=1, description="Worker进程数，1=单进程，>1=并行")
    mini_batch_size: int = Field(default=50_000, description="并行模式下mini-batch大小")

class WorkerResult(BaseModel):
    """Worker进程返回的统计结果"""
    worker_id: int = Field(...)
    records_processed: int = Field(default=0)
    # ... 与 FlowStatResult 对齐的统计字段 ...
    errors: list[str] = Field(default_factory=list)
    execution_time: Optional[float] = Field(default=None)
```

## 向后兼容规范

- `num_workers=1` 必须与改造前行为完全一致
- 保留 `_run_sequential()` 原有逻辑，不修改
- 新增字段必须有合理默认值
- CLI 参数新增而非替换

## 质量检查清单

- [ ] `build_csv_offset_index()` 返回 `(offsets, line_count)` 元组
- [ ] `iter_csv_partition()` 使用 `io.TextIOWrapper` 包裹二进制文件
- [ ] Worker 函数定义在模块级别
- [ ] 共享数据通过 `_shared_*` 模块级变量传递
- [ ] Worker 内重置 PG 连接 + SQLAlchemy engine
- [ ] 每个 Worker 创建独立 Repository
- [ ] 批量 upsert 含批次内去重
- [ ] ON CONFLICT 累加使用表名限定
- [ ] chunk 大小 < 65535 / 参数数量
- [ ] `num_workers=1` 行为与改造前一致
- [ ] 测试覆盖：分区读取、WorkerResult、静态函数一致性
