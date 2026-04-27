"""
M4 分流路径优化模块 Pydantic 模型
定义任务参数和结果的数据结构
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class M4TaskParams(BaseModel):
  """M4 分流路径优化任务参数"""

  schemeId: str = Field(..., description="施工方案ID")
  startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="是否覆盖已有数据")

  model_config = {"arbitrary_types_allowed": True}


class M4TaskResult(BaseModel):
  """M4 分流路径优化任务结果"""

  status: str = Field(..., description="任务状态: pending/running/success/failed")
  recordsProcessed: int = Field(default=0, description="已处理记录数")
  errors: list[str] = Field(default_factory=list, description="错误信息列表")
  warnings: list[str] = Field(default_factory=list, description="警告信息列表")
  executionTime: Optional[float] = Field(default=None, description="执行时间（秒）")

  model_config = {"arbitrary_types_allowed": True}


class CandidatePathRecord(BaseModel):
  """OD 对的候选分流路径"""

  odId: str
  pathId: str
  schemeId: str
  statDate: date
  originalPathId: Optional[str] = None
  controlSectionId: Optional[str] = None  # 施工中的路段
  mileageKm: float = 0.0
  mileageDiff: float = 0.0  # 与原路径相比的里程差
  feeYuan: float = 0.0
  feeDiff: float = 0.0  # 与原路径相比的费用差
  travelTimeMin: Optional[float] = None
  isViable: bool = True
  pathRank: Optional[int] = None  # 备选路径中的排名

  model_config = {"from_attributes": True}


class DiversionPlanRecord(BaseModel):
  """OD 对的分流方案"""

  odId: str
  schemeId: str
  statDate: date
  originalPathId: str
  recommendedPathId: str
  controlSectionId: str
  divertedFlowPcu: int = 0
  mileageDiff: float = 0.0
  feeDiff: float = 0.0
  travelTimeDiffMin: Optional[float] = None
  diversionRatio: float = 0.0
  planStatus: str = "recommended"  # recommended/accepted/rejected

  model_config = {"from_attributes": True}


class M4CheckResult(BaseModel):
  """M4 校验检查结果"""

  table: str
  check: str
  valid: bool
  errors: list[str] = Field(default_factory=list)
  warnings: list[str] = Field(default_factory=list)
  recordCount: Optional[int] = None

  model_config = {"arbitrary_types_allowed": True}
