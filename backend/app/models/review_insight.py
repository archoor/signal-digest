"""ReviewInsight 模型（设计文档第 6.4）。

由轻量分类器或 LLM 对单条评论打标签的结果。
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow
from app.models.enums import Intent, Priority, Sentiment


class ReviewInsight(SQLModel, table=True):
    __tablename__ = "review_insight"

    id: int | None = Field(default=None, primary_key=True)
    review_id: int = Field(foreign_key="app_review.id", index=True, unique=True)

    sentiment: Sentiment
    intent: Intent
    feature_area: str | None = None
    priority: Priority = Field(default=Priority.NONE, index=True)
    summary: str | None = None

    created_at: datetime = Field(default_factory=utcnow)
