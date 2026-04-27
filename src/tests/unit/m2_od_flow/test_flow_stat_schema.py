"""
flow_stat_schema 的单元测试

测试覆盖：
1. FlowStatParams — 默认值、自定义值
2. FlowStatResult — 构造、序列化
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.modules.m2_od_flow.flow_stat_schema import FlowStatParams, FlowStatResult


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
        assert params.section_version == "202603"
        assert params.topo_version == "202512"
        assert params.batch_size == 500_000
        assert params.upsert_interval == 5
        assert params.save_local is False
        assert params.output_dir == "outputs/m2_flow_stat"
        assert params.max_records == 0

    def test_custom_values(self):
        """自定义值"""
        params = FlowStatParams(
            version_yyyyMM="202604",
            csv_path="/tmp/test.csv",
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

    def test_zero_max_records_means_all(self):
        """max_records=0 表示全量"""
        params = FlowStatParams(max_records=0)
        assert params.max_records == 0


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
