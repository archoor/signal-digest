"""周期对比与变化检测（设计文档第 7.3）。

对比当前 7 天窗口与上一 7 天窗口，聚合评分、情绪、主题、竞品变化，
产出喂给 LLM 的结构化「变化摘要」与证据评论候选。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models.app_review import AppReview
from app.models.base import utcnow
from app.models.enums import SourceKind


@dataclass(slots=True)
class WindowStats:
    """单个时间窗口的聚合统计。"""

    review_count: int = 0
    avg_rating: float | None = None
    rating_distribution: dict[int, int] = field(default_factory=dict)


@dataclass(slots=True)
class ChangeContext:
    """变化检测产物，作为 digest_generator 的输入。"""

    monitored_app_id: int
    period_start: datetime
    period_end: datetime
    current: WindowStats
    previous: WindowStats
    current_reviews: list[AppReview]
    competitor_reviews: list[AppReview]


def _window_stats(reviews: list[AppReview]) -> WindowStats:
    if not reviews:
        return WindowStats()
    ratings = [r.rating for r in reviews if r.rating is not None]
    dist: dict[int, int] = {}
    for r in ratings:
        dist[r] = dist.get(r, 0) + 1
    avg = round(sum(ratings) / len(ratings), 2) if ratings else None
    return WindowStats(review_count=len(reviews), avg_rating=avg, rating_distribution=dist)


def build_change_context(
    session: Session, monitored_app_id: int, *, now: datetime | None = None
) -> ChangeContext:
    """构建当前周与上一周的对比上下文。"""
    now = now or utcnow()
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    def _fetch(start: datetime, end: datetime, *, own: bool) -> list[AppReview]:
        kind = SourceKind.OWN if own else SourceKind.COMPETITOR
        stmt = select(AppReview).where(
            AppReview.monitored_app_id == monitored_app_id
            if own
            else AppReview.competitor_app_id.is_not(None),
            AppReview.source_kind == kind,
            AppReview.source_created_at >= start,
            AppReview.source_created_at < end,
        )
        return list(session.exec(stmt).all())

    current_reviews = _fetch(current_start, now, own=True)
    previous_reviews = _fetch(previous_start, current_start, own=True)
    competitor_reviews = _fetch(current_start, now, own=False)

    return ChangeContext(
        monitored_app_id=monitored_app_id,
        period_start=current_start,
        period_end=now,
        current=_window_stats(current_reviews),
        previous=_window_stats(previous_reviews),
        current_reviews=current_reviews,
        competitor_reviews=competitor_reviews,
    )
