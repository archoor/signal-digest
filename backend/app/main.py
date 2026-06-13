"""FastAPI 应用入口（设计文档第 5.1）。

启动时建表并按需启动调度器；提供健康检查与 /api 全部路由。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    init_db()
    logger.info("%s 启动，env=%s", settings.app_name, settings.environment)

    if settings.enable_scheduler:
        from app.scheduler.jobs import shutdown_scheduler, start_scheduler

        start_scheduler()
        try:
            yield
        finally:
            shutdown_scheduler()
    else:
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="App 评论信号周报系统 - SignalDigest for App Reviews",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 允许前端（Next.js dev server / 同源部署）跨域访问 API（设计文档第 5.1 前端对接）。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
