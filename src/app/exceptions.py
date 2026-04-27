"""
自定义异常类模块
为全项目提供结构化的异常处理体系
"""


class AppException(Exception):
  """所有应用异常的基类"""

  def __init__(self, message: str, details: dict | None = None):
    self.message = message
    self.details = details or {}
    super().__init__(self.message)

  def to_dict(self) -> dict:
    """将异常转换为字典，用于 API 响应"""
    return {
      "error_type": self.__class__.__name__,
      "message": self.message,
      "details": self.details,
    }


class ConfigError(AppException):
  """配置相关错误"""

  def __init__(self, message: str, config_key: str | None = None):
    details = {"config_key": config_key} if config_key else {}
    super().__init__(message, details)


class DatabaseError(AppException):
  """数据库操作错误"""

  def __init__(self, message: str, sql_state: str | None = None, table_name: str | None = None):
    details = {}
    if sql_state:
      details["sql_state"] = sql_state
    if table_name:
      details["table_name"] = table_name
    super().__init__(message, details)


class DataValidationError(AppException):
  """数据校验错误"""

  def __init__(
    self,
    message: str,
    field: str | None = None,
    value: any = None,
    constraint: str | None = None,
  ):
    details = {}
    if field:
      details["field"] = field
    if value is not None:
      details["value"] = str(value)
    if constraint:
      details["constraint"] = constraint
    super().__init__(message, details)


class BusinessRuleError(AppException):
  """业务规则违反错误"""

  def __init__(
    self,
    message: str,
    rule_id: str | None = None,
    context: dict | None = None,
  ):
    details = {}
    if rule_id:
      details["rule_id"] = rule_id
    if context:
      details["context"] = context
    super().__init__(message, details)


class ExternalServiceError(AppException):
  """外部服务通信错误"""

  def __init__(
    self,
    message: str,
    service_name: str | None = None,
    status_code: int | None = None,
    response_body: str | None = None,
  ):
    details = {}
    if service_name:
      details["service_name"] = service_name
    if status_code:
      details["status_code"] = status_code
    if response_body:
      details["response_body"] = response_body[:500]  # 截断过长响应
    super().__init__(message, details)


class PipelineError(AppException):
  """流水线执行错误"""

  def __init__(
    self,
    message: str,
    module: str | None = None,
    step: str | None = None,
    stage: str | None = None,
  ):
    details = {}
    if module:
      details["module"] = module
    if step:
      details["step"] = step
    if stage:
      details["stage"] = stage
    super().__init__(message, details)


class TableNotFoundError(DatabaseError):
  """表不存在错误"""

  def __init__(self, table_name: str):
    super().__init__(f"表不存在: {table_name}", table_name=table_name)


class DuplicateRecordError(DatabaseError):
  """重复记录错误"""

  def __init__(self, table_name: str, key_fields: dict):
    super().__init__(
      f"表中有重复记录: {table_name}",
      table_name=table_name,
    )
    self.details["key_fields"] = key_fields


class SchemaMismatchError(DatabaseError):
  """Schema 不匹配错误"""

  def __init__(self, table_name: str, expected_fields: list[str], actual_fields: list[str]):
    super().__init__(
      f"表 Schema 不匹配: {table_name}",
      table_name=table_name,
    )
    self.details["expected_fields"] = expected_fields
    self.details["actual_fields"] = actual_fields
