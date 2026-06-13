"""评论标准化与去重入库（设计文档第 7.2）。

把采集器产出的 RawReview 写入 AppReview，按 platform + external_review_id 去重。
作者名按第 15.1 合规要求做 hash，不存原文。
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import Enum

from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models.app_review import AppReview
from app.models.enums import SourceKind
from app.services.ingestion.base import RawReview

logger = get_logger(__name__)


def _hash_author(author: str | None) -> str | None:
    if not author:
        return None
    return hashlib.sha256(author.encode("utf-8")).hexdigest()[:16]


def json_safe_payload(value: object) -> object:
    """将 raw_payload 转为可 JSON 序列化的结构（Google Play 含 datetime）。"""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: json_safe_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe_payload(v) for v in value]
    return value


def persist_reviews(
    session: Session,
    raw_reviews: list[RawReview],
    *,
    source_kind: SourceKind,
    monitored_app_id: int | None = None,
    competitor_app_id: int | None = None,
) -> int:
    """标准化并去重入库，返回新增条数。"""
    inserted = 0
    for raw in raw_reviews:
        exists = session.exec(
            select(AppReview).where(
                AppReview.platform == raw.platform,
                AppReview.external_review_id == raw.external_review_id,
            )
        ).first()
        if exists:
            continue

        review = AppReview(
            monitored_app_id=monitored_app_id,
            competitor_app_id=competitor_app_id,
            source_kind=source_kind,
            platform=raw.platform,
            external_review_id=raw.external_review_id,
            rating=raw.rating,
            title=raw.title,
            body=raw.body,
            author_hash=_hash_author(raw.author),
            country=raw.country,
            language=raw.language,
            app_version=raw.app_version,
            source_created_at=raw.source_created_at,
            raw_payload=json_safe_payload(raw.raw_payload)
            if raw.raw_payload is not None
            else None,
        )
        session.add(review)
        inserted += 1

    session.commit()
    logger.info("入库完成：新增 %d / 抓取 %d 条", inserted, len(raw_reviews))
    return inserted
