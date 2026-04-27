# Testing Requirements
# 陕交控多路段改扩建韧性提升项目测试规范

## Minimum Test Coverage: 80%

测试类型（全部需要）：
1. **单元测试** - 单个函数、工具、组件
2. **集成测试** - API 端点、数据库操作
3. **SQL 校验测试** - 数据质量校验、值范围检查

## Test-Driven Development

### 对于 Python 代码

强制工作流：
1. 先写测试（RED）
2. 运行测试 - 应该失败
3. 写最小实现（GREEN）
4. 运行测试 - 应该通过
5. 重构（IMPROVE）
6. 验证覆盖率（80%+）

### 对于 SQL 代码

对于每个 DML SQL 文件，应先写对应的 `checks/` SQL 来验证结果：
1. 写数据质量检查 SQL（`sql/checks/m{N}/`）
2. 写业务逻辑 SQL（`sql/dml/m{N}/`）
3. 运行检查 SQL 验证结果

## 测试重点

### 单元测试重点

| 组件 | 测试内容 |
|------|---------|
| `src/app/enums.py` | 枚举值、属性方法 |
| `src/common/time_utils.py` | 日期解析、批次号生成 |
| `src/common/validators.py` | 输入校验 |
| `src/common/sql_runner.py` | SQL 加载、渲染、执行 |

### 集成测试重点

| 层级 | 测试内容 |
|------|---------|
| Repository 层 | SQL 模板参数渲染、数据完整性 |
| Service 层 | 业务流程编排、异常处理 |
| Query API | 端点、请求响应格式 |
| SQL 层 | 主键唯一性、必填字段非空、值范围合理 |

## SQL 校验检查表

每个模块的 `checks/` SQL 应包含：

- [ ] 主键唯一性检查
- [ ] 必填字段非空检查
- [ ] 枚举值在规定范围内
- [ ] 数值字段合理（例如 `lane_cnt > 0`）
- [ ] 日期范围有效（`start_date <= end_date`）
- [ ] 外键引用完整性
- [ ] 业务逻辑正确性（例如 `available_lane_cnt = lane_cnt - lane_occupied_cnt`）

## Troubleshooting Test Failures

1. 使用 **tdd-guide** agent
2. 检查测试隔离
3. 验证 mock 是否正确
4. 修复实现，而不是测试（除非测试错了）

## Agent Support

- **tdd-guide** - 新功能时主动使用，强制先写测试
- **senior-data-engineer** - SQL 校验和数据质量问题
