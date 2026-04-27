"""
应用日志配置模块
提供全项目统一的日志记录器
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.app.settings import get_settings

# 全局日志缓存
_loggers: dict[str, logging.Logger] = {}


def setup_logging() -> None:
  """配置全项目日志"""
  settings = get_settings()

  # 创建日志目录
  log_dir = Path("outputs/logs")
  log_dir.mkdir(parents=True, exist_ok=True)

  # 配置根日志记录器
  root_logger = logging.getLogger()
  root_logger.setLevel(getattr(logging, settings.log_level.upper()))

  # 清除已有 handlers
  root_logger.handlers.clear()

  # 控制台 handler
  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setLevel(logging.INFO)
  console_formatter = logging.Formatter(
    "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
  )
  console_handler.setFormatter(console_formatter)
  root_logger.addHandler(console_handler)

  # 文件 handler
  log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
  file_handler = logging.FileHandler(log_file, encoding="utf-8")
  file_handler.setLevel(logging.DEBUG)
  file_formatter = logging.Formatter(
    "%(asctime)s | %(name)-30s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
  )
  file_handler.setFormatter(file_formatter)
  root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
  """
  获取或创建指定名称的日志记录器

  Args:
    name: 日志记录器名称，通常使用模块的 __name__

  Returns:
    配置好的日志记录器实例
  """
  if name not in _loggers:
    logger = logging.getLogger(name)
    _loggers[name] = logger
  return _loggers[name]


class LoggerMixin:
  """为类提供日志能力的 Mixin"""

  @property
  def logger(self) -> logging.Logger:
    """获取当前类的日志记录器"""
    name = f"{self.__class__.__module__}.{self.__class__.__name__}"
    return get_logger(name)


def log_sql_execution(logger: logging.Logger, sql: str, params: Optional[dict] = None) -> None:
  """记录 SQL 执行详情"""
  logger.debug(f"Executing SQL: {sql[:200]}...")
  if params:
    logger.debug(f"SQL parameters: {params}")


def log_execution_time(logger: logging.Logger, operation: str, duration_ms: float) -> None:
  """记录操作执行耗时"""
  if duration_ms > 5000:
    logger.warning(f"慢操作 [{operation}]: {duration_ms:.2f}ms")
  else:
    logger.debug(f"操作 [{operation}] 完成，耗时 {duration_ms:.2f}ms")


# 模块导入时初始化日志
try:
  setup_logging()
except Exception:
  # 如果配置加载失败，使用基础配置作为降级方案
  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
  )
