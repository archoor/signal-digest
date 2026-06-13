"""Reviews API 响应模型。"""

from __future__ import annotations

from pydantic import BaseModel

from app.models.app_review import AppReview
from app.models.enums import Priority, Sentiment


class ReviewInsightBrief(BaseModel):
    summary: str | None
    feature_area: str | None
    sentiment: Sentiment
    priority: Priority


class ReviewHighlightEntry(BaseModel):
    review: AppReview
    insight: ReviewInsightBrief


class ReviewHighlightsRead(BaseModel):
    praise: list[ReviewHighlightEntry]
    complaints: list[ReviewHighlightEntry]
