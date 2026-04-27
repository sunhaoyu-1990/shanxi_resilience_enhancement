"""
基于 pydantic-settings 的应用配置管理模块
从 YAML 文件和环境变量加载配置
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
  """数据库连接配置"""

  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
  )

  driver: str = Field(default="postgresql+psycopg", alias="DB_DRIVER")
  host: str = Field(default="127.0.0.1", alias="DB_HOST")
  port: int = Field(default=5432, alias="DB_PORT")
  user: str = Field(default="postgres", alias="DB_USER")
  password: str = Field(default="postgres", alias="DB_PASSWORD")
  database: str = Field(default="shaanxi_resilience", alias="DB_NAME")
  db_schema: str = Field(default="public")
  pool_size: int = Field(default=10)
  max_overflow: int = Field(default=20)
  echo: bool = Field(default=False)

  @property
  def connection_url(self) -> str:
    """构建 SQLAlchemy 连接 URL"""
    # 对密码进行 URL 编码，避免特殊字符导致解析错误
    encoded_password = quote(self.password, safe="")
    return (
      f"{self.driver}://{self.user}:{encoded_password}"
      f"@{self.host}:{self.port}/{self.database}"
    )


class Settings(BaseSettings):
  """应用配置"""

  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
  )

  # 应用配置
  app_name: str = Field(default="shaanxi-resilience")
  app_version: str = Field(default="0.1.0")
  app_env: str = Field(default="dev", alias="APP_ENV")
  debug: bool = Field(default=False)

  # 数据库配置
  database: DatabaseSettings = Field(default_factory=DatabaseSettings)

  # 路径配置
  project_root: Path = Field(default=Path("."))
  configs_dir: Path = Field(default=Path("configs"))
  sql_dir: Path = Field(default=Path("sql"))
  outputs_dir: Path = Field(default=Path("outputs"))

  # 日志配置
  log_level: str = Field(default="INFO", alias="LOG_LEVEL")

  # 流水线配置
  pipeline_mode: str = Field(default="full")
  pipeline_overwrite: bool = Field(default=False)

  # API 配置
  api_host: str = Field(default="0.0.0.0")
  api_port: int = Field(default=8010)
  api_reload: bool = Field(default=False)

  def get_config_path(self, config_name: str) -> Path:
    """获取配置文件路径"""
    return self.configs_dir / f"{config_name}.yaml"

  def load_yaml_config(self, config_name: str) -> dict[str, Any]:
    """加载 YAML 配置文件"""
    config_path = self.get_config_path(config_name)
    if config_path.exists():
      with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
    return {}

  def resolve_env_vars(self, config: dict[str, Any]) -> dict[str, Any]:
    """解析配置中的环境变量引用"""
    if isinstance(config, dict):
      return {k: self.resolve_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
      return [self.resolve_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
      env_var = config[2:-1]
      default = None
      if ":" in env_var:
        env_var, default = env_var.split(":", 1)
      return os.environ.get(env_var, default or config)
    return config


@lru_cache
def get_settings() -> Settings:
  """获取缓存的配置实例"""
  return Settings()
