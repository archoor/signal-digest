"""Google Play 评论采集器（设计文档第 4.4）。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import UTC, datetime

from google_play_scraper import reviews as gp_reviews

from app.config import get_settings
from app.core.logging import get_logger
from app.models.enums import Platform
from app.services.external_http import (
    ExternalNetworkError,
    google_play_scraper_proxy,
    proxy_error_message,
)
from app.services.ingestion.base import RawReview, ReviewIngestor
from app.services.ingestion.errors import IngestSourceError

logger = get_logger(__name__)


def _fetch_gp_reviews(
    app_identifier: str, country: str, max_reviews: int
) -> list[dict]:
    with google_play_scraper_proxy():
        batch, _ = gp_reviews(
            app_identifier,
            lang="en",
            country=country.lower(),
            count=max_reviews,
        )
    return batch


class GooglePlayIngestor(ReviewIngestor):
    platform = Platform.GOOGLE_PLAY

    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        settings = get_settings()
        countries = country_codes or ["us"]
        out: list[RawReview] = []
        errors: list[str] = []

        for country in countries:
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        _fetch_gp_reviews, app_identifier, country, max_reviews
                    )
                    batch = future.result(timeout=settings.ingest_google_play_timeout)
            except FuturesTimeout:
                msg = (
                    f"Google Play 抓取超时（>{settings.ingest_google_play_timeout}s），"
                    "请检查网络或在设置页配置外网代理。"
                )
                logger.warning("%s package=%s country=%s", msg, app_identifier, country)
                errors.append(msg)
                continue
            except ExternalNetworkError as exc:
                logger.warning(
                    "Google Play 代理失败 package=%s country=%s err=%s",
                    app_identifier,
                    country,
                    exc,
                )
                errors.append(exc.message)
                continue
            except Exception as exc:  # noqa: BLE001
                proxy_msg = proxy_error_message(exc, "Google Play 抓取")
                if proxy_msg:
                    logger.warning(
                        "Google Play 代理失败 package=%s country=%s err=%s",
                        app_identifier,
                        country,
                        exc,
                    )
                    errors.append(proxy_msg)
                    continue
                logger.warning(
                    "Google Play 抓取失败 package=%s country=%s err=%s",
                    app_identifier,
                    country,
                    exc,
                )
                errors.append(str(exc))
                continue

            for item in batch:
                created_at = item.get("at")
                if isinstance(created_at, datetime):
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=UTC)
                else:
                    created_at = datetime.now(UTC)

                body = item.get("content") or ""
                review_id = item.get("reviewId") or ""
                out.append(
                    RawReview(
                        platform=Platform.GOOGLE_PLAY,
                        external_review_id=review_id
                        or RawReview.fallback_review_id(
                            Platform.GOOGLE_PLAY, country, body, created_at
                        ),
                        body=body,
                        title=None,
                        rating=item.get("score"),
                        author=item.get("userName"),
                        country=country.lower(),
                        app_version=item.get("reviewCreatedVersion"),
                        source_created_at=created_at,
                        raw_payload=item if isinstance(item, dict) else None,
                    )
                )

        if not out and errors:
            raise IngestSourceError(
                Platform.GOOGLE_PLAY.value,
                errors[0],
            )

        return out
