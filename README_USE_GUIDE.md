# 陕交控多路段改扩建韧性提升项目（一期）- 使用指南

## 目录结构总览

```
shanxi_resilience_enhancement/
├── configs/              # 配置文件（YAML）
├── docs/                 # 项目文档（Org 格式）
├── outputs/              # 临时输出（不提交 Git）
│   ├── logs/            # 运行日志
│   ├── exports/         # CSV/Excel 导出
│   ├── reports/         # 分析报告
│   └── temp/            # 临时中间文件
├── research/             # 研究与试验代码（与工程分离）
├── scripts/              # 运维辅助脚本
├── sql/                  # SQL 文件
│   ├── ddl/            # 建表（CREATE TABLE）
│   │   ├── dim/        # 维表层
│   │   ├── dwd/        # 明细事实层
│   │   ├── dws/        # 汇总事实层
│   │   └── ads/        # 应用结果层
│   ├── dml/            # 数据加工（INSERT/SELECT INTO）
│   │   └── m0~m5/      # 按模块拆分
│   └── checks/         # 数据校验 SQL
├── src/                  # 正式工程代码
│   ├── app/            # 应用核心基础设施
│   │   ├── db.py       # 数据库连接管理
│   │   ├── enums.py    # 全局枚举常量
│   │   ├── exceptions.py # 统一异常类
│   │   ├── logger.py   # 日志工具
│   │   └── settings.py # 配置加载
│   ├── common/         # 跨模块通用工具
│   │   ├── sql_runner.py  # SQL 加载/渲染/执行
│   │   ├── time_utils.py  # 日期时间工具
│   │   ├── validators.py  # 输入校验
│   │   ├── file_loader.py # 文件加载
│   │   └── postgis_utils.py # PostGIS 工具
│   ├── modules/        # 核心业务模块（M0~M5）
│   │   ├── mN_xxx/
│   │   │   ├── task.py      # （未使用）
│   │   │   ├── service.py   # 业务编排
│   │   │   ├── repository.py # 数据访问
│   │   │   ├── schema.py    # Pydantic 模型
│   │   │   └── checks.py    # 数据校验
│   ├── jobs/           # 命令行任务入口
│   │   ├── run_m0.py ~ run_m5.py  # 各模块独立入口
│   │   └── run_pipeline.py          # 流水线总控
│   ├── services/       # 查询服务
│   │   └── query_api/  # FastAPI HTTP API
│   └── tests/          # 测试
│       ├── unit/       # 单元测试
│       └── integration/ # 集成测试
├── .env                  # 环境变量（不提交 Git）
├── .env.example          # 环境变量模板
├── pyproject.toml        # Python 包配置
└── README.org           # 主文档（Org 格式）
```

---

## 核心概念

### 模块代码结构（每个模块都一样）

| 文件 | 职责 |
|------|------|
| `service.py` | 业务流程编排：调用 repository，记录日志，异常捕获 |
| `repository.py` | 数据访问：调用 SqlRunner 执行 SQL |
| `schema.py` | Pydantic 模型：TaskParams、TaskResult 等 |
| `checks.py` | 数据质量校验 |

### 枚举体系（src/app/enums.py）

| 枚举类 | 用途 |
|--------|------|
| `ModuleCode` | 模块标识（M0~M5），带 `sql_dir`、`checks_dir` 属性 |
| `TaskStatus` | 任务状态，含 `is_terminal`、`is_success` 判断属性 |
| `SourceFlag` | 数据溯源标记：`actual`（真实）→ `filled`（补全）→ `rule`（规则）→ `api`（接口）→ `computed`（计算） |

**关键字段：`SourceFlag`**
让每个数字都可以追溯来源，下游模块可据此判断数据置信度。

---

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境（推荐 uv）
uv venv .venv

# 激活虚拟环境
# Windows PowerShell
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 安装依赖
uv pip install -e .
```

### 2. 配置数据库

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入真实数据库连接信息
```

`.env` 示例：
```ini
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=shaanxi_resilience

APP_ENV=dev
LOG_LEVEL=INFO
```

### 3. 初始化数据库

```bash
# 一键初始化（需要 PostgreSQL 已启动）
bash scripts/init_db.sh
```

建表顺序：DIM 层 → DWD 层 → DWS 层 → ADS 层

### 4. 运行流水线

```bash
# 完整流水线（M0→M1→M2→M3→M4→M5）
run-pipeline --scheme-id SCH_001 --start-date 2024-01-01 --end-date 2024-12-31

# 单独运行某个模块
run-m0 --scheme-id SCH_001 --start-date 2024-01-01 --end-date 2024-12-31
run-m1 --scheme-id SCH_001 --start-date 2024-01-01 --end-date 2024-12-31

# 选模块子集
run-pipeline --scheme-id SCH_001 --start-date 2024-01-01 --end-date 2024-12-31 --modules m0 m1 m2

# 覆盖重跑
run-pipeline --scheme-id SCH_001 --start-date 2024-01-01 --end-date 2024-12-31 --overwrite

# 出错时继续执行后续模块
run-pipeline --scheme-id SCH_001 --start-date 2024-01-01 --end-date 2024-12-31 --continue-on-error
```

### 5. 启动查询 API

```bash
run-query-api
```

- API 文档：http://localhost:8010/docs
- 健康检查：http://localhost:8010/health

---

## 配置文件说明

### configs/ 目录结构

| 文件 | 用途 |
|------|------|
| `base.yaml` | 所有环境共享的基础配置 |
| `db.yaml` | 数据库连接配置（支持环境变量占位） |
| `logging.yaml` | 日志配置 |
| `dev.yaml` | 开发环境配置（覆盖 base） |
| `prod.yaml` | 生产环境配置（覆盖 base） |
| `task.yaml` | 任务特定参数配置 |

### 配置读取优先级

```
.env（环境变量）
    ↑
dev.yaml / prod.yaml（环境特定）
    ↑
base.yaml（基础默认值）
```

---

## 数据仓库分层

| 层级 | 用途 | 例子 |
|------|------|------|
| ODS | 原始数据直接入库 | `ods_section_info` |
| DIM | 维表（不变/缓慢变化） | `dim_section_info`、`dim_capacity_rule` |
| DWD | 明细事实表（原子事实） | `dwd_scheme_section_map`、`dwd_od_path_map` |
| DWS | 轻度汇总事实表 | `dws_section_capacity_day`、`dws_impacted_od_flow_day` |
| ADS | 应用结果表（可直接消费） | `ads_od_diversion_plan`、`ads_toll_impact_result` |

### 数据流向全景

```
M0: ODS原始数据
    → dim_section_info（维表）
    → dwd_scheme_section_map（方案-路段映射）
    → dwd_od_path_map（OD路径映射）

M1: 读取 dwd_scheme_section_map + dim_section_info
    → dws_section_capacity_day（可用车道数 = lane_cnt - lane_occupied_cnt）

M2: 读取 M1 结果 + dim_od_info
    → dws_section_od_flow_day + dws_section_flow_day（带 SourceFlag）

M3: 读取 M2 结果
    → dws_impacted_od_flow_day（impact_ratio、impact_level）

M4: 读取 M3 结果 + dim_road_topology
    → dws_od_candidate_path（mileage_diff、fee_diff）
    → ads_od_diversion_plan（分流方案）

M5: 读取 M4 结果
    → ads_toll_impact_result（通行费增减）
    → ads_scheme_summary（方案汇总）
```

---

## 关键目录说明

### src/app/ - 应用核心基础设施

所有模块都依赖它，但不包含任何业务逻辑。

| 文件 | 职责 |
|------|------|
| `db.py` | SQLAlchemy engine / session 管理、连接池配置、PostGIS 检测 |
| `enums.py` | 全局枚举常量：ModuleCode / TaskStatus / SourceFlag 等 |
| `exceptions.py` | 统一异常类：`DatabaseError` / `PipelineError` / `BusinessRuleError` 等 |
| `logger.py` | 结构化日志配置，支持输出到文件和 stdout |
| `settings.py` | 从 `.env` + `configs/*.yaml` 加载配置，提供 `get_settings()` 单例 |

### src/common/ - 跨模块通用工具

各业务模块（M0~M5）都可以直接引用，不包含具体业务逻辑。

| 文件 | 职责 |
|------|------|
| `sql_runner.py` | SQL 文件加载、Jinja2 渲染、执行/查询封装 |
| `time_utils.py` | 日期时间工具：解析、生成批次号、日期范围等 |
| `validators.py` | 输入校验：scheme_id 格式、日期范围合法性等 |
| `file_loader.py` | 配置文件加载：YAML/JSON/CSV 等 |
| `postgis_utils.py` | PostGIS 扩展工具：几何计算、空间关系判断等 |

### src/jobs/ - 命令行任务入口

每个文件对应一个可独立执行的脚本。

| 文件 | 对应命令 |
|------|---------|
| `run_m0.py` | `run-m0` |
| `run_m1.py` | `run-m1` |
| `run_m2.py` | `run-m2` |
| `run_m3.py` | `run-m3` |
| `run_m4.py` | `run-m4` |
| `run_m5.py` | `run-m5` |
| `run_pipeline.py` | `run-pipeline` |

### src/services/ - 查询服务

通过 FastAPI 对外提供 HTTP API，查询离线批处理的结果数据。

```
离线批处理（jobs/）                    在线查询（services/）
┌─────────────────────────┐          ┌─────────────────────────┐
│  M0 → M1 → M2 → M3 →   │          │  FastAPI Query API      │
│  M4 → M5                │   落表   │  GET /api/v1/results/*  │
│                         │ ──────→ │  GET /api/v1/tasks/*    │
└─────────────────────────┘          └─────────────────────────┘
      数据写入 ADS 层                        读出给前端/调用方
```

### research/ - 研究与试验代码

| 目录 | 用途 |
|------|------|
| `research/m0` ~ `research/m5` | 各模块的研究试验（Notebook、临时脚本、探索性分析） |

**关键原则：**
- 不要把 `research/` 下的代码直接复用 到 `src/modules/`
- 先在 `research/` 里验证算法、确认逻辑，成熟后再迁移到 `src/` 工程化

### outputs/ - 临时输出目录

| 目录 | 用途 | 已在 .gitignore 中？ |
|------|------|--------------------|
| `outputs/logs/` | 运行日志 | ✓ |
| `outputs/exports/` | CSV/Excel 导出结果 | ✓ |
| `outputs/reports/` | 分析报告、图表 | ✓ |
| `outputs/temp/` | 临时中间文件 | ✓ |

### scripts/ - 运维辅助脚本

| 文件 | 用途 |
|------|------|
| `init_db.sh` | 一键初始化数据库：创建库 → 按顺序执行 DDL 建表 |
| `run_dev.sh` | 开发环境启动工具：一键 setup/运行模块/运行流水线/启动 API |
| `cron/example_crontab` | 定时任务配置示例（`crontab -e` 时参考） |

---

## 测试

### 运行测试

```bash
# 运行所有测试
pytest src/tests/ -v

# 运行单元测试
pytest src/tests/unit/ -v

# 运行特定模块
pytest src/tests/unit/test_enums.py -v

# 带覆盖率
pytest src/tests/ --cov=src --cov-report=html
```

### 测试内容建议

按模块分层补充：

| 层级 | 测试重点 |
|------|---------|
| **app/** | 数据库连接测试、配置加载、枚举边界值 |
| **common/** | `SqlRunner` 加载/渲染 SQL、文件加载、PostGIS 工具 |
| **repository/** | SQL 模板参数渲染、数据完整性校验 |
| **service/** | 业务流程编排、异常处理、日志输出 |
| **jobs/** | CLI 参数解析、退出码 |
| **services/** | API 端点、请求响应格式 |

---

## 常见问题

### shaanxi_resilience.egg-info/ 是什么？

Python 包安装后自动生成的**元数据目录**，不需要维护，也不应该提交到 Git。可以直接删除，下次重新 `pip install -e .` 会自动重建。

### SQL 视图（views/）在哪里？

目前项目中还没有 `sql/views/` 目录。视图（View）是预先写好的查询封装，介于"裸表"和"API 接口"之间的中间层。

当前项目选择把查询封装在 FastAPI Python 层而不是数据库视图，这样可以做参数校验、缓存、关联多表聚合后返回，未来方便扩展认证、限流等能力。

---

## 下一步建议

1. **补充 ODS 层 DDL**：当前只有 DIM 及以上的表结构，缺少 `ods_section_info` 等原始数据表的建表语句
2. **填充 DML 业务 SQL**：`sql/dml/m0/` 等目录下的 SQL 文件有大量 `TODO` 待填业务逻辑
3. **完善集成测试**：用测试数据库跑完整的 M0~M5 流水线，验证各层表都有输出

