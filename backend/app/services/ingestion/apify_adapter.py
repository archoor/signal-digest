"""Apify / 第三方 Review API 采集适配器（设计文档第 4.4 / 5.2）。

用于商业托管版接入更稳定的数据源；开源版作为可选项。
"""

from __future__ import annotations

from app.models.enums import Platform
from app.services.ingestion.base import RawReview, ReviewIngestor


class ApifyIngestor(ReviewIngestor):
    # 平台在实例化时指定，Apify 上有不同 App Store / Google Play actor。
    def __init__(self, platform: Platform) -> None:
        self.platform = platform

    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        # TODO: 调用 Apify actor 并映射为 RawReview。
        raise NotImplementedError("Apify 适配器为商业托管版可选数据源。")
