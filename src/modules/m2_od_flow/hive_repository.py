"""
Hive 数据访问模块

用于从 Hive 表读取收费单元数据
"""

import json
from typing import Generator, Optional

from src.app.hive import get_hive_session, get_hive_connection
from src.app.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# 常量
# ============================================================================

DEFAULT_TABLE = "gstx_exit_with_min_fee202603"
DEFAULT_DATABASE = "dbbase2026"
DEFAULT_BATCH_SIZE = 10000


# ============================================================================
# 数据读取
# ============================================================================


def read_sample_from_hive(
    table: str = DEFAULT_TABLE,
    database: str = DEFAULT_DATABASE,
    limit: int = 100,
    columns: Optional[list[str]] = None,
) -> list[dict]:
    """
    从 Hive 表读取样例数据

    Args:
        table: 表名
        database: 数据库名
        limit: 返回行数
        columns: 要读取的列，None 表示所有列

    Returns:
        记录列表
    """
    if columns:
        col_str = ", ".join(columns)
        sql = f"SELECT {col_str} FROM {database}.{table} LIMIT {limit}"
    else:
        sql = f"SELECT * FROM {database}.{table} LIMIT {limit}"

    logger.info(f"Reading sample from Hive: {sql}")

    with get_hive_session() as cursor:
        cursor.execute(sql)
        columns_meta = [desc[0] for desc in cursor.description]

        results = []
        for row in cursor.fetchall():
            record = dict(zip(columns_meta, row))
            results.append(record)

    logger.info(f"Read {len(results)} records from Hive")
    return results


def read_batch_from_hive(
    table: str = DEFAULT_TABLE,
    database: str = DEFAULT_DATABASE,
    batch_size: int = DEFAULT_BATCH_SIZE,
    offset: int = 0,
    columns: Optional[list[str]] = None,
    where_clause: Optional[str] = None,
) -> list[dict]:
    """
    从 Hive 表读取一批数据

    Args:
        table: 表名
        database: 数据库名
        batch_size: 每批大小
        offset: 起始偏移
        columns: 要读取的列
        where_clause: WHERE 条件

    Returns:
        记录列表
    """
    if columns:
        col_str = ", ".join(columns)
        sql = f"SELECT {col_str} FROM {database}.{table}"
    else:
        sql = f"SELECT * FROM {database}.{table}"

    if where_clause:
        sql += f" WHERE {where_clause}"

    sql += f" LIMIT {batch_size} OFFSET {offset}"

    logger.info(f"Reading batch from Hive: offset={offset}, size={batch_size}")

    with get_hive_session() as cursor:
        cursor.execute(sql)
        columns_meta = [desc[0] for desc in cursor.description]

        results = []
        for row in cursor.fetchall():
            record = dict(zip(columns_meta, row))
            results.append(record)

    return results


def iter_hive_batches(
    table: str = DEFAULT_TABLE,
    database: str = DEFAULT_DATABASE,
    batch_size: int = DEFAULT_BATCH_SIZE,
    columns: Optional[list[str]] = None,
    where_clause: Optional[str] = None,
) -> Generator[list[dict], None, None]:
    """
    迭代读取 Hive 表的所有批次

    Args:
        table: 表名
        database: 数据库名
        batch_size: 每批大小
        columns: 要读取的列
        where_clause: WHERE 条件

    Yields:
        每批记录列表
    """
    offset = 0

    while True:
        batch = read_batch_from_hive(
            table=table,
            database=database,
            batch_size=batch_size,
            offset=offset,
            columns=columns,
            where_clause=where_clause,
        )

        if not batch:
            break

        yield batch
        offset += batch_size


def get_total_count(
    table: str = DEFAULT_TABLE,
    database: str = DEFAULT_DATABASE,
    where_clause: Optional[str] = None,
) -> int:
    """
    获取表的总记录数

    Args:
        table: 表名
        database: 数据库名
        where_clause: WHERE 条件

    Returns:
        记录总数
    """
    sql = f"SELECT COUNT(*) AS cnt FROM {database}.{table}"

    if where_clause:
        sql += f" WHERE {where_clause}"

    with get_hive_session() as cursor:
        cursor.execute(sql)
        result = cursor.fetchone()
        return result[0] if result else 0


# ============================================================================
# 验证输出
# ============================================================================


def save_fix_results_to_json(
    results: list,
    output_path: str,
) -> None:
    """
    保存修复结果到 JSON 文件

    Args:
        results: 修复结果列表
        output_path: 输出文件路径
    """
    output_data = []

    for result in results:
        if hasattr(result, "to_dict"):
            output_data.append(result.to_dict())
        else:
            output_data.append(result)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(results)} results to {output_path}")


# ============================================================================
# 抽样读取（带条件）
# ============================================================================


def read_sample_with_filter(
    filter_expr: str,
    table: str = DEFAULT_TABLE,
    database: str = DEFAULT_DATABASE,
    limit: int = 100,
) -> list[dict]:
    """
    读取满足条件的样例数据

    Args:
        filter_expr: 过滤表达式，如 "SIZE(SPLIT(intervalgroup, '|')) > 3"
        table: 表名
        database: 数据库名
        limit: 返回行数

    Returns:
        记录列表
    """
    # 使用子查询先过滤，再取样
    sql = f"""
        SELECT *
        FROM (
            SELECT *,
                   SIZE(SPLIT(intervalgroup, '\\\\|')) as section_cnt
            FROM {database}.{table}
            WHERE {filter_expr}
        ) t
        LIMIT {limit}
    """

    logger.info(f"Reading filtered sample: {filter_expr}")

    with get_hive_session() as cursor:
        cursor.execute(sql)
        columns_meta = [desc[0] for desc in cursor.description]

        results = []
        for row in cursor.fetchall():
            record = dict(zip(columns_meta, row))
            results.append(record)

    return results
