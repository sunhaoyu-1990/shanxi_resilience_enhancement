"""
M8 路径修正与折返识别 — Pydantic 数据模型
"""

from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 路径修正记录
# ============================================================


class PathRepairRecord(BaseModel):
    """单条路径修正结果"""
    record_id: str = Field(..., description="通行记录唯一标识")
    enid: str = Field(..., description="入口收费站或收费单元ID")
    exid: str = Field(..., description="出口收费站或收费单元ID")
    raw_path: str = Field(..., description="原始路径")
    corrected_path: str = Field(..., description="修正后路径")
    raw_node_count: int = Field(..., description="原始节点数")
    corrected_node_count: int = Field(..., description="修正后节点数")
    inserted_node_count: int = Field(default=0, description="插入节点数")
    dropped_node_count: int = Field(default=0, description="删除节点数")
    raw_match_ratio: float = Field(default=1.0, description="原始节点匹配率")
    detour_ratio: float = Field(default=1.0, description="绕行比 = 修正路径长度 / 起终点最短路长度")
    reverse_edge_count: int = Field(default=0, description="反向边数量")
    backward_progress_count: int = Field(default=0, description="到终点距离反增次数")
    backward_progress_distance: float = Field(default=0.0, description="到终点距离反增累计距离(米)")
    u_turn_count: int = Field(default=0, description="几何掉头次数")
    repeated_node_count: int = Field(default=0, description="重复出现的节点数")
    backtrack_index: float = Field(default=0.0, description="综合折返指数 0-100")
    repair_confidence: float = Field(default=100.0, description="修正置信度 0-100")
    repair_status: str = Field(default="HIGH_CONFIDENCE", description="修正状态")
    repair_detail: dict = Field(default_factory=dict, description="修正详情")
    corrected_geo_points: list[dict] = Field(default_factory=list, description="修正后经纬度序列")

    model_config = {"arbitrary_types_allowed": True}


# ============================================================
# 任务参数与结果
# ============================================================


class PathRepairParams(BaseModel):
    """路径修正任务输入参数"""
    input_csv: str = Field(..., description="输入CSV文件路径")
    output_csv: str = Field(..., description="输出CSV文件路径")
    topology_version: str = Field(default="202512", description="拓扑数据版本")
    limit: Optional[int] = Field(default=None, description="限制处理条数，None=全部")
    detail_geo: bool = Field(default=True, description="是否输出经纬度详情")

    model_config = {"arbitrary_types_allowed": True}


class PathRepairTaskResult(BaseModel):
    """路径修正任务执行结果"""
    status: str = Field(default="pending", description="任务状态: pending/running/success/failed")
    totalRecords: int = Field(default=0, description="总处理记录数")
    successRecords: int = Field(default=0, description="成功修正记录数")
    failedRecords: int = Field(default=0, description="失败记录数")
    highConfidenceCount: int = Field(default=0, description="高置信度记录数")
    mediumConfidenceCount: int = Field(default=0, description="中置信度记录数")
    lowConfidenceCount: int = Field(default=0, description="低置信度记录数")
    needReviewCount: int = Field(default=0, description="需要人工复核记录数")
    outputCsvPath: Optional[str] = Field(default=None, description="输出CSV文件路径")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息")
    executionTime: Optional[float] = Field(default=None, description="执行时间(秒)")

    model_config = {"arbitrary_types_allowed": True}
