"""冒烟测试：验证应用可创建、健康检查可用、URL 解析正确。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.url_parser import parse_app_url


def test_health() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_parse_app_store_url() -> None:
    parsed = parse_app_url("https://apps.apple.com/us/app/demo/id389801252")
    assert parsed.app_store_id == "389801252"


def test_parse_google_play_url() -> None:
    parsed = parse_app_url("https://play.google.com/store/apps/details?id=com.foo.bar")
    assert parsed.google_play_package == "com.foo.bar"


def test_build_app_store_url() -> None:
    from app.services.url_parser import build_app_store_url

    url = build_app_store_url("12345", "us")
    assert url == "https://apps.apple.com/us/app/id12345"
