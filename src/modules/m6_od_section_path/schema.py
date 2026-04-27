"""
M6 OD-Section-Path 映射模块 Pydantic 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class M6TaskParams(BaseModel):
    """M6 任务参数"""
    hive_table: str = Field(
        default="gstx_exit_with_min_fee202603",
        description="Hive 表名",
    )
    hive_database: str = Field(
        default="dbbase2026",
        description="Hive 数据库名（2025年表用 dbbase2025，2026年表用 dbbase2026）",
    )
    version_yyyyMM: str = Field(
        default="202603",
        description="版本年月，与 Hive 表名一致",
    )
    section_version: str = Field(
        default="202603",
        description="dwd_section_path 的版本年月",
    )
    topo_version: str = Field(
        default="202512",
        description="拓扑数据版本",
    )
    batch_size: int = Field(
        default=500_000,
        description="每批处理记录数（测试时用100）",
    )
    overwrite: bool = Field(
        default=False,
        description="是否覆盖已有数据（当前未实现truncate，仅upsert）",
    )
    save_local: bool = Field(
        default=False,
        description="是否保存结果到本地 JSON（测试模式）",
    )
    output_dir: str = Field(
        default="outputs/m6_test",
        description="本地输出目录",
    )

    model_config = {"arbitrary_types_allowed": True}


class M6TaskResult(BaseModel):
    """M6 任务结果"""
    status: str = Field(
        ...,
        description="任务状态: pending/running/success/failed",
    )
    records_processed: int = Field(
        default=0,
        description="已处理的原始记录数",
    )
    maps_written: int = Field(
        default=0,
        description="写入 dwd_od_section_path_map 的记录数",
    )
    freq_written: int = Field(
        default=0,
        description="写入 dwd_od_section_path_numpath_freq 的记录数",
    )
    batches: int = Field(
        default=0,
        description="处理批次数",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="错误信息列表",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="警告信息列表",
    )
    execution_time: Optional[float] = Field(
        default=None,
        description="执行时间（秒）",
    )
    local_output_path: Optional[str] = Field(
        default=None,
        description="本地输出文件路径（测试模式）",
    )

    model_config = {"arbitrary_types_allowed": True}


class ODPathMapRecord(BaseModel):
    """OD-Section-Path 映射记录"""
    id: Optional[int] = Field(None, description="自增主键，仅用于关联查询")
    enid: str = Field(..., description="OD起点ID")
    exid: str = Field(..., description="OD终点ID")
    numpath: str = Field(..., description="去重后的 section_number 序列")
    version_yyyyMM: str = Field(..., description="版本年月")
    fixed_intervalpath: str = Field(..., description="统计量最大的 fixed_intervalgroup（拓扑修复后）")
    intervalpath_cnt: int = Field(default=0, description="该 fixed_intervalpath 在同一 numpath 下的统计量")
    total_trip_cnt: int = Field(default=0, description="该 (enid, exid, numpath) 组合的总通行记录数")
    path_freq_ratio: float = Field(default=0.0, description="路径一致性比例")
    source_flag: str = Field(default="hive_computed", description="数据来源")

    model_config = {"from_attributes": True}


class NumPathFreqRecord(BaseModel):
    """numPath 到 fixed_intervalgroup 频率映射记录"""
    id: Optional[int] = Field(None, description="自增主键，仅用于关联查询")
    enid: str = Field(..., description="OD起点ID")
    exid: str = Field(..., description="OD终点ID")
    numpath: str = Field(..., description="去重后的 section_number 序列")
    fixed_intervalgroup: str = Field(..., description="修复后的 intervalgroup（拓扑修复后）")
    version_yyyyMM: str = Field(..., description="版本年月")
    ig_count: int = Field(default=0, description="该 fixed_intervalgroup 在此 numpath 下的统计量")
    ig_rank: int = Field(default=0, description="在同 numpath 下按 ig_count 降序排名，1为统计量最大")
    source_flag: str = Field(default="hive_computed", description="数据来源")

    model_config = {"from_attributes": True}


class BatchProcessDetail(BaseModel):
    """单批处理详情（用于测试结果保存）"""
    batch_no: int
    input_records: int
    output_map_records: int
    output_freq_records: int
    duration_seconds: float


class M6TestResult(BaseModel):
    """M6 测试结果（保存到本地 JSON）"""
    params: M6TaskParams
    batches: list[BatchProcessDetail]
    summary: dict
    map_records_sample: list[dict] = Field(default_factory=list)
    freq_records_sample: list[dict] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
