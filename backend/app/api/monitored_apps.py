"""Apps 路由（设计文档第 10.1）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.enums import Platform, SourceKind
from app.models.monitored_app import MonitoredApp
from app.schemas.apps import MonitoredAppCreate, MonitoredAppRead, MonitoredAppUpdate
from app.services.ingestion import get_ingestor
from app.services.review_classifier import classify_pending, get_unclassified_reviews
from app.services.review_normalizer import persist_reviews
from app.services.url_parser import parse_app_url

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("", response_model=list[MonitoredAppRead])
def list_apps(session: SessionDep) -> list[MonitoredApp]:
    return list(session.exec(select(MonitoredApp)).all())


@router.post("", response_model=MonitoredAppRead, status_code=201)
def create_app(payload: MonitoredAppCreate, session: SessionDep) -> MonitoredApp:
    parsed_store = parse_app_url(payload.app_store_url or "")
    parsed_play = parse_app_url(payload.google_play_url or "")
    app = MonitoredApp(
        name=payload.name,
        owner_email=payload.owner_email,
        app_store_url=payload.app_store_url,
        google_play_url=payload.google_play_url,
        app_store_id=parsed_store.app_store_id,
        google_play_package=parsed_play.google_play_package,
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
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, key, value)
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{app_id}/ingest")
def ingest_app(app_id: int, session: SessionDep) -> dict:
    """手动触发采集（第 10.1）。"""
    app = session.get(MonitoredApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    if not app.app_store_id:
        raise HTTPException(status_code=400, detail="该 App 缺少 app_store_id")

    ingestor = get_ingestor(Platform.APP_STORE)
    raw = ingestor.fetch(app_identifier=app.app_store_id, country_codes=app.country_codes)
    inserted = persist_reviews(
        session, raw, source_kind=SourceKind.OWN, monitored_app_id=app.id
    )
    # 采集后立即分类新评论（第 7.2）。
    pending = get_unclassified_reviews(session, monitored_app_id=app.id)
    classified = classify_pending(session, pending)
    return {"fetched": len(raw), "inserted": inserted, "classified": classified}


@router.post("/{app_id}/classify")
def classify_app_reviews(app_id: int, session: SessionDep) -> dict:
    """手动对某 App 尚未分类的评论补跑分类。"""
    if not session.get(MonitoredApp, app_id):
        raise HTTPException(status_code=404, detail="App not found")
    pending = get_unclassified_reviews(session, monitored_app_id=app_id)
    classified = classify_pending(session, pending)
    return {"classified": classified}
