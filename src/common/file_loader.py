"""
文件加载工具模块
提供各类文件加载功能，支持路径解析和格式转换
"""

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from src.app.exceptions import ConfigError
from src.app.logger import get_logger

logger = get_logger(__name__)


class FileLoader:
  """
  统一文件加载器，支持多种文件类型
  处理路径解析、编码和格式转换
  """

  def __init__(self, base_dir: str | Path | None = None):
    """
    初始化文件加载器

    Args:
      base_dir: 相对路径的基准目录（默认为当前目录）
    """
    self.base_dir = Path(base_dir) if base_dir else Path.cwd()

  def resolve_path(self, relative_path: str) -> Path:
    """
    将相对路径解析为绝对路径

    Args:
      relative_path: 相对于 base_dir 的路径

    Returns:
      绝对 Path 对象
    """
    path = Path(relative_path)
    if path.is_absolute():
      return path
    return self.base_dir / path

  def load_yaml(self, file_path: str) -> dict[str, Any]:
    """
    加载 YAML 文件

    Args:
      file_path: YAML 文件路径（相对或绝对）

    Returns:
      解析后的 YAML 内容（字典）

    Raises:
      ConfigError: 文件无法加载或解析时抛出
    """
    path = self.resolve_path(file_path)

    if not path.exists():
      raise ConfigError(f"YAML 文件未找到: {path}", config_key=str(path))

    try:
      with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
      logger.debug(f"已加载 YAML: {path}")
      return content or {}
    except yaml.YAMLError as e:
      raise ConfigError(f"YAML 解析失败: {e}", config_key=str(path))
    except Exception as e:
      raise ConfigError(f"YAML 加载失败: {e}", config_key=str(path))

  def load_json(self, file_path: str) -> dict[str, Any]:
    """
    加载 JSON 文件

    Args:
      file_path: JSON 文件路径

    Returns:
      解析后的 JSON 内容（字典）

    Raises:
      ConfigError: 文件无法加载或解析时抛出
    """
    path = self.resolve_path(file_path)

    if not path.exists():
      raise ConfigError(f"JSON 文件未找到: {path}", config_key=str(path))

    try:
      with open(path, encoding="utf-8") as f:
        content = json.load(f)
      logger.debug(f"已加载 JSON: {path}")
      return content
    except json.JSONDecodeError as e:
      raise ConfigError(f"JSON 解析失败: {e}", config_key=str(path))
    except Exception as e:
      raise ConfigError(f"JSON 加载失败: {e}", config_key=str(path))

  def load_text(self, file_path: str, encoding: str = "utf-8") -> str:
    """
    加载文本文件

    Args:
      file_path: 文本文件路径
      encoding: 文件编码

    Returns:
      文件内容字符串

    Raises:
      ConfigError: 文件无法加载时抛出
    """
    path = self.resolve_path(file_path)

    if not path.exists():
      raise ConfigError(f"文本文件未找到: {path}", config_key=str(path))

    try:
      with open(path, encoding=encoding) as f:
        content = f.read()
      logger.debug(f"已加载文本: {path}")
      return content
    except Exception as e:
      raise ConfigError(f"文本加载失败: {e}", config_key=str(path))

  def load_sql(self, file_path: str) -> str:
    """
    加载 SQL 文件

    Args:
      file_path: SQL 文件路径

    Returns:
      SQL 内容字符串
    """
    return self.load_text(file_path, encoding="utf-8")

  def save_yaml(self, file_path: str, data: dict[str, Any]) -> None:
    """
    将数据保存为 YAML 文件

    Args:
      file_path: 保存路径
      data: 待保存的数据
    """
    path = self.resolve_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
      yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    logger.debug(f"已保存 YAML: {path}")

  def save_json(self, file_path: str, data: dict[str, Any], indent: int = 2) -> None:
    """
    将数据保存为 JSON 文件

    Args:
      file_path: 保存路径
      data: 待保存的数据
      indent: JSON 缩进
    """
    path = self.resolve_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=indent)

    logger.debug(f"已保存 JSON: {path}")

  def save_text(self, file_path: str, content: str, encoding: str = "utf-8") -> None:
    """
    将文本内容保存到文件

    Args:
      file_path: 保存路径
      content: 文本内容
      encoding: 文件编码
    """
    path = self.resolve_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding=encoding) as f:
      f.write(content)

    logger.debug(f"已保存文本: {path}")

  def file_exists(self, file_path: str) -> bool:
    """检查文件是否存在"""
    return self.resolve_path(file_path).exists()

  def list_files(
    self,
    directory: str,
    pattern: str = "*",
    recursive: bool = False,
  ) -> list[Path]:
    """
    列出目录下匹配模式的所有文件

    Args:
      directory: 目录路径
      pattern: glob 模式
      recursive: 是否递归搜索

    Returns:
      匹配的文件路径列表
    """
    path = self.resolve_path(directory)

    if not path.exists() or not path.is_dir():
      return []

    if recursive:
      return list(path.rglob(pattern))
    else:
      return list(path.glob(pattern))


# 模块级便捷函数
_default_loader: Optional[FileLoader] = None


def get_file_loader() -> FileLoader:
  """获取或创建默认文件加载器"""
  global _default_loader
  if _default_loader is None:
    _default_loader = FileLoader()
  return _default_loader


def load_yaml(file_path: str) -> dict[str, Any]:
  """使用默认加载器加载 YAML 文件"""
  return get_file_loader().load_yaml(file_path)


def load_json(file_path: str) -> dict[str, Any]:
  """使用默认加载器加载 JSON 文件"""
  return get_file_loader().load_json(file_path)


def load_sql(file_path: str) -> str:
  """使用默认加载器加载 SQL 文件"""
  return get_file_loader().load_sql(file_path)


def load_text(file_path: str) -> str:
  """使用默认加载器加载文本文件"""
  return get_file_loader().load_text(file_path)
