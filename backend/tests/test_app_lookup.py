"""App 搜索与 URL 构造测试。"""

from __future__ import annotations

from unittest.mock import patch

from app.services.app_lookup import AppSearchResult, _merge_results, search_itunes
from app.services.url_parser import (
    build_app_store_url,
    build_google_play_url,
    normalize_app_name,
)


def test_normalize_app_name() -> None:
    assert normalize_app_name("My App!") == "myapp"


def test_build_urls() -> None:
    assert "id123" in build_app_store_url("123", "us")
    assert "com.foo" in build_google_play_url("com.foo")


def test_merge_results_combines_platforms() -> None:
    itunes = [
        AppSearchResult(
            name="Demo App",
            app_store_id="111",
            app_store_url="https://apps.apple.com/us/app/id111",
            platforms=["app_store"],
        )
    ]
    play = [
        AppSearchResult(
            name="Demo App",
            google_play_package="com.demo",
            google_play_url="https://play.google.com/store/apps/details?id=com.demo",
            platforms=["google_play"],
        )
    ]
    merged = _merge_results(itunes, play, 10)
    assert len(merged) == 1
    assert merged[0].app_store_id == "111"
    assert merged[0].google_play_package == "com.demo"
    assert set(merged[0].platforms) == {"app_store", "google_play"}


def test_search_itunes_mock() -> None:
    fake = {
        "results": [
            {
                "trackId": 999,
                "trackName": "Test",
                "artistName": "Dev",
                "trackViewUrl": "https://apps.apple.com/us/app/id999",
            }
        ]
    }
    with patch("app.services.app_lookup.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value.json.return_value = fake
        mock_client.return_value.__enter__.return_value.get.return_value.raise_for_status = lambda: None
        results = search_itunes("Test", "us", 5)
    assert len(results) == 1
    assert results[0].app_store_id == "999"
