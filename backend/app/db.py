"""数据库引擎与会话管理。

设计文档对应：第 5.2 节（SQLite 开发 / PostgreSQL 生产）。
"""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

# SQLite 需要 check_same_thread=False 以支持多线程（FastAPI + APScheduler）。
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_connect_args,
)


def init_db() -> None:
    """建表。

    MVP 阶段用 SQLModel.metadata.create_all 直接建表，
    生产引入 Alembic 迁移后可替换此函数。
    """
    # 确保所有模型已被导入并注册到 metadata。
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供一个数据库会话。"""
    with Session(engine) as session:
        yield session
