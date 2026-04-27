"""
API Pydantic Schema 模块
查询 API 的请求和响应模型定义
"""

from datetime import date, datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


# ============ 通用 Schema ============

class PaginationParams(BaseModel):
  """分页参数"""
  page: int = Field(default=1, ge=1)
  page_size: int = Field(default=50, ge=1, le=1000)


class APIResponse(BaseModel):
  """标准 API 响应包装"""
  success: bool = True
  message: Optional[str] = None
  data: Optional[Any] = None
  meta: Optional[dict] = None


# ============ 任务 Schema ============

class SchemeRunRequest(BaseModel):
  """运行方案流水线的请求"""
  scheme_id: str = Field(..., description="施工方案ID")
  start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  modules: Optional[list[str]] = Field(
    default=None,
    description="要执行的模块（默认全部）",
  )
  overwrite: bool = Field(default=False, description="覆盖已有结果")


class ModuleRunRequest(BaseModel):
  """运行单个模块的请求"""
  module: str = Field(..., description="模块代码 (m0-m5)")
  scheme_id: str = Field(..., description="施工方案ID")
  start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
  end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
  overwrite: bool = Field(default=False, description="覆盖已有结果")


class TaskStatus(BaseModel):
  """任务执行状态"""
  task_id: str
  module: str
  status: str  # pending, running, success, failed, partial_success
  progress: int = Field(ge=0, le=100)
  started_at: Optional[datetime] = None
  completed_at: Optional[datetime] = None
  message: Optional[str] = None


class TaskListResponse(BaseModel):
  """任务列表"""
  tasks: list[TaskStatus]
  total: int


# ============ 结果 Schema ============

class SchemeSummary(BaseModel):
  """方案汇总结果"""
  scheme_id: str
  scheme_name: Optional[str] = None
  start_date: Optional[date] = None
  end_date: Optional[date] = None
  impacted_section_cnt: int = 0
  impacted_od_cnt: int = 0
  total_fee_increase: float = 0.0
  total_fee_decrease: float = 0.0
  net_fee_impact: float = 0.0
  recommended_plan_cnt: int = 0


class SectionImpact(BaseModel):
  """路段影响结果"""
  section_id: str
  section_name: Optional[str] = None
  lane_cnt: int
  lane_occupied_cnt: int
  available_lane_cnt: int
  capacity_pcu: float
  construction_mode: Optional[str] = None


class PathComparison(BaseModel):
  """OD 路径对比结果"""
  od_id: str
  entry_station: str
  exit_station: str
  original_path_id: Optional[str] = None
  candidate_paths: list[dict] = []


class TollImpact(BaseModel):
  """通行费影响结果"""
  scheme_id: str
  stat_date: date
  od_id: str
  vehicle_type: str
  original_fee_amount: float
  diverted_fee_amount: float
  fee_change_amount: float
  impact_type: str
  recommended_path_id: Optional[str] = None


# ============ 汇总 Schema ============

class SchemeSummaryListResponse(BaseModel):
  """方案汇总列表"""
  schemes: list[SchemeSummary]
  total: int


class SectionImpactListResponse(BaseModel):
  """路段影响列表"""
  scheme_id: str
  sections: list[SectionImpact]
  total: int


class PathComparisonListResponse(BaseModel):
  """路径对比列表"""
  od_id: str
  comparisons: list[PathComparison]
  total: int


class TollImpactListResponse(BaseModel):
  """通行费影响列表"""
  scheme_id: str
  impacts: list[TollImpact]
  total: int
  summary: dict = {}
