"""Reviews API 测试。"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.app_reviews import _dedupe_highlight_rows
from app.db import engine
from app.main import create_app
from app.models.app_review import AppReview
from app.models.base import utcnow
from app.models.enums import Intent, Platform, Priority, Sentiment, SourceKind
from app.models.review_insight import ReviewInsight


def _seed_reviews(app_id: int) -> None:
    uid = uuid4().hex[:8]
    with Session(engine) as session:
        r1 = AppReview(
            monitored_app_id=app_id,
            source_kind=SourceKind.OWN,
            platform=Platform.APP_STORE,
            external_review_id=f"r-positive-{uid}",
            rating=5,
            body="界面很清爽，上手快",
            source_created_at=utcnow(),
        )
        r2 = AppReview(
            monitored_app_id=app_id,
            source_kind=SourceKind.OWN,
            platform=Platform.GOOGLE_PLAY,
            external_review_id=f"r-negative-{uid}",
            rating=1,
            body="闪退无法登录",
            source_created_at=utcnow(),
        )
        session.add(r1)
        session.add(r2)
        session.commit()
        session.refresh(r1)
        session.refresh(r2)
        session.add(
            ReviewInsight(
                review_id=r1.id,
                sentiment=Sentiment.POSITIVE,
                intent=Intent.PRAISE,
                priority=Priority.NONE,
                summary="UI 简洁， onboarding 体验好",
            )
        )
        session.add(
            ReviewInsight(
                review_id=r2.id,
                sentiment=Sentiment.NEGATIVE,
                intent=Intent.BUG,
                priority=Priority.P1,
                summary="启动崩溃，登录流程失败",
                feature_area="auth",
            )
        )
        session.commit()


def test_dedupe_highlight_rows() -> None:
    uid = uuid4().hex[:8]
    with Session(engine) as session:
        review = AppReview(
            monitored_app_id=1,
            source_kind=SourceKind.OWN,
            platform=Platform.APP_STORE,
            external_review_id=f"dedupe-{uid}",
            rating=5,
            body="ok",
            source_created_at=utcnow(),
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        old = ReviewInsight(
            review_id=review.id,
            sentiment=Sentiment.POSITIVE,
            intent=Intent.PRAISE,
            priority=Priority.NONE,
            summary="old",
        )
        new = ReviewInsight(
            review_id=review.id,
            sentiment=Sentiment.POSITIVE,
            intent=Intent.PRAISE,
            priority=Priority.NONE,
            summary="new",
        )
        session.add(old)
        session.add(new)
        session.commit()
        session.refresh(old)
        session.refresh(new)

    rows = _dedupe_highlight_rows([(review, old), (review, new)])
    assert len(rows) == 1
    assert rows[0][1].summary == "new"


def test_urgent_reviews_no_duplicate_ids() -> None:
    client = TestClient(create_app())
    app_resp = client.post(
        "/api/apps",
        json={"name": "Urgent Dedup App", "app_store_id": "888999000"},
    )
    app_id = app_resp.json()["id"]
    _seed_reviews(app_id)

    resp = client.get("/api/reviews/urgent", params={"app_id": app_id})
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert len(ids) == len(set(ids))


def test_review_stats_by_platform() -> None:
    client = TestClient(create_app())
    app_resp = client.post(
        "/api/apps",
        json={"name": "Review Stats App", "app_store_id": "111222333"},
    )
    app_id = app_resp.json()["id"]
    _seed_reviews(app_id)

    resp = client.get("/api/reviews/stats", params={"app_id": app_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert "by_platform" in data

    ios = client.get(
        "/api/reviews/stats",
        params={"app_id": app_id, "platform": "app_store"},
    )
    assert ios.json()["total"] == 1


def test_review_highlights() -> None:
    client = TestClient(create_app())
    app_resp = client.post(
        "/api/apps",
        json={"name": "Highlights App", "app_store_id": "444555666"},
    )
    app_id = app_resp.json()["id"]
    _seed_reviews(app_id)

    resp = client.get("/api/reviews/highlights", params={"app_id": app_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["praise"]) >= 1
    assert len(data["complaints"]) >= 1
    assert data["praise"][0]["insight"]["summary"]
