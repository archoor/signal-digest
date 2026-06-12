"""Google Play 评论采集器（设计文档第 4.4）。

开源版：best-effort 第三方抓取（如 google-play-scraper）。
商业版：官方 Google Play Developer API / Apify。
官方 API 只能读自己账号下 App，不能读竞品。
"""

from __future__ import annotations

from app.models.enums import Platform
from app.services.ingestion.base import RawReview, ReviewIngestor


class GooglePlayIngestor(ReviewIngestor):
    platform = Platform.GOOGLE_PLAY

    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        # TODO(Phase 2): 接入 best-effort 抓取或官方 Developer API。
        raise NotImplementedError(
            "Google Play 采集器为 Phase 2，先用第三方 best-effort 抓取。"
        )
