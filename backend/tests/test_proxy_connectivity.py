"""代理连通性测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from app.services.external_http import (
    test_proxy_connectivity as run_proxy_connectivity_test,
    validate_proxy_url,
)


def test_validate_proxy_url_rejects_bad_scheme() -> None:
    assert validate_proxy_url("ftp://127.0.0.1:1080") is not None


def test_validate_proxy_url_accepts_socks5_with_auth() -> None:
    assert validate_proxy_url("socks5://user:pass@127.0.0.1:12080") is None


def test_test_proxy_connectivity_success() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("app.services.external_http.httpx.Client", return_value=mock_client):
        result = run_proxy_connectivity_test("socks5://127.0.0.1:12080")

    assert result.ok is True
    assert result.mode == "proxy"
    assert len(result.checks) == 2
    assert all(c.ok for c in result.checks)


def test_test_proxy_connectivity_invalid_format() -> None:
    result = run_proxy_connectivity_test("not-a-valid-proxy")
    assert result.ok is False
    assert result.checks == []


def test_test_proxy_connectivity_failure() -> None:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = httpx.ConnectError("connection refused")

    with patch("app.services.external_http.httpx.Client", return_value=mock_client):
        result = run_proxy_connectivity_test("socks5://127.0.0.1:12080")

    assert result.ok is False
    assert result.mode == "proxy"
    assert all(not c.ok for c in result.checks)


def test_proxy_test_api() -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    with patch("app.api.settings.test_proxy_connectivity") as mock_test:
        mock_test.return_value.ok = True
        mock_test.return_value.mode = "proxy"
        mock_test.return_value.proxy = "socks5://127.0.0.1:12080"
        mock_test.return_value.message = "ok"
        from app.services.external_http import ProxyCheckResult

        mock_test.return_value.checks = [
            ProxyCheckResult(name="iTunes", ok=True, latency_ms=10, status_code=200)
        ]

        client = TestClient(create_app())
        resp = client.post(
            "/api/settings/proxy-test",
            json={"ingest_http_proxy": "socks5://127.0.0.1:12080"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["mode"] == "proxy"
    mock_test.assert_called_once_with("socks5://127.0.0.1:12080")
