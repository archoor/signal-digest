"""Competitors 路由（设计文档第 10.2）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.competitor_app import CompetitorApp
from app.models.monitored_app import MonitoredApp
from app.schemas.apps import CompetitorCreate, CompetitorRead
from app.services.url_parser import (
    build_app_store_url,
    build_google_play_url,
    parse_app_url,
)

router = APIRouter(tags=["competitors"])


def _resolve_competitor_ids(
    payload: CompetitorCreate, country: str = "us"
) -> tuple[str | None, str | None, str | None, str | None]:
    store_id = payload.app_store_id
    play_pkg = payload.google_play_package
    store_url = payload.app_store_url
    play_url = payload.google_play_url

    if store_url and not store_id:
        store_id = parse_app_url(store_url).app_store_id
    if play_url and not play_pkg:
        play_pkg = parse_app_url(play_url).google_play_package

    if store_id and not store_url:
        store_url = build_app_store_url(store_id, country)
    if play_pkg and not play_url:
        play_url = build_google_play_url(play_pkg)

    return store_id, play_pkg, store_url, play_url


@router.get("/apps/{app_id}/competitors", response_model=list[CompetitorRead])
def list_competitors(app_id: int, session: SessionDep) -> list[CompetitorApp]:
    return list(
        session.exec(
            select(CompetitorApp).where(CompetitorApp.monitored_app_id == app_id)
        ).all()
    )


@router.post("/apps/{app_id}/competitors", response_model=CompetitorRead, status_code=201)
def add_competitor(
    app_id: int, payload: CompetitorCreate, session: SessionDep
) -> CompetitorApp:
    app = session.get(MonitoredApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    existing = session.exec(
        select(CompetitorApp).where(CompetitorApp.monitored_app_id == app_id)
    ).all()
    if len(existing) >= 3:
        raise HTTPException(status_code=400, detail="每个 App 最多 3 个竞品")

    country = (app.country_codes or ["us"])[0]
    store_id, play_pkg, store_url, play_url = _resolve_competitor_ids(payload, country)
    if not store_id and not play_pkg:
        raise HTTPException(
            status_code=400,
            detail="至少配置 App Store 或 Google Play 其中一个平台",
        )

    competitor = CompetitorApp(
        monitored_app_id=app_id,
        name=payload.name,
        app_store_url=store_url,
        google_play_url=play_url,
        app_store_id=store_id,
        google_play_package=play_pkg,
    )
    session.add(competitor)
    session.commit()
    session.refresh(competitor)
    return competitor


@router.delete("/competitors/{competitor_id}", status_code=204)
def delete_competitor(competitor_id: int, session: SessionDep) -> None:
    competitor = session.get(CompetitorApp, competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    session.delete(competitor)
    session.commit()
