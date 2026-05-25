# AGENTS.md

## 1. 角色定位
你正在参与“陕交控多路段改扩建韧性提升项目（一期）”后端算法工程开发。
你的工作目标不是泛化研究，而是围绕一期最小可用版本（MVP）主链路，协助完成工程化实现、文档整理、表结构设计、SQL 编写、离线任务开发与查询服务支持。

在开始工作前，请先阅读 `.Codex/memory/MEMORY.md` 了解项目状态、上下文和当前进展。

## 2. 当前项目边界
当前一期主链路模块固定为：

- M0 数据工程
- M1 通行能力评估
- M2 流量与OD迁移统计补全
- M3 交通影响分析
- M4 分流路径优化
- M5 通行费影响测算

当前阶段默认：
- 以统计、经验规则、工程化实现为主
- 不擅自扩展到未纳入一期范围的高级寻优、动态优化、完整效果评估
- 不擅自改动模块编号和边界

## 3. 工程技术约束
- Python + SQL 为主
- PostgreSQL + PostGIS
- SQLAlchemy 用于数据库连接、会话与事务管理
- 核心分析逻辑优先使用原生 SQL
- YAML 配置
- Org 文档（主文档）+ Markdown（使用指南）
- 离线批处理为主，查询服务为辅

## 4. 开发总原则
1. 先文档，后代码
2. 先表结构与口径，后实现逻辑
3. 先最小可用链路，后增强能力
4. 先保证主链可跑通，后优化性能和抽象层次
5. 所有实现必须可审查、可复现、可迭代

## 5. 绝对禁止事项
1. 禁止绕过项目文档直接新增未定义表结构
2. 禁止在正式目录中加入一次性实验脚本
3. 禁止把复杂业务逻辑硬编码在命令行入口文件中
4. 禁止把数据库连接、账号密码、服务器路径写死在代码里
5. 禁止新增无文档说明的字段、接口、任务
6. 禁止跨模块直接依赖未公开的私有中间表
7. 禁止生成“看起来完整但无法执行”的伪代码冒充正式实现

## 6. 代码组织规则
### Python
- 正式工程代码放在 `src/`
- 模块代码放在 `src/modules/`
- 任务入口放在 `src/jobs/`
- 查询服务放在 `src/services/`
- 公共工具放在 `src/common/`

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

### SQL
- DDL 放在 `sql/ddl/`
- DML 放在 `sql/dml/`
- 按模块拆分目录 `m0` ~ `m5`
- 校验 SQL 放在 `sql/checks/`

数据层组织：
```
sql/ddl/
├── dim/              # 维表层
├── dwd/              # 明细事实层
├── dws/              # 汇总事实层
└── ads/              # 应用结果层
```

### 文档
- 正式文档统一放在 `docs/`
- 主文档默认使用 Org
- 使用指南使用 Markdown（`README_USE_GUIDE.md`）
- 表口径、字段字典、接口文档必须同步维护

## 7. Python 编写规则
1. 所有正式函数必须有类型标注
2. 复杂逻辑拆分为函数，不允许堆在 main 中
3. 使用日志替代 print
4. 统一异常体系，不允许裸 `except`
5. 数据库访问优先通过统一的 db / repository / sql_runner 封装
6. 文件命名使用英文小写下划线
7. 不随意引入重型依赖

变量命名约定：
- 变量命名使用 camelCase
- 常量命名使用 UPPER_SNAKE_CASE
- 数据库字段使用 snake_case

## 8. SQL 编写规则
1. 核心统计逻辑优先用原生 SQL
2. 大 SQL 必须拆成可读的 CTE
3. 每个 SQL 文件顶部必须注明：
   - 作用
   - 输入表
   - 输出表
   - 粒度
   - 关键字段
4. 所有落表 SQL 必须说明主键粒度
5. 所有汇总逻辑必须明确时间口径
6. 对 `section_number`、`scheme_id`、`section_id`、`od_id`、`path_id` 等关键字段命名保持统一

SQL 文件头部注释模板：
```sql
-- ============================================================
-- M{N}: {SQL 文件功能描述}
-- ============================================================
-- 作用: {这个 SQL 做什么}
-- 输入表: {依赖的表名列表}
-- 输出表: {写入的表名}
-- 粒度: {一行代表什么，例如 section_id × day}
-- 关键字段: {关键字段列表，例如 section_id, day, ...}
-- ============================================================
```

## 9. 表结构与口径规则
1. 所有输出表必须先登记到《表口径总表》
2. 所有字段必须能在《字段字典》中找到解释
3. 所有时间字段必须写明：
   - 自然日 / 小时 / 批次
   - 是否施工期口径
4. 所有表必须写清楚：
   - 表用途
   - 粒度
   - 主键
   - 来源
   - 下游使用模块

## 10. 开发顺序规则
每个模块必须按以下顺序推进：
1. 模块文档
2. 输入输出定义
3. 表结构设计
4. SQL 原型
5. Python 编排
6. 校验 SQL / 数据检查
7. 联调
8. 查询结果输出

## 11. 生成内容时的要求
当被要求输出代码、SQL、文档时：
- 优先输出可直接使用的正式版本
- 不要只给抽象建议
- 明确文件路径
- 明确模块归属
- 明确输入输出
- 若有待确认项，明确标记 TODO，而不是私自假定

## 12. 任务完成标准
只有同时满足以下条件，才算完成：
- 文件位置明确
- 内容结构完整
- 能直接纳入项目仓库
- 与当前一期主链路一致
- 不与现有编号、模块边界冲突

## 13. 项目配置与规则使用

### 项目特定规则
在执行任务时，优先使用本项目 `.Codex/` 目录下的配置：
- `.Codex/rules/` - 项目特定编码规范
- `.Codex/memory/` - 项目状态与上下文

### 关键文档（优先查阅）
- `docs/数据表说明.md` - **所有表的权威说明**，含连接信息、数据字典、查询示例，新建表后必须同步更新
- `docs/业务逻辑记录.md` - 业务逻辑条目（BL-00x）
- `.Codex/memory/MEMORY.md` - 项目状态、已建立的开发模式、规则表汇总

### 新建维表的标准工作流（三件套）
每次新建一张维表，固定输出以下三个文件：

1. `sql/ddl/dim/create_dim_{name}.sql` — DDL 建表（含约束、索引、COMMENT）
2. `sql/dml/m{N}/insert_dim_{name}.sql` — 初始数据插入（含 ON CONFLICT）
3. `scripts/import_{name}.py` — 建表+插入+验证一体化脚本

执行后同步更新 `docs/数据表说明.md`。

### Python 导入脚本固定结构
参考 `scripts/import_toll_road.py`（最成熟的范例）：
- `_read_env()` → 从 `.env` 读 DB 配置
- `test_connection()` → 测试连接
- `create_table()` → DROP + 读取 DDL 文件执行 CREATE
- `import_data()` → `executemany` 批量插入
- `verify_data()` → 统计 + 质量检查（psycopg dict_row）

### Agent 使用
项目专用 Agent（优先使用）：
- `shanxi-resilience-data-engineer` - 数据工程：导入、建表、ETL、SQL
- `shanxi-resilience-path-analyzer` - 路网路径分析
- `shanxi-resilience-dim-manager` - 维表/规则表管理（新建、查询、更新）

通用 Agent（按需使用）：
- `planner` - 复杂功能规划
- `code-reviewer` - 代码审查
- `security-reviewer` - 安全分析
- `senior-data-engineer` - 数据工程专家

### Skill 使用
项目专用 Skill：
- `shanxi-resilience-table-creator` - 一键生成 DDL + DML + Python 脚本三件套
- `shanxi-resilience-sql-generator` - SQL 生成（DDL/DML/检查）
- `shanxi-resilience-data-importer` - 数据导入工具
- `shanxi-resilience-doc-updater` - 文档更新（含 数据表说明.md）
- `shanxi-resilience-pgrouting` - pgRouting 路网优化
- `shanxi-resilience-path-query` - 路径查询

### 注意事项
- 本项目未启用 Git（.git 目录不存在）
- 项目骨架已完整创建（109 个文件）
- 数据库连接：192.168.0.75:5432 / shanxi_resilience_db / sunhaoyu
- 后续工作重点：M1~M5 各模块 DML SQL 业务逻辑实现
