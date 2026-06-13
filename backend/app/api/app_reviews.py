"""Reviews 路由（设计文档第 10.3）。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import or_
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.models.app_review import AppReview
from app.models.enums import Platform, Priority, Sentiment
from app.models.review_insight import ReviewInsight
from app.schemas.reviews import ReviewHighlightEntry, ReviewHighlightsRead, ReviewInsightBrief
from app.services.review_classifier import is_displayable_summary

router = APIRouter(prefix="/reviews", tags=["reviews"])

_PRIORITY_ORDER = {
    Priority.P0: 0,
    Priority.P1: 1,
    Priority.P2: 2,
    Priority.P3: 3,
    Priority.NONE: 4,
}


def _review_filters(app_id: int, platform: Platform | None):
    clauses = [AppReview.monitored_app_id == app_id]
    if platform is not None:
        clauses.append(AppReview.platform == platform)
    return clauses


def _dedupe_highlight_rows(
    rows: list[tuple[AppReview, ReviewInsight]],
) -> list[tuple[AppReview, ReviewInsight]]:
    """同一评论可能有多条 insight（历史重复写入），只保留最新一条。"""
    by_review: dict[int, tuple[AppReview, ReviewInsight]] = {}
    for review, insight in rows:
        review_id = insight.review_id
        prev = by_review.get(review_id)
        if prev is None or insight.created_at > prev[1].created_at:
            by_review[review_id] = (review, insight)
    return list(by_review.values())


def _platform_stats(session, app_id: int) -> dict:
    by_platform: dict[str, dict] = {}
    for plat in (Platform.APP_STORE, Platform.GOOGLE_PLAY):
        total = session.exec(
            select(func.count())
            .select_from(AppReview)
            .where(AppReview.monitored_app_id == app_id, AppReview.platform == plat)
        ).one()
        avg_rating = session.exec(
            select(func.avg(AppReview.rating)).where(
                AppReview.monitored_app_id == app_id, AppReview.platform == plat
            )
        ).one()
        if total:
            by_platform[plat.value] = {
                "total": total,
                "avg_rating": avg_rating,
            }
    return by_platform


@router.get("")
def list_reviews(
    session: SessionDep,
    app_id: int = Query(..., description="MonitoredApp id"),
    platform: Platform | None = Query(None),
    limit: int = Query(50, le=200),
) -> list[AppReview]:
    stmt = (
        select(AppReview)
        .where(*_review_filters(app_id, platform))
        .order_by(AppReview.source_created_at.desc())
        .limit(limit)
    )
    return list(session.exec(stmt).all())


@router.get("/stats")
def review_stats(
    session: SessionDep,
    app_id: int = Query(...),
    platform: Platform | None = Query(None),
) -> dict:
    clauses = _review_filters(app_id, platform)
    total = session.exec(
        select(func.count()).select_from(AppReview).where(*clauses)
    ).one()
    avg_rating = session.exec(
        select(func.avg(AppReview.rating)).where(*clauses)
    ).one()
    return {
        "app_id": app_id,
        "total": total,
        "avg_rating": avg_rating,
        "by_platform": _platform_stats(session, app_id),
    }


@router.get("/urgent")
def urgent_reviews(
    session: SessionDep,
    app_id: int = Query(...),
    platform: Platform | None = Query(None),
    limit: int = Query(50, le=200),
) -> list[AppReview]:
    """高优先级评论：P0/P1（第 10.3 / 8.2）。"""
    stmt = (
        select(AppReview)
        .join(ReviewInsight, ReviewInsight.review_id == AppReview.id)
        .where(
            *_review_filters(app_id, platform),
            ReviewInsight.priority.in_([Priority.P0, Priority.P1]),
        )
        .distinct()
        .order_by(AppReview.source_created_at.desc())
        .limit(limit)
    )
    return list(session.exec(stmt).all())


@router.get("/highlights", response_model=ReviewHighlightsRead)
def review_highlights(
    session: SessionDep,
    app_id: int = Query(...),
    platform: Platform | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> ReviewHighlightsRead:
    """评论重点：好评（好在哪里）与差评（痛点）分栏展示。"""
    base = _review_filters(app_id, platform)

    praise_stmt = (
        select(AppReview, ReviewInsight)
        .join(ReviewInsight, ReviewInsight.review_id == AppReview.id)
        .where(
            *base,
            ReviewInsight.sentiment == Sentiment.POSITIVE,
            AppReview.rating >= 4,
        )
        .order_by(AppReview.source_created_at.desc())
        .limit(limit)
    )
    praise_rows = _dedupe_highlight_rows(list(session.exec(praise_stmt).all()))

    complaint_stmt = (
        select(AppReview, ReviewInsight)
        .join(ReviewInsight, ReviewInsight.review_id == AppReview.id)
        .where(
            *base,
            or_(
                ReviewInsight.sentiment.in_([Sentiment.NEGATIVE, Sentiment.URGENT]),
                AppReview.rating <= 2,
            ),
        )
        .limit(limit * 3)
    )
    complaint_rows = _dedupe_highlight_rows(list(session.exec(complaint_stmt).all()))
    complaint_rows.sort(
        key=lambda row: (
            _PRIORITY_ORDER.get(row[1].priority, 99),
            -row[0].source_created_at.timestamp(),
        )
    )
    complaint_rows = complaint_rows[:limit]

    def _entry(review: AppReview, insight: ReviewInsight) -> ReviewHighlightEntry:
        summary = insight.summary if is_displayable_summary(insight.summary) else None
        return ReviewHighlightEntry(
            review=review,
            insight=ReviewInsightBrief(
                summary=summary,
                feature_area=insight.feature_area,
                sentiment=insight.sentiment,
                priority=insight.priority,
            ),
        )

    return ReviewHighlightsRead(
        praise=[_entry(r, i) for r, i in praise_rows],
        complaints=[_entry(r, i) for r, i in complaint_rows],
    )
