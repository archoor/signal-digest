"""App Store 公开 RSS 采集器（设计文档第 4.2）。

Apple RSS 在限流时会返回 HTTP 200 但 feed 中无 entry，需重试并给出明确提示。
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.services.external_http import httpx_client_kwargs, raise_if_proxy_error
from app.models.enums import Platform
from app.services.ingestion.base import RawReview, ReviewIngestor
from app.services.ingestion.errors import IngestSourceError

logger = get_logger(__name__)

_RSS_URL_TEMPLATES = (
    "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/page={page}/json",
    "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json",
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _is_rss_throttled(feed: dict) -> bool:
    """Apple 限流时常见：200 OK 但 feed 里没有 entry。"""
    entry = feed.get("entry")
    if entry is None:
        return True
    entries = [entry] if isinstance(entry, dict) else entry
    return not any(isinstance(e, dict) and "im:rating" in e for e in entries)


class AppStoreRssIngestor(ReviewIngestor):
    """基于公开 RSS 的 App Store 评论采集。"""

    platform = Platform.APP_STORE

    def __init__(self, max_pages: int = 5, max_retries: int = 3) -> None:
        self.max_pages = max_pages
        self.max_retries = max_retries

    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        settings = get_settings()
        countries = country_codes or settings.country_code_list

        try:
            with httpx.Client(**httpx_client_kwargs(headers=_DEFAULT_HEADERS)) as client:
                return self._fetch_all_pages(
                    client, app_identifier, countries, max_reviews
                )
        except httpx.HTTPError as exc:
            raise_if_proxy_error(exc, "App Store RSS 采集")
            raise

    def _fetch_all_pages(
        self,
        client: httpx.Client,
        app_identifier: str,
        countries: list[str],
        max_reviews: int,
    ) -> list[RawReview]:
        reviews: list[RawReview] = []
        throttled = False

        for country in countries:
            for page in range(1, self.max_pages + 1):
                if len(reviews) >= max_reviews:
                    break
                batch, page_throttled = self._fetch_page_with_retry(
                    client, app_identifier, country, page
                )
                if page_throttled:
                    throttled = True
                if not batch:
                    break
                reviews.extend(batch)

        if not reviews and throttled:
            raise IngestSourceError(
                Platform.APP_STORE.value,
                "App Store RSS 未返回评论（可能被 Apple 限流，或当前网络无法访问 iTunes）。"
                "请稍后重试，或在管理后台「设置」页配置外网代理。",
            )

        logger.info(
            "AppStore RSS 采集完成 app_id=%s countries=%s 共 %d 条",
            app_identifier,
            countries,
            len(reviews),
        )
        return reviews[:max_reviews]

    def _fetch_page_with_retry(
        self, client: httpx.Client, app_id: str, country: str, page: int
    ) -> tuple[list[RawReview], bool]:
        """带退避重试的单页抓取；返回 (评论列表, 是否遭遇限流)。"""
        throttled = False
        delay = 1.5

        for attempt in range(1, self.max_retries + 1):
            for template in _RSS_URL_TEMPLATES:
                url = template.format(country=country, app_id=app_id, page=page)
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, ValueError) as exc:
                    raise_if_proxy_error(exc, "App Store RSS 抓取")
                    logger.warning("RSS 抓取失败 url=%s err=%s", url, exc)
                    continue

                feed = data.get("feed", {})
                if _is_rss_throttled(feed):
                    throttled = True
                    logger.warning(
                        "RSS 疑似限流 app_id=%s country=%s page=%s attempt=%s",
                        app_id,
                        country,
                        page,
                        attempt,
                    )
                    continue

                entries = feed.get("entry", [])
                if isinstance(entries, dict):
                    entries = [entries]
                out: list[RawReview] = []
                for entry in entries:
                    if "im:rating" not in entry:
                        continue
                    out.append(self._parse_entry(entry, country))
                return out, False

            if attempt < self.max_retries:
                time.sleep(delay)
                delay *= 2

        return [], throttled

    def _parse_entry(self, entry: dict, country: str) -> RawReview:
        def _label(key: str) -> str | None:
            node = entry.get(key)
            if isinstance(node, dict):
                return node.get("label")
            return None

        external_id = _label("id") or ""
        created_raw = _label("updated")
        created_at = self._parse_dt(created_raw)
        rating_raw = _label("im:rating")

        return RawReview(
            platform=Platform.APP_STORE,
            external_review_id=external_id
            or RawReview.fallback_review_id(
                Platform.APP_STORE, country, _label("content") or "", created_at
            ),
            body=_label("content") or "",
            title=_label("title"),
            rating=int(rating_raw) if rating_raw and rating_raw.isdigit() else None,
            author=(entry.get("author") or {}).get("name", {}).get("label"),
            country=country,
            app_version=_label("im:version"),
            source_created_at=created_at,
            raw_payload=entry,
        )

    @staticmethod
    def _parse_dt(value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(UTC)
