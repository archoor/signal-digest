"""模型基类与公共字段。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """统一的 UTC 当前时间。"""
    return datetime.now(UTC)


class TimestampMixin(SQLModel):
    """带创建 / 更新时间的混入。"""

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
