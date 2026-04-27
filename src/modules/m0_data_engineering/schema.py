"""
M0 数据工程模块的 Pydantic 模型
定义任务参数与结果的输入输出结构
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class M0TaskParams(BaseModel):
  """M0 数据工程任务参数"""

  schemeId: str = Field(..., description="施工方案ID")
  startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="是否覆盖已有数据")

  model_config = {"arbitrary_types_allowed": True}


class M0TaskResult(BaseModel):
  """M0 数据工程任务结果"""

  status: str = Field(..., description="任务状态: pending/running/success/failed")
  recordsProcessed: int = Field(default=0, description="已处理的记录数")
  errors: list[str] = Field(default_factory=list, description="错误信息列表")
  warnings: list[str] = Field(default_factory=list, description="警告信息列表")
  executionTime: Optional[float] = Field(default=None, description="执行时间（秒）")

  model_config = {"arbitrary_types_allowed": True}


class SectionInfoRecord(BaseModel):
  """路段信息记录"""

  sectionId: str
  sectionName: Optional[str] = None
  roadId: Optional[str] = None
  roadName: Optional[str] = None
  direction: Optional[str] = None
  laneCnt: int = 0
  sectionNumber: str
  validStartDate: Optional[date] = None
  validEndDate: Optional[date] = None

  model_config = {"from_attributes": True}


class SchemeSectionMapRecord(BaseModel):
  """方案-路段映射记录"""

  schemeId: str
  sectionId: str
  laneOccupiedCnt: int = 0
  constructionMode: Optional[str] = None
  speedLimit: Optional[int] = None
  validStartDate: Optional[date] = None
  validEndDate: Optional[date] = None

  model_config = {"from_attributes": True}


class ODPathMapRecord(BaseModel):
  """OD-路径映射记录"""

  odId: str
  pathId: str
  entryStationId: str
  exitStationId: str
  pathSections: Optional[str] = None
  sourceFlag: str = "actual"

  model_config = {"from_attributes": True}
