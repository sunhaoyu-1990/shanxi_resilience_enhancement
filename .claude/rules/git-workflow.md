# Git Workflow
# 陕交控多路段改扩建韧性提升项目 Git 工作流

## 注意

本项目当前未启用 Git（.git 目录不存在），以下为未来启用 Git 时的工作流规范。

## Commit Message Format

```
<type>: <description>

<optional body>
```

Type 类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构（非功能、非 Bug 修复）
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具链相关
- `perf`: 性能优化
- `ci`: CI/CD 相关

示例：
```
feat(m0): 补充 ODS 层 DDL 建表语句
fix(m1): 修复通行能力计算逻辑
docs: 更新 README_USE_GUIDE.md
chore: 添加 .gitignore
```

## Pull Request Workflow

创建 PR 时：
1. 分析完整的提交历史（不仅仅是最新提交）
2. 使用 `git diff [base-branch]...HEAD` 查看所有变更
3. 起草全面的 PR 摘要
4. 包含带 TODO 的测试计划
5. 如果是新分支，使用 `-u` 参数推送

## Feature Implementation Workflow

### 1. 先计划
   - 使用 **planner** agent 创建实施方案
   - 识别依赖和风险
   - 分阶段推进

### 2. 模块开发顺序（每个模块必须按此顺序）
   1. 模块文档（`docs/`）
   2. 输入输出定义
   3. 表结构设计（`sql/ddl/`）
   4. SQL 原型（`sql/dml/`）
   5. Python 编排（`src/modules/`）
   6. 校验 SQL / 数据检查（`sql/checks/`）
   7. 联调
   8. 查询结果输出

### 3. TDD 方法
   - 使用 **tdd-guide** agent
   - 先写测试（RED）
   - 实现以通过测试（GREEN）
   - 重构（IMPROVE）
   - 验证 80%+ 覆盖率

### 4. 代码审查
   - 编写代码后立即使用 **code-reviewer** agent
   - 解决 CRITICAL 和 HIGH 问题
   - 尽可能修复 MEDIUM 问题

### 5. 提交与推送
   - 详细的提交消息
   - 遵循约定提交格式

## 开发总原则

1. 先文档，后代码
2. 先表结构与口径，后实现逻辑
3. 先最小可用链路，后增强能力
4. 先保证主链可跑通，后优化性能和抽象层次
5. 所有实现必须可审查、可复现、可迭代

## 绝对禁止事项

1. 禁止绕过项目文档直接新增未定义表结构
2. 禁止在正式目录中加入一次性实验脚本
3. 禁止把复杂业务逻辑硬编码在命令行入口文件中
4. 禁止把数据库连接、账号密码、服务器路径写死在代码里
5. 禁止新增无文档说明的字段、接口、任务
6. 禁止跨模块直接依赖未公开的私有中间表
7. 禁止生成"看起来完整但无法执行"的伪代码冒充正式实现
