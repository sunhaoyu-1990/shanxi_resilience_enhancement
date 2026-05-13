"""
intervalgroup 修复失败记录器

将修复失败的原始记录增量写入本地 CSV 文件，
方便后续针对性调查和失败数据再次处理。

CSV 字段: enid, exid, intervalgroup, intervaltimegroup,
          envehicleid, exvehicleid, entime, extime,
          feevehicletype, envehicletype, failure_reason
"""

import csv
import os

from src.app.logger import get_logger

logger = get_logger(__name__)

# CSV header — matches the required failure record fields
FAILURE_CSV_HEADER = [
    "enid",
    "exid",
    "intervalgroup",
    "intervaltimegroup",
    "envehicleid",
    "exvehicleid",
    "entime",
    "extime",
    "feevehicletype",
    "envehicletype",
    "failure_reason",
]


class FixFailureLogger:
    """Incrementally write fix-failure records to a local CSV file"""

    def __init__(self, output_dir: str, version: str) -> None:
        """
        Args:
            output_dir: directory for failure CSV files
            version: version string (e.g. "202603")
        """
        os.makedirs(output_dir, exist_ok=True)
        self._file_path = os.path.join(
            output_dir, f"fix_failures_v{version}.csv"
        )
        need_header = not os.path.exists(self._file_path) or os.path.getsize(self._file_path) == 0
        self._file = open(self._file_path, "a", encoding="utf-8", newline="")
        self._writer = csv.writer(self._file)
        self._count = 0

        if need_header:
            self._writer.writerow(FAILURE_CSV_HEADER)
            self._file.flush()

        logger.info(f"Failure log: {self._file_path}")

    def log_failure(self, record: dict, reason: str) -> None:
        """
        Append one failure record to CSV

        Args:
            record: original CSV record dict
            reason: failure reason string (from IntervalFixResult.error)
        """
        row = [
            record.get("enid", ""),
            record.get("exid", ""),
            record.get("intervalgroup", ""),
            record.get("intervaltimegroup", ""),
            record.get("envehicleid", ""),
            record.get("exvehicleid", ""),
            record.get("entime", ""),
            record.get("extime", ""),
            record.get("feevehicletype", ""),
            record.get("envehicletype", ""),
            reason,
        ]
        self._writer.writerow(row)
        self._count += 1

        # Flush every 100 records to avoid data loss on crash
        if self._count % 100 == 0:
            self._file.flush()

    @property
    def count(self) -> int:
        """Total failures logged"""
        return self._count

    @property
    def file_path(self) -> str:
        """Output CSV file path"""
        return self._file_path

    def flush(self) -> None:
        """Flush pending writes to disk"""
        self._file.flush()

    def close(self) -> None:
        """Close the file"""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()
            logger.info(
                f"Failure log closed: {self._count} records written to {self._file_path}"
            )
