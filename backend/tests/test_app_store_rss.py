"""App Store RSS 采集器测试。"""

from __future__ import annotations

from app.services.ingestion.app_store_rss import _is_rss_throttled


def test_is_rss_throttled_empty_feed() -> None:
    assert _is_rss_throttled({"title": {"label": "Customer Reviews"}})


def test_is_rss_throttled_with_reviews() -> None:
    feed = {
        "entry": [
            {"im:rating": {"label": "5"}, "content": {"label": "great"}},
        ]
    }
    assert not _is_rss_throttled(feed)


def test_is_rss_throttled_single_entry_dict() -> None:
    feed = {"entry": {"im:rating": {"label": "4"}, "content": {"label": "ok"}}}
    assert not _is_rss_throttled(feed)
