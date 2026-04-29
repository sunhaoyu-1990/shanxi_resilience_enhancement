"""
fix_failure_logger 的单元测试

测试覆盖：
1. FixFailureLogger — 创建、写入、关闭
2. CSV格式和header正确性
3. 文件追加模式
"""

import csv
import os
import tempfile
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.fix_failure_logger import (
    FixFailureLogger,
    FAILURE_CSV_HEADER,
)


class TestFixFailureLogger:
    """修复失败记录器测试"""

    def test_create_with_header(self):
        """新建文件自动写header"""
        tmpdir = tempfile.mkdtemp()
        logger = FixFailureLogger(tmpdir, "202603")

        # File should exist with header row
        assert os.path.exists(logger.file_path)
        logger.close()

        with open(logger.file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == FAILURE_CSV_HEADER

    def test_log_failure_writes_row(self):
        """写入一条失败记录"""
        tmpdir = tempfile.mkdtemp()
        logger = FixFailureLogger(tmpdir, "202603")

        record = {
            "enid": "E001",
            "exid": "X001",
            "intervalgroup": "A|B|C",
            "intervaltimegroup": "2026-03-15 10:00:00|2026-03-15 10:10:00",
            "envehicleid": "V123",
            "exvehicleid": "V456",
            "entime": "2026-03-15 09:50:00",
            "extime": "2026-03-15 10:20:00",
        }
        logger.log_failure(record, "path_fill_failed:A->B")
        logger.close()

        with open(logger.file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)

        assert row[0] == "E001"
        assert row[1] == "X001"
        assert row[2] == "A|B|C"
        assert row[3] == "2026-03-15 10:00:00|2026-03-15 10:10:00"
        assert row[4] == "V123"
        assert row[5] == "V456"
        assert row[6] == "2026-03-15 09:50:00"
        assert row[7] == "2026-03-15 10:20:00"
        assert row[8] == "path_fill_failed:A->B"

    def test_log_multiple_failures(self):
        """写入多条失败记录"""
        tmpdir = tempfile.mkdtemp()
        logger = FixFailureLogger(tmpdir, "202603")

        for i in range(5):
            logger.log_failure(
                {"enid": f"E{i}", "exid": f"X{i}",
                 "intervalgroup": "", "intervaltimegroup": "",
                 "envehicleid": "", "exvehicleid": "",
                 "entime": "", "extime": ""},
                f"reason_{i}",
            )
        logger.close()

        assert logger.count == 5

        with open(logger.file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # header + 5 data rows
        assert len(rows) == 6

    def test_missing_fields_default_empty(self):
        """缺失字段默认空字符串"""
        tmpdir = tempfile.mkdtemp()
        logger = FixFailureLogger(tmpdir, "202603")

        # Only provide enid, missing everything else
        logger.log_failure({"enid": "E1"}, "some_error")
        logger.close()

        with open(logger.file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)

        assert row[0] == "E1"
        assert row[1] == ""  # exid missing
        assert row[8] == "some_error"

    def test_append_mode_no_duplicate_header(self):
        """追加模式不重复写header"""
        tmpdir = tempfile.mkdtemp()

        # First session
        logger1 = FixFailureLogger(tmpdir, "202603")
        logger1.log_failure({"enid": "E1"}, "err1")
        logger1.close()

        # Second session — same file
        logger2 = FixFailureLogger(tmpdir, "202603")
        logger2.log_failure({"enid": "E2"}, "err2")
        logger2.close()

        with open(logger2.file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # 1 header + 2 data rows, no duplicate header
        assert len(rows) == 3
        assert rows[0] == FAILURE_CSV_HEADER
        assert rows[1][0] == "E1"
        assert rows[2][0] == "E2"

    def test_count_property(self):
        """count属性跟踪写入数量"""
        tmpdir = tempfile.mkdtemp()
        logger = FixFailureLogger(tmpdir, "202603")

        assert logger.count == 0
        logger.log_failure({"enid": "E1"}, "err")
        assert logger.count == 1
        logger.log_failure({"enid": "E2"}, "err")
        assert logger.count == 2
        logger.close()

    def test_version_in_filename(self):
        """版本号出现在文件名中"""
        tmpdir = tempfile.mkdtemp()
        logger = FixFailureLogger(tmpdir, "202604")
        assert "202604" in logger.file_path
        assert "fix_failures_v202604.csv" in logger.file_path
        logger.close()

    def test_output_dir_created(self):
        """输出目录不存在时自动创建"""
        tmpdir = tempfile.mkdtemp()
        nested_dir = os.path.join(tmpdir, "sub", "dir")
        logger = FixFailureLogger(nested_dir, "202603")
        assert os.path.isdir(nested_dir)
        logger.close()
