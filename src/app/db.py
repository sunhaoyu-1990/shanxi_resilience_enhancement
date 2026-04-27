"""
使用 SQLAlchemy 进行数据库连接和会话管理的模块
提供 engine、session factory 和连接工具函数
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.app.settings import get_settings
from src.app.logger import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
  """获取或创建 SQLAlchemy engine"""
  global _engine
  if _engine is None:
    settings = get_settings()
    db_config = settings.database

    _engine = create_engine(
      url=db_config.connection_url,
      poolclass=QueuePool,
      pool_size=db_config.pool_size,
      max_overflow=db_config.max_overflow,
      pool_pre_ping=True,
      pool_recycle=3600,
      echo=db_config.echo,
      query_cache_size=12000,
    )
    logger.info(
      "数据库引擎已创建",
      extra={
        "host": db_config.host,
        "port": db_config.port,
        "database": db_config.database,
        "db_schema": db_config.db_schema,
      },
    )
  return _engine


def get_session_factory() -> sessionmaker:
  """获取或创建 session factory"""
  global _SessionFactory
  if _SessionFactory is None:
    engine = get_engine()
    _SessionFactory = sessionmaker(
      bind=engine,
      autocommit=False,
      autoflush=False,
      expire_on_commit=False,
    )
  return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
  """数据库会话上下文管理器"""
  session_factory = get_session_factory()
  session = session_factory()
  try:
    yield session
    session.commit()
  except Exception as e:
    session.rollback()
    logger.error(f"数据库会话错误: {e}")
    raise
  finally:
    session.close()


def get_db() -> Generator[Session, None, None]:
  """FastAPI 依赖注入的数据库会话"""
  session_factory = get_session_factory()
  session = session_factory()
  try:
    yield session
    session.commit()
  except Exception as e:
    session.rollback()
    raise
  finally:
    session.close()


def test_connection() -> bool:
  """测试数据库连接"""
  try:
    engine = get_engine()
    with engine.connect() as conn:
      result = conn.execute(text("SELECT 1"))
      if result.scalar() == 1:
        logger.info("数据库连接测试成功")
        return True
    return False
  except Exception as e:
    logger.error(f"数据库连接测试失败: {e}")
    return False


def check_postgis() -> bool:
  """检查 PostGIS 扩展是否可用"""
  try:
    engine = get_engine()
    with engine.connect() as conn:
      result = conn.execute(text("SELECT PostGIS_Version()"))
      version = result.scalar()
      if version:
        logger.info(f"PostGIS 版本: {version}")
        return True
    return False
  except Exception as e:
    logger.warning(f"PostGIS 不可用: {e}")
    return False


def dispose_engine() -> None:
  """关闭引擎并释放所有连接"""
  global _engine, _SessionFactory
  if _engine is not None:
    _engine.dispose()
    _engine = None
    _SessionFactory = None
    logger.info("数据库引擎已释放")
