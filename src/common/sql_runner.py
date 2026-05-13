"""
SQL 文件执行器模块
提供 SQL 文件加载、渲染和执行的工具
"""

import time
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.app.db import get_db_session, get_engine
from src.app.exceptions import DatabaseError
from src.app.logger import get_logger

logger = get_logger(__name__)


class SqlRunner:
  """
  SQL 执行器，支持加载、渲染和执行 SQL 文件
  使用 Jinja2 模板引擎支持参数化 SQL
  """

  def __init__(self, sql_dir: str | Path = "sql"):
    self.sql_dir = Path(sql_dir)
    self.jinja_env = Environment(
      loader=FileSystemLoader(str(self.sql_dir)),
      autoescape=False,
      trim_blocks=True,
      lstrip_blocks=True,
    )
    logger.debug(f"SQL 执行器已初始化，目录: {self.sql_dir}")

  def load_sql(self, relative_path: str) -> str:
    """
    从文件加载 SQL 内容

    Args:
      relative_path: 相对于 sql_dir 的路径

    Returns:
      SQL 内容字符串
    """
    file_path = self.sql_dir / relative_path
    if not file_path.exists():
      raise FileNotFoundError(f"SQL 文件未找到: {file_path}")

    with open(file_path, encoding="utf-8") as f:
      content = f.read()

    logger.debug(f"已加载 SQL 文件: {relative_path}")
    return content

  def render_sql(self, sql_text: str, params: dict[str, Any] | None = None) -> str:
    """
    使用 Jinja2 将参数渲染进 SQL 模板

    Args:
      sql_text: SQL 模板字符串
      params: 渲染参数

    Returns:
      渲染后的 SQL 字符串
    """
    if not params:
      return sql_text

    template = Template(sql_text)
    try:
      rendered = template.render(**params)
      return rendered
    except Exception as e:
      logger.error(f"SQL 模板渲染失败: {e}")
      raise DatabaseError(f"SQL 模板渲染失败: {e}")

  def execute_sql(
    self,
    sql_text: str,
    params: dict[str, Any] | None = None,
    session: Session | None = None,
    commit: bool = True,
  ) -> None:
    """
    执行 SQL 语句

    Args:
      sql_text: 待执行的 SQL 语句
      params: SQL 参数
      session: 使用的数据库会话（不提供则创建新会话）
      commit: 执行后是否提交
    """
    start_time = time.time()
    should_close_session = session is None

    try:
      if session is None:
        session = get_db_session().__enter__()

      logger.debug(f"正在执行 SQL: {sql_text[:200]}...")
      if params:
        logger.debug(f"参数: {params}")

      session.execute(text(sql_text), params or {})

      if commit:
        session.commit()

      duration_ms = (time.time() - start_time) * 1000
      logger.info(f"SQL 执行成功，耗时 {duration_ms:.2f}ms")

    except Exception as e:
      if session:
        session.rollback()
      logger.error(f"SQL 执行失败: {e}")
      raise DatabaseError(f"SQL 执行失败: {e}")

    finally:
      if should_close_session and session is not None:
        session.close()

  def fetch_all(
    self,
    sql_text: str,
    params: dict[str, Any] | None = None,
    session: Session | None = None,
  ) -> list[dict[str, Any]]:
    """
    执行 SELECT 查询并获取所有结果

    Args:
      sql_text: SELECT SQL 语句
      params: SQL 参数
      session: 使用的数据库会话

    Returns:
      结果行列表（每行为字典）
    """
    start_time = time.time()
    should_close_session = session is None

    try:
      if session is None:
        session = get_db_session().__enter__()

      logger.debug(f"正在查询 SQL: {sql_text[:200]}...")

      result = session.execute(text(sql_text), params or {})
      rows = [dict(row._mapping) for row in result.fetchall()]

      duration_ms = (time.time() - start_time) * 1000
      logger.debug(f"查询完成，获取 {len(rows)} 行，耗时 {duration_ms:.2f}ms")

      return rows

    except Exception as e:
      logger.error(f"SQL 查询失败: {e}")
      raise DatabaseError(f"SQL 查询失败: {e}")

    finally:
      if should_close_session and session is not None:
        session.close()

  def fetch_one(
    self,
    sql_text: str,
    params: dict[str, Any] | None = None,
    session: Session | None = None,
  ) -> Optional[dict[str, Any]]:
    """
    执行 SELECT 查询并获取一条结果

    Args:
      sql_text: SELECT SQL 语句
      params: SQL 参数
      session: 使用的数据库会话

    Returns:
      单条结果行（字典），无结果时返回 None
    """
    start_time = time.time()
    should_close_session = session is None

    try:
      if session is None:
        session = get_db_session().__enter__()

      logger.debug(f"正在查询单条 SQL: {sql_text[:200]}...")

      result = session.execute(text(sql_text), params or {})
      row = result.fetchone()

      duration_ms = (time.time() - start_time) * 1000
      if row:
        logger.debug(f"查询完成，获取 1 行，耗时 {duration_ms:.2f}ms")
        return dict(row._mapping)
      else:
        logger.info(f"查询完成，无结果，耗时 {duration_ms:.2f}ms")
        return None

    except Exception as e:
      logger.error(f"SQL fetch_one 失败: {e}")
      raise DatabaseError(f"SQL fetch_one 失败: {e}")

    finally:
      if should_close_session and session is not None:
        session.close()

  def run_sql_file(
    self,
    relative_path: str,
    params: dict[str, Any] | None = None,
    commit: bool = True,
  ) -> None:
    """
    加载并执行 SQL 文件

    Args:
      relative_path: 相对于 sql_dir 的路径
      params: 渲染参数
      commit: 执行后是否提交
    """
    sql_text = self.load_sql(relative_path)
    if params:
      sql_text = self.render_sql(sql_text, params)
    self.execute_sql(sql_text, commit=commit)

  def run_sql_file_with_session(
    self,
    relative_path: str,
    params: dict[str, Any] | None = None,
    session: Session | None = None,
    commit: bool = True,
  ) -> None:
    """
    使用指定会话加载并执行 SQL 文件

    Args:
      relative_path: 相对于 sql_dir 的路径
      params: 渲染参数
      session: 使用的数据库会话
      commit: 执行后是否提交
    """
    sql_text = self.load_sql(relative_path)
    if params:
      sql_text = self.render_sql(sql_text, params)
    self.execute_sql(sql_text, params=None, session=session, commit=commit)

  def execute_transaction(
    self,
    statements: list[str],
    params_list: list[dict[str, Any]] | None = None,
  ) -> None:
    """
    在事务中执行多条 SQL 语句

    Args:
      statements: SQL 语句列表
      params_list: 每条语句对应的参数列表
    """
    if params_list is None:
      params_list = [{} for _ in statements]

    with get_db_session() as session:
      try:
        for sql_text, params in zip(statements, params_list):
          session.execute(text(sql_text), params)
        session.commit()
        logger.info(f"事务已提交: 执行了 {len(statements)} 条语句")
      except Exception as e:
        session.rollback()
        logger.error(f"事务已回滚: {e}")
        raise DatabaseError(f"事务执行失败: {e}")


# 全局 SQL 执行器实例
_default_sql_runner: Optional[SqlRunner] = None


def get_sql_runner() -> SqlRunner:
  """获取或创建默认 SQL 执行器实例"""
  global _default_sql_runner
  if _default_sql_runner is None:
    _default_sql_runner = SqlRunner()
  return _default_sql_runner
