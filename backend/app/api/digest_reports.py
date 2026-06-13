"""Digests 路由（设计文档第 10.4）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.digest_report import DigestReport
from app.models.enums import DigestStatus
from app.config import get_settings
from app.models.monitored_app import MonitoredApp
from app.services.change_detector import build_change_context
from app.services.digest_delivery import send_digest
from app.services.digest_generator import generate_digest
from app.services.notion_exporter import NotionExportError, export_digest_to_notion

# 人工审核允许的状态流转（第 8.3）；sent 仅能通过 send 接口写入。
_ALLOWED_STATUS_TRANSITIONS: dict[DigestStatus, set[DigestStatus]] = {
    DigestStatus.DRAFT: {DigestStatus.DRAFT, DigestStatus.NEEDS_REVIEW},
    DigestStatus.NEEDS_REVIEW: {
        DigestStatus.NEEDS_REVIEW,
        DigestStatus.DRAFT,
        DigestStatus.APPROVED,
    },
    DigestStatus.APPROVED: {DigestStatus.APPROVED, DigestStatus.NEEDS_REVIEW},
    DigestStatus.SENT: {DigestStatus.SENT, DigestStatus.APPROVED},
    DigestStatus.FAILED: {DigestStatus.FAILED, DigestStatus.APPROVED},
}


def _validate_status_transition(current: DigestStatus, target: DigestStatus) -> None:
    allowed = _ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不允许从 {current.value} 变更为 {target.value}",
        )
    if target == DigestStatus.SENT:
        raise HTTPException(
            status_code=400,
            detail="已发送状态请通过「发送邮件」接口写入",
        )


router = APIRouter(prefix="/digests", tags=["digests"])


class DigestUpdate(BaseModel):
    """周报可编辑字段（审核流程：第 8.3）。"""

    status: DigestStatus | None = None
    title: str | None = None
    summary: str | None = None


@router.get("", response_model=list[DigestReport])
def list_digests(
    session: SessionDep,
    app_id: int | None = Query(default=None),
    status: DigestStatus | None = Query(default=None, description="按状态过滤"),
) -> list[DigestReport]:
    stmt = select(DigestReport).order_by(DigestReport.created_at.desc())
    if app_id is not None:
        stmt = stmt.where(DigestReport.monitored_app_id == app_id)
    if status is not None:
        stmt = stmt.where(DigestReport.status == status)
    return list(session.exec(stmt).all())


@router.get("/{digest_id}", response_model=DigestReport)
def get_digest(digest_id: int, session: SessionDep) -> DigestReport:
    report = session.get(DigestReport, digest_id)
    if not report:
        raise HTTPException(status_code=404, detail="Digest not found")
    return report


@router.patch("/{digest_id}", response_model=DigestReport)
def update_digest(
    digest_id: int, payload: DigestUpdate, session: SessionDep
) -> DigestReport:
    """更新周报状态/标题/摘要，支持人工审核流转（第 8.3）。"""
    report = session.get(DigestReport, digest_id)
    if not report:
        raise HTTPException(status_code=404, detail="Digest not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        _validate_status_transition(report.status, data["status"])
    for key, value in data.items():
        setattr(report, key, value)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


@router.post("/{digest_id}/export-notion", response_model=DigestReport)
def export_notion(
    digest_id: int,
    session: SessionDep,
    force: bool = Query(default=False, description="已导出时是否重新创建页面"),
) -> DigestReport:
    """把周报推送到 Notion Weekly Reports 数据库（第 8.3）。"""
    report = session.get(DigestReport, digest_id)
    if not report:
        raise HTTPException(status_code=404, detail="Digest not found")
    try:
        export_digest_to_notion(report, session, force=force)
    except NotionExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    to_email = get_settings().digest_recipient_email
    if not to_email:
        raise HTTPException(
            status_code=400, detail="未配置周报接收邮箱，请前往设置页配置"
        )
    ok = send_digest(session, report, to_email)
    return {"sent": ok}
