"""
checkpoint 的单元测试

测试覆盖：
1. 原有字节偏移模式: load/save/clear/get_path
2. 日文件模式: load_daily/save_daily/clear_daily/get_daily_path
3. 两种模式共存互不干扰
"""

import json
import os
import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


# ============================================================================
# 原有字节偏移模式 checkpoint
# ============================================================================

class TestGetCheckpointPath:
    """checkpoint 路径生成测试"""

    def test_path_format(self):
        """路径格式正确"""
        from src.modules.m2_od_flow.checkpoint import get_checkpoint_path
        path = get_checkpoint_path(0, "202603")
        assert "w0_v202603.json" in str(path)

    def test_different_worker_ids(self):
        """不同 worker_id 生成不同路径"""
        from src.modules.m2_od_flow.checkpoint import get_checkpoint_path
        path0 = get_checkpoint_path(0, "202603")
        path5 = get_checkpoint_path(5, "202603")
        assert path0 != path5
        assert "w0_" in str(path0)
        assert "w5_" in str(path5)

    def test_different_versions(self):
        """不同版本生成不同路径"""
        from src.modules.m2_od_flow.checkpoint import get_checkpoint_path
        path1 = get_checkpoint_path(1, "202603")
        path2 = get_checkpoint_path(1, "202604")
        assert path1 != path2
        assert "v202603" in str(path1)
        assert "v202604" in str(path2)


class TestCheckpointIntegration:
    """checkpoint 完整流程测试（使用真实临时目录）"""

    def test_save_and_load_checkpoint(self):
        """保存并加载 checkpoint"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=1, version="202603",
                    last_offset=5000000, records_processed=10000,
                    flow_records_written=5000, map_records_inserted=100,
                    completed=False,
                )

                path = cp_module.get_checkpoint_path(1, "202603")
                assert path.exists()

                data = cp_module.load_checkpoint(1, "202603")
                assert data is not None
                assert data["worker_id"] == 1
                assert data["last_offset"] == 5000000
                assert data["records_processed"] == 10000
                assert data["completed"] is False

            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_load_nonexistent_returns_none(self):
        """加载不存在的 checkpoint 返回 None"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                result = cp_module.load_checkpoint(99, "209999")
                assert result is None
            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_clear_checkpoint(self):
        """清除 checkpoint"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=2, version="202603",
                    last_offset=1000000, records_processed=5000,
                    flow_records_written=2500, map_records_inserted=50,
                    completed=False,
                )
                path = cp_module.get_checkpoint_path(2, "202603")
                assert path.exists()

                cp_module.clear_checkpoint(2, "202603")
                assert not path.exists()

            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_clear_nonexistent_no_error(self):
        """清除不存在的文件不报错"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.clear_checkpoint(999, "209999")
            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_save_load_clear_cycle(self):
        """保存→加载→清除 完整流程"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=3, version="202603",
                    last_offset=3000000, records_processed=30000,
                    flow_records_written=15000, map_records_inserted=75,
                    completed=False,
                )
                checkpoint = cp_module.load_checkpoint(3, "202603")
                assert checkpoint is not None
                assert checkpoint["last_offset"] == 3000000

                cp_module.clear_checkpoint(3, "202603")
                checkpoint2 = cp_module.load_checkpoint(3, "202603")
                assert checkpoint2 is None

            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_completed_flag_workflow(self):
        """completed 标志工作流"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=4, version="202603",
                    last_offset=1000000, records_processed=10000,
                    flow_records_written=5000, map_records_inserted=50,
                    completed=False,
                )
                checkpoint = cp_module.load_checkpoint(4, "202603")
                assert checkpoint["completed"] is False

                cp_module.save_checkpoint(
                    worker_id=4, version="202603",
                    last_offset=5000000, records_processed=50000,
                    flow_records_written=25000, map_records_inserted=250,
                    completed=True,
                )
                checkpoint2 = cp_module.load_checkpoint(4, "202603")
                assert checkpoint2["completed"] is True
                assert checkpoint2["last_offset"] == 5000000

            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_checkpoint_content_fields(self):
        """checkpoint 内容包含所有必需字段"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=5, version="202604",
                    last_offset=10000000, records_processed=50000,
                    flow_records_written=25000, map_records_inserted=50,
                    completed=True,
                )

                data = cp_module.load_checkpoint(5, "202604")
                assert data is not None
                for key in ["worker_id", "version", "last_offset", "records_processed",
                            "flow_records_written", "map_records_inserted", "completed", "timestamp"]:
                    assert key in data

                assert data["worker_id"] == 5
                assert data["version"] == "202604"
                assert data["completed"] is True

            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_offset_mode_has_mode_field(self):
        """字节偏移模式 checkpoint 包含 mode='offset'"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=1, version="202603",
                    last_offset=1000, records_processed=100,
                    flow_records_written=50, map_records_inserted=5,
                )
                data = cp_module.load_checkpoint(1, "202603")
                assert data["mode"] == "offset"
            finally:
                cp_module.CHECKPOINT_DIR = original_dir


# ============================================================================
# 日文件模式 checkpoint
# ============================================================================

class TestGetDailyCheckpointPath:
    """日文件 checkpoint 路径生成测试"""

    def test_path_format(self):
        """路径格式正确，包含 _daily 后缀"""
        from src.modules.m2_od_flow.checkpoint import get_daily_checkpoint_path
        path = get_daily_checkpoint_path(0, "202603")
        assert "w0_v202603_daily.json" in str(path)

    def test_different_worker_ids(self):
        """不同 worker_id 生成不同路径"""
        from src.modules.m2_od_flow.checkpoint import get_daily_checkpoint_path
        path0 = get_daily_checkpoint_path(0, "202603")
        path5 = get_daily_checkpoint_path(5, "202603")
        assert path0 != path5

    def test_daily_path_differs_from_offset_path(self):
        """日文件路径与字节偏移路径不同"""
        from src.modules.m2_od_flow.checkpoint import get_checkpoint_path, get_daily_checkpoint_path
        offset_path = get_checkpoint_path(1, "202603")
        daily_path = get_daily_checkpoint_path(1, "202603")
        assert offset_path != daily_path
        assert "_daily" not in str(offset_path)
        assert "_daily" in str(daily_path)


class TestDailyCheckpointSaveLoad:
    """日文件 checkpoint 保存和加载测试"""

    def _use_temp_dir(self, cp_module):
        """Context manager: 临时修改 CHECKPOINT_DIR"""
        class TempDirContext:
            def __init__(self, original):
                self.original = original
                self.tmpdir = tempfile.mkdtemp()
            def __enter__(self):
                cp_module.CHECKPOINT_DIR = Path(self.tmpdir)
                return self
            def __exit__(self, *args):
                cp_module.CHECKPOINT_DIR = self.original
        return TempDirContext(cp_module.CHECKPOINT_DIR)

    def test_save_and_load(self):
        """保存并加载日文件 checkpoint"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            cp_module.save_daily_checkpoint(
                worker_id=1, version="202603",
                completed_files=["/path/data_20260301.csv", "/path/data_20260302.csv"],
                current_file="/path/data_20260303.csv",
                records_processed=50000, flow_records_written=25000,
                map_records_inserted=100, completed=False,
            )

            data = cp_module.load_daily_checkpoint(1, "202603")
            assert data is not None
            assert data["worker_id"] == 1
            assert data["version"] == "202603"
            assert data["mode"] == "daily"
            assert len(data["completed_files"]) == 2
            assert data["current_file"] == "/path/data_20260303.csv"
            assert data["records_processed"] == 50000
            assert data["completed"] is False

    def test_load_nonexistent_returns_none(self):
        """加载不存在的日文件 checkpoint 返回 None"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            result = cp_module.load_daily_checkpoint(99, "209999")
            assert result is None

    def test_clear_daily_checkpoint(self):
        """清除日文件 checkpoint"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            cp_module.save_daily_checkpoint(
                worker_id=2, version="202603",
                completed_files=[], current_file="",
                records_processed=0, flow_records_written=0,
                map_records_inserted=0,
            )

            path = cp_module.get_daily_checkpoint_path(2, "202603")
            assert path.exists()

            cp_module.clear_daily_checkpoint(2, "202603")
            assert not path.exists()

    def test_clear_nonexistent_no_error(self):
        """清除不存在的日文件 checkpoint 不报错"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            cp_module.clear_daily_checkpoint(999, "209999")

    def test_save_load_clear_cycle(self):
        """保存→加载→清除 完整流程"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            cp_module.save_daily_checkpoint(
                worker_id=3, version="202603",
                completed_files=["f1.csv"], current_file="f2.csv",
                records_processed=10000, flow_records_written=5000,
                map_records_inserted=50, completed=False,
            )

            data = cp_module.load_daily_checkpoint(3, "202603")
            assert data is not None
            assert data["completed_files"] == ["f1.csv"]

            cp_module.clear_daily_checkpoint(3, "202603")
            assert cp_module.load_daily_checkpoint(3, "202603") is None

    def test_completed_flag_progression(self):
        """completed 标志从 False 到 True"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            # 中间状态
            cp_module.save_daily_checkpoint(
                worker_id=4, version="202603",
                completed_files=["f1.csv", "f2.csv"], current_file="f3.csv",
                records_processed=20000, flow_records_written=10000,
                map_records_inserted=100, completed=False,
            )
            data = cp_module.load_daily_checkpoint(4, "202603")
            assert data["completed"] is False

            # 完成状态
            cp_module.save_daily_checkpoint(
                worker_id=4, version="202603",
                completed_files=["f1.csv", "f2.csv", "f3.csv"], current_file="",
                records_processed=30000, flow_records_written=15000,
                map_records_inserted=150, completed=True,
            )
            data = cp_module.load_daily_checkpoint(4, "202603")
            assert data["completed"] is True
            assert len(data["completed_files"]) == 3

    def test_all_required_fields(self):
        """日文件 checkpoint 包含所有必需字段"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            cp_module.save_daily_checkpoint(
                worker_id=5, version="202604",
                completed_files=["a.csv"], current_file="b.csv",
                records_processed=1000, flow_records_written=500,
                map_records_inserted=10, completed=False,
            )

            data = cp_module.load_daily_checkpoint(5, "202604")
            assert data is not None
            for key in ["worker_id", "version", "mode", "completed_files",
                        "current_file", "records_processed", "flow_records_written",
                        "map_records_inserted", "completed", "timestamp"]:
                assert key in data, f"Missing key: {key}"

            assert data["mode"] == "daily"

    def test_completed_files_order_preserved(self):
        """completed_files 保持插入顺序"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            files = [f"day_{i:02d}.csv" for i in range(1, 6)]
            cp_module.save_daily_checkpoint(
                worker_id=6, version="202603",
                completed_files=files, current_file="",
                records_processed=0, flow_records_written=0,
                map_records_inserted=0,
            )

            data = cp_module.load_daily_checkpoint(6, "202603")
            assert data["completed_files"] == files

    def test_empty_completed_files(self):
        """空的 completed_files"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with self._use_temp_dir(cp_module):
            cp_module.save_daily_checkpoint(
                worker_id=7, version="202603",
                completed_files=[], current_file="first.csv",
                records_processed=0, flow_records_written=0,
                map_records_inserted=0,
            )

            data = cp_module.load_daily_checkpoint(7, "202603")
            assert data["completed_files"] == []
            assert data["current_file"] == "first.csv"


class TestDailyAndOffsetCoexistence:
    """两种模式 checkpoint 共存互不干扰"""

    def test_different_paths(self):
        """两种模式使用不同文件路径"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                # 保存两种模式的 checkpoint
                cp_module.save_checkpoint(
                    worker_id=1, version="202603",
                    last_offset=5000, records_processed=1000,
                    flow_records_written=500, map_records_inserted=10,
                )
                cp_module.save_daily_checkpoint(
                    worker_id=1, version="202603",
                    completed_files=["f1.csv"], current_file="f2.csv",
                    records_processed=2000, flow_records_written=1000,
                    map_records_inserted=20,
                )

                # 两个文件都存在
                offset_path = cp_module.get_checkpoint_path(1, "202603")
                daily_path = cp_module.get_daily_checkpoint_path(1, "202603")
                assert offset_path.exists()
                assert daily_path.exists()

                # 内容不互相覆盖
                offset_data = cp_module.load_checkpoint(1, "202603")
                daily_data = cp_module.load_daily_checkpoint(1, "202603")
                assert offset_data["mode"] == "offset"
                assert daily_data["mode"] == "daily"
                assert offset_data["records_processed"] == 1000
                assert daily_data["records_processed"] == 2000

            finally:
                cp_module.CHECKPOINT_DIR = original_dir

    def test_clear_one_does_not_affect_other(self):
        """清除一种模式不影响另一种"""
        from src.modules.m2_od_flow import checkpoint as cp_module

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = cp_module.CHECKPOINT_DIR
            cp_module.CHECKPOINT_DIR = Path(tmpdir)

            try:
                cp_module.save_checkpoint(
                    worker_id=2, version="202603",
                    last_offset=5000, records_processed=1000,
                    flow_records_written=500, map_records_inserted=10,
                )
                cp_module.save_daily_checkpoint(
                    worker_id=2, version="202603",
                    completed_files=["f1.csv"], current_file="",
                    records_processed=0, flow_records_written=0,
                    map_records_inserted=0,
                )

                # 清除 offset 模式
                cp_module.clear_checkpoint(2, "202603")
                assert not cp_module.get_checkpoint_path(2, "202603").exists()
                assert cp_module.get_daily_checkpoint_path(2, "202603").exists()

                # daily 数据仍可用
                data = cp_module.load_daily_checkpoint(2, "202603")
                assert data is not None

            finally:
                cp_module.CHECKPOINT_DIR = original_dir
