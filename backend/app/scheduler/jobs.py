"""定时任务编排（设计文档第 4.5 / 5.1 / 7.2 / 7.3）。

用 APScheduler 跑：每日采集 + 每周周报生成。
MVP 单进程内嵌调度；规模化后可拆独立 worker。
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from app.config import get_settings
from app.core.logging import get_logger
from app.db import engine
from app.models.enums import MonitorStatus, Platform, SourceKind
from app.models.monitored_app import MonitoredApp
from app.services.change_detector import build_change_context
from app.services.digest_generator import generate_digest
from app.services.ingestion import get_ingestor
from app.services.review_classifier import classify_pending, get_unclassified_reviews
from app.services.review_normalizer import persist_reviews

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_daily_ingest() -> None:
    """每日采集：遍历 active App，采集自身与竞品评论并入库（第 7.2）。"""
    settings = get_settings()
    with Session(engine) as session:
        apps = session.exec(
            select(MonitoredApp).where(MonitoredApp.status == MonitorStatus.ACTIVE)
        ).all()
        for app in apps:
            if not app.app_store_id:
                continue
            try:
                ingestor = get_ingestor(Platform.APP_STORE)
                raw = ingestor.fetch(
                    app_identifier=app.app_store_id,
                    country_codes=app.country_codes or settings.country_code_list,
                )
                persist_reviews(
                    session,
                    raw,
                    source_kind=SourceKind.OWN,
                    monitored_app_id=app.id,
                )
                # 采集后立即对新评论分类（第 7.2）。
                pending = get_unclassified_reviews(session, monitored_app_id=app.id)
                classify_pending(session, pending)
            except Exception as exc:  # noqa: BLE001
                logger.error("采集失败 app_id=%s err=%s", app.id, exc)


def run_weekly_digest() -> None:
    """每周周报：为每个 active App 生成 draft 周报（第 7.3）。"""
    with Session(engine) as session:
        apps = session.exec(
            select(MonitoredApp).where(MonitoredApp.status == MonitorStatus.ACTIVE)
        ).all()
        for app in apps:
            if app.id is None:
                continue
            ctx = build_change_context(session, app.id)
            generate_digest(session, ctx)


def start_scheduler() -> BackgroundScheduler:
    """启动后台调度器（幂等）。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_daily_ingest,
        CronTrigger(hour=settings.daily_ingest_hour),
        id="daily_ingest",
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_digest,
        CronTrigger(
            day_of_week=settings.weekly_digest_weekday, hour=settings.weekly_digest_hour
        ),
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("调度器已启动：daily_ingest + weekly_digest")
    _scheduler = scheduler
    return scheduler


def shutdown_scheduler() -> None:
    """停止调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
