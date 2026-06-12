"""Digests 路由（设计文档第 10.4）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.digest_report import DigestReport
from app.models.monitored_app import MonitoredApp
from app.services.change_detector import build_change_context
from app.services.digest_delivery import send_digest
from app.services.digest_generator import generate_digest

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("", response_model=list[DigestReport])
def list_digests(
    session: SessionDep, app_id: int | None = Query(default=None)
) -> list[DigestReport]:
    stmt = select(DigestReport).order_by(DigestReport.created_at.desc())
    if app_id is not None:
        stmt = stmt.where(DigestReport.monitored_app_id == app_id)
    return list(session.exec(stmt).all())


@router.get("/{digest_id}", response_model=DigestReport)
def get_digest(digest_id: int, session: SessionDep) -> DigestReport:
    report = session.get(DigestReport, digest_id)
    if not report:
        raise HTTPException(status_code=404, detail="Digest not found")
    return report


@router.post("/generate", response_model=DigestReport)
def generate(app_id: int = Query(...), *, session: SessionDep) -> DigestReport:
    """手动生成周报（第 10.4）。"""
    if not session.get(MonitoredApp, app_id):
        raise HTTPException(status_code=404, detail="App not found")
    ctx = build_change_context(session, app_id)
    return generate_digest(session, ctx)


@router.post("/{digest_id}/send")
def send(digest_id: int, session: SessionDep) -> dict:
    """手动发送周报（需 status=approved，第 8.3）。"""
    report = session.get(DigestReport, digest_id)
    if not report:
        raise HTTPException(status_code=404, detail="Digest not found")
    app = session.get(MonitoredApp, report.monitored_app_id)
    to_email = app.owner_email if app else None
    if not to_email:
        raise HTTPException(status_code=400, detail="App 缺少 owner_email")
    ok = send_digest(session, report, to_email)
    return {"sent": ok}
