# Tools 使用说明书

> 本目录存放项目级独立工具，每个工具可独立运行，不依赖 `src/` 模块体系。

---

## hive_export.py — Hive 通行流水数据导出工具

### 功能

从远程 Hive 数据仓库导出通行流水数据到本地 CSV 文件，支持断点续传。

### 数据源

连接信息从项目根目录 `.env` 文件读取：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `HIVE_HOST` | Hive 服务器地址 | `172.16.5.1` |
| `HIVE_PORT` | Hive 端口 | `10000` |
| `HIVE_USER` | 用户名 | `hive` |
| `HIVE_PASSWORD` | 密码 | 空 |

数据库名和表名通过命令行参数指定。

### 导出字段

固定导出以下 8 个字段：

| 字段名 | 说明 |
|--------|------|
| `exid` | 出口站 ID |
| `enid` | 入口站 ID |
| `intervalgroup` | 经过的门架/收费单元路径（`|` 分隔） |
| `intervaltimegroup` | 对应的通行时间组（`|` 分隔） |
| `envehicleid` | 入口车牌 |
| `exvehicleid` | 出口车牌 |
| `entime` | 入口时间 |
| `extime` | 出口时间 |

### 用法

```bash
# 基本用法
uv run python tools/hive_export.py -t <表名> -d <数据库名>

# 导出 dbbase2026 中的 2026年3月数据
uv run python tools/hive_export.py -t gstx_exit_with_min_fee202603 -d dbbase2026

# 导出 dbbase2025 中的 2025年3月数据
uv run python tools/hive_export.py -t gstx_exit_with_min_fee202503 -d dbbase2025

# 指定输出路径
uv run python tools/hive_export.py -t gstx_exit_with_min_fee202603 -d dbbase2026 -o /data/export/202603.csv

# 强制从头导出（忽略已有进度）
uv run python tools/hive_export.py -t gstx_exit_with_min_fee202603 -d dbbase2026 --force
```

### 参数说明

| 参数 | 缩写 | 必填 | 说明 |
|------|------|------|------|
| `--table` | `-t` | 是 | Hive 表名 |
| `--db` | `-d` | 是 | Hive 数据库名 |
| `--output` | `-o` | 否 | 输出文件路径，默认 `outputs/<表名>.csv` |
| `--force` | `-f` | 否 | 强制从头导出，忽略已有进度 |

### 断点续传

导出过程中若因网络中断、Ctrl+C 等原因停止，进度会自动保存。再次运行相同命令即可从断点继续。

**进度文件**：导出时在同目录生成 `<文件名>.csv.progress`，记录已导出行数。导出完成后自动删除。

| 场景 | 行为 |
|------|------|
| 正常首次导出 | 全新导出，生成 CSV + .progress |
| 中断后重新运行 | 检测 .progress + CSV，校验一致后续传 |
| 进度文件与 CSV 不一致 | 报错提示，建议使用 `--force` |
| 加 `--force` 参数 | 删除旧 CSV 和 .progress，从头开始 |
| 导出完成 | 自动删除 .progress 文件 |

**注意**：续传跳行时，数据仍需从 Hive 传输到本地（Hive 无服务端游标），跳过阶段耗时与正常导出相当。如需快速续传，建议导出完成后手动删除 .progress 和 CSV 重新导出，或联系运维对大表建立分区。

### 输出格式

CSV 文件，UTF-8 编码，逗号分隔，首行为表头：

```
exid,enid,intervalgroup,intervaltimegroup,envehicleid,exvehicleid,entime,extime
G000561001000120,G000561001000110,G000561001000110|G000561001000210|...,2026-02-28 18:15:31|...,陕E708V9_0,陕E708V9_0,2026-02-28 18:15:31,2026-03-04 12:20:47
```

字段值含逗号、双引号、换行时，自动用双引号包裹并转义。空值输出为空字符串。

### 依赖

```bash
# 已在项目 .venv 中安装
uv add pyhive sasl thrift-sasl tqdm python-dotenv
```

### 已知可用表

| 数据库 | 表名 | 说明 |
|--------|------|------|
| `dbbase2026` | `gstx_exit_with_min_fee202603` | 2026年3月出口流水（~3900万行） |
| `dbbase2025` | `gstx_exit_with_min_fee202503` | 2025年3月出口流水 |

---

## extract_gaosu_data.py — 高速公路数据按日期范围提取

### 功能

按日期范围从 `/home/shy/gaosu_data/` 中提取数据，支持单日或日期范围筛选。

### 用法

```bash
python3 extract_gaosu_data.py <日期范围> [-o <输出文件>] [-d <数据目录>]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `日期范围` | 是 | 格式 `YYYYMMDD-YYYYMMDD`，如 `20260301-20260303` |
| `-o, --output` | 否 | 输出文件路径，默认输出到 stdout |
| `-d, --data-dir` | 否 | 数据目录，默认 `/home/shy/gaosu_data` |

### 示例

```bash
# 提取单日数据
python3 extract_gaosu_data.py 20260301-20260301 -o output.csv

# 提取日期范围数据
python3 extract_gaosu_data.py 20260301-20260303 -o output.csv

# 输出到标准输出
python3 extract_gaosu_data.py 20260301-20260303 | head -100
```

### 数据量参考

| 日期范围 | 预估记录数 |
|----------|-----------|
| 单日 | ~120 万条 |
| 1 周 | ~840 万条 |
| 1 月 | ~3600 万条（16GB 文件）|

---

## split_by_month.py — 高速公路月度数据拆分

### 功能

将月度大文件拆分为每日数据文件，首末日自动包含边界数据。

### 拆分规则

| 文件 | 筛选条件 |
|------|----------|
| `data_YYYYMMDD.csv`（首日） | 所有 extime ≤ 首日 的数据 |
| `data_YYYYMMDD.csv`（中间日） | 所有 extime = 当天 的数据 |
| `data_YYYYMMDD.csv`（末日） | 所有 extime ≥ 末日 的数据 |

### 用法

```bash
python3 split_by_month.py <YYYYMM> -o <输出目录> [-d <数据目录>]
```

### 示例

```bash
# 拆分 2026年3月数据
python3 split_by_month.py 202603 -o /tmp/march_split

# 查看输出结果
ls /tmp/march_split/
# data_20260301.csv  data_20260302.csv  ...  data_20260331.csv
```

### 数据源文件

位于 `/home/shy/gaosu_data/`，按年月命名：

```
gstx_exit_with_min_fee202501.csv  (1月)
gstx_exit_with_min_fee202502.csv  (2月)
...
gstx_exit_with_min_fee202603.csv  (3月)
```

每文件约 16GB，3900 万行记录。

### 注意事项

1. 脚本逐行扫描，不加载整个文件到内存，适合大数据量
2. `extime` 格式为 `2026-03-04 12:20:47`，脚本自动提取日期部分进行比较
3. 输出目录不存在时会自动创建
4. 处理大文件时请耐心等待，16GB 文件约需数分钟

---

## query_od_vehicles.py — 按 OD 对查询车辆记录

### 功能

按 OD 对（enid:exid）和日期范围，从每日拆分文件中查找匹配的车辆记录。支持多 OD 对查询，输出明细 CSV 及车辆类型统计汇总。

### 用法

```bash
python3 tools/query_od_vehicles.py --od <ENID:EXID> --date-range <YYYYMMDD-YYYYMMDD> [-o 输出文件] [-d 数据目录] [--summary-only]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--od ENID:EXID` | 是 | OD 对，格式 enid:exid，可多次指定 |
| `--date-range YYYYMMDD-YYYYMMDD` | 是 | 日期范围，如 20260301-20260331 |
| `-o, --output` | 否 | 输出 CSV 文件路径，默认 `outputs/tmp/od_vehicles_{enid}_{exid}_{daterange}.csv` |
| `-d, --data-dir` | 否 | 数据目录，默认 `/home/shy/gaosu_data` |
| `--summary-only` | 否 | 仅输出统计汇总，不输出明细行 |

### 示例

```bash
# 查询单个 OD 对，2026 年 3 月
python3 tools/query_od_vehicles.py \
  --od S0030610010030:G0070610020010 \
  --date-range 20260301-20260331 \
  -o /tmp/od_vehicles_202603.csv

# 查询多个 OD 对
python3 tools/query_od_vehicles.py \
  --od S0030610010030:G0070610020010 \
  --od G000561001000110:G000561001000120 \
  --date-range 20260301-20260315

# 仅看统计（不输出明细）
python3 tools/query_od_vehicles.py \
  --od S0030610010030:G0070610020010 \
  --date-range 20260301-20260331 \
  --summary-only
```

### 输出格式

明细模式输出完整 CSV（含全部 13 列），统计模式输出各 OD 对的车辆类型（feevehicletype）分布：

```
OD: S0030610010030 → G0070610020010  (共 1,234 条)
  车型类型              编码       数量     占比
  ----------------------------------------------
  一型客车              1          900    72.93%
  六型货车              16         200    16.21%
  ...
```

### 注意事项

1. 使用每日拆分文件（`YYYYMM/data_YYYYMMDD.csv`），而非月度大文件，按日期范围精确扫描
2. 跨月日期范围自动支持（如 `20260225-20260305` 会扫描 202602 和 202603 两个目录）
3. 逐行扫描，不加载全量到内存，每个文件约 600MB 需数十秒

---

## query_path_fee.py — 路径费额批量查询

### 功能

批量查询路径在所有车型下的通行费、交控费额、里程、交控里程。输入一个 CSV 文件（每行一个 `|` 分隔的收费单元路径字符串或单个收费单元 ID），输出每条路径 × 10 种车型的费额明细。

### 用法

```bash
uv run python tools/query_path_fee.py --fee-version <版本号>

# 指定输入输出
uv run python tools/query_path_fee.py --input tools/data/path.csv --fee-version 202603 -o result.csv
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--fee-version` | 是 | 费率版本，对应 `dwd_section_path` 的 `version_yyyyMM`，如 `202603` |
| `--input` | 否 | 输入 CSV 路径，每行一个路径字符串，默认 `tools/data/path.csv` |
| `-o, --output` | 否 | 输出 CSV 路径，默认 `outputs/tmp/path_fee_result_{fee_version}.csv` |

### 车型范围

| 车型名称 | vehicle_type |
|---------|-------------|
| 客车1型 | 1 |
| 客车2型 | 2 |
| 客车3型 | 3 |
| 客车4型 | 4 |
| 货车1型 | 11 |
| 货车2型 | 12 |
| 货车3型 | 13 |
| 货车4型 | 14 |
| 货车5型 | 15 |
| 货车6型 | 16 |

### 输出格式

CSV 文件，UTF-8 编码，逗号分隔，首行为表头：

```
path,vehicle_type,vehicle_type_name,fee_yuan,control_fee_yuan,length_km,control_length_km,section_count,skipped_count
G065W61001000110|G065W61001000210|...,1,客车1型,58.74,58.74,97.893,97.893,6,0
```

| 列名 | 说明 |
|------|------|
| `path` | 原始路径字符串 |
| `vehicle_type` | 车型编码 |
| `vehicle_type_name` | 车型名称 |
| `fee_yuan` | 通行费（元） |
| `control_fee_yuan` | 交控费额（还贷性路段，元） |
| `length_km` | 总里程（公里） |
| `control_length_km` | 交控里程（公里） |
| `section_count` | 收费单元数量 |
| `skipped_count` | 跳过的单元数量（roadtype 3/4 或查无数据） |

### 依赖

- 数据库：查询 `dwd_section_path`（收费单元信息）、`dim_road_vehicle_fee_map`（费率）、`dim_toll_road`（路段性质）
- 项目模块：`src/common/toll_calculator.py`（TollCalculator）

---

## vehicle_treat_analyse.py — 车辆行为挖掘

### 功能

根据车辆信息，从每日通行数据中提取指定车辆的所有通行记录，并与"附近上下站车辆明细"和"中途上下站车辆明细"进行比对打标，输出合并 CSV。

### 用法

```bash
uv run python tools/vehicle_treat_analyse.py \
  --start-date 2026-03-01 \
  --end-date 2026-03-31 \
  --output tools/data/vehicle_treat_analyse/output.csv
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--start-date` | 是 | 开始日期，格式 YYYY-MM-DD |
| `--end-date` | 是 | 结束日期，格式 YYYY-MM-DD |
| `--output` | 否 | 输出 CSV 路径，默认 `tools/data/vehicle_treat_analyse/output.csv` |

### 输入数据

所有输入文件位于 `tools/data/vehicle_treat_analyse/`：

| 文件 | 说明 | 格式 |
|------|------|------|
| `vehicle_info.csv` | 待分析车辆清单 | 无表头，每行一个 `vehicle_id` 或 `vehicle_id,vehicle_type` |
| `附近上下站车辆明细.csv` | 附近上下站匹配源 | 含 `record_enid`/`record_exid`，无时间字段 |
| `中途上下站车辆明细.csv` | 中途上下站匹配源 | 含 `trip1_*`/`trip2_*` 时间字段 |

通行数据位于 `/home/shy/gaosu_data/YYYYMM/data_YYYYMMDD.csv`，按 `--start-date`/`--end-date` 自动定位。

### 匹配规则

| 匹配来源 | 匹配条件 | 标签 |
|---------|---------|------|
| 附近上下站 | vehicle_id + enid + exid | `附近上下站` |
| 中途上下站-前段 | vehicle_id + enid + exid + entime + extime | `中途上下站-前段` |
| 中途上下站-后段 | vehicle_id + enid + exid + entime + extime | `中途上下站-后段` |

- 车辆匹配：优先 `exvehicleid`，为空时用 `envehicleid`
- 一条记录可匹配多个来源，以逗号分隔
- 无匹配则 `match_source` 为空

### 输出格式

CSV 文件，UTF-8 编码，逗号分隔：

```
vehicle_id,vehicle_type,passid,enid,exid,entime,extime,intervalgroup,match_source
陕HU8051_0,11,0161012018...,G0070610010060,G0070610020020,2026-03-01 15:21:37,...,附近上下站
陕UEP631_0,1,...,...,...,...,...,附近上下站,中途上下站-前段
```

### 数据量参考

| 日期范围 | 扫描数据量 | 预估耗时 |
|---------|-----------|---------|
| 单日 | ~120 万行 | ~10 秒 |
| 1 周 | ~840 万行 | ~1 分钟 |
| 1 月 | ~3600 万行 | ~5 分钟 |
