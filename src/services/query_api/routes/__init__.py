"""
src.services.query_api.routes 包
API 路由处理器
"""

from src.services.query_api.routes.tasks import router as tasks_router
from src.services.query_api.routes.results import router as results_router

__all__ = ["tasks_router", "results_router"]
