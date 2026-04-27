"""
结果查询 API 路由
处理分析结果查询
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Query

from src.app.logger import get_logger
from src.app.enums import ModuleCode
from src.services.query_api.schemas import (
  APIResponse,
  SchemeSummary,
  SectionImpact,
  PathComparison,
  TollImpact,
  SchemeSummaryListResponse,
  SectionImpactListResponse,
  PathComparisonListResponse,
  TollImpactListResponse,
)
from src.services.query_api.deps import get_current_user, get_sql_runner_dep
from src.common.sql_runner import SqlRunner

logger = get_logger(__name__)
router = APIRouter()


@router.get("/schemes/{scheme_id}/summary", response_model=APIResponse)
async def get_scheme_summary(
  scheme_id: str,
  sql_runner: SqlRunner = Depends(get_sql_runner_dep),
):
  """
  获取方案的汇总结果

  返回聚合统计数据，包括：
  - 受影响路段数量
  - 受影响 OD 对数量
  - 通行费增减
  - 净通行费影响
  """
  # TODO: 表填充后替换为实际 SQL 查询
  # 目前返回模拟数据
  mock_summary = SchemeSummary(
    scheme_id=scheme_id,
    scheme_name=f"施工方案_{scheme_id}",
    start_date=date(2026, 4, 1),
    end_date=date(2026, 4, 30),
    impacted_section_cnt=0,  # TODO: 从 ads_scheme_summary 查询
    impacted_od_cnt=0,
    total_fee_increase=0.0,
    total_fee_decrease=0.0,
    net_fee_impact=0.0,
    recommended_plan_cnt=0,
  )

  return APIResponse(
    success=True,
    data=mock_summary.model_dump(),
  )


@router.get("/schemes/{scheme_id}/sections", response_model=APIResponse)
async def get_scheme_sections(
  scheme_id: str,
  sql_runner: SqlRunner = Depends(get_sql_runner_dep),
):
  """
  获取方案的受影响路段

  返回施工影响详情列表。
  """
  # TODO: 替换为实际 SQL 查询
  # 从 dwd_scheme_section_map 关联 dim_section_info 查询

  return APIResponse(
    success=True,
    data={
      "scheme_id": scheme_id,
      "sections": [],  # TODO: 查询并返回路段影响
      "total": 0,
    },
  )


@router.get("/schemes/{scheme_id}/ods/{od_id}/paths", response_model=APIResponse)
async def get_od_paths(
  scheme_id: str,
  od_id: str,
  sql_runner: SqlRunner = Depends(get_sql_runner_dep),
):
  """
  获取指定方案下某 OD 的路径对比

  返回原始路径和候选替代路径的收费/里程对比。
  """
  # TODO: 替换为实际 SQL 查询
  # 从 dws_od_candidate_path 查询

  return APIResponse(
    success=True,
    data={
      "scheme_id": scheme_id,
      "od_id": od_id,
      "entry_station": "STATION_A",
      "exit_station": "STATION_B",
      "original_path_id": None,
      "candidate_paths": [],  # TODO: 查询并返回路径
    },
  )


@router.get("/schemes/{scheme_id}/toll-impact", response_model=APIResponse)
async def get_toll_impact(
  scheme_id: str,
  start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
  end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
  vehicle_type: Optional[str] = Query(None, description="按车型过滤"),
  od_id: Optional[str] = Query(None, description="按 OD ID 过滤"),
  page: int = Query(1, ge=1),
  page_size: int = Query(50, ge=1, le=1000),
  sql_runner: SqlRunner = Depends(get_sql_runner_dep),
):
  """
  获取方案的通行费影响结果

  返回详细的通行费影响记录，支持过滤。
  """
  # TODO: 替换为实际 SQL 查询
  # 从 ads_toll_impact_result 查询

  return APIResponse(
    success=True,
    data={
      "scheme_id": scheme_id,
      "impacts": [],  # TODO: 查询并返回通行费影响
      "total": 0,
      "summary": {
        "total_fee_increase": 0.0,
        "total_fee_decrease": 0.0,
        "net_impact": 0.0,
      },
    },
    meta={
      "page": page,
      "page_size": page_size,
    },
  )


@router.get("/schemes", response_model=APIResponse)
async def list_schemes(
  status_filter: Optional[str] = Query(None, description="按状态过滤"),
  page: int = Query(1, ge=1),
  page_size: int = Query(50, ge=1, le=1000),
  sql_runner: SqlRunner = Depends(get_sql_runner_dep),
):
  """
  列出所有方案及其分析汇总

  返回分页的方案列表及其分析结果摘要。
  """
  # TODO: 替换为实际 SQL 查询
  # 从 dim_scheme_info 关联 ads_scheme_summary 查询

  return APIResponse(
    success=True,
    data={
      "schemes": [],  # TODO: 查询并返回方案
      "total": 0,
    },
    meta={
      "page": page,
      "page_size": page_size,
    },
  )


@router.get("/ods", response_model=APIResponse)
async def list_ods(
  scheme_id: Optional[str] = Query(None, description="按方案过滤"),
  page: int = Query(1, ge=1),
  page_size: int = Query(50, ge=1, le=1000),
  sql_runner: SqlRunner = Depends(get_sql_runner_dep),
):
  """
  列出所有 OD 对，支持按方案过滤

  返回有分析结果的 OD 对分页列表。
  """
  # TODO: 替换为实际 SQL 查询

  return APIResponse(
    success=True,
    data={
      "ods": [],  # TODO: 查询并返回 OD
      "total": 0,
    },
    meta={
      "page": page,
      "page_size": page_size,
    },
  )
