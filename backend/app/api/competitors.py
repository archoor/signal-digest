"""Competitors 路由（设计文档第 10.2）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.competitor_app import CompetitorApp
from app.models.monitored_app import MonitoredApp
from app.schemas.apps import CompetitorCreate, CompetitorRead
from app.services.url_parser import parse_app_url

router = APIRouter(tags=["competitors"])


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
    if not session.get(MonitoredApp, app_id):
        raise HTTPException(status_code=404, detail="App not found")

    # 第 3.1：每个 App 限制 1-3 个竞品。
    existing = session.exec(
        select(CompetitorApp).where(CompetitorApp.monitored_app_id == app_id)
    ).all()
    if len(existing) >= 3:
        raise HTTPException(status_code=400, detail="每个 App 最多 3 个竞品")

    parsed_store = parse_app_url(payload.app_store_url or "")
    parsed_play = parse_app_url(payload.google_play_url or "")
    competitor = CompetitorApp(
        monitored_app_id=app_id,
        name=payload.name,
        app_store_url=payload.app_store_url,
        google_play_url=payload.google_play_url,
        app_store_id=parsed_store.app_store_id,
        google_play_package=parsed_play.google_play_package,
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
