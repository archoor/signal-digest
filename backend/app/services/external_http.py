"""外网 HTTP 访问与 SOCKS/HTTP 代理统一配置。

采集、App 搜索等需要访问 iTunes / Google Play 的流程均通过本模块走代理：
- 未配置外网代理（设置页留空）→ 直连
- 已配置 → httpx 与 google-play-scraper 均走该代理
- 支持带认证：`socks5://用户名:密码@host:port` 或 `http://用户名:密码@host:port`
- 密码含特殊字符请 URL 编码（如 `@` → `%40`）
- 代理不可用 → 抛出 `ExternalNetworkError`（错误信息中密码已脱敏）
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote, unquote, urlparse, urlunparse

import httpx

from app.config import get_settings

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

_SUPPORTED_PROXY_SCHEMES = frozenset({"socks5", "socks4", "http", "https"})

# 连通性探测目标（与采集/搜索实际访问的站点一致）
_PROXY_TEST_TARGETS: tuple[tuple[str, str], ...] = (
    ("iTunes", "https://itunes.apple.com/search?term=Test&entity=software&limit=1"),
    (
        "Google Play",
        "https://play.google.com/store/apps/details?id=org.telegram.messenger",
    ),
)


class ExternalNetworkError(Exception):
    """外网访问失败；配置了代理时多为代理连接问题。"""

    def __init__(self, message: str, *, via_proxy: bool = False) -> None:
        self.message = message
        self.via_proxy = via_proxy
        super().__init__(message)


def normalize_proxy_url(url: str) -> str:
    """规范化代理 URL，对用户名/密码做 URL 编码以便 httpx 正确解析。"""
    stripped = url.strip()
    if not stripped:
        return stripped

    parsed = urlparse(stripped)
    if not parsed.scheme or not parsed.hostname:
        return stripped

    if parsed.username is None and parsed.password is None:
        return stripped

    user = quote(unquote(parsed.username or ""), safe="")
    passwd = quote(unquote(parsed.password or ""), safe="")
    host = parsed.hostname
    netloc = f"{user}:{passwd}@{host}"
    if parsed.port is not None:
        netloc += f":{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "", "", "", ""))


def mask_proxy_url(url: str) -> str:
    """脱敏代理 URL 中的密码，便于日志与错误提示。"""
    parsed = urlparse(url)
    if not parsed.hostname:
        return url
    if parsed.username is None and parsed.password is None:
        return url

    user = parsed.username or ""
    host = parsed.hostname
    netloc = f"{user}:***@{host}"
    if parsed.port is not None:
        netloc += f":{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "", "", "", ""))


def get_http_proxy_url() -> str | None:
    """当前生效的代理 URL；未配置或空字符串时返回 None（直连）。"""
    raw = get_settings().ingest_http_proxy
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    return normalize_proxy_url(stripped)


def is_proxy_configured() -> bool:
    return get_http_proxy_url() is not None


def validate_proxy_url(url: str) -> str | None:
    """校验代理 URL 格式；合法返回 None，否则返回错误说明。"""
    stripped = url.strip()
    if not stripped:
        return None

    parsed = urlparse(stripped)
    if not parsed.scheme:
        return "代理地址缺少协议，请使用 socks5:// 或 http://"
    if parsed.scheme not in _SUPPORTED_PROXY_SCHEMES:
        return f"不支持的代理协议「{parsed.scheme}」，请使用 socks5 / http / https"
    if not parsed.hostname:
        return "代理地址缺少主机名"
    if parsed.port is None:
        return "代理地址缺少端口号"
    return None


@dataclass(slots=True)
class ProxyCheckResult:
    name: str
    ok: bool
    latency_ms: int | None = None
    status_code: int | None = None
    error: str | None = None


@dataclass(slots=True)
class ProxyConnectivityResult:
    ok: bool
    mode: Literal["proxy", "direct"]
    proxy: str | None
    message: str
    checks: list[ProxyCheckResult]


def test_proxy_connectivity(
    proxy_url: str | None = None,
    *,
    timeout: float | None = None,
) -> ProxyConnectivityResult:
    """探测 iTunes / Google Play 连通性；proxy_url 留空则测试直连。"""
    settings = get_settings()
    probe_timeout = timeout if timeout is not None else min(settings.ingest_http_timeout, 20.0)

    stripped = (proxy_url or "").strip()
    if not stripped:
        normalized: str | None = None
        mode: Literal["proxy", "direct"] = "direct"
        display_proxy: str | None = None
    else:
        fmt_err = validate_proxy_url(stripped)
        if fmt_err:
            return ProxyConnectivityResult(
                ok=False,
                mode="proxy",
                proxy=mask_proxy_url(normalize_proxy_url(stripped))
                if urlparse(stripped).hostname
                else stripped,
                message=fmt_err,
                checks=[],
            )
        normalized = normalize_proxy_url(stripped)
        mode = "proxy"
        display_proxy = mask_proxy_url(normalized)

    checks: list[ProxyCheckResult] = []
    all_ok = True

    client_kwargs: dict[str, Any] = {
        "timeout": probe_timeout,
        "follow_redirects": True,
    }
    if normalized:
        client_kwargs["proxy"] = normalized

    for name, url in _PROXY_TEST_TARGETS:
        started = time.perf_counter()
        check = ProxyCheckResult(name=name, ok=False)
        try:
            with httpx.Client(**client_kwargs) as client:
                resp = client.get(url)
                resp.raise_for_status()
            check.ok = True
            check.status_code = resp.status_code
        except httpx.HTTPError as exc:
            all_ok = False
            check.error = f"{type(exc).__name__}: {exc}"
        except OSError as exc:
            all_ok = False
            check.error = f"{type(exc).__name__}: {exc}"
        check.latency_ms = int((time.perf_counter() - started) * 1000)
        checks.append(check)

    if all_ok:
        if mode == "proxy":
            message = f"代理 {display_proxy} 连通正常，iTunes 与 Google Play 均可访问。"
        else:
            message = "直连连通正常，iTunes 与 Google Play 均可访问。"
    elif mode == "proxy":
        failed = "、".join(c.name for c in checks if not c.ok)
        message = f"代理 {display_proxy} 连通失败（{failed} 不可达），请检查地址、端口与用户名/密码。"
    else:
        failed = "、".join(c.name for c in checks if not c.ok)
        message = f"直连无法访问 {failed}，建议配置外网代理后重试。"

    return ProxyConnectivityResult(
        ok=all_ok,
        mode=mode,
        proxy=display_proxy,
        message=message,
        checks=checks,
    )


def httpx_client_kwargs(
    *,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """构造 httpx.Client 参数（含可选代理）。"""
    settings = get_settings()
    kwargs: dict[str, Any] = {"timeout": timeout if timeout is not None else settings.ingest_http_timeout}
    if headers:
        kwargs["headers"] = headers
    proxy = get_http_proxy_url()
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


def _looks_like_connect_failure(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.ProxyError, httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return True
    name = type(exc).__name__.lower()
    if "proxy" in name or "connect" in name or "timeout" in name:
        return True
    if isinstance(exc, OSError):
        return True
    cause = exc.__cause__
    return _looks_like_connect_failure(cause) if cause is not None else False


def proxy_error_message(exc: BaseException, context: str) -> str | None:
    """若配置了代理且错误像连接失败，返回用户可读提示；否则 None。"""
    if not is_proxy_configured() or not _looks_like_connect_failure(exc):
        return None
    proxy = get_http_proxy_url()
    masked = mask_proxy_url(proxy) if proxy else ""
    return (
        f"{context}：代理 {masked} 连接失败（{type(exc).__name__}: {exc}）。"
        "请确认代理已启动、地址与用户名/密码正确；不需要代理时请在设置页留空。"
    )


def raise_if_proxy_error(exc: BaseException, context: str) -> None:
    """配置了代理且连接失败时抛出 ExternalNetworkError。"""
    msg = proxy_error_message(exc, context)
    if msg:
        raise ExternalNetworkError(msg, via_proxy=True) from exc


@contextmanager
def google_play_scraper_proxy():
    """google-play-scraper 使用 urllib，SOCKS5 需改用 httpx 走代理。"""
    proxy = get_http_proxy_url()
    if not proxy:
        yield
        return

    import google_play_scraper.utils.request as gpr
    from urllib.request import Request

    original_urlopen = gpr._urlopen
    settings = get_settings()

    def _httpx_urlopen(obj: Request | str) -> str:
        if isinstance(obj, Request):
            url = obj.full_url
            method = obj.get_method()
            headers = {k: v for k, v in obj.header_items()}
            data = obj.data
        elif isinstance(obj, str):
            url = obj
            method = "GET"
            headers = {}
            data = None
        else:
            return original_urlopen(obj)

        timeout = settings.ingest_google_play_timeout
        with httpx.Client(
            proxy=proxy,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            if method == "POST":
                resp = client.post(url, content=data, headers=headers)
            else:
                resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    gpr._urlopen = _httpx_urlopen
    try:
        yield
    finally:
        gpr._urlopen = original_urlopen


@contextmanager
def llm_proxy_env():
    """LiteLLM / OpenAI 请求走 ingest_http_proxy（与采集共用代理配置）。"""
    with requests_proxy_env():
        yield


@contextmanager
def requests_proxy_env():
    """为仍依赖 requests/环境变量的库临时注入代理（httpx 请直接用 httpx_client_kwargs）。"""
    proxy = get_http_proxy_url()
    if not proxy:
        yield
        return

    saved = {k: os.environ.get(k) for k in _PROXY_ENV_KEYS}
    try:
        for key in _PROXY_ENV_KEYS:
            os.environ[key] = proxy
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

