"""
M5 通行费影响测算模块 Pydantic 模型
定义任务参数和结果的数据结构
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class M5TaskParams(BaseModel):
  """M5 通行费影响测算任务参数"""

  schemeId: str = Field(..., description="施工方案ID")
  startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="是否覆盖已有数据")

  model_config = {"arbitrary_types_allowed": True}


class M5TaskResult(BaseModel):
  """M5 通行费影响测算任务结果"""

  status: str = Field(..., description="任务状态: pending/running/success/failed")
  recordsProcessed: int = Field(default=0, description="已处理记录数")
  errors: list[str] = Field(default_factory=list, description="错误信息列表")
  warnings: list[str] = Field(default_factory=list, description="警告信息列表")
  executionTime: Optional[float] = Field(default=None, description="执行时间（秒）")

  model_config = {"arbitrary_types_allowed": True}


class TollImpactRecord(BaseModel):
  """通行费影响结果记录"""

  odId: str
  schemeId: str
  statDate: date
  vehicleType: Optional[str] = None
  originalPathId: str
  recommendedPathId: str
  divertedFlowPcu: int = 0
  originalFeeYuan: float = 0.0
  divertedFeeYuan: float = 0.0
  feeImpactYuan: float = 0.0  # diverted_flow * fee_diff
  impactType: str = Field(..., description="影响类型: fee_increase/fee_decrease/no_impact")
  mileageDiff: float = 0.0

  model_config = {"from_attributes": True}


class SchemeSummaryRecord(BaseModel):
  """方案汇总记录"""

  schemeId: str
  statDate: Optional[date] = None
  impactedSectionCnt: int = 0
  impactedOdCnt: int = 0
  totalDivertedFlowPcu: int = 0
  totalFeeIncreaseYuan: float = 0.0
  totalFeeDecreaseYuan: float = 0.0
  netFeeImpactYuan: float = 0.0
  recommendedPlanCnt: int = 0
  avgFeeImpactPerVehicle: float = 0.0

  model_config = {"from_attributes": True}


class M5CheckResult(BaseModel):
  """M5 校验检查结果"""

  table: str
  check: str
  valid: bool
  errors: list[str] = Field(default_factory=list)
  warnings: list[str] = Field(default_factory=list)
  recordCount: Optional[int] = None

  model_config = {"arbitrary_types_allowed": True}
