# Security Guidelines
# 陕交控多路段改扩建韧性提升项目安全规范

## Mandatory Security Checks

在任何提交前，必须检查：
- [ ] 无硬编码密钥（API 密钥、密码、令牌）
- [ ] 所有用户输入已验证
- [ ] SQL 注入防护（参数化查询）
- [ ] XSS 防护（HTML 转义）
- [ ] CSRF 防护已启用
- [ ] 认证/授权已验证
- [ ] 所有端点有速率限制
- [ ] 错误消息不泄露敏感数据

## Secret Management

数据库连接、API 密钥等敏感信息必须通过环境变量配置：

```python
# NEVER: 硬编码密钥
DB_PASSWORD = "mysecretpassword123"

# ALWAYS: 环境变量
import os
from src.app.settings import get_settings

settings = get_settings()
db_password = settings.database.password

if not db_password:
    raise ConfigError("DB_PASSWORD not configured")
```

## SQL 注入防护

所有 SQL 执行必须使用参数化查询：

```python
# GOOD: 参数化查询
sql = """
    SELECT * FROM dim_section_info
    WHERE scheme_id = :scheme_id
      AND day BETWEEN :start_date AND :end_date
"""
params = {
    "scheme_id": scheme_id,
    "start_date": start_date,
    "end_date": end_date,
}
result = sql_runner.fetch_all(sql, params=params)

# BAD: 字符串拼接
sql = f"""
    SELECT * FROM dim_section_info
    WHERE scheme_id = '{scheme_id}'
"""
# 这会导致 SQL 注入！
```

## 数据库安全

- 数据库用户权限最小化
- 生产环境与开发环境使用不同的数据库用户
- 定期轮换数据库密码
- 所有数据库操作通过统一的 `db.py` 封装，不直接使用 psycopg

## 日志安全

- 日志中不记录密码、密钥等敏感信息
- 日志中截断 SQL 参数（或不记录）
- 在 `configs/logging.yaml` 中配置：

```yaml
logging:
  special:
    sql_execution:
      log_sql_params: false  # 生产环境设为 false
```

## 错误消息安全

错误消息不应泄露数据库结构、表名、字段名等敏感信息：

```python
# GOOD: 通用错误消息
try:
    result = sql_runner.fetch_all(sql, params=params)
except DatabaseError as e:
    logger.exception("Database operation failed")
    raise AppException("Database operation failed, please contact support")

# BAD: 泄露敏感信息
try:
    result = sql_runner.fetch_all(sql, params=params)
except DatabaseError as e:
    logger.exception(f"Database error: {e}")
    raise AppException(f"Error: {e}")  # 泄露了数据库错误详情
```

## Security Response Protocol

发现安全问题时：
1. 立即停止
2. 使用 **security-reviewer** agent
3. 在继续前修复 CRITICAL 问题
4. 轮换所有已暴露的密钥
5. 检查整个代码库是否有类似问题

## 项目特定安全注意事项

由于本项目处理高速公路收费数据，特别注意：
- OD 流量数据属于敏感数据
- 收费单元信息应按最小权限访问
- 分流方案等决策数据应限制访问
- 所有数据导出应记录审计日志
