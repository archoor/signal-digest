"""App Store 公开 RSS 采集器（设计文档第 4.2）。

URL 形式：
  https://itunes.apple.com/{country}/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json

这是首期最快路径：无需授权，可采集竞品公开评论。
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.models.enums import Platform
from app.services.ingestion.base import RawReview, ReviewIngestor

logger = get_logger(__name__)

_RSS_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews/"
    "page={page}/id={app_id}/sortby=mostrecent/json"
)


class AppStoreRssIngestor(ReviewIngestor):
    """基于公开 RSS 的 App Store 评论采集。"""

    platform = Platform.APP_STORE

    def __init__(self, max_pages: int = 5) -> None:
        # App Store RSS 每页约 50 条，最多约 10 页。
        self.max_pages = max_pages
        self._timeout = get_settings().ingest_http_timeout

    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        countries = country_codes or get_settings().country_code_list
        reviews: list[RawReview] = []

        with httpx.Client(timeout=self._timeout) as client:
            for country in countries:
                for page in range(1, self.max_pages + 1):
                    if len(reviews) >= max_reviews:
                        break
                    batch = self._fetch_page(client, app_identifier, country, page)
                    if not batch:
                        break
                    reviews.extend(batch)

        logger.info(
            "AppStore RSS 采集完成 app_id=%s countries=%s 共 %d 条",
            app_identifier,
            countries,
            len(reviews),
        )
        return reviews[:max_reviews]

    def _fetch_page(
        self, client: httpx.Client, app_id: str, country: str, page: int
    ) -> list[RawReview]:
        url = _RSS_URL.format(country=country, page=page, app_id=app_id)
        try:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("RSS 抓取失败 url=%s err=%s", url, exc)
            return []

        entries = data.get("feed", {}).get("entry", [])
        # 第一个 entry 通常是 App 自身信息，需跳过；只有评论才有 im:rating。
        out: list[RawReview] = []
        for entry in entries:
            if "im:rating" not in entry:
                continue
            out.append(self._parse_entry(entry, country))
        return out

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
            # 形如 2026-06-01T12:34:56-07:00
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(UTC)
