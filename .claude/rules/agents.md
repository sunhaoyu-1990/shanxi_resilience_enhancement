# Agent Orchestration
# 陕交控多路段改扩建韧性提升项目专用
#
# 仅启用与本项目相关的 Agent

## Available Agents

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | 实施方案规划 | 复杂功能开发、多模块重构 |
| tdd-guide | 测试驱动开发 | 新功能、Bug 修复 |
| code-reviewer | 代码审查 | 编写代码后立即使用 |
| security-reviewer | 安全分析 | 提交前审查 |
| build-error-resolver | 构建错误修复 | 构建失败时 |
| refactor-cleaner | 代码清理 | 代码维护期 |
| doc-updater | 文档更新 | 更新文档时 |
| senior-data-engineer | 数据工程专家 | SQL 编写、ETL 设计、数据质量 |

## Immediate Agent Usage

无需用户提示，自动触发：
1. 复杂功能请求 - 使用 **planner** agent
2. 代码刚编写/修改 - 使用 **code-reviewer** agent
3. Bug 修复或新功能 - 使用 **tdd-guide** agent
4. 架构决策 - 使用 **senior-data-engineer** agent（优先）或 **architect** agent

## Parallel Task Execution

ALWAYS use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution
并行启动 3 个 agent：
1. Agent 1: M0 模块 SQL 安全审查
2. Agent 2: M1 模块性能检查
3. Agent 3: M2 模块类型检查

# BAD: Sequential when unnecessary
先 agent 1，再 agent 2，再 agent 3
```

## Multi-Perspective Analysis

对于复杂问题，使用分工审查：
- 事实审查（Factual reviewer）
- 资深数据工程师（Senior Data Engineer）
- 安全专家（Security expert）
- 一致性审查（Consistency reviewer）
- 冗余检查（Redundancy checker）
