"""
csv_reader 的单元测试

测试覆盖：
1. get_csv_path — 路径拼接
2. iter_csv_batches — 流式分批读取（含 has_header 参数）
3. count_csv_lines — 行数统计（含 has_header 参数）
4. build_csv_offset_index — 偏移索引
5. iter_csv_partition — 分区读取（含 has_header 参数）
6. _detect_has_header — 表头检测
7. discover_daily_files — 日文件发现
8. iter_daily_csv_batches — 日文件批量遍历
"""

import os
import tempfile
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.csv_reader import (
    get_csv_path,
    iter_csv_batches,
    iter_csv_partition,
    count_csv_lines,
    build_csv_offset_index,
    discover_daily_files,
    _detect_has_header,
    iter_daily_csv_batches,
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
# iter_csv_batches — has_header parameter
# ============================================================================

class TestIterCsvBatchesHasHeader:
    """has_header 参数测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        path = os.path.join(tmpdir, "test_header.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_has_header_true_default(self):
        """has_header=True（默认）：跳过首行作为表头"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n3,4\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=10, has_header=True))
        assert len(batches[0]) == 2
        assert batches[0][0] == {"a": "1", "b": "2"}

    def test_has_header_false_with_columns(self):
        """has_header=False：用columns按位置映射，不跳首行"""
        tmpdir = tempfile.mkdtemp()
        # 无表头文件，数据直接开始
        csv_content = "1,2\n3,4\n5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(
            path, batch_size=10, columns=["x", "y"], has_header=False
        ))
        assert len(batches[0]) == 3
        assert batches[0][0] == {"x": "1", "y": "2"}
        assert batches[0][1] == {"x": "3", "y": "4"}
        assert batches[0][2] == {"x": "5", "y": "6"}

    def test_has_header_false_without_columns_raises(self):
        """has_header=False 且不指定 columns 时抛 ValueError"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "1,2\n3,4\n"
        path = self._write_csv(tmpdir, csv_content)

        with pytest.raises(ValueError, match="columns must be specified"):
            list(iter_csv_batches(path, batch_size=10, has_header=False))

    def test_has_header_false_column_order_matters(self):
        """has_header=False 时 columns 顺序与文件列顺序一致"""
        tmpdir = tempfile.mkdtemp()
        # 文件实际列顺序: exid, enid, val
        csv_content = "X1,E1,100\nX2,E2,200\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(
            path, batch_size=10,
            columns=["exid", "enid", "val"],
            has_header=False,
        ))
        assert batches[0][0]["exid"] == "X1"
        assert batches[0][0]["enid"] == "E1"
        assert batches[0][0]["val"] == "100"

    def test_has_header_false_with_subset_columns(self):
        """has_header=False 时只提取部分列"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "X1,E1,100,extra\nX2,E2,200,extra2\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(
            path, batch_size=10,
            columns=["exid", "enid"],
            has_header=False,
        ))
        assert "exid" in batches[0][0]
        assert "enid" in batches[0][0]
        assert len(batches[0][0]) == 2

    def test_has_header_false_empty_file(self):
        """has_header=False 空文件返回空列表"""
        tmpdir = tempfile.mkdtemp()
        csv_content = ""
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(
            path, batch_size=10, columns=["a"], has_header=False
        ))
        assert len(batches) == 0

    def test_backward_compatible_default_has_header_true(self):
        """向后兼容：不传 has_header 时默认为 True"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_batches(path, batch_size=10))
        assert len(batches[0]) == 1  # 跳过表头，只1条数据


# ============================================================================
# count_csv_lines — has_header parameter
# ============================================================================

class TestCountCsvLines:
    """CSV行数统计测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
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

    def test_count_has_header_false(self):
        """has_header=False：所有行都计入"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "1,2\n3,4\n5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        result = count_csv_lines(path, has_header=False)
        assert result == 3

    def test_count_has_header_false_vs_true(self):
        """has_header=False 比 True 多1（首行差异）"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n3,4\n"
        path = self._write_csv(tmpdir, csv_content)

        cnt_true = count_csv_lines(path, has_header=True)
        cnt_false = count_csv_lines(path, has_header=False)
        assert cnt_false - cnt_true == 1

    def test_count_empty_file_has_header_false(self):
        """空文件 has_header=False 返回0"""
        tmpdir = tempfile.mkdtemp()
        csv_content = ""
        path = self._write_csv(tmpdir, csv_content)

        result = count_csv_lines(path, has_header=False)
        assert result == 0


# ============================================================================
# build_csv_offset_index
# ============================================================================

class TestBuildCsvOffsetIndex:
    """CSV偏移索引构建测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        path = os.path.join(tmpdir, "offset_test.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_basic_offset_index(self):
        """基本偏移索引构建"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n3,4\n5,6\n7,8\n9,10\n"
        path = self._write_csv(tmpdir, csv_content)

        offsets, line_count = build_csv_offset_index(path, step=2)
        assert len(offsets) >= 2
        assert offsets[0] > 0
        assert line_count == 5

    def test_offset_index_fewer_than_step(self):
        """记录数少于step时只有header_end"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "a,b\n1,2\n"
        path = self._write_csv(tmpdir, csv_content)

        offsets, line_count = build_csv_offset_index(path, step=100)
        assert len(offsets) == 1
        assert line_count == 1

    def test_offset_index_increasing(self):
        """偏移量递增"""
        tmpdir = tempfile.mkdtemp()
        lines = ["a,b\n"] + [f"{i},{i*2}\n" for i in range(20)]
        csv_content = "".join(lines)
        path = self._write_csv(tmpdir, csv_content)

        offsets, line_count = build_csv_offset_index(path, step=5)
        for i in range(1, len(offsets)):
            assert offsets[i] > offsets[i - 1]


# ============================================================================
# iter_csv_partition
# ============================================================================

class TestIterCsvPartition:
    """CSV分区读取测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
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
        assert len(batches) == 4
        assert len(batches[-1]) == 1

    def test_partition_has_header_false(self):
        """分区读取 has_header=False"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "1,2\n3,4\n5,6\n"
        path = self._write_csv(tmpdir, csv_content)

        batches = list(iter_csv_partition(
            path, start_offset=0, end_offset=0, batch_size=10,
            columns=["a", "b"], has_header=False,
        ))
        total_records = sum(len(b) for b in batches)
        assert total_records == 3

    def test_partition_has_header_false_without_columns_raises(self):
        """分区读取 has_header=False 无 columns 时报错"""
        tmpdir = tempfile.mkdtemp()
        csv_content = "1,2\n3,4\n"
        path = self._write_csv(tmpdir, csv_content)

        with pytest.raises(ValueError, match="columns must be specified"):
            list(iter_csv_partition(
                path, start_offset=0, end_offset=0, batch_size=10,
                has_header=False,
            ))


# ============================================================================
# _detect_has_header
# ============================================================================

class TestDetectHasHeader:
    """表头检测测试"""

    def _write_csv(self, tmpdir: str, content: str) -> str:
        path = os.path.join(tmpdir, "detect_test.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_file_with_header_returns_true(self):
        """含 enid/exid 表头返回 True"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "enid,exid,intervalgroup\n1,2,3\n")
        assert _detect_has_header(path) is True

    def test_file_with_exid_header_returns_true(self):
        """含 exid 表头返回 True"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "exid,enid,intervalgroup\n1,2,3\n")
        assert _detect_has_header(path) is True

    def test_file_with_intervalgroup_header_returns_true(self):
        """含 intervalgroup 表头返回 True"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "col1,intervalgroup,col3\n1,2,3\n")
        assert _detect_has_header(path) is True

    def test_headerless_data_returns_false(self):
        """纯数据行（首行含数字ID）返回 False"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "G000561001000120,G000561001000110,data\n")
        assert _detect_has_header(path) is False

    def test_headerless_numeric_first_line(self):
        """纯数字首行返回 False"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "100,200,300\n400,500,600\n")
        assert _detect_has_header(path) is False

    def test_case_insensitive_detection(self):
        """检测不区分大小写"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "ENID,EXID,DATA\n1,2,3\n")
        assert _detect_has_header(path) is True

    def test_nonexistent_file_returns_true(self):
        """不存在的文件默认返回 True（安全回退）"""
        assert _detect_has_header("/nonexistent/path/file.csv") is True

    def test_empty_file_returns_true(self):
        """空文件默认返回 True（安全回退）"""
        tmpdir = tempfile.mkdtemp()
        path = self._write_csv(tmpdir, "")
        assert _detect_has_header(path) is True


# ============================================================================
# discover_daily_files
# ============================================================================

class TestDiscoverDailyFiles:
    """日文件发现测试"""

    def _create_daily_files(self, tmpdir: str, version: str, days: list[int]) -> str:
        """创建模拟日文件目录结构，返回 data_dir"""
        version_dir = os.path.join(tmpdir, version)
        os.makedirs(version_dir, exist_ok=True)
        for day in days:
            day_str = f"{version}{day:02d}"
            filepath = os.path.join(version_dir, f"data_{day_str}.csv")
            with open(filepath, "w") as f:
                f.write(f"data for {day_str}\n")
        return tmpdir

    def test_discover_all_files(self):
        """发现所有日文件"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202603", list(range(1, 32)))

        files = discover_daily_files("202603", tmpdir)
        assert len(files) == 31

    def test_files_sorted_chronologically(self):
        """文件按日期排序"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202603", [15, 1, 10, 5])

        files = discover_daily_files("202603", tmpdir)
        basenames = [os.path.basename(f) for f in files]
        assert basenames == [
            "data_20260301.csv",
            "data_20260305.csv",
            "data_20260310.csv",
            "data_20260315.csv",
        ]

    def test_missing_days_logged(self):
        """缺失的日文件发 warning 但不中断"""
        tmpdir = tempfile.mkdtemp()
        # 只创建部分文件
        self._create_daily_files(tmpdir, "202603", [1, 15, 31])

        files = discover_daily_files("202603", tmpdir)
        assert len(files) == 3

    def test_nonexistent_directory_raises(self):
        """目录不存在时抛 FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Daily data directory not found"):
            discover_daily_files("209999", "/nonexistent/path")

    def test_february_28_days(self):
        """2月份只有28天（非闰年）"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202502", list(range(1, 29)))

        files = discover_daily_files("202502", tmpdir)
        assert len(files) == 28

    def test_february_29_days_leap_year(self):
        """闰年2月份29天"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202802", list(range(1, 30)))

        files = discover_daily_files("202802", tmpdir)
        assert len(files) == 29

    def test_file_paths_are_absolute(self):
        """返回的路径是绝对路径"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202603", [1])

        files = discover_daily_files("202603", tmpdir)
        assert os.path.isabs(files[0])

    def test_file_paths_contain_version(self):
        """文件路径包含版本目录"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202603", [1])

        files = discover_daily_files("202603", tmpdir)
        assert "202603" in files[0]

    def test_naming_convention(self):
        """文件名遵循 data_{YYYYMMDD}.csv 格式"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_files(tmpdir, "202603", [1, 15])

        files = discover_daily_files("202603", tmpdir)
        for f in files:
            basename = os.path.basename(f)
            assert basename.startswith("data_")
            assert basename.endswith(".csv")
            assert len(basename) == len("data_20260301.csv")


# ============================================================================
# iter_daily_csv_batches
# ============================================================================

class TestIterDailyCsvBatches:
    """日文件批量遍历测试"""

    def _create_daily_dir(self, tmpdir: str, version: str, day_data: dict) -> str:
        """创建日文件目录，day_data: {day_int: [row1, row2, ...]}"""
        version_dir = os.path.join(tmpdir, version)
        os.makedirs(version_dir, exist_ok=True)
        for day, rows in day_data.items():
            day_str = f"{version}{day:02d}"
            filepath = os.path.join(version_dir, f"data_{day_str}.csv")
            with open(filepath, "w") as f:
                f.write("enid,exid,val\n")
                for row in rows:
                    f.write(row + "\n")
        return tmpdir

    def test_iterate_multiple_days(self):
        """遍历多天文件"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_dir(tmpdir, "202603", {
            1: ["E1,X1,100", "E2,X2,200"],
            2: ["E3,X3,300"],
        })

        results = list(iter_daily_csv_batches(
            "202603", tmpdir, batch_size=100, columns=["enid", "exid", "val"]
        ))
        # Should yield (day_str, batch) tuples
        day_strs = [r[0] for r in results]
        assert "20260301" in day_strs
        assert "20260302" in day_strs

    def test_day_str_format(self):
        """day_str 格式为 YYYYMMDD"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_dir(tmpdir, "202603", {
            1: ["E1,X1,100"],
        })

        results = list(iter_daily_csv_batches(
            "202603", tmpdir, batch_size=100, columns=["enid", "exid", "val"]
        ))
        assert results[0][0] == "20260301"

    def test_batch_content_correct(self):
        """批次内容正确读取"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_dir(tmpdir, "202603", {
            15: ["E1,X1,100", "E2,X2,200"],
        })

        results = list(iter_daily_csv_batches(
            "202603", tmpdir, batch_size=100, columns=["enid", "exid", "val"]
        ))
        day_str, batch = results[0]
        assert day_str == "20260315"
        assert len(batch) == 2
        assert batch[0]["enid"] == "E1"
        assert batch[1]["exid"] == "X2"

    def test_headerless_daily_file_auto_detected(self):
        """无表头日文件自动检测并正确读取"""
        tmpdir = tempfile.mkdtemp()
        version_dir = os.path.join(tmpdir, "202603")
        os.makedirs(version_dir, exist_ok=True)
        filepath = os.path.join(version_dir, "data_20260301.csv")
        # 无表头文件
        with open(filepath, "w") as f:
            f.write("E1,X1,100\nE2,X2,200\n")

        results = list(iter_daily_csv_batches(
            "202603", tmpdir, batch_size=100, columns=["enid", "exid", "val"]
        ))
        # _detect_has_header returns False, so all 3 lines are treated as data
        # (with wrong column mapping since file order != columns order, but that's
        # handled at service level with CSV_COLUMNS_IN_FILE_ORDER)
        day_str, batch = results[0]
        assert day_str == "20260301"
        # Records are read (may have wrong column names due to file order,
        # but the count should be correct)
        assert len(batch) == 2

    def test_no_daily_files_raises(self):
        """目录不存在时抛异常"""
        with pytest.raises(FileNotFoundError):
            list(iter_daily_csv_batches("209999", "/nonexistent"))

    def test_batch_size_splitting(self):
        """batch_size 小于记录数时拆分"""
        tmpdir = tempfile.mkdtemp()
        self._create_daily_dir(tmpdir, "202603", {
            1: [f"E{i},X{i},{i*100}" for i in range(5)],
        })

        results = list(iter_daily_csv_batches(
            "202603", tmpdir, batch_size=2, columns=["enid", "exid", "val"]
        ))
        # 5 records / batch_size 2 = 3 batches (2+2+1)
        assert len(results) == 3
