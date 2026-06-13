"""API 路由聚合（设计文档第 10 章）。"""

from fastapi import APIRouter

from app.api import app_reviews, competitors, digest_reports, monitored_apps, settings

api_router = APIRouter(prefix="/api")
api_router.include_router(monitored_apps.router)
api_router.include_router(competitors.router)
api_router.include_router(app_reviews.router)
api_router.include_router(digest_reports.router)
api_router.include_router(settings.router)

__all__ = ["api_router"]
