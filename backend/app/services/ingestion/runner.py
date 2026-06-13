"""双平台采集编排。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.models.enums import Platform, SourceKind
from app.models.monitored_app import MonitoredApp
from app.services.ingestion import get_ingestor
from app.services.ingestion.errors import IngestSourceError
from app.services.external_http import ExternalNetworkError
from app.services.review_classifier import get_unclassified_reviews
from app.services.review_normalizer import persist_reviews

logger = get_logger(__name__)


@dataclass
class PlatformIngestResult:
    platform: str
    fetched: int = 0
    inserted: int = 0
    status: str = "ok"  # ok | skipped | error
    message: str | None = None


@dataclass
class IngestResult:
    fetched: int = 0
    inserted: int = 0
    classified: int = 0
    platforms: list[PlatformIngestResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def ingest_monitored_app(session: Session, app: MonitoredApp) -> dict:
    """采集 MonitoredApp 已配置的全部平台评论并分类。"""
    settings = get_settings()
    country_codes = app.country_codes or settings.country_code_list
    result = IngestResult()

    platforms: list[tuple[Platform, str | None]] = [
        (Platform.APP_STORE, app.app_store_id),
        (Platform.GOOGLE_PLAY, app.google_play_package),
    ]

    for platform, identifier in platforms:
        plat_key = platform.value
        if not identifier:
            result.platforms.append(
                PlatformIngestResult(platform=plat_key, status="skipped")
            )
            continue

        plat_result = PlatformIngestResult(platform=plat_key)
        try:
            ingestor = get_ingestor(platform)
            raw = ingestor.fetch(
                app_identifier=identifier,
                country_codes=country_codes,
            )
            inserted = persist_reviews(
                session,
                raw,
                source_kind=SourceKind.OWN,
                monitored_app_id=app.id,
            )
            plat_result.fetched = len(raw)
            plat_result.inserted = inserted
            result.fetched += len(raw)
            result.inserted += inserted

            if len(raw) == 0:
                plat_result.status = "empty"
                plat_result.message = "未抓取到评论"
                result.warnings.append(f"{plat_key}：未抓取到评论")
            elif inserted == 0:
                result.warnings.append(
                    f"{plat_key}：抓取 {len(raw)} 条，均为已入库评论（无新增）"
                )
        except IngestSourceError as exc:
            plat_result.status = "error"
            plat_result.message = exc.message
            result.warnings.append(f"{plat_key}：{exc.message}")
            logger.error(
                "采集失败 app_id=%s platform=%s err=%s", app.id, platform, exc.message
            )
        except ExternalNetworkError as exc:
            plat_result.status = "error"
            plat_result.message = exc.message
            result.warnings.append(f"{plat_key}：{exc.message}")
            logger.error(
                "采集失败（代理） app_id=%s platform=%s err=%s", app.id, platform, exc.message
            )
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            plat_result.status = "error"
            plat_result.message = str(exc)
            result.warnings.append(f"{plat_key}：{exc}")
            logger.error("采集失败 app_id=%s platform=%s err=%s", app.id, platform, exc)

        result.platforms.append(plat_result)

    pending = get_unclassified_reviews(session, monitored_app_id=app.id)
    # 采集 API 不做分类，避免 LLM 阻塞导致前端超时；请点「补跑分类」。
    result.classified = 0
    if pending:
        result.warnings.append(
            f"有 {len(pending)} 条新评论待分类，请点击「补跑分类」。"
        )

    from app.models.base import utcnow

    app.last_ingested_at = utcnow()
    session.add(app)
    session.commit()

    configured = [p for p in result.platforms if p.status != "skipped"]
    if configured and result.fetched == 0 and all(p.status == "error" for p in configured):
        result.warnings.insert(
            0,
            "所有已配置平台均未成功抓取。若在中国大陆网络环境，请在管理后台设置页配置外网代理后重试。",
        )

    return {
        "fetched": result.fetched,
        "inserted": result.inserted,
        "classified": result.classified,
        "platforms": [
            {
                "platform": p.platform,
                "fetched": p.fetched,
                "inserted": p.inserted,
                "status": p.status,
                "message": p.message,
            }
            for p in result.platforms
        ],
        "warnings": result.warnings,
    }
