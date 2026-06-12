"""邮件传输层（设计文档第 5.2 / 7.3）。

把"发什么"（周报内容）与"怎么发"（传输通道）解耦：
本模块只负责把一封 HTML 邮件通过指定 provider 发出去。

支持的 provider：
- smtp：标准 SMTP（STARTTLS / SSL），开源自部署首选。
- resend：Resend HTTP API。
- console：不真正发送，仅打印到日志，便于本地开发与测试。
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailDeliveryError(RuntimeError):
    """邮件发送失败。"""


def send_email(to_email: str, subject: str, html: str) -> bool:
    """按配置的 provider 发送一封邮件，成功返回 True。"""
    settings = get_settings()
    provider = (settings.email_provider or "console").lower()

    if provider == "smtp":
        return _send_via_smtp(to_email, subject, html)
    if provider == "resend":
        return _send_via_resend(to_email, subject, html)
    if provider == "console":
        logger.info("[console] 邮件 to=%s subject=%s\n%s", to_email, subject, html)
        return True

    raise EmailDeliveryError(f"未知 email_provider: {provider}")


def _build_message(to_email: str, subject: str, html: str) -> EmailMessage:
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = subject
    # 纯文本兜底（部分客户端不渲染 HTML）。
    msg.set_content("请使用支持 HTML 的邮件客户端查看本周报。")
    msg.add_alternative(html, subtype="html")
    return msg


def _send_via_smtp(to_email: str, subject: str, html: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host:
        raise EmailDeliveryError("未配置 SMTP_HOST")

    msg = _build_message(to_email, subject, html)
    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password or "")
                smtp.send_message(msg)
        else:
            # 非 STARTTLS：通常是 465 SSL 端口。
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password or "")
                smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError(f"SMTP 发送失败: {exc}") from exc

    logger.info("SMTP 邮件已发送 to=%s subject=%s", to_email, subject)
    return True


def _send_via_resend(to_email: str, subject: str, html: str) -> bool:
    settings = get_settings()
    if not settings.resend_api_key:
        raise EmailDeliveryError("未配置 RESEND_API_KEY")

    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.email_from,
                "to": [to_email],
                "subject": subject,
                "html": html,
            },
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(f"Resend 发送失败: {exc}") from exc

    logger.info("Resend 邮件已发送 to=%s subject=%s", to_email, subject)
    return True
