"""
csv_reader 的单元测试

测试覆盖：
1. get_csv_path — 路径拼接
2. iter_csv_batches — 流式分批读取
3. count_csv_lines — 行数统计
"""

import os
import tempfile
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.csv_reader import (
    get_csv_path,
    iter_csv_batches,
    iter_csv_partition,
    count_csv_lines,
    build_csv_offset_index,
    DATA_DIR,
    FILE_PATTERN,
)


# ============================================================================
# get_csv_path
# ============================================================================

class TestGetCsvPath:
    """CSV路径拼接测试"""

    def test_default_data_dir(self):
        """默认数据目录"""
        result = get_csv_path("202603")
        expected = os.path.join(DATA_DIR, FILE_PATTERN.format(version="202603"))
        assert result == expected

    def test_custom_data_dir(self):
        """自定义数据目录"""
        result = get_csv_path("202604", data_dir="/tmp/data")
        expected = os.path.join("/tmp/data", "gstx_exit_with_min_fee202604.csv")
        assert result == expected

    def test_version_in_filename(self):
        """版本号正确出现在文件名中"""
        result = get_csv_path("202512")
        assert "202512" in result
        assert "gstx_exit_with_min_fee202512.csv" in result


# ============================================================================
# iter_csv_batches
# ============================================================================

class TestIterCsvBatches:
    """CSV流式分批读取测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        """Write CSV content to temp file and return path"""
        path = os.path.join(tmpdir, "test.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_read_all_columns(self):
        """不指定columns时返回所有列"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b,c\n1,2,3\n4,5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=10))
        assert len(batches) == 1
        assert len(batches[0]) == 2
        assert batches[0][0] == {"a": "1", "b": "2", "c": "3"}
        assert batches[0][1] == {"a": "4", "b": "5", "c": "6"}

    def test_read_selected_columns(self):
        """指定columns时只返回指定列"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "enid,exid,intervalgroup,other\nE1,X1,A|B|C,foo\nE2,X2,D|E|F,bar\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(
            path, batch_size=10, columns=["enid", "exid", "intervalgroup"]
        ))
        assert len(batches) == 1
        record = batches[0][0]
        assert "enid" in record
        assert "exid" in record
        assert "intervalgroup" in record
        assert "other" not in record

    def test_multiple_batches(self):
        """数据量超过batch_size时分成多批"""
        tmpdir = tempfile.mkdtemp()
        lines = ["x,y\n"] + [f"{i},{i*2}\n" for i in range(10)]
        csv_content = "".join(lines)
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=3))
        assert len(batches) == 4  # 3+3+3+1
        assert len(batches[0]) == 3
        assert len(batches[-1]) == 1

    def test_empty_csv(self):
        """只有表头的空CSV"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b,c\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=10))
        assert len(batches) == 0

    def test_missing_columns_skipped(self):
        """请求不存在的列时跳过，不报错"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(
            path, batch_size=10, columns=["a", "nonexistent"]
        ))
        assert len(batches) == 1
        record = batches[0][0]
        assert "a" in record
        assert "nonexistent" not in record

    def test_single_record(self):
        """单条记录"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "enid,exid\nE1,X1\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=100))
        assert len(batches) == 1
        assert len(batches[0]) == 1
        assert batches[0][0]["enid"] == "E1"

    def test_large_batch_size(self):
        """batch_size大于记录数时返回单批"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "x\n1\n2\n3\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=1_000_000))
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_chinese_content(self):
        """中文内容正确读取"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "name,value\n测试,123\n数据,456\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=10))
        assert batches[0][0]["name"] == "测试"
        assert batches[0][0]["value"] == "123"


# ============================================================================
# count_csv_lines
# ============================================================================

class TestCountCsvLines:
    """CSV行数统计测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        """Write CSV content to temp file and return path"""
        path = os.path.join(tmpdir, "count_test.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_count_with_header(self):
        """有表头时不计入行数"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n3,4\n5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        result = count_csv_lines(path)
        assert result == 3

    def test_count_only_header(self):
        """只有表头返回0"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b,c\n"
        path = self._write_csv(tmpdir, csv_content)

        result = count_csv_lines(path)
        assert result == 0

    def test_count_single_record(self):
        """单条记录返回1"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "x\n1\n"
        path = self._write_csv(tmpdir, csv_content)

        result = count_csv_lines(path)
        assert result == 1

    def test_count_many_records(self):
        """多行记录正确统计"""
        tmpdir = tempfile.mkdtemp()
        lines = ["x\n"] + [f"{i}\n" for i in range(100)]
        csv_content = "".join(lines)
        path = self._write_csv(tmpdir, csv_content)

        result = count_csv_lines(path)
        assert result == 100


# ============================================================================
# build_csv_offset_index
# ============================================================================


class TestBuildCsvOffsetIndex:
    """CSV偏移索引构建测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        """Write CSV content to temp file and return path"""
        path = os.path.join(tmpdir, "offset_test.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_basic_offset_index(self):
        """基本偏移索引构建"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n3,4\n5,6\n7,8\n9,10\n"
        path = self._write_csv(tmpdir, csv_content)

        offsets = build_csv_offset_index(path, step=2)
        # Should have: header_end_offset, offset at line 2, offset at line 4
        assert len(offsets) >= 2  # at least header_end + one checkpoint
        assert offsets[0] > 0  # header_end offset

    def test_offset_index_fewer_than_step(self):
        """记录数少于step时只有header_end"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n"
        path = self._write_csv(tmpdir, csv_content)

        offsets = build_csv_offset_index(path, step=100)
        # Only header offset, no checkpoint
        assert len(offsets) == 1

    def test_offset_index_increasing(self):
        """偏移量递增"""
        tmpdir = tempfile.mkdtemp()
        lines = ["a,b\n"] + [f"{i},{i*2}\n" for i in range(20)]
        csv_content = "".join(lines)
        path = self._write_csv(tmpdir, csv_content)

        offsets = build_csv_offset_index(path, step=5)
        for i in range(1, len(offsets)):
            assert offsets[i] > offsets[i - 1]


# ============================================================================
# iter_csv_partition
# ============================================================================


class TestIterCsvPartition:
    """CSV分区读取测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        """Write CSV content to temp file and return path"""
        path = os.path.join(tmpdir, "partition_test.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_full_partition(self):
        """从0到EOF读取全部数据"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n3,4\n5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_partition(path, start_offset=0, end_offset=0, batch_size=10))
        total_records = sum(len(b) for b in batches)
        assert total_records == 3

    def test_partition_with_selected_columns(self):
        """分区读取指定列"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "x,y,z\n1,2,3\n4,5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_partition(
            path, start_offset=0, end_offset=0, batch_size=10, columns=["x", "z"]
        ))
        record = batches[0][0]
        assert "x" in record
        assert "z" in record
        assert "y" not in record

    def test_mini_batch_splitting(self):
        """小batch_size分批"""
        tmpdir = tempfile.mkdtemp()
        lines = ["x\n"] + [f"{i}\n" for i in range(10)]
        csv_content = "".join(lines)
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_partition(path, start_offset=0, end_offset=0, batch_size=3))
        assert len(batches) == 4  # 3+3+3+1
        assert len(batches[-1]) == 1
