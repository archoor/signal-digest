"""AppReview 模型（设计文档第 6.3）。

去重唯一键：platform + external_review_id。
若平台无稳定 review_id，external_review_id 用
sha256(platform + app_identifier + body + source_created_at) 兜底。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import utcnow
from app.models.enums import Platform, SourceKind


class AppReview(SQLModel, table=True):
    __tablename__ = "app_review"
    __table_args__ = (
        UniqueConstraint("platform", "external_review_id", name="uq_platform_review"),
    )

    id: int | None = Field(default=None, primary_key=True)

    # own 评论关联 monitored_app_id；competitor 评论关联 competitor_app_id。
    monitored_app_id: int | None = Field(
        default=None, foreign_key="monitored_app.id", index=True
    )
    competitor_app_id: int | None = Field(
        default=None, foreign_key="competitor_app.id", index=True
    )

    source_kind: SourceKind
    platform: Platform = Field(index=True)
    external_review_id: str = Field(index=True)

    rating: int | None = None
    title: str | None = None
    body: str
    author_hash: str | None = None  # 第 15.1：作者名默认 hash，不存可识别个人信息

    country: str | None = Field(default=None, index=True)
    language: str | None = None
    app_version: str | None = Field(default=None, index=True)

    source_created_at: datetime = Field(index=True)
    fetched_at: datetime = Field(default_factory=utcnow)

    # 原始抓取负载，便于回溯与调试。
    raw_payload: dict | None = Field(default=None, sa_column=Column(JSON))
