"""
M2 流量统计 Pydantic 模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class FlowStatParams(BaseModel):
    """流量统计任务参数"""
    version_yyyyMM: str = Field(
        default="202603",
        description="版本年月，与CSV文件名一致",
    )
    csv_path: str = Field(
        default="",
        description="CSV文件路径，为空则自动拼接到 /home/shy/gaosu_data/gstx_exit_with_min_fee{version}.csv",
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
        description="每批处理记录数（单进程模式）",
    )
    upsert_interval: int = Field(
        default=5,
        description="每N批执行一次数据库upsert（单进程模式）",
    )
    save_local: bool = Field(
        default=False,
        description="是否保存结果到本地JSON（测试模式）",
    )
    output_dir: str = Field(
        default="outputs/m2_flow_stat",
        description="本地输出目录",
    )
    max_records: int = Field(
        default=0,
        description="最大处理记录数，0表示全量",
    )
    num_workers: int = Field(
        default=1,
        description="Worker进程数，1=单进程模式，>1=并行模式",
    )
    mini_batch_size: int = Field(
        default=50_000,
        description="并行模式下每个mini-batch的记录数",
    )

    model_config = {"arbitrary_types_allowed": True}


class FlowStatResult(BaseModel):
    """流量统计任务结果"""
    status: str = Field(..., description="任务状态: success/failed")
    records_processed: int = Field(default=0, description="已处理的原始记录数")
    flow_records_written: int = Field(default=0, description="写入流量表的记录数")
    map_records_inserted: int = Field(default=0, description="插入map表的新记录数")
    fix_failures: int = Field(default=0, description="intervalgroup修复失败记录数")
    batches: int = Field(default=0, description="处理批次数")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    execution_time: Optional[float] = Field(default=None, description="执行时间(秒)")
    local_output_path: Optional[str] = Field(default=None)

    model_config = {"arbitrary_types_allowed": True}


class WorkerResult(BaseModel):
    """Worker进程返回的统计结果"""
    worker_id: int = Field(..., description="Worker编号")
    records_processed: int = Field(default=0, description="已处理的原始记录数")
    flow_records_written: int = Field(default=0, description="写入流量表的记录数")
    map_records_inserted: int = Field(default=0, description="插入map表的新记录数")
    fix_failures: int = Field(default=0, description="修复失败记录数")
    batches: int = Field(default=0, description="处理批次数")
    errors: list[str] = Field(default_factory=list)
    execution_time: Optional[float] = Field(default=None, description="执行时间(秒)")
