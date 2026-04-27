"""
任务管理 API 路由
处理任务提交和状态查询
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends

from src.app.logger import get_logger
from src.app.enums import ModuleCode, TaskStatus as TaskStatusEnum
from src.services.query_api.schemas import (
  SchemeRunRequest,
  ModuleRunRequest,
  TaskStatus,
  TaskListResponse,
  APIResponse,
)
from src.services.query_api.deps import get_current_user

logger = get_logger(__name__)
router = APIRouter()

# 内存任务存储（生产环境应替换为 Redis 或数据库）
_tasks: dict[str, TaskStatus] = {}


@router.post("/scheme-run", response_model=APIResponse)
async def run_scheme_task(
  request: SchemeRunRequest,
  current_user: dict = Depends(get_current_user),
):
  """
  提交方案流水线任务

  按顺序执行 M0 ~ M5，处理指定的方案和日期范围。
  """
  task_id = f"TASK_{datetime.now().strftime('%Y%m%d%H%M%S')}"

  # 创建任务记录
  task = TaskStatus(
    task_id=task_id,
    module="pipeline",
    status="pending",
    progress=0,
    message=f"已提交方案 {request.scheme_id} 的流水线任务",
  )
  _tasks[task_id] = task

  logger.info(f"任务 {task_id} 已提交，方案: {request.scheme_id}")

  # TODO: 提交到任务队列或异步执行
  # 目前直接返回 task_id

  return APIResponse(
    success=True,
    message="任务提交成功",
    data={"task_id": task_id, "status": task.status},
  )


@router.post("/module-run", response_model=APIResponse)
async def run_module_task(
  request: ModuleRunRequest,
  current_user: dict = Depends(get_current_user),
):
  """
  提交单个模块任务

  执行指定的模块（M0-M5），处理指定的方案和日期范围。
  """
  # 校验模块代码
  try:
    ModuleCode(request.module)
  except ValueError:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"无效的模块代码: {request.module}，有效值: m0-m5",
    )

  task_id = f"TASK_{request.module.upper()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

  # 创建任务记录
  task = TaskStatus(
    task_id=task_id,
    module=request.module,
    status="pending",
    progress=0,
    message=f"已提交模块 {request.module} 任务，方案: {request.scheme_id}",
  )
  _tasks[task_id] = task

  logger.info(f"模块任务 {task_id} 已提交: {request.module}")

  # TODO: 提交到任务队列或异步执行

  return APIResponse(
    success=True,
    message="模块任务提交成功",
    data={"task_id": task_id, "status": task.status},
  )


@router.get("/{task_id}", response_model=APIResponse)
async def get_task_status(task_id: str):
  """
  获取任务状态
  """
  if task_id not in _tasks:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"任务未找到: {task_id}",
    )

  task = _tasks[task_id]
  return APIResponse(
    success=True,
    data=task.model_dump(),
  )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
  module: Optional[str] = None,
  status_filter: Optional[str] = None,
  limit: int = 100,
):
  """
  列出所有任务，支持过滤
  """
  tasks = list(_tasks.values())

  # 按模块过滤
  if module:
    tasks = [t for t in tasks if t.module == module]

  # 按状态过滤
  if status_filter:
    tasks = [t for t in tasks if t.status == status_filter]

  # 按提交时间倒序排列（最新的在前）
  tasks = sorted(tasks, key=lambda t: t.task_id, reverse=True)

  # 应用 limit
  tasks = tasks[:limit]

  return TaskListResponse(
    tasks=tasks,
    total=len(tasks),
  )


@router.delete("/{task_id}", response_model=APIResponse)
async def cancel_task(task_id: str):
  """
  取消待执行或正在运行的任务
  """
  if task_id not in _tasks:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"任务未找到: {task_id}",
    )

  task = _tasks[task_id]

  if task.status in ("success", "failed"):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"无法取消状态为 {task.status} 的任务",
    )

  task.status = "cancelled"
  task.message = "任务已被用户取消"

  logger.info(f"任务 {task_id} 已取消")

  return APIResponse(
    success=True,
    message=f"任务 {task_id} 已取消",
    data={"task_id": task_id, "status": "cancelled"},
  )
