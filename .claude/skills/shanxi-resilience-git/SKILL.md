---
name: shanxi-resilience-git
description: 陕交控项目专用 Git 操作管理 - 规范化的提交、分支管理、GitHub 协作流程，包含常用 Git 操作命令模板和最佳实践
---

# 陕交控项目 Git 操作管理

## 1. 环境信息

**仓库地址**: `https://github.com/sunhaoyu-1990/shanxi_resilience_enhancement.git`

**分支策略**: `main` 为主分支，所有开发在 `main` 上进行

**主要开发者**: sunhaoyu

## 2. 常用操作命令模板

### 首次克隆
```bash
git clone https://github.com/sunhaoyu-1990/shanxi_resilience_enhancement.git
cd shanxi_resilience_enhancement
uv sync  # 重建虚拟环境
```

### 日常提交流程
```bash
# 1. 查看当前状态
git status

# 2. 添加文件（按模块添加，不使用 git add -A）
git add src/modules/m1_xxx/
git add sql/dml/m1/
git add docs/

# 3. 提交（使用约定格式）
git commit -m "feat(m1): 补充收费单元通行能力计算"

# 4. 推送（首次推送加 -u）
git push
```

### 查看变更
```bash
# 查看工作区变更
git status -s

# 查看文件差异
git diff src/modules/m1/service.py

# 查看提交历史
git log --oneline -10

# 查看某次提交的所有变更
git show HEAD --stat
```

## 3. Commit Message 规范

### 格式
```
<type>(<scope>): <description>

[optional body]
```

### Type 类型
| Type | 说明 | 适用场景 |
|------|------|---------|
| `feat` | 新功能 | 新增模块功能 |
| `fix` | Bug 修复 | 修复已知问题 |
| `refactor` | 重构 | 代码优化 |
| `docs` | 文档 | 文档更新 |
| `test` | 测试 | 测试用例 |
| `chore` | 构建/工具 | 工具链变更 |
| `perf` | 性能 | 性能优化 |
| `ci` | CI/CD | CI 配置 |

### Scope 范围
- `m0` ~ `m6`: 对应模块
- `sql`: SQL 文件变更
- `docs`: 文档变更
- `scripts`: 脚本变更
- `configs`: 配置变更

### 示例
```
feat(m1): 补充收费单元通行能力计算
fix(m2): 修复流量统计空值处理
docs: 更新数据表说明文档
chore: 添加 .gitignore 配置
refactor(sql): 重构 M3 交通影响分析 SQL
```

## 4. 禁止操作

### 绝对禁止
1. ~~`git push --force`~~ - 禁止强制推送
2. ~~`git add .` 或 `git add -A`~~ - 禁止全量添加
3. ~~提交 .env 文件~~ - 禁止提交敏感信息
4. ~~提交 .venv 目录~~ - 禁止提交虚拟环境
5. ~~提交 outputs/*.csv~~ - 禁止提交大数据文件
6. ~~提交 uv.lock~~ - 禁止提交锁文件

### 正确做法
- 敏感信息使用 `.env` + `.env.example`
- 大文件使用 `.gitignore` 排除
- 按模块、分层添加文件

## 5. GitHub 协作流程

### 克隆后设置
```bash
# 设置用户名和邮箱（项目级别）
git config user.name "sunhaoyu"
git config user.email "sunhaoyu@163.com"

# 设置默认分支
git branch -M main

# 检查远程仓库
git remote -v
```

### 同步最新代码
```bash
git fetch origin
git pull origin main
```

## 6. 大文件管理

### 已排除的文件类型
```
.venv/           # 虚拟环境（~150MB）
uv.lock          # 自动生成
outputs/*.csv    # 数据导出文件
outputs/logs/*.log  # 日志文件
research/data/*.pptx  # 大型 PPT
research/data/*.pdf   # 大型 PDF
*.log            # 所有日志文件
*.tmp            # 临时文件
```

### 提交前自检
```bash
# 检查将要提交的文件大小
git status -s

# 检查是否有大文件
git ls-files | xargs -I{} du -h "{}" 2>/dev/null | sort -h | tail -10
```

## 7. 错误恢复

### 撤销工作区修改
```bash
git checkout -- src/modules/m1/service.py
```

### 撤销暂存
```bash
git reset HEAD src/modules/m1/service.py
```

### 修改最后一次提交
```bash
# 添加遗漏的文件
git add missed_file.py
git commit --amend --no-edit

# 修改提交信息
git commit --amend -m "新的提交信息"
```

### 撤销最后一次提交（保留修改）
```bash
git reset --soft HEAD~1
```

## 8. 分支管理（本项目简化模式）

由于是单人开发，采用简化模式：

```
main (受保护)
  └── 所有开发直接在 main 进行
```

### 提交前检查清单
- [ ] `git status` 确认变更文件
- [ ] 不包含 .env / .venv / outputs/*.csv
- [ ] Commit message 符合规范
- [ ] 代码已通过审查（如有）

## 9. 安全提醒

### 不要提交的内容
- 数据库密码、API 密钥
- 个人本地配置
- 编译产物（__pycache__、.pyc）
- 大型二进制文件

### 已配置的安全措施
- `.gitignore` 已排除常见敏感文件
- `.env` 不在版本控制中
- `settings.local.json` 不在版本控制中

## 10. 常用 Git 别名（可选）

```bash
# 设置别名（可选）
git config --global alias.st "status -s"
git config --global alias.lg "log --oneline -10"
git config --global alias.co "checkout"
git config --global alias.cb "checkout -b"
```

## 快速参考卡

```bash
# 查看状态
git status

# 添加变更（按模块）
git add src/ sql/ docs/

# 提交
git commit -m "feat(module): description"

# 推送
git push

# 查看历史
git log --oneline -5
```