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
from app.models.enums import MonitorStatus
from app.models.monitored_app import MonitoredApp
from app.services.change_detector import build_change_context
from app.services.digest_generator import generate_digest
from app.services.ingestion.runner import ingest_monitored_app

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_daily_ingest() -> None:
    """每日采集：遍历 active App，采集自身与竞品评论并入库（第 7.2）。"""
    with Session(engine) as session:
        apps = session.exec(
            select(MonitoredApp).where(MonitoredApp.status == MonitorStatus.ACTIVE)
        ).all()
        for app in apps:
            if not app.app_store_id and not app.google_play_package:
                continue
            try:
                ingest_monitored_app(session, app)
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
    settings = get_settings()
    if not settings.enable_scheduler:
        logger.info("调度器未启用（ENABLE_SCHEDULER=false）")
        return None  # type: ignore[return-value]

    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    _register_jobs(scheduler, settings)
    scheduler.start()
    logger.info("调度器已启动：daily_ingest + weekly_digest")
    _scheduler = scheduler
    return scheduler


def _register_jobs(scheduler: BackgroundScheduler, settings) -> None:
    scheduler.add_job(
        run_daily_ingest,
        CronTrigger(hour=settings.daily_ingest_hour),
        id="daily_ingest",
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_digest,
        CronTrigger(
            day_of_week=settings.weekly_digest_weekday,
            hour=settings.weekly_digest_hour,
        ),
        id="weekly_digest",
        replace_existing=True,
    )


def reload_scheduler_jobs() -> None:
    """配置变更后热重载调度任务（无需重启进程）。"""
    global _scheduler
    settings = get_settings()

    if not settings.enable_scheduler:
        shutdown_scheduler()
        logger.info("调度器已关闭（ENABLE_SCHEDULER=false）")
        return

    if _scheduler is None:
        start_scheduler()
        return

    _register_jobs(_scheduler, settings)
    logger.info(
        "调度任务已重载：daily=%s:00 weekly=周%d %s:00",
        settings.daily_ingest_hour,
        settings.weekly_digest_weekday,
        settings.weekly_digest_hour,
    )


def shutdown_scheduler() -> None:
    """停止调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
