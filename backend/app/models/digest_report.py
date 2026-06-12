"""DigestReport 模型（设计文档第 6.5）。

每个 App 每周生成一份周报，sections 为固定结构 JSON（第 9.3）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import DigestStatus


def empty_sections() -> dict:
    """周报 sections 的固定空骨架（第 6.5 / 9.3）。"""
    return {
        "top_changes": [],
        "new_complaints": [],
        "new_praise": [],
        "rating_movement": [],
        "release_impact": [],
        "competitor_moves": [],
        "recommended_actions": [],
        "confidence_notes": [],
    }


class DigestReport(TimestampMixin, table=True):
    __tablename__ = "digest_report"

    id: int | None = Field(default=None, primary_key=True)
    monitored_app_id: int = Field(foreign_key="monitored_app.id", index=True)

    period_start: datetime
    period_end: datetime

    status: DigestStatus = Field(default=DigestStatus.DRAFT, index=True)
    title: str = ""
    summary: str = ""

    sections: dict = Field(default_factory=empty_sections, sa_column=Column(JSON))
    evidence_review_ids: list[int] = Field(default_factory=list, sa_column=Column(JSON))

    llm_model: str | None = None
    tokens_used: int = 0
    notion_page_url: str | None = None
    sent_at: datetime | None = None
