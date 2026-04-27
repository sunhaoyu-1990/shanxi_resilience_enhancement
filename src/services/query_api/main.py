"""
FastAPI 查询服务主应用

用法：
    uvicorn src.services.query_api.main:app --reload --port 8010
    python -m src.services.query_api.main
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 将项目根目录加入路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.logger import get_logger, setup_logging
from src.app.db import test_connection, check_postgis
from src.services.query_api.routes import tasks_router, results_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
  """应用生命周期管理"""
  # 启动时
  setup_logging()
  logger.info("正在启动陕交控韧性查询服务...")

  # 测试数据库连接
  if test_connection():
    logger.info("数据库连接验证通过")
  else:
    logger.warning("数据库连接失败 - 部分接口可能无法使用")

  # 检查 PostGIS
  if check_postgis():
    logger.info("PostGIS 扩展可用")
  else:
    logger.info("PostGIS 不可用 - GIS 功能已禁用")

  yield

  # 关闭时
  logger.info("正在关闭查询服务...")


def create_app() -> FastAPI:
  """创建并配置 FastAPI 应用"""
  app = FastAPI(
    title="陕交控韧性查询服务",
    description="施工方案分析结果查询服务",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
  )

  # 配置 CORS
  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  # 注册路由
  app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["Tasks"])
  app.include_router(results_router, prefix="/api/v1/results", tags=["Results"])

  @app.get("/health", tags=["Health"])
  async def health_check():
    """健康检查接口"""
    return {
      "status": "healthy",
      "service": "shaanxi-resilience-query-api",
      "version": "0.1.0",
    }

  @app.get("/", tags=["Root"])
  async def root():
    """根路径接口"""
    return {
      "message": "陕交控韧性查询服务",
      "version": "0.1.0",
      "docs": "/docs",
    }

  return app


# 创建应用实例
app = create_app()


def main():
  """启动 API 服务器"""
  import uvicorn

  uvicorn.run(
    "src.services.query_api.main:app",
    host="0.0.0.0",
    port=8010,
    reload=True,
    log_level="info",
  )


if __name__ == "__main__":
  main()
