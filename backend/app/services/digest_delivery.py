"""周报邮件投递（设计文档第 7.3 / 8.3 / 11.2）。

职责：把已审核（approved）的周报渲染成邮件并发送，更新状态。
传输细节委托给 email_sender；本模块只关心"内容渲染 + 状态流转"。
"""

from __future__ import annotations

from html import escape

from sqlmodel import Session

from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.digest_report import DigestReport
from app.models.enums import DigestStatus
from app.services.email_sender import EmailDeliveryError, send_email

logger = get_logger(__name__)

# 周报详情页要求像邮件、不像 BI 面板（第 11.2）：标题 + 摘要 + 重点变化 + 行动。
SECTION_TITLES = {
    "top_changes": "本周最重要的变化",
    "new_complaints": "新增/增多的投诉",
    "new_praise": "新增/增多的好评",
    "rating_movement": "评分变化",
    "release_impact": "发版影响",
    "competitor_moves": "竞品动向",
    "recommended_actions": "建议优先处理的事项",
    "confidence_notes": "置信度提示",
}


def item_to_text(item) -> str:
    """把 section 中的单个条目（可能是字符串或 dict）转成可读文本。"""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # 优先取常见字段，兜底用 title/summary/text。
        for key in ("title", "summary", "text", "change", "action", "note"):
            if item.get(key):
                detail = item.get("detail") or item.get("why") or ""
                return f"{item[key]}{(' — ' + str(detail)) if detail else ''}"
        return "; ".join(f"{k}: {v}" for k, v in item.items() if v)
    return str(item)


def _render_section(key: str, items: list) -> str:
    if not items:
        return ""
    title = SECTION_TITLES.get(key, key)
    rows = "".join(f"<li>{escape(item_to_text(i))}</li>" for i in items)
    return f"<h3 style='margin:18px 0 6px'>{escape(title)}</h3><ul>{rows}</ul>"


def render_email_html(report: DigestReport) -> str:
    """把周报渲染成邮件 HTML。"""
    title = escape(report.title or "SignalDigest 周报")
    summary = escape(report.summary or "")
    body_sections = "".join(
        _render_section(key, report.sections.get(key, []))
        for key in SECTION_TITLES
    )
    period = f"{report.period_start:%Y-%m-%d} ~ {report.period_end:%Y-%m-%d}"

    return f"""<!DOCTYPE html>
<html lang="zh">
<body style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
             max-width:640px;margin:0 auto;padding:24px;color:#1f2937;line-height:1.6">
  <p style="color:#6b7280;font-size:13px;margin:0 0 4px">SignalDigest 周报 · {period}</p>
  <h1 style="font-size:22px;margin:0 0 12px">{title}</h1>
  <p style="font-size:16px;background:#f3f4f6;padding:12px 14px;border-radius:8px">{summary}</p>
  {body_sections}
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
  <p style="color:#9ca3af;font-size:12px">
    本报告由 SignalDigest 自动生成，每条结论均关联证据评论。
  </p>
</body>
</html>"""


def send_digest(session: Session, report: DigestReport, to_email: str) -> bool:
    """发送一份已审核周报；仅 status=approved 才会真正发送。"""
    if report.status != DigestStatus.APPROVED:
        logger.warning("周报未审核通过，跳过发送 report_id=%s status=%s", report.id, report.status)
        return False

    subject = report.title or f"SignalDigest 周报 {report.period_end:%Y-%m-%d}"
    html = render_email_html(report)

    try:
        send_email(to_email, subject, html)
    except EmailDeliveryError as exc:
        logger.error("周报发送失败 report_id=%s err=%s", report.id, exc)
        report.status = DigestStatus.FAILED
        session.add(report)
        session.commit()
        return False

    report.status = DigestStatus.SENT
    report.sent_at = utcnow()
    session.add(report)
    session.commit()
    logger.info("周报已发送 report_id=%s to=%s", report.id, to_email)
    return True
