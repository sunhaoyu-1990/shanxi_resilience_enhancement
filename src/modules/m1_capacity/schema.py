"""
M1 通行能力评估模块 Pydantic Schema
定义任务参数和结果的输入/输出结构
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class M1TaskParams(BaseModel):
  """M1 通行能力评估任务参数"""

  schemeId: str = Field(..., description="施工方案ID")
  startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="是否覆盖已有数据")

  model_config = {"arbitrary_types_allowed": True}


class M1TaskResult(BaseModel):
  """M1 通行能力评估任务结果"""

  status: str = Field(..., description="任务状态: pending/running/success/failed")
  recordsProcessed: int = Field(default=0, description="已处理的记录数")
  errors: list[str] = Field(default_factory=list, description="错误信息列表")
  warnings: list[str] = Field(default_factory=list, description="警告信息列表")
  executionTime: Optional[float] = Field(default=None, description="执行时间（秒）")

  model_config = {"arbitrary_types_allowed": True}


class SectionCapacityRecord(BaseModel):
  """路段通行能力日统计记录"""

  sectionId: str
  sectionNumber: str
  schemeId: str
  statDate: date
  laneCnt: int = 0
  laneOccupiedCnt: int = 0
  availableLaneCnt: int = 0
  capacityPcu: int = 0
  speedLimit: int = 0
  constructionMode: Optional[str] = None
  capacityLevel: Optional[str] = None  # A/B/C/D/E/F 等级

  model_config = {"from_attributes": True}


class CapacityRuleRecord(BaseModel):
  """通行能力规则参考记录"""

  availableLaneCnt: int
  capacityPcu: int
  speedLimit: int
  capacityLevel: str
  constructionMode: Optional[str] = None

  model_config = {"from_attributes": True}


class M1CheckResult(BaseModel):
  """M1 校验检查结果"""

  table: str
  check: str
  valid: bool
  errors: list[str] = Field(default_factory=list)
  warnings: list[str] = Field(default_factory=list)
  recordCount: Optional[int] = None

  model_config = {"arbitrary_types_allowed": True}
