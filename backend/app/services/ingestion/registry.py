"""采集器注册表：按平台路由到默认适配器。

MVP 默认：App Store 走 RSS；Google Play 走 best-effort（待实现）。
"""

from __future__ import annotations

from app.models.enums import Platform
from app.services.ingestion.app_store_rss import AppStoreRssIngestor
from app.services.ingestion.base import ReviewIngestor
from app.services.ingestion.google_play import GooglePlayIngestor

_DEFAULT_INGESTORS: dict[Platform, type[ReviewIngestor]] = {
    Platform.APP_STORE: AppStoreRssIngestor,
    Platform.GOOGLE_PLAY: GooglePlayIngestor,
}


def get_ingestor(platform: Platform) -> ReviewIngestor:
    """获取指定平台的默认采集器实例。"""
    try:
        return _DEFAULT_INGESTORS[platform]()
    except KeyError as exc:
        raise ValueError(f"暂不支持的平台: {platform}") from exc
