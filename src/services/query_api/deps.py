"""
API 依赖注入模块
FastAPI 依赖注入函数
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.db import get_db
from src.app.settings import get_settings
from src.common.sql_runner import get_sql_runner, SqlRunner


def get_database() -> Generator[Session, None, None]:
  """FastAPI 依赖注入：数据库会话"""
  try:
    db = next(get_db())
    yield db
  finally:
    db.close()


def get_sql_runner_dep() -> SqlRunner:
  """FastAPI 依赖注入：SQL 执行器"""
  return get_sql_runner()


def get_current_user(token: str = None) -> dict:
  """
  FastAPI 依赖注入：当前用户认证

  TODO: 实现实际的认证逻辑
  """
  # 认证占位符
  return {
    "user_id": "system",
    "username": "system",
    "roles": ["admin"],
  }


def require_role(required_roles: list[str]):
  """
  基于角色的访问控制依赖工厂

  用法:
    @app.get("/admin", dependencies=[Depends(require_role(["admin"]))])
  """
  def role_checker(current_user: dict = Depends(get_current_user)):
    if not any(role in current_user.get("roles", []) for role in required_roles):
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"所需角色: {required_roles}",
      )
    return current_user

  return role_checker
