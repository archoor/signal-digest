"""周报邮件渲染与传输测试。"""

from __future__ import annotations

from app.models.base import utcnow
from app.models.digest_report import DigestReport, empty_sections
from app.services.digest_delivery import render_email_html


def _make_report() -> DigestReport:
    sections = empty_sections()
    sections["top_changes"] = ["崩溃投诉增加 3 倍"]
    sections["recommended_actions"] = [
        {"title": "修复登录崩溃", "detail": "影响 iOS 17 用户"}
    ]
    return DigestReport(
        id=1,
        monitored_app_id=1,
        period_start=utcnow(),
        period_end=utcnow(),
        title="本周用户开始抱怨登录崩溃",
        summary="登录崩溃投诉明显增多，建议优先修复。",
        sections=sections,
    )


def test_render_email_html_contains_key_parts() -> None:
    html = render_email_html(_make_report())
    assert "本周用户开始抱怨登录崩溃" in html
    assert "登录崩溃投诉明显增多" in html
    assert "本周最重要的变化" in html
    assert "崩溃投诉增加 3 倍" in html
    # dict 条目应被渲染成 "标题 — 细节"
    assert "修复登录崩溃" in html
    assert "影响 iOS 17 用户" in html


def test_render_email_escapes_html() -> None:
    report = _make_report()
    report.title = "<script>alert(1)</script>"
    html = render_email_html(report)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
