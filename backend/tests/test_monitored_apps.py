"""MonitoredApp API 测试。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_with_platform_ids() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/apps",
        json={
            "name": "Test Dual Platform",
            "app_store_id": "389801252",
            "google_play_package": "com.example.test",
            "country_codes": ["us"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["app_store_id"] == "389801252"
    assert data["google_play_package"] == "com.example.test"
    assert data["app_store_url"]
    assert data["google_play_url"]


def test_create_app_requires_platform() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/api/apps",
        json={"name": "No Platform", "country_codes": ["us"]},
    )
    assert resp.status_code == 422


def test_search_apps_endpoint() -> None:
    client = TestClient(create_app())
    with patch("app.api.monitored_apps.search_apps", return_value=[]):
        resp = client.get("/api/apps/search", params={"q": "notion"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_update_app_supplement_google_play() -> None:
    client = TestClient(create_app())
    create = client.post(
        "/api/apps",
        json={
            "name": "iOS Only",
            "app_store_id": "389801252",
            "country_codes": ["us"],
        },
    )
    app_id = create.json()["id"]
    assert create.json()["google_play_package"] is None

    patch = client.patch(
        f"/api/apps/{app_id}",
        json={
            "google_play_url": "https://play.google.com/store/apps/details?id=com.example.app",
        },
    )
    assert patch.status_code == 200
    data = patch.json()
    assert data["app_store_id"] == "389801252"
    assert data["google_play_package"] == "com.example.app"
    assert data["google_play_url"]


def test_update_app_requires_one_platform() -> None:
    client = TestClient(create_app())
    create = client.post(
        "/api/apps",
        json={"name": "Single", "app_store_id": "111", "country_codes": ["us"]},
    )
    app_id = create.json()["id"]

    resp = client.patch(
        f"/api/apps/{app_id}",
        json={"app_store_url": ""},
    )
    assert resp.status_code == 400
