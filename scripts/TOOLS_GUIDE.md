# 项目工具使用说明书

## 运行前提

所有 Python 脚本必须使用 `uv run` 执行（项目使用 uv 管理虚拟环境）：

```bash
uv run python <script>
# 或
uv run <cli-command>
```

---

## 一、CLI 命令（pyproject.toml 定义）

| 命令 | 说明 | 用法 |
|------|------|------|
| `run-m0` | M0 数据工程 | `uv run run-m0 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-m1` | M1 通行能力评估 | `uv run run-m1 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-m2` | M2 流量与 OD 补全 | `uv run run-m2 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-m3` | M3 交通影响分析 | `uv run run-m3 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-m4` | M4 分流路径优化 | `uv run run-m4 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-m5` | M5 通行费影响测算 | `uv run run-m5 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-pipeline` | 完整流水线 | `uv run run-pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30` |
| `run-query-api` | 启动查询 API 服务 | `uv run run-query-api` |

通用参数：
- `--scheme-id` 施工方案 ID（必填）
- `--start-date` 开始日期 YYYY-MM-DD（必填）
- `--end-date` 结束日期 YYYY-MM-DD（必填）
- `--overwrite` 覆盖已有数据
- `--config-env` 配置环境（dev/prod）

---

## 二、数据导入脚本

### 2.1 维表导入（三件套标准）

| 脚本 | 导入内容 | 依赖数据 |
|------|---------|---------|
| `import_toll_road.py` | 收费路段维表 | `research/data/基础数据/收费路段.xls` |
| `import_toll_station.py` | 收费站维表 | `research/data/基础数据/收费站.xls` |
| `import_toll_station_strict.py` | 收费站维表（严格模式） | 同上 |
| `import_section_path.py` | 收费单元路径映射 | `research/data/基础数据/单元路径映射.xls` |
| `import_construction_segment.py` | 施工分段信息 | `research/data/基础数据/施工分段.xls` |
| `import_lane_capacity_rule.py` | 车道通行能力规则 | `research/data/基础数据/车道通行能力规则.xlsx` |
| `import_detour_ratio_rule.py` | 绕行比例规则 | `research/data/基础数据/绕行比例规则.xlsx` |
| `import_tom_noderelation.py` | Tom 网络节点关系 | `research/data/基础数据/Tom节点关系.xlsx` |

统一用法：
```bash
uv run python scripts/import_xxx.py
```

每个脚本内部自动完成：
1. 读取 `.env` 数据库配置
2. 测试连接
3. 创建/重建表（DROP + CREATE）
4. 读取 Excel 数据并导入
5. 验证数据质量（主键唯一性、必填字段非空等）

### 2.2 Hive 数据导出

```bash
# 导出指定表到本地 CSV（支持断点续传）
uv run python scripts/export_gstx_exit.py -t <表名> -d <数据库名>

# 示例：导出 dbbase2026 的 gstx_exit_with_min_fee202603
uv run python scripts/export_gstx_exit.py -t gstx_exit_with_min_fee202603 -d dbbase2026

# 导出 dbbase2025 的 gstx_exit_with_min_fee202503
uv run python scripts/export_gstx_exit.py -t gstx_exit_with_min_fee202503 -d dbbase2025

# 强制从头导出（忽略已有进度）
uv run python scripts/export_gstx_exit.py -t xxx -d xxx --force
```

参数：
- `-t, --table` 表名（必填）
- `-d, --db` 数据库名（必填）
- `-o, --output` 输出文件路径（默认 `outputs/<table>.csv`）
- `-f, --force` 强制从头导出

---

## 三、pgRouting 路网工具

| 脚本 | 说明 | 用法 |
|------|------|------|
| `install_pgrouting.py` | 安装 pgRouting 扩展 | `uv run python scripts/install_pgrouting.py` |
| `build_tom_network_pgr.py` | 构建 Tom 网络拓扑 | `uv run python scripts/build_tom_network_pgr.py` |
| `optimize_tom_network.py` | 优化网络拓扑 | `uv run python scripts/optimize_tom_network.py` |
| `complete_pgrouting_setup.py` | 完整 pgRouting 初始化 | `uv run python scripts/complete_pgrouting_setup.py` |
| `create_all_path_functions.py` | 创建路径查询函数 | `uv run python scripts/create_all_path_functions.py` |
| `update_tom_functions.py` | 更新 Tom 网络函数 | `uv run python scripts/update_tom_functions.py` |

测试脚本：
```bash
uv run python scripts/test_pgrouting.py          # 基础 pgRouting 测试
uv run python scripts/test_path_schemes.py        # 路径方案测试
uv run python scripts/test_path_schemes_v2.py     # 路径方案测试 v2
uv run python scripts/test_top_n_paths.py         # Top N 路径测试
uv run python scripts/test_top_n_simple.py        # 简化版 Top N 测试
uv run python scripts/test_top_n_pgr.py           # pgRouting Top N 测试
uv run python scripts/test_exclude_paths.py       # 排除路径测试
uv run python scripts/final_test_pgrouting.py     # 完整测试套件
```

---

## 四、数据检查与验证

| 脚本 | 说明 | 用法 |
|------|------|------|
| `test_db_connection.py` | 测试 PostgreSQL 连接 | `uv run python scripts/test_db_connection.py` |
| `test_hive_connection.py` | 测试 Hive 连接并查看表结构 | `uv run python scripts/test_hive_connection.py` |
| `check_field_lengths.py` | 检查字段长度限制 | `uv run python scripts/check_field_lengths.py` |
| `check_toll_station_fields.py` | 检查收费站字段 | `uv run python scripts/check_toll_station_fields.py` |
| `verify_batch_upsert.py` | 验证批量 upsert 逻辑 | `uv run python scripts/verify_batch_upsert.py` |
| `verify_interval_fix.py` | 验证区间修复 | `uv run python scripts/verify_interval_fix.py` |

---

## 五、查询 API 服务

FastAPI 查询服务，提供 HTTP 接口查询分析结果。

```bash
# 启动服务（开发模式，热重载）
uv run run-query-api

# 或直接使用 uvicorn
uv run uvicorn src.services.query_api.main:app --reload --port 8010
```

接口：
- `GET /` - 根路径
- `GET /health` - 健康检查
- `GET /docs` - Swagger 文档
- `GET /api/v1/tasks/...` - 任务相关接口
- `GET /api/v1/results/...` - 结果查询接口

---

## 六、公共工具模块（src/common/）

| 模块 | 功能 | 典型用法 |
|------|------|---------|
| `sql_runner.py` | SQL 文件加载/渲染/执行 | `from src.common.sql_runner import get_sql_runner; runner = get_sql_runner(); runner.run_sql_file("ddl/dim/create_dim_xxx.sql")` |
| `time_utils.py` | 日期解析、批次号生成 | `from src.common.time_utils import parse_date, generate_batch_no` |
| `validators.py` | 输入校验 | `from src.common.validators import validate_scheme_id` |
| `file_loader.py` | 文件加载工具 | `from src.common.file_loader import load_yaml, load_json` |
| `postgis_utils.py` | PostGIS 空间操作 | `from src.common.postgis_utils import create_geometry, buffer_geometry` |

### SqlRunner 核心方法

```python
from src.common.sql_runner import get_sql_runner

runner = get_sql_runner()

# 执行 SQL 文件（支持 Jinja2 模板参数）
runner.run_sql_file("dml/m1/build_section_capacity.sql", params={"scheme_id": "SCH_001"})

# 执行 SQL 字符串
runner.execute_sql("INSERT INTO dim_xxx VALUES (:id)", params={"id": "xxx"})

# 查询所有结果
rows = runner.fetch_all("SELECT * FROM dim_xxx WHERE scheme_id = :sid", params={"sid": "SCH_001"})

# 查询单条
row = runner.fetch_one("SELECT COUNT(*) AS cnt FROM dim_xxx")

# 事务执行
runner.execute_transaction([
    "INSERT INTO a VALUES (1)",
    "INSERT INTO b VALUES (2)",
])
```

---

## 七、项目专用 Skill

| Skill | 功能 | 触发方式 |
|-------|------|---------|
| `shanxi-resilience-table-creator` | 一键生成 DDL + DML + Python 导入脚本三件套 | `/shanxi-resilience-table-creator` |
| `shanxi-resilience-sql-generator` | SQL 生成（DDL/DML/检查） | `/shanxi-resilience-sql-generator` |
| `shanxi-resilience-data-importer` | 数据导入工具 | `/shanxi-resilience-data-importer` |
| `shanxi-resilience-doc-updater` | 更新文档（含数据表说明.md） | `/shanxi-resilience-doc-updater` |
| `shanxi-resilience-pgrouting` | pgRouting 路网优化 | `/shanxi-resilience-pgrouting` |
| `shanxi-resilience-path-query` | 路径查询 | `/shanxi-resilience-path-query` |

---

## 八、快速参考

### 常用工作流

```bash
# 1. 测试数据库连接
uv run python scripts/test_db_connection.py
uv run python scripts/test_hive_connection.py

# 2. 导入基础维表
uv run python scripts/import_toll_road.py
uv run python scripts/import_toll_station.py
uv run python scripts/import_section_path.py

# 3. 运行模块分析
uv run run-m0 --scheme-id SCH_001 --start-date 2026-03-01 --end-date 2026-03-31
uv run run-m1 --scheme-id SCH_001 --start-date 2026-03-01 --end-date 2026-03-31

# 4. 导出 Hive 数据到本地
uv run python scripts/export_gstx_exit.py -t gstx_exit_with_min_fee202603 -d dbbase2026

# 5. 启动查询服务
uv run run-query-api
```

### 数据库连接配置

配置在 `.env` 文件中：

```env
# PostgreSQL（本地分析库）
DB_HOST=192.168.0.75
DB_PORT=5432
DB_USER=sunhaoyu
DB_PASSWORD=xxx
DB_NAME=shanxi_resilience_db

# Hive（远程数据源）
HIVE_HOST=172.16.5.1
HIVE_PORT=10000
HIVE_DATABASE=dbbase2026
HIVE_USER=hive
HIVE_PASSWORD=xxx
```
