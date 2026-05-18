# 陕交控韧性提升项目 — Jobs 使用说明

本文档汇总 `src/jobs/` 下所有命令行任务入口的使用方式。

> 所有命令均使用 `uv run python -m src.jobs.<模块名>` 执行。

---

## 一、流水线总控

### run_pipeline — M0~M5 全链路流水线

按顺序执行 M0→M1→M2→M3→M4→M5，支持选择子集、失败策略。

```bash
# 全链路执行
uv run python -m src.jobs.run_pipeline \
  --scheme-id SCH_001 \
  --start-date 2026-04-01 --end-date 2026-04-30

# 只执行部分模块
uv run python -m src.jobs.run_pipeline \
  --scheme-id SCH_001 \
  --start-date 2026-04-01 --end-date 2026-04-30 \
  --modules m0 m1 m2

# 失败时继续执行后续模块
uv run python -m src.jobs.run_pipeline \
  --scheme-id SCH_001 \
  --start-date 2026-04-01 --end-date 2026-04-30 \
  --continue-on-error

# 覆盖已有数据
uv run python -m src.jobs.run_pipeline \
  --scheme-id SCH_001 \
  --start-date 2026-04-01 --end-date 2026-04-30 \
  --overwrite
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--scheme-id` | str | — | 是 | 施工方案ID |
| `--start-date` | str | — | 是 | 开始日期 (YYYY-MM-DD) |
| `--end-date` | str | — | 是 | 结束日期 (YYYY-MM-DD) |
| `--modules` | str[] | m0~m5 | 否 | 要执行的模块列表 |
| `--overwrite` | flag | False | 否 | 覆盖已有数据 |
| `--stop-on-error` | flag | True | 否 | 模块失败时停止 |
| `--continue-on-error` | flag | — | 否 | 模块失败时继续（与 stop-on-error 互斥） |
| `--config-env` | str | dev | 否 | 配置环境 (dev/prod) |

---

## 二、M0~M5 单模块入口

M0~M5 单模块 CLI 参数格式完全一致，仅模块名和描述不同。

### 通用参数

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--scheme-id` | str | — | 是 | 施工方案ID |
| `--start-date` | str | — | 是 | 开始日期 (YYYY-MM-DD) |
| `--end-date` | str | — | 是 | 结束日期 (YYYY-MM-DD) |
| `--overwrite` | flag | False | 否 | 覆盖已有数据 |
| `--config-env` | str | dev | 否 | 配置环境 (dev/prod) |

### 各模块命令

```bash
# M0 数据工程
uv run python -m src.jobs.run_m0 \
  --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30

# M1 通行能力评估
uv run python -m src.jobs.run_m1 \
  --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30

# M2 流量与OD迁移统计
uv run python -m src.jobs.run_m2 \
  --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30

# M3 交通影响分析
uv run python -m src.jobs.run_m3 \
  --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30

# M4 分流路径优化
uv run python -m src.jobs.run_m4 \
  --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30

# M5 通行费影响测算
uv run python -m src.jobs.run_m5 \
  --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30
```

> **注**: M0~M5 单模块入口目前为框架占位，实际业务逻辑尚未填充。M2 的实际流量统计功能见下方 `run_m2_flow_stat`。

---

## 三、M2 流量统计（专用入口）

### run_m2_flow_stat — 收费单元-OD(path)小时流量统计

支持月文件/日文件两种模式，支持单进程/多进程并行。

```bash
# 日文件模式（推荐）— 单月
uv run python -m src.jobs.run_m2_flow_stat \
  --version 202603 --data-dir /home/shy/gaosu_data

# 日文件模式 — 多月（逗号分隔）
uv run python -m src.jobs.run_m2_flow_stat \
  --versions 202603,202604,202605 --data-dir /home/shy/gaosu_data

# 日文件模式 — 多月（范围）
uv run python -m src.jobs.run_m2_flow_stat \
  --from-version 202603 --to-version 202605 --data-dir /home/shy/gaosu_data

# 并行模式 — 5 个 Worker
uv run python -m src.jobs.run_m2_flow_stat \
  --version 202603 --data-dir /home/shy/gaosu_data \
  --workers 5 --mini-batch-size 50000

# 跳过已处理月份
uv run python -m src.jobs.run_m2_flow_stat \
  --versions 202603,202604,202605 --data-dir /home/shy/gaosu_data \
  --skip-months 202604

# 测试模式 — 限制记录数 + 本地保存
uv run python -m src.jobs.run_m2_flow_stat \
  --version 202603 --data-dir /home/shy/gaosu_data \
  --max-records 1000 --save-local

# 月文件模式（不传 --data-dir，向后兼容）
uv run python -m src.jobs.run_m2_flow_stat \
  --version 202603 --workers 10
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--version` | str | 202603 | 否 | 单月版本 YYYYMM（与 --versions 互斥） |
| `--versions` | str | — | 否 | 多月列表，逗号分隔，如 202603,202604 |
| `--from-version` | str | — | 否 | 起始月份（与 --to-version 配合） |
| `--to-version` | str | — | 否 | 结束月份 |
| `--skip-months` | str | — | 否 | 跳过的月份，逗号分隔 |
| `--data-dir` | str | /home/shy/gaosu_data | 否 | 日文件数据目录，设置后启用日文件模式 |
| `--csv-path` | str | 自动 | 否 | 月文件CSV路径（月文件模式） |
| `--section-version` | str | 同--version | 否 | dwd_section_path 版本 |
| `--topo-version` | str | 同--version | 否 | 拓扑数据版本 |
| `--batch-size` | int | 50000 | 否 | 单进程模式批次大小 |
| `--upsert-interval` | int | 5 | 否 | 每 N 批 flush 一次（单进程） |
| `--workers` | int | 2 | 否 | Worker 进程数，1=单进程 |
| `--mini-batch-size` | int | 50000 | 否 | 并行模式 mini-batch 大小 |
| `--max-records` | int | 0 | 否 | 最大记录数，0=全量 |
| `--save-local` | flag | False | 否 | 保存结果到本地 JSON |
| `--output-dir` | str | outputs/m2_flow_stat | 否 | 本地输出目录 |

---

## 四、M2 验证工具

### validate_m2_daily_flow — 日表统计结果验证

对 M2 流量统计结果进行数量级验证和抽样溯源验证。

```bash
# 基本验证
uv run python -m src.jobs.validate_m2_daily_flow \
  --version 20260301 --data-dir /home/shy/gaosu_data

# 详细输出
uv run python -m src.jobs.validate_m2_daily_flow \
  --version 20260301 --data-dir /home/shy/gaosu_data --verbose

# 自定义容差
uv run python -m src.jobs.validate_m2_daily_flow \
  --version 20260301 --data-dir /home/shy/gaosu_data --tolerance 0.05

# 自定义抽样数
uv run python -m src.jobs.validate_m2_daily_flow \
  --version 20260301 --data-dir /home/shy/gaosu_data --sample-size 100
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--version` | str | — | 是 | 日版本 YYYYMMDD，如 20260301 |
| `--data-dir` | str | /home/shy/gaosu_data | 否 | 原始数据目录 |
| `--tolerance` | float | 0.05 | 否 | 误差容忍度（0.05=5%） |
| `--sample-size` | int | 50 | 否 | 抽样验证数量 |
| `--verbose` | flag | False | 否 | 输出详细信息 |

---

## 五、M6 OD-Section-Path 映射

### run_m6 — OD-Section-Path 映射构建

从 Hive 表读取通行记录，修复 intervalgroup，映射 section_number，构建 OD-Section-Path 映射表。

```bash
# 测试模式 — 100条记录，本地 JSON 输出
uv run python -m src.jobs.run_m6 \
  --version 202603 --batch-size 100 --save-local

# 全量模式 — 50万条/批，2 Worker，直接落库
uv run python -m src.jobs.run_m6 \
  --version 202603 --batch-size 500000 --workers 2

# 指定 Hive 表和拓扑版本
uv run python -m src.jobs.run_m6 \
  --version 202603 \
  --section-version 202512 \
  --topo-version 202512
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--version` | str | 202603 | 否 | 版本年月，自动推导 Hive 表名 |
| `--hive-table` | str | 自动 | 否 | Hive 表名（默认根据 version 生成） |
| `--hive-database` | str | 自动 | 否 | Hive 数据库（2025→dbbase2025，2026→dbbase2026） |
| `--section-version` | str | 同--version | 否 | dwd_section_path 表版本 |
| `--topo-version` | str | 自动 | 否 | 拓扑数据版本 |
| `--batch-size` | int | 500000 | 否 | 每批处理记录数 |
| `--save-local` | flag | False | 否 | 保存到本地 JSON（测试模式） |
| `--output-dir` | str | outputs/m6_test | 否 | 本地输出目录 |
| `--workers` | int | 2 | 否 | 并行 Worker 数 |

---

## 六、M3 交通影响分析（三个子流程）

M3 包含三个独立子流程，可单独运行，也可通过串联入口一键执行。

### 6.1 run_affected_od_query — 流程1：受影响OD-Path流量查询

输入施工收费单元ID，输出受影响的OD对及其流量统计。

```bash
# 基本用法
uv run python -m src.jobs.run_affected_od_query \
  --section-ids "G007061003000210|G300161001002220" \
  --start-date 20260315 --end-date 20260415

# 指定输出路径和流量阈值
uv run python -m src.jobs.run_affected_od_query \
  --section-ids "G007061003000210" \
  --start-date 20260301 --end-date 20260331 \
  --min-affected-path-flow 10 --min-flow 50 \
  --output analysis_results/affected_od_flow.csv
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--section-ids` | str | — | 否 | 施工收费单元ID，多个用 `\|` 分隔 |
| `--start-date` | str | 20260301 | 否 | 施工开始日期 (YYYYMMDD) |
| `--end-date` | str | 20260302 | 否 | 施工结束日期 (YYYYMMDD) |
| `--output` | str | 自动生成 | 否 | 输出CSV路径 |
| `--min-affected-path-flow` | int | 10 | 否 | 受影响path单条流量阈值 |
| `--min-flow` | int | 50 | 否 | OD对聚合总流量阈值 |

### 6.2 run_mid_trip_exit_detector — 流程2：中途下站检测

检测受影响OD的中途下站车辆（同一车牌相邻两次行程，间隔<24h）。

```bash
# 从流程1 CSV 加载 OD 对
uv run python -m src.jobs.run_mid_trip_exit_detector \
  --affected-od-csv analysis_results/affected_od_flow.csv \
  --section-ids "G007061001000610" \
  --start-date 20260301 --end-date 20260331

# 手动指定 OD 对
uv run python -m src.jobs.run_mid_trip_exit_detector \
  --od-pairs "G000561001000110:G007061001000120,G000561001000110:G0070610010020" \
  --section-ids "G007061001000610" \
  --start-date 20260315 --end-date 20260415
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--affected-od-csv` | str | — | 否 | 流程1输出CSV路径 |
| `--od-pairs` | str | — | 否 | 手动指定OD对，格式 enid1:exid1,enid2:exid2 |
| `--section-ids` | str | — | 否 | 施工收费单元ID（用于路径过滤） |
| `--start-date` | str | — | 是 | 施工开始日期 (YYYYMMDD) |
| `--end-date` | str | — | 是 | 施工结束日期 (YYYYMMDD) |
| `--data-dir` | str | /home/shy/gaosu_data | 否 | CSV数据根目录 |
| `--output` | str | 自动生成 | 否 | 输出CSV路径 |

> `--affected-od-csv` 和 `--od-pairs` 至少提供一个。

### 6.3 run_detour_record_detector — 流程3：绕行记录检测

检测受影响OD的绕行车辆（经过施工段但未按原路径通行的车辆）。

```bash
# 从流程1 CSV 加载 OD 对
uv run python -m src.jobs.run_detour_record_detector \
  --affected-od-csv analysis_results/affected_od_flow.csv \
  --section-ids "G007061001000610" \
  --start-date 20260301 --end-date 20260331

# 手动指定 OD 对
uv run python -m src.jobs.run_detour_record_detector \
  --od-pairs "enid1:exid1,enid2:exid2" \
  --section-ids "G007061001000610" \
  --start-date 20260301 --end-date 20260331
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--affected-od-csv` | str | — | 否 | 流程1输出CSV路径 |
| `--od-pairs` | str | — | 否 | 手动指定OD对 |
| `--section-ids` | str | — | 是 | 施工收费单元ID |
| `--start-date` | str | — | 是 | 施工开始日期 (YYYYMMDD) |
| `--end-date` | str | — | 是 | 施工结束日期 (YYYYMMDD) |
| `--data-dir` | str | /home/shy/gaosu_data | 否 | CSV数据根目录 |
| `--max-sections` | int | 5 | 否 | OD到施工单元最短路径节点数上限 |
| `--max-construction-sections` | int | 5 | 否 | 最短路径中施工段个数上限 |
| `--output` | str | 自动生成 | 否 | 输出CSV路径 |

### 6.4 run_affected_od_and_mid_trip — 串联入口：流程1→3→2 + 综合汇总

一键执行流程1（受影响OD查询）→ 流程3（绕行记录）→ 流程2（中途下站）→ 综合汇总，流程间数据自动传递。

```bash
# 完整串联（推荐）
uv run python -m src.jobs.run_affected_od_and_mid_trip \
  --section-ids "G007061001000610|G007061001000620" \
  --start-date 20260301 --end-date 20260331 \
  --min-affected-path-flow 5 --min-flow 10

# 指定各流程输出路径
uv run python -m src.jobs.run_affected_od_and_mid_trip \
  --section-ids "G007061001000610" \
  --start-date 20260301 --end-date 20260302 \
  --output-od analysis_results/affected_od.csv \
  --output-detour analysis_results/detour.csv \
  --output-mid analysis_results/mid_trip.csv \
  --output-summary analysis_results/summary.csv
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--section-ids` | str | — | 否 | 施工收费单元ID，多个用 `\|` 分隔 |
| `--start-date` | str | 20260301 | 否 | 施工开始日期 (YYYYMMDD) |
| `--end-date` | str | 20260331 | 否 | 施工结束日期 (YYYYMMDD) |
| `--min-affected-path-flow` | int | 5 | 否 | 流程1：受影响path单条流量阈值 |
| `--min-flow` | int | 10 | 否 | 流程1：OD对聚合总流量阈值 |
| `--data-dir` | str | /home/shy/gaosu_data | 否 | CSV数据根目录 |
| `--max-sections` | int | 5 | 否 | 流程3：OD到施工单元节点数上限 |
| `--max-construction-sections` | int | 6 | 否 | 流程3：施工段个数上限 |
| `--output-od` | str | 自动生成 | 否 | 流程1输出CSV路径 |
| `--output-detour` | str | 自动生成 | 否 | 流程3输出CSV路径 |
| `--output-mid` | str | 自动生成 | 否 | 流程2输出CSV路径 |
| `--output-summary` | str | 自动生成 | 否 | 综合汇总输出CSV路径 |

---

## 七、M7 数据挖掘

### 7.1 run_m7_lost_vehicle — 流失高频车辆挖掘

根据OD列表和时间段，从日表CSV中筛选匹配OD的通行记录，统计车牌出现频次。

**OD输入格式自动识别**：长度>9视为 enid/exid 格式，长度≤9视为 section_number 格式。支持双向匹配。

```bash
# enid/exid 格式
uv run python -m src.jobs.run_m7_lost_vehicle \
  --od-list "G000561001000110,G007061001000120" \
  --start-date 2026-03-01 --end-date 2026-03-31

# section_number 格式
uv run python -m src.jobs.run_m7_lost_vehicle \
  --od-list "2,146" "378,152" \
  --start-date 2026-03-01 --end-date 2026-03-31

# 从文件读取OD列表
uv run python -m src.jobs.run_m7_lost_vehicle \
  --od-file od_list.csv \
  --start-date 2026-03-01 --end-date 2026-03-31 \
  --top-n 50

# 指定输出路径
uv run python -m src.jobs.run_m7_lost_vehicle \
  --od-list "2,146" \
  --start-date 2026-03-01 --end-date 2026-03-31 \
  --output outputs/m7/lost_vehicles.csv
```

**OD列表文件格式** (`od_list.csv`):
```csv
origin,destination
G000561001000110,G007061001000120
2,146
```

**输出CSV格式**:
```csv
vehicle_id,vehicle_type,frequency
陕E708V9_0,1,156
陕A12345_0,1,89
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--od-list` | str[] | — | 否 | OD对列表，格式 "origin,destination"（可多个） |
| `--od-file` | str | — | 否 | OD对CSV文件路径 |
| `--start-date` | str | 2026-03-01 | 否 | 开始日期 (YYYY-MM-DD) |
| `--end-date` | str | 2026-03-02 | 否 | 结束日期 (YYYY-MM-DD) |
| `--data-dir` | str | /home/shy/gaosu_data | 否 | 日表数据根目录 |
| `--section-version` | str | 202401 | 否 | section_number 映射版本 |
| `--top-n` | int | 0 | 否 | 输出TopN车辆，0=全部 |
| `--output` | str | outputs/m7/lost_vehicles.csv | 否 | 输出CSV路径 |

> `--od-list` 和 `--od-file` 至少提供一个。

### 7.2 run_m7_detour_section — 绕行高频路段挖掘

根据OD列表（含流量X）和基础表，通过累加 construction_flow 找出绕行高频路段。

```bash
# 手动指定 OD+流量
uv run python -m src.jobs.run_m7_detour_section \
  --od-flow-list "G000561001000110,G007061001000120,100" "2,146,50"

# 从文件读取
uv run python -m src.jobs.run_m7_detour_section \
  --od-flow-file od_flow_list.csv \
  --base-table research/analysis/基础表.csv \
  --output outputs/m7/detour_sections.csv
```

**OD流量文件格式** (`od_flow_list.csv`):
```csv
origin,destination,flow_x
G000561001000110,G007061001000120,100
2,146,50
```

**输出CSV格式**:
```csv
section_number,accumulated_flow
358,1250.5
2,980.3
4,876.1
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--od-flow-list` | str[] | — | 否 | OD流量对，格式 "origin,destination,flow_x" |
| `--od-flow-file` | str | — | 否 | OD流量对CSV文件路径 |
| `--base-table` | str | research/analysis/基础表.csv | 否 | 基础表CSV路径 |
| `--section-version` | str | 202401 | 否 | section_number 映射版本 |
| `--output` | str | outputs/m7/detour_sections.csv | 否 | 输出CSV路径 |

> `--od-flow-list` 和 `--od-flow-file` 至少提供一个。

---

## 八、Jobs 速查表

| 命令 | 模块 | 功能 | 数据源 |
|------|------|------|--------|
| `run_pipeline` | 全链路 | M0~M5 顺序执行 | PG |
| `run_m0` | M0 | 数据工程 | PG |
| `run_m1` | M1 | 通行能力评估 | PG |
| `run_m2` | M2 | 流量与OD迁移（框架占位） | PG |
| `run_m2_flow_stat` | M2 | 收费单元-OD(path)小时流量统计 | CSV/日文件 |
| `validate_m2_daily_flow` | M2 | 日表流量统计结果验证 | CSV+PG |
| `run_m3` | M3 | 交通影响分析（框架占位） | PG |
| `run_affected_od_query` | M3 | 流程1：受影响OD-Path流量查询 | PG |
| `run_mid_trip_exit_detector` | M3 | 流程2：中途下站检测 | CSV/日文件 |
| `run_detour_record_detector` | M3 | 流程3：绕行记录检测 | CSV/日文件 |
| `run_affected_od_and_mid_trip` | M3 | 流程1→3→2串联+综合汇总 | PG+CSV |
| `run_m4` | M4 | 分流路径优化（框架占位） | PG |
| `run_m5` | M5 | 通行费影响测算（框架占位） | PG |
| `run_m6` | M6 | OD-Section-Path映射构建 | Hive |
| `run_m7_lost_vehicle` | M7 | 流失高频车辆挖掘 | CSV/日文件 |
| `run_m7_detour_section` | M7 | 绕行高频路段挖掘 | 基础表CSV |

> 标注"框架占位"的入口已有 CLI 框架但业务逻辑尚未填充，调用后仅打印占位信息。
