"""
Hive 数据库连接模块
用于连接远程 Hive 数据仓库
"""

import os
from contextlib import contextmanager
from typing import Any, Generator, Optional

from dotenv import load_dotenv

load_dotenv()

from src.app.logger import get_logger

logger = get_logger(__name__)


def _get_hive_config() -> dict[str, Any]:
    """获取 Hive 配置"""
    return {
        "host": os.getenv("HIVE_HOST", "localhost"),
        "port": int(os.getenv("HIVE_PORT", "10000")),
        "database": os.getenv("HIVE_DATABASE", "default"),
        "username": os.getenv("HIVE_USER", "hive"),
        "password": os.getenv("HIVE_PASSWORD", ""),
    }


def get_hive_connection():
    """
    获取 Hive 连接
    使用 PyHive 连接 HiveServer2
    """
    from pyhive import hive

    config = _get_hive_config()
    logger.info(
        f"Hive 连接配置",
        extra={
            "host": config["host"],
            "port": config["port"],
            "database": config["database"],
            "username": config["username"],
        },
    )

    # Hive 默认认证模式为 NONE，不需要密码
    # 如果需要 LDAP 认证，需要设置 auth="LDAP" 和密码
    auth = config.get("auth", "NONE")

    if auth == "LDAP":
        conn = hive.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            username=config["username"],
            password=config["password"],
            auth="LDAP",
        )
    else:
        conn = hive.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            username=config["username"],
        )
    return conn


@contextmanager
def get_hive_session() -> Generator:
    """
    Hive 会话上下文管理器
    使用方式:
        with get_hive_session() as cursor:
            cursor.execute("SELECT * FROM table LIMIT 10")
            results = cursor.fetchall()
    """
    conn = get_hive_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Hive 会话错误: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def test_hive_connection() -> bool:
    """测试 Hive 连接"""
    try:
        conn = get_hive_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0] == 1:
            logger.info("Hive 连接测试成功")
            return True
        return False
    except ImportError as e:
        logger.error(f"PyHive 未安装: {e}")
        logger.info("请运行: uv add pyhive sasl thrift-sasl")
        return False
    except Exception as e:
        logger.error(f"Hive 连接测试失败: {e}")
        return False


def list_tables(pattern: Optional[str] = None) -> list[str]:
    """
    列出数据库中的表

    Args:
        pattern: 表名过滤模式 (支持 SQL LIKE 语法, 如 'gstx_%')

    Returns:
        表名列表
    """
    with get_hive_session() as cursor:
        if pattern:
            cursor.execute(f"SHOW TABLES LIKE '{pattern}'")
        else:
            cursor.execute("SHOW TABLES")
        return [row[0] for row in cursor.fetchall()]


def describe_table(table_name: str) -> list[tuple]:
    """
    获取表结构

    Args:
        table_name: 表名

    Returns:
        字段信息列表 [(字段名, 类型, 注释), ...]
    """
    with get_hive_session() as cursor:
        cursor.execute(f"DESCRIBE {table_name}")
        return cursor.fetchall()


def show_create_table(table_name: str) -> str:
    """获取建表语句"""
    with get_hive_session() as cursor:
        cursor.execute(f"SHOW CREATE TABLE {table_name}")
        result = cursor.fetchone()
        return result[0] if result else ""


def get_table_count(table_name: str) -> int:
    """获取表行数"""
    with get_hive_session() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        result = cursor.fetchone()
        return result[0] if result else 0


def sample_query(
    table_name: str,
    limit: int = 10,
    columns: Optional[list[str]] = None,
) -> list[tuple]:
    """
    查询表样例数据

    Args:
        table_name: 表名
        limit: 返回行数
        columns: 指定列，None 表示所有列

    Returns:
        查询结果列表
    """
    col_str = ", ".join(columns) if columns else "*"
    with get_hive_session() as cursor:
        cursor.execute(f"SELECT {col_str} FROM {table_name} LIMIT {limit}")
        return cursor.fetchall()
