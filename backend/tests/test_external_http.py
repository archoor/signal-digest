"""外网代理工具测试。"""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest

from app.services.external_http import (
    ExternalNetworkError,
    get_http_proxy_url,
    mask_proxy_url,
    normalize_proxy_url,
    proxy_error_message,
    raise_if_proxy_error,
    requests_proxy_env,
)


def test_get_http_proxy_url_empty() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = None
        assert get_http_proxy_url() is None
        mock_settings.return_value.ingest_http_proxy = "   "
        assert get_http_proxy_url() is None


def test_get_http_proxy_url_configured() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = " socks5://127.0.0.1:12080 "
        assert get_http_proxy_url() == "socks5://127.0.0.1:12080"


def test_get_http_proxy_url_with_auth() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = "socks5://myuser:mypass@127.0.0.1:12080"
        assert get_http_proxy_url() == "socks5://myuser:mypass@127.0.0.1:12080"


def test_normalize_proxy_url_encodes_special_password() -> None:
    assert (
        normalize_proxy_url("socks5://user:p@ss@127.0.0.1:12080")
        == "socks5://user:p%40ss@127.0.0.1:12080"
    )


def test_mask_proxy_url_hides_password() -> None:
    masked = mask_proxy_url("socks5://myuser:secret@127.0.0.1:12080")
    assert masked == "socks5://myuser:***@127.0.0.1:12080"
    assert "secret" not in masked


def test_proxy_error_message_masks_credentials() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = "socks5://myuser:secret@127.0.0.1:12080"
        msg = proxy_error_message(httpx.ProxyError("bad proxy"), "Google Play")
        assert msg is not None
        assert "myuser:***@" in msg
        assert "secret" not in msg


def test_raise_if_proxy_error_when_no_proxy() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = None
        exc = httpx.ConnectError("connection refused")
        raise_if_proxy_error(exc, "测试")  # 不应抛出


def test_raise_if_proxy_error_when_proxy_configured() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = "socks5://127.0.0.1:12080"
        exc = httpx.ConnectError("connection refused")
        with pytest.raises(ExternalNetworkError) as err:
            raise_if_proxy_error(exc, "App Store 搜索")
        assert "socks5://127.0.0.1:12080" in err.value.message
        assert err.value.via_proxy is True


def test_proxy_error_message() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = "socks5://127.0.0.1:12080"
        msg = proxy_error_message(httpx.ProxyError("bad proxy"), "Google Play")
        assert msg is not None
        assert "Google Play" in msg


def test_requests_proxy_env_sets_and_restores() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = "socks5://127.0.0.1:12080"
        os.environ["HTTP_PROXY"] = "http://old"
        try:
            with requests_proxy_env():
                assert os.environ.get("HTTP_PROXY") == "socks5://127.0.0.1:12080"
            assert os.environ.get("HTTP_PROXY") == "http://old"
        finally:
            os.environ.pop("HTTP_PROXY", None)


def test_requests_proxy_env_noop_without_proxy() -> None:
    with patch("app.services.external_http.get_settings") as mock_settings:
        mock_settings.return_value.ingest_http_proxy = None
        with requests_proxy_env():
            assert "HTTP_PROXY" not in os.environ or os.environ.get("HTTP_PROXY") != "socks5://127.0.0.1:12080"
