"""采集适配器抽象基类与原始评论 DTO（设计文档第 4 / 5.3）。

设计原则（SOLID）：
- 依赖倒置：上层 ingestion pipeline 只依赖 ReviewIngestor 抽象，不关心具体平台。
- 开放封闭：新增数据源只需新增子类，不改动调度与入库逻辑。
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.models.enums import Platform


@dataclass(slots=True)
class RawReview:
    """采集器产出的标准化前的原始评论。

    各平台适配器负责把自家字段映射到这里，由 review_normalizer 进一步入库。
    """

    platform: Platform
    external_review_id: str
    body: str
    source_created_at: datetime
    rating: int | None = None
    title: str | None = None
    author: str | None = None
    country: str | None = None
    language: str | None = None
    app_version: str | None = None
    raw_payload: dict = field(default_factory=dict)

    @staticmethod
    def fallback_review_id(
        platform: Platform, app_identifier: str, body: str, created_at: datetime
    ) -> str:
        """当平台无稳定 review_id 时的兜底键（设计文档第 6.3）。"""
        seed = f"{platform}|{app_identifier}|{body}|{created_at.isoformat()}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()


class ReviewIngestor(ABC):
    """评论采集器统一接口。

    具体实现见同目录：app_store_rss / app_store_connect / google_play / apify_adapter。
    """

    #: 适配器对应的平台，用于注册表路由。
    platform: Platform

    @abstractmethod
    def fetch(
        self,
        *,
        app_identifier: str,
        country_codes: list[str] | None = None,
        max_reviews: int = 200,
    ) -> list[RawReview]:
        """抓取最近评论。

        Args:
            app_identifier: App Store 为数字 id，Google Play 为 package name。
            country_codes: 需要抓取的国家列表（部分平台适用）。
            max_reviews: 单次最多抓取条数（成本与频控保护）。

        Returns:
            原始评论列表（未去重、未入库）。
        """
        raise NotImplementedError
