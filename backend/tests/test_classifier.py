"""评论分类器测试（规则兜底路径，无需网络）。"""

from __future__ import annotations

from app.models.app_review import AppReview
from app.models.base import utcnow
from app.models.enums import Intent, Platform, Priority, Sentiment, SourceKind
from app.services.review_classifier import (
    _safe_enum,
    classify_review_rule,
    rule_based_sentiment,
)


def test_rule_based_sentiment() -> None:
    assert rule_based_sentiment(1) == Sentiment.NEGATIVE
    assert rule_based_sentiment(3) == Sentiment.NEUTRAL
    assert rule_based_sentiment(5) == Sentiment.POSITIVE
    assert rule_based_sentiment(None) == Sentiment.NEUTRAL


def test_safe_enum_case_insensitive() -> None:
    assert _safe_enum(Priority, "p0", Priority.NONE) == Priority.P0
    assert _safe_enum(Sentiment, "POSITIVE", Sentiment.NEUTRAL) == Sentiment.POSITIVE
    assert _safe_enum(Intent, "不存在", Intent.OTHER) == Intent.OTHER
    assert _safe_enum(Priority, None, Priority.NONE) == Priority.NONE


def test_classify_review_rule_low_rating_is_p1() -> None:
    review = AppReview(
        id=1,
        source_kind=SourceKind.OWN,
        platform=Platform.APP_STORE,
        external_review_id="x1",
        rating=1,
        body="一直崩溃",
        source_created_at=utcnow(),
    )
    insight = classify_review_rule(review)
    assert insight.sentiment == Sentiment.NEGATIVE
    assert insight.priority == Priority.P1
