"""Apps 路由（设计文档第 10.1）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.monitored_app import MonitoredApp
from app.schemas.apps import (
    AppSearchResultRead,
    MonitoredAppCreate,
    MonitoredAppRead,
    MonitoredAppUpdate,
)
from app.services.app_lookup import app_search_result_to_dict, search_apps
from app.services.external_http import ExternalNetworkError
from app.services.url_parser import (
    build_app_store_url,
    build_google_play_url,
    parse_app_url,
)

router = APIRouter(prefix="/apps", tags=["apps"])


def _finalize_platform_urls(
    country: str,
    store_id: str | None,
    play_pkg: str | None,
    store_url: str | None,
    play_url: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """根据 ID 补全标准链接。"""
    if store_id and not store_url:
        store_url = build_app_store_url(store_id, country)
    if play_pkg and not play_url:
        play_url = build_google_play_url(play_pkg)
    return store_id, play_pkg, store_url, play_url


def _resolve_platform_ids(
    payload: MonitoredAppCreate,
) -> tuple[str | None, str | None, str | None, str | None]:
    """合并直接传入的 ID 与 URL 解析结果，并补全标准链接。"""
    store_id = payload.app_store_id
    play_pkg = payload.google_play_package
    store_url = payload.app_store_url
    play_url = payload.google_play_url

    if store_url and not store_id:
        store_id = parse_app_url(store_url).app_store_id
    if play_url and not play_pkg:
        play_pkg = parse_app_url(play_url).google_play_package

    country = (payload.country_codes or ["us"])[0]
    return _finalize_platform_urls(country, store_id, play_pkg, store_url, play_url)


def _apply_platform_patch(app: MonitoredApp, data: dict) -> None:
    """将 PATCH 中的平台字段合并到已有 App，并从 data 中移除已处理键。"""
    platform_keys = (
        "app_store_id",
        "google_play_package",
        "app_store_url",
        "google_play_url",
    )
    if not any(k in data for k in platform_keys):
        return

    country = (data.get("country_codes") or app.country_codes or ["us"])[0]
    store_id = app.app_store_id
    play_pkg = app.google_play_package
    store_url = app.app_store_url
    play_url = app.google_play_url

    if "app_store_url" in data:
        raw = data.pop("app_store_url")
        if raw:
            store_url = raw.strip()
            store_id = parse_app_url(store_url).app_store_id or store_id
        else:
            store_id = None
            store_url = None
    if "app_store_id" in data:
        store_id = data.pop("app_store_id") or None
        if store_id:
            store_url = None
        else:
            store_url = None

    if "google_play_url" in data:
        raw = data.pop("google_play_url")
        if raw:
            play_url = raw.strip()
            play_pkg = parse_app_url(play_url).google_play_package or play_pkg
        else:
            play_pkg = None
            play_url = None
    if "google_play_package" in data:
        play_pkg = data.pop("google_play_package") or None
        if play_pkg:
            play_url = None
        else:
            play_url = None

    store_id, play_pkg, store_url, play_url = _finalize_platform_urls(
        country, store_id, play_pkg, store_url, play_url
    )

    if not store_id and not play_pkg:
        raise HTTPException(
            status_code=400,
            detail="至少保留 App Store 或 Google Play 其中一个平台",
        )

    app.app_store_id = store_id
    app.app_store_url = store_url
    app.google_play_package = play_pkg
    app.google_play_url = play_url


@router.get("/search", response_model=list[AppSearchResultRead])
def search_app_catalog(
    q: str = Query(..., min_length=1, description="App 名称关键词"),
    country: str = Query("us", description="搜索国家代码"),
    limit: int = Query(10, ge=1, le=20),
) -> list[dict]:
    """按 App 名称搜索 App Store / Google Play 候选。"""
    try:
        results = search_apps(q, country=country, limit=limit)
    except ExternalNetworkError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    return [app_search_result_to_dict(r) for r in results]


@router.get("", response_model=list[MonitoredAppRead])
def list_apps(session: SessionDep) -> list[MonitoredApp]:
    return list(session.exec(select(MonitoredApp)).all())


@router.post("", response_model=MonitoredAppRead, status_code=201)
def create_app(payload: MonitoredAppCreate, session: SessionDep) -> MonitoredApp:
    store_id, play_pkg, store_url, play_url = _resolve_platform_ids(payload)
    if not store_id and not play_pkg:
        raise HTTPException(
            status_code=400,
            detail="至少配置 App Store 或 Google Play 其中一个平台",
        )

    app = MonitoredApp(
        name=payload.name,
        app_store_url=store_url,
        google_play_url=play_url,
        app_store_id=store_id,
        google_play_package=play_pkg,
        country_codes=payload.country_codes,
    )
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.get("/{app_id}", response_model=MonitoredAppRead)
def get_app(app_id: int, session: SessionDep) -> MonitoredApp:
    app = session.get(MonitoredApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.patch("/{app_id}", response_model=MonitoredAppRead)
def update_app(app_id: int, payload: MonitoredAppUpdate, session: SessionDep) -> MonitoredApp:
    app = session.get(MonitoredApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    data = payload.model_dump(exclude_unset=True)
    _apply_platform_patch(app, data)
    for key, value in data.items():
        setattr(app, key, value)
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{app_id}/ingest")
def ingest_app(app_id: int, session: SessionDep) -> dict:
    """手动触发采集（第 10.1）。"""
    from app.services.ingestion.runner import ingest_monitored_app

    app = session.get(MonitoredApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    if not app.app_store_id and not app.google_play_package:
        raise HTTPException(
            status_code=400, detail="该 App 未配置任何平台 ID，无法采集"
        )
    return ingest_monitored_app(session, app)


@router.post("/{app_id}/classify")
def classify_app_reviews(app_id: int, session: SessionDep) -> dict:
    """规则分类（立即返回）；LLM 深度分析在后台按批次执行。"""
    from app.core.logging import get_logger
    from app.services.review_classifier import classify_app_sync, enqueue_enrich_insights

    logger = get_logger(__name__)
    if not session.get(MonitoredApp, app_id):
        raise HTTPException(status_code=404, detail="App not found")
    try:
        result = classify_app_sync(session, app_id)
        if result.get("enrich_queued"):
            started = enqueue_enrich_insights(app_id)
            if not started:
                result = {
                    **result,
                    "message": result["message"].replace(
                        "已后台排队", "后台分析进行中，无需重复点击；已跳过重复排队"
                    ),
                }
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("补跑分类失败 app_id=%s", app_id)
        raise HTTPException(status_code=500, detail=f"分类失败: {exc}") from exc
