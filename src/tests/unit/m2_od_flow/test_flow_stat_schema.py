"""
flow_stat_schema 的单元测试

测试覆盖：
1. FlowStatParams — 默认值、自定义值、data_dir 字段
2. FlowStatResult — 构造、序列化
3. WorkerResult — completed_files 字段
4. WorkerStatus — 枚举值
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams, FlowStatResult, WorkerResult, WorkerStatus


# ============================================================================
# FlowStatParams
# ============================================================================

class TestFlowStatParams:
    """FlowStatParams 参数模型测试"""

    def test_defaults(self):
        """默认值"""
        params = FlowStatParams()
        assert params.version_yyyyMM == "202603"
        assert params.csv_path == ""
        assert params.data_dir == ""
        assert params.section_version == "202603"
        assert params.topo_version == "202512"
        assert params.batch_size == 500_000
        assert params.upsert_interval == 5
        assert params.save_local is False
        assert params.output_dir == "outputs/m2_flow_stat"
        assert params.max_records == 0
        assert params.num_workers == 1
        assert params.mini_batch_size == 50_000

    def test_custom_values(self):
        """自定义值"""
        params = FlowStatParams(
            version_yyyyMM="202604",
            csv_path="/tmp/test.csv",
            data_dir="/home/shy/gaosu_data",
            section_version="202604",
            topo_version="202601",
            batch_size=100_000,
            upsert_interval=10,
            save_local=True,
            output_dir="/tmp/out",
            max_records=5000,
        )
        assert params.version_yyyyMM == "202604"
        assert params.csv_path == "/tmp/test.csv"
        assert params.data_dir == "/home/shy/gaosu_data"
        assert params.batch_size == 100_000
        assert params.save_local is True
        assert params.max_records == 5000

    def test_model_dump(self):
        """序列化为字典"""
        params = FlowStatParams(version_yyyyMM="202603")
        d = params.model_dump()
        assert "version_yyyyMM" in d
        assert d["version_yyyyMM"] == "202603"
        assert d["batch_size"] == 500_000
        assert "data_dir" in d

    def test_zero_max_records_means_all(self):
        """max_records=0 表示全量"""
        params = FlowStatParams(max_records=0)
        assert params.max_records == 0

    def test_data_dir_empty_means_monthly_mode(self):
        """data_dir 为空表示月文件模式"""
        params = FlowStatParams()
        assert not params.data_dir

    def test_data_dir_set_means_daily_mode(self):
        """data_dir 非空表示日文件模式"""
        params = FlowStatParams(data_dir="/home/shy/gaosu_data")
        assert params.data_dir
        assert params.data_dir == "/home/shy/gaosu_data"

    def test_data_dir_in_model_dump(self):
        """data_dir 字段包含在序列化结果中"""
        params = FlowStatParams(data_dir="/tmp/data")
        d = params.model_dump()
        assert d["data_dir"] == "/tmp/data"

    def test_parallel_params(self):
        """并行模式参数"""
        params = FlowStatParams(
            num_workers=10,
            mini_batch_size=50_000,
        )
        assert params.num_workers == 10
        assert params.mini_batch_size == 50_000

    def test_parallel_mode_dispatch(self):
        """num_workers>1时表示并行模式"""
        params = FlowStatParams(num_workers=4)
        assert params.num_workers > 1

    def test_daily_parallel_mode(self):
        """日文件 + 并行模式参数组合"""
        params = FlowStatParams(
            data_dir="/home/shy/gaosu_data",
            num_workers=4,
            mini_batch_size=50000,
        )
        assert params.data_dir
        assert params.num_workers > 1

    def test_daily_sequential_mode(self):
        """日文件 + 单进程模式参数组合"""
        params = FlowStatParams(
            data_dir="/home/shy/gaosu_data",
            num_workers=1,
        )
        assert params.data_dir
        assert params.num_workers == 1


# ============================================================================
# FlowStatResult
# ============================================================================

class TestFlowStatResult:
    """FlowStatResult 结果模型测试"""

    def test_success_result(self):
        """成功结果"""
        result = FlowStatResult(
            status="success",
            records_processed=1000,
            flow_records_written=500,
            map_records_inserted=10,
            batches=5,
            execution_time=12.5,
        )
        assert result.status == "success"
        assert result.records_processed == 1000
        assert result.flow_records_written == 500
        assert result.map_records_inserted == 10
        assert result.batches == 5
        assert result.execution_time == 12.5
        assert result.errors == []
        assert result.warnings == []

    def test_failed_result(self):
        """失败结果"""
        result = FlowStatResult(
            status="failed",
            errors=["CSV not found", "DB connection failed"],
        )
        assert result.status == "failed"
        assert len(result.errors) == 2
        assert result.flow_records_written == 0

    def test_defaults(self):
        """默认值"""
        result = FlowStatResult(status="success")
        assert result.records_processed == 0
        assert result.flow_records_written == 0
        assert result.map_records_inserted == 0
        assert result.batches == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.execution_time is None
        assert result.local_output_path is None

    def test_with_local_output(self):
        """含本地输出路径"""
        result = FlowStatResult(
            status="success",
            local_output_path="/tmp/m2_flow_stat_v202603.json",
        )
        assert result.local_output_path == "/tmp/m2_flow_stat_v202603.json"

    def test_with_warnings(self):
        """含警告"""
        result = FlowStatResult(
            status="success",
            warnings=["Validation: 3 orphan records"],
        )
        assert len(result.warnings) == 1
        assert "orphan" in result.warnings[0]

    def test_fix_failures_default_zero(self):
        """fix_failures默认为0"""
        result = FlowStatResult(status="success")
        assert result.fix_failures == 0

    def test_fix_failures_reported(self):
        """fix_failures正常报告"""
        result = FlowStatResult(
            status="success",
            fix_failures=1234,
        )
        assert result.fix_failures == 1234


# ============================================================================
# WorkerStatus
# ============================================================================

class TestWorkerStatus:
    """WorkerStatus 枚举测试"""

    def test_success_status(self):
        assert WorkerStatus.SUCCESS == "success"

    def test_partial_status(self):
        assert WorkerStatus.PARTIAL == "partial"

    def test_failed_status(self):
        assert WorkerStatus.FAILED == "failed"

    def test_status_is_string(self):
        assert isinstance(WorkerStatus.SUCCESS, str)
        assert isinstance(WorkerStatus.PARTIAL, str)
        assert isinstance(WorkerStatus.FAILED, str)


# ============================================================================
# WorkerResult — 含 completed_files 字段
# ============================================================================

class TestWorkerResult:
    """WorkerResult 结果模型测试"""

    def test_success_result(self):
        """成功Worker结果"""
        result = WorkerResult(
            worker_id=0,
            status=WorkerStatus.SUCCESS,
            records_processed=100000,
            flow_records_written=50000,
            map_records_inserted=100,
            fix_failures=50,
            batches=10,
            execution_time=120.5,
        )
        assert result.worker_id == 0
        assert result.status == WorkerStatus.SUCCESS
        assert result.records_processed == 100000
        assert result.flow_records_written == 50000
        assert result.map_records_inserted == 100
        assert result.fix_failures == 50
        assert result.batches == 10
        assert result.execution_time == 120.5
        assert result.errors == []

    def test_partial_result(self):
        """部分成功Worker结果"""
        result = WorkerResult(
            worker_id=1,
            status=WorkerStatus.PARTIAL,
            errors=["some records failed to fix"],
        )
        assert result.worker_id == 1
        assert result.status == WorkerStatus.PARTIAL
        assert len(result.errors) == 1

    def test_failed_worker(self):
        """失败Worker结果"""
        result = WorkerResult(
            worker_id=3,
            status=WorkerStatus.FAILED,
            errors=["DB connection timeout"],
        )
        assert result.worker_id == 3
        assert result.status == WorkerStatus.FAILED
        assert len(result.errors) == 1
        assert result.records_processed == 0

    def test_defaults(self):
        """默认值"""
        result = WorkerResult(worker_id=0)
        assert result.worker_id == 0
        assert result.status == WorkerStatus.SUCCESS
        assert result.last_batch_offset == 0
        assert result.records_processed == 0
        assert result.flow_records_written == 0
        assert result.map_records_inserted == 0
        assert result.fix_failures == 0
        assert result.batches == 0
        assert result.errors == []
        assert result.execution_time is None
        assert result.completed_files == []

    def test_with_last_batch_offset(self):
        """含最后处理的字节偏移"""
        result = WorkerResult(
            worker_id=2,
            last_batch_offset=5000000,
            status=WorkerStatus.SUCCESS,
        )
        assert result.last_batch_offset == 5000000

    def test_completed_files_default_empty(self):
        """completed_files 默认为空列表"""
        result = WorkerResult(worker_id=0)
        assert result.completed_files == []
        assert isinstance(result.completed_files, list)

    def test_completed_files_with_values(self):
        """completed_files 含日文件路径"""
        files = ["/path/data_20260301.csv", "/path/data_20260302.csv"]
        result = WorkerResult(
            worker_id=0,
            completed_files=files,
        )
        assert len(result.completed_files) == 2
        assert result.completed_files == files

    def test_completed_files_daily_mode(self):
        """日文件模式 WorkerResult 包含 completed_files"""
        result = WorkerResult(
            worker_id=1,
            status=WorkerStatus.SUCCESS,
            records_processed=50000,
            flow_records_written=25000,
            completed_files=[
                "/home/shy/gaosu_data/202603/data_20260301.csv",
                "/home/shy/gaosu_data/202603/data_20260303.csv",
            ],
        )
        assert len(result.completed_files) == 2
        assert "data_20260301.csv" in result.completed_files[0]

    def test_completed_files_partial_worker(self):
        """部分完成的 Worker 也报告 completed_files"""
        result = WorkerResult(
            worker_id=2,
            status=WorkerStatus.PARTIAL,
            errors=["some upsert failures"],
            completed_files=["/path/data_20260301.csv"],
        )
        assert result.status == WorkerStatus.PARTIAL
        assert len(result.completed_files) == 1

    def test_completed_files_failed_worker(self):
        """失败的 Worker 仍报告已完成的文件"""
        result = WorkerResult(
            worker_id=3,
            status=WorkerStatus.FAILED,
            errors=["unrecoverable error"],
            completed_files=["/path/data_20260301.csv", "/path/data_20260302.csv"],
        )
        assert result.status == WorkerStatus.FAILED
        assert len(result.completed_files) == 2

    def test_model_dump_includes_completed_files(self):
        """序列化包含 completed_files"""
        result = WorkerResult(
            worker_id=0,
            completed_files=["f1.csv"],
        )
        d = result.model_dump()
        assert "completed_files" in d
        assert d["completed_files"] == ["f1.csv"]

    def test_all_statuses_have_default(self):
        """每个状态都能作为默认值"""
        for status in [WorkerStatus.SUCCESS, WorkerStatus.PARTIAL, WorkerStatus.FAILED]:
            result = WorkerResult(worker_id=0, status=status)
            assert result.status == status
