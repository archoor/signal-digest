"""Settings API 冒烟测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_get_settings_includes_digest_recipient_email() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert "digest_recipient_email" in resp.json()


def test_get_settings_includes_ingest_http_proxy() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert "ingest_http_proxy" in resp.json()


def test_patch_settings_ingest_http_proxy() -> None:
    client = TestClient(create_app())
    patch_resp = client.patch(
        "/api/settings",
        json={"ingest_http_proxy": "socks5://127.0.0.1:12080"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["ingest_http_proxy"] == "socks5://127.0.0.1:12080"

    clear_resp = client.patch(
        "/api/settings",
        json={"ingest_http_proxy": None},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["ingest_http_proxy"] in (None, "")


def test_get_settings() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "llm_model" in data
    assert "llm_api_key_set" in data
    assert "email_provider" in data
    assert "enable_scheduler" in data


def test_patch_settings_llm_model() -> None:
    client = TestClient(create_app())
    get_resp = client.get("/api/settings")
    original = get_resp.json()["llm_model"]

    patch_resp = client.patch(
        "/api/settings",
        json={"llm_model": original},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["llm_model"] == original
