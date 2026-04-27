"""
M3 交通影响分析模块 Pydantic 模型
定义任务参数和结果的数据结构
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class M3TaskParams(BaseModel):
  """M3 交通影响分析任务参数"""

  schemeId: str = Field(..., description="施工方案ID")
  startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="是否覆盖已有数据")

  model_config = {"arbitrary_types_allowed": True}


class M3TaskResult(BaseModel):
  """M3 交通影响分析任务结果"""

  status: str = Field(..., description="任务状态: pending/running/success/failed")
  recordsProcessed: int = Field(default=0, description="已处理记录数")
  errors: list[str] = Field(default_factory=list, description="错误信息列表")
  warnings: list[str] = Field(default_factory=list, description="警告信息列表")
  executionTime: Optional[float] = Field(default=None, description="执行时间（秒）")

  model_config = {"arbitrary_types_allowed": True}


class ImpactedODFlowRecord(BaseModel):
  """受影响 OD 流量日记录"""

  odId: str
  sectionId: str
  sectionNumber: str
  schemeId: str
  statDate: date
  demandFlowPcu: int = 0
  capacityPcu: int = 0
  impactRatio: float = 0.0  # 当 capacity < demand 时，impact_ratio = (demand - capacity) / demand
  isImpacted: bool = False
  impactLevel: Optional[str] = None  # none/mild/moderate/severe
  originalFlowPcu: Optional[int] = None
  divertedFlowPcu: Optional[int] = None

  model_config = {"from_attributes": True}


class ImpactSummaryRecord(BaseModel):
  """影响汇总统计"""

  schemeId: str
  statDate: date
  totalOdCount: int = 0
  impactedOdCount: int = 0
  totalDemandPcu: int = 0
  totalCapacityPcu: int = 0
  avgImpactRatio: float = 0.0
  impactLevel: str = "none"  # none/mild/moderate/severe

  model_config = {"from_attributes": True}


class M3CheckResult(BaseModel):
  """M3 校验检查结果"""

  table: str
  check: str
  valid: bool
  errors: list[str] = Field(default_factory=list)
  warnings: list[str] = Field(default_factory=list)
  recordCount: Optional[int] = None

  model_config = {"arbitrary_types_allowed": True}
