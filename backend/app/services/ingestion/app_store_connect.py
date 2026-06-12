"""App Store Connect 官方 API 采集器（设计文档第 4.3）。

接口：GET /v1/customerReviews?filter[app]=APP_ID&sort=-createdAt&include=responses
特点：需 API Key，只能读自己账号名下 App，不能读竞品。
首期不强制接入，作为 P1/P2 高稳定数据源。
"""

from __future__ import annotations

from app.models.enums import Platform
from app.services.ingestion.base import RawReview, ReviewIngestor


class AppStoreConnectIngestor(ReviewIngestor):
    platform = Platform.APP_STORE

    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        # TODO(P1): 接入 App Store Connect API（需 JWT + API Key）。
        raise NotImplementedError(
            "App Store Connect API 采集器尚未实现，作为 P1/P2 高稳定数据源。"
        )
