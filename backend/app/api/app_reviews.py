"""Reviews 路由（设计文档第 10.3）。"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.models.app_review import AppReview
from app.models.enums import Priority
from app.models.review_insight import ReviewInsight

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
def list_reviews(
    session: SessionDep,
    app_id: int = Query(..., description="MonitoredApp id"),
    limit: int = Query(50, le=200),
) -> list[AppReview]:
    stmt = (
        select(AppReview)
        .where(AppReview.monitored_app_id == app_id)
        .order_by(AppReview.source_created_at.desc())
        .limit(limit)
    )
    return list(session.exec(stmt).all())


@router.get("/stats")
def review_stats(session: SessionDep, app_id: int = Query(...)) -> dict:
    total = session.exec(
        select(func.count()).select_from(AppReview).where(
            AppReview.monitored_app_id == app_id
        )
    ).one()
    avg_rating = session.exec(
        select(func.avg(AppReview.rating)).where(AppReview.monitored_app_id == app_id)
    ).one()
    return {"app_id": app_id, "total": total, "avg_rating": avg_rating}


@router.get("/urgent")
def urgent_reviews(
    session: SessionDep, app_id: int = Query(...), limit: int = Query(50, le=200)
) -> list[AppReview]:
    """高优先级评论：P0/P1（第 10.3 / 8.2）。"""
    stmt = (
        select(AppReview)
        .join(ReviewInsight, ReviewInsight.review_id == AppReview.id)
        .where(
            AppReview.monitored_app_id == app_id,
            ReviewInsight.priority.in_([Priority.P0, Priority.P1]),
        )
        .limit(limit)
    )
    return list(session.exec(stmt).all())
