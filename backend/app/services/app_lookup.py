"""App Store / Google Play 名称搜索（设计文档第 7.1 onboarding）。"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from google_play_scraper import search as gp_search

from app.core.logging import get_logger
from app.services.external_http import (
    ExternalNetworkError,
    google_play_scraper_proxy,
    httpx_client_kwargs,
    proxy_error_message,
    raise_if_proxy_error,
)
from app.services.url_parser import (
    build_app_store_url,
    build_google_play_url,
    normalize_app_name,
)

logger = get_logger(__name__)

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


@dataclass(slots=True)
class AppSearchResult:
    name: str
    developer: str | None = None
    icon_url: str | None = None
    app_store_id: str | None = None
    app_store_url: str | None = None
    google_play_package: str | None = None
    google_play_url: str | None = None
    platforms: list[str] = field(default_factory=list)


def search_itunes(term: str, country: str = "us", limit: int = 10) -> list[AppSearchResult]:
    """通过 iTunes Search API 搜索 App Store。"""
    if not term.strip():
        return []
    try:
        with httpx.Client(**httpx_client_kwargs()) as client:
            resp = client.get(
                ITUNES_SEARCH_URL,
                params={
                    "term": term.strip(),
                    "entity": "software",
                    "country": country.lower(),
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise_if_proxy_error(exc, "App Store 搜索")
        logger.warning("iTunes 搜索失败 term=%s err=%s", term, exc)
        return []
    except ValueError as exc:
        logger.warning("iTunes 搜索失败 term=%s err=%s", term, exc)
        return []

    out: list[AppSearchResult] = []
    for item in data.get("results", []):
        app_id = str(item.get("trackId", "")) or None
        if not app_id:
            continue
        out.append(
            AppSearchResult(
                name=item.get("trackName") or "",
                developer=item.get("artistName"),
                icon_url=item.get("artworkUrl100"),
                app_store_id=app_id,
                app_store_url=item.get("trackViewUrl")
                or build_app_store_url(app_id, country),
                platforms=["app_store"],
            )
        )
    return out


def search_google_play(
    term: str, country: str = "us", limit: int = 10
) -> list[AppSearchResult]:
    """通过 google-play-scraper 搜索 Google Play。"""
    if not term.strip():
        return []
    try:
        with google_play_scraper_proxy():
            raw = gp_search(term.strip(), lang="en", country=country.lower(), n_hits=limit)
    except ExternalNetworkError:
        raise
    except Exception as exc:  # noqa: BLE001
        proxy_msg = proxy_error_message(exc, "Google Play 搜索")
        if proxy_msg:
            raise ExternalNetworkError(proxy_msg, via_proxy=True) from exc
        logger.warning("Google Play 搜索失败 term=%s err=%s", term, exc)
        return []

    out: list[AppSearchResult] = []
    for item in raw[:limit]:
        package = item.get("appId") or item.get("app_id")
        if not package:
            continue
        out.append(
            AppSearchResult(
                name=item.get("title") or "",
                developer=item.get("developer"),
                icon_url=item.get("icon"),
                google_play_package=package,
                google_play_url=build_google_play_url(package),
                platforms=["google_play"],
            )
        )
    return out


def _merge_results(
    itunes: list[AppSearchResult], play: list[AppSearchResult], limit: int
) -> list[AppSearchResult]:
    """按规范化名称尝试合并双平台；无法匹配则分开展示。"""
    merged: dict[str, AppSearchResult] = {}
    unmatched_play: list[AppSearchResult] = []

    for r in itunes:
        key = normalize_app_name(r.name)
        if key:
            merged[key] = r

    for r in play:
        key = normalize_app_name(r.name)
        if key and key in merged:
            existing = merged[key]
            existing.google_play_package = r.google_play_package
            existing.google_play_url = r.google_play_url
            if "google_play" not in existing.platforms:
                existing.platforms.append("google_play")
            if not existing.icon_url and r.icon_url:
                existing.icon_url = r.icon_url
            if not existing.developer and r.developer:
                existing.developer = r.developer
        elif key:
            merged[key] = r
        else:
            unmatched_play.append(r)

    results = list(merged.values())
    # 名称过短无法归一化的 Play 结果追加
    for r in unmatched_play:
        if r not in results:
            results.append(r)

    return results[:limit]


def search_apps(term: str, country: str = "us", limit: int = 10) -> list[AppSearchResult]:
    """搜索 App Store 与 Google Play，合并后返回。"""
    per_platform = max(limit, 5)
    itunes = search_itunes(term, country, per_platform)
    try:
        play = search_google_play(term, country, per_platform)
    except ExternalNetworkError as exc:
        if itunes:
            logger.warning("Google Play 搜索代理失败，仍返回 App Store 结果: %s", exc.message)
            play = []
        else:
            raise
    return _merge_results(itunes, play, limit)


def app_search_result_to_dict(r: AppSearchResult) -> dict:
    """转为 API 响应 dict。"""
    return {
        "name": r.name,
        "developer": r.developer,
        "icon_url": r.icon_url,
        "app_store_id": r.app_store_id,
        "app_store_url": r.app_store_url,
        "google_play_package": r.google_play_package,
        "google_play_url": r.google_play_url,
        "platforms": r.platforms,
    }
