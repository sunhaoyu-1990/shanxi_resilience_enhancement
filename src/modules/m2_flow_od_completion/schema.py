"""
M2 流量与OD迁移统计补全模块 Pydantic Schema
定义任务参数和结果的输入/输出结构
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class M2TaskParams(BaseModel):
  """M2 流量与OD迁移统计补全任务参数"""

  schemeId: str = Field(..., description="施工方案ID")
  startDate: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  endDate: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="是否覆盖已有数据")

  model_config = {"arbitrary_types_allowed": True}


class M2TaskResult(BaseModel):
  """M2 流量与OD迁移统计补全任务结果"""

  status: str = Field(..., description="任务状态: pending/running/success/failed")
  recordsProcessed: int = Field(default=0, description="已处理的记录数")
  errors: list[str] = Field(default_factory=list, description="错误信息列表")
  warnings: list[str] = Field(default_factory=list, description="警告信息列表")
  executionTime: Optional[float] = Field(default=None, description="执行时间（秒）")

  model_config = {"arbitrary_types_allowed": True}


class SectionODFlowRecord(BaseModel):
  """路段-OD流量日统计记录（带数据来源标识）"""

  odId: str
  sectionId: str
  sectionNumber: str
  schemeId: str
  statDate: date
  flowPcu: int = 0
  sourceFlag: str = Field(..., description="数据来源: actual/filled/rule")
  passengerFlow: Optional[float] = None
  truckFlow: Optional[int] = None
  avgSpeed: Optional[float] = None

  model_config = {"from_attributes": True}


class SectionFlowRecord(BaseModel):
  """路段总流量日统计记录"""

  sectionId: str
  sectionNumber: str
  schemeId: str
  statDate: date
  totalFlowPcu: int = 0
  sourceFlag: str = Field(..., description="数据来源: actual/filled/rule")
  passengerFlow: Optional[float] = None
  truckFlow: Optional[int] = None
  odCount: Optional[int] = None

  model_config = {"from_attributes": True}


class M2CheckResult(BaseModel):
  """M2 校验检查结果"""

  table: str
  check: str
  valid: bool
  errors: list[str] = Field(default_factory=list)
  warnings: list[str] = Field(default_factory=list)
  recordCount: Optional[int] = None

  model_config = {"arbitrary_types_allowed": True}
