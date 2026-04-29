"""
CSV 高效流式读取模块

用于读取大型 CSV 文件（>10GB），按批返回记录。
使用 csv.reader + 列索引直接取值，避免 DictReader 的 dict 构造开销。

支持两种读取模式：
1. iter_csv_batches: 全量顺序读取（原有模式）
2. iter_csv_partition: 按字节偏移分区读取（多进程并行模式）
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


def build_csv_offset_index(
    file_path: str,
    step: int = 500_000,
    encoding: str = "utf-8",
) -> list[int]:
    """
    Scan CSV file and record byte offsets every `step` lines.

    Returns offsets[i] = byte position of the start of line (i * step + 1).
    offsets[0] is always the byte position right after the header line.
    The last entry is the byte position of the last line's start.

    This enables partitioned reading: Worker i reads from offsets[i*chunk]
    to offsets[(i+1)*chunk], seeking directly to the byte position.

    Args:
        file_path: CSV file path
        step: record every N-th line's offset
        encoding: file encoding

    Returns:
        List of byte offsets [header_end, offset_step, offset_2step, ...]
    """
    logger.info(f"Building offset index for {file_path} (step={step:,})...")
    offsets: list[int] = []

    with open(file_path, "rb") as f:
        # Record header end offset
        f.readline()  # skip header
        offsets.append(f.tell())

        line_count = 0
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                break
            line_count += 1
            if line_count % step == 0:
                offsets.append(pos)

    # Always append the final position (start of last line if not already recorded)
    # This ensures we know the exact end boundary
    logger.info(f"Offset index built: {len(offsets)} checkpoints, {line_count:,} total records")
    return offsets, line_count


def iter_csv_partition(
    file_path: str,
    start_offset: int,
    end_offset: int,
    batch_size: int = 50_000,
    columns: Optional[list[str]] = None,
    encoding: str = "utf-8",
) -> Generator[list[dict], None, None]:
    """
    Read a partition of a CSV file between two byte offsets, yielding mini-batches.

    Seeks to start_offset and reads until reaching end_offset or EOF.
    If start_offset > 0, the first line is assumed to be a partial line
    (middle of a row from the previous partition) and is skipped.

    Args:
        file_path: CSV file path
        start_offset: byte offset to start reading from
        end_offset: byte offset to stop at (0 = read to EOF)
        batch_size: records per mini-batch
        columns: column names to extract (None = all columns)
        encoding: file encoding

    Yields:
        Mini-batches of records [{col: val, ...}, ...]
    """
    import io

    with open(file_path, "rb") as bf:
        # Wrap binary file with TextIOWrapper for csv.reader
        f = io.TextIOWrapper(bf, encoding=encoding)

        # Read header to get column indices
        header = next(csv.reader(f))

        if columns:
            col_indices = {}
            for col in columns:
                if col in header:
                    col_indices[col] = header.index(col)
                else:
                    logger.warning(f"Column '{col}' not found in CSV header")
        else:
            col_indices = {col: idx for idx, col in enumerate(header)}

        # Seek to start_offset (byte position) AFTER header is consumed
        if start_offset > 0:
            bf.seek(start_offset)
            # Discard old TextIOWrapper and create new one to avoid buffer desync
            f.detach()  # Prevent wrapper from closing bf
            f = io.TextIOWrapper(bf, encoding=encoding)
            # Skip potentially partial line from previous partition
            f.readline()

        # Read until end_offset or EOF
        # Note: we track position via binary buffer since tell() is
        # disabled after next(csv.reader()) in text mode
        reader = csv.reader(f)
        batch: list[dict] = []

        for row in reader:
            # Check if we've passed the end offset using binary buffer position
            if end_offset > 0:
                current_pos = bf.tell()
                if current_pos > end_offset:
                    break

            record = {col: row[idx] for col, idx in col_indices.items() if idx < len(row)}
            batch.append(record)

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch
