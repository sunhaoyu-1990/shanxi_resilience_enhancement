"""
CSV 高效流式读取模块

用于读取大型 CSV 文件（>10GB），按批返回记录。
使用 csv.reader + 列索引直接取值，避免 DictReader 的 dict 构造开销。
"""

import csv
from typing import Generator, Optional

from src.app.logger import get_logger

logger = get_logger(__name__)

# Default data directory on the server
DATA_DIR = "/home/shy/gaosu_data"

# File naming pattern: gstx_exit_with_min_fee{YYYYMM}.csv
FILE_PATTERN = "gstx_exit_with_min_fee{version}.csv"


def get_csv_path(version: str, data_dir: str = DATA_DIR) -> str:
    """
    Build CSV file path from version string

    Args:
        version: version string like "202603"
        data_dir: data directory path

    Returns:
        Full file path
    """
    import os
    filename = FILE_PATTERN.format(version=version)
    return os.path.join(data_dir, filename)


def iter_csv_batches(
    file_path: str,
    batch_size: int = 500_000,
    columns: Optional[list[str]] = None,
    encoding: str = "utf-8",
) -> Generator[list[dict], None, None]:
    """
    Stream-read CSV file in batches using csv.reader with index-based column extraction.
    Faster than DictReader for large files with many columns.

    Args:
        file_path: CSV file path
        batch_size: records per batch
        columns: column names to extract (None = all columns)
        encoding: file encoding

    Yields:
        Batches of records [{col: val, ...}, ...]
    """
    logger.info(f"Opening CSV: {file_path}")

    with open(file_path, "r", encoding=encoding) as f:
        # Read header to get column indices
        header = next(csv.reader(f))

        if columns:
            col_indices = {}
            for col in columns:
                if col in header:
                    col_indices[col] = header.index(col)
                else:
                    logger.warning(f"Column '{col}' not found in CSV header")
            missing = set(columns) - set(col_indices.keys())
            if missing:
                logger.warning(f"Missing columns: {missing}")
        else:
            col_indices = {col: idx for idx, col in enumerate(header)}

        logger.info(f"CSV columns ({len(col_indices)}): {list(col_indices.keys())}")

        reader = csv.reader(f)
        batch = []
        line_count = 0

        for row in reader:
            line_count += 1
            record = {col: row[idx] for col, idx in col_indices.items() if idx < len(row)}
            batch.append(record)

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

        logger.info(f"CSV read complete: {line_count:,} records")


def count_csv_lines(file_path: str, encoding: str = "utf-8") -> int:
    """
    Count total lines in CSV (excluding header) for progress display.
    Fast: reads raw bytes, counts newlines.

    Args:
        file_path: CSV file path
        encoding: file encoding

    Returns:
        Total record count
    """
    logger.info(f"Counting lines in {file_path}...")
    with open(file_path, "r", encoding=encoding) as f:
        # Skip header
        next(f)
        count = 0
        for _ in f:
            count += 1
    logger.info(f"Total records: {count:,}")
    return count
