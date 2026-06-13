"""LLM enrich 与有效字数测试。"""

from __future__ import annotations

from unittest.mock import patch

from app.models.app_review import AppReview
from app.models.base import utcnow
from app.models.enums import Platform, Sentiment, SourceKind
from app.models.review_insight import ReviewInsight
from app.services.review_classifier import (
    SUMMARY_PLACEHOLDER_POSITIVE,
    classify_review_rule,
    effective_body_length,
    is_displayable_summary,
    is_placeholder_summary,
)


def test_effective_body_length() -> None:
    assert effective_body_length("") == 0
    assert effective_body_length("   peak   ") == 4
    assert effective_body_length("界面很清爽，上手快，推荐") >= 10


def test_short_review_no_placeholder() -> None:
    review = AppReview(
        id=1,
        source_kind=SourceKind.OWN,
        platform=Platform.GOOGLE_PLAY,
        external_review_id="s1",
        rating=5,
        body="peak",
        source_created_at=utcnow(),
    )
    insight = classify_review_rule(review)
    assert insight.summary is None


def test_long_review_gets_placeholder() -> None:
    review = AppReview(
        id=2,
        source_kind=SourceKind.OWN,
        platform=Platform.GOOGLE_PLAY,
        external_review_id="s2",
        rating=5,
        body="This app is amazing because the video generation quality is excellent and fast.",
        source_created_at=utcnow(),
    )
    insight = classify_review_rule(review)
    assert insight.summary == SUMMARY_PLACEHOLDER_POSITIVE


def test_is_displayable_summary() -> None:
    assert not is_displayable_summary(SUMMARY_PLACEHOLDER_POSITIVE)
    assert is_displayable_summary("用户认可视频生成质量与速度")


def test_enrich_batch_llm_parses_results() -> None:
    from app.services.review_classifier import _enrich_batch_llm

    review = AppReview(
        id=99,
        source_kind=SourceKind.OWN,
        platform=Platform.GOOGLE_PLAY,
        external_review_id="e1",
        rating=1,
        body="The app crashes every time I try to login with my Google account on Android 14.",
        source_created_at=utcnow(),
    )
    fake_resp = type(
        "R",
        (),
        {"choices": [type("C", (), {"message": type("M", (), {"content": '{"results": [{"review_id": 99, "summary": "登录流程在 Android 14 上反复崩溃"}]}'})()})()]},
    )()
    with patch("litellm.completion", return_value=fake_resp):
        with patch("app.services.review_classifier.get_settings") as mock_settings:
            mock_settings.return_value.llm_classifier_model = "openai/gpt-4o-mini"
            mock_settings.return_value.llm_api_key = "sk-test"
            mock_settings.return_value.llm_api_base = None
            mock_settings.return_value.llm_timeout = 60
            mock_settings.return_value.classifier_body_max_chars = 600
            out = _enrich_batch_llm([review])
    assert out[99] == "登录流程在 Android 14 上反复崩溃"
