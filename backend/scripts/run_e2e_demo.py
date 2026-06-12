"""端到端演示：采集真实 App Store 评论 → LLM 分类 → 生成周报 → 写入临时文件。

用法（在 backend 目录）：
    uv run python scripts/run_e2e_demo.py

输出：backend/tmp/digest-report-<timestamp>.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models.competitor_app import CompetitorApp
from app.models.enums import Platform, SourceKind
from app.models.monitored_app import MonitoredApp
from app.services.change_detector import build_change_context
from app.services.digest_generator import generate_digest
from app.services.ingestion import get_ingestor
from app.services.review_classifier import classify_pending, get_unclassified_reviews
from app.services.review_normalizer import persist_reviews
from app.services.url_parser import parse_app_url

# 演示 App：Telegram（评论量稳定、话题丰富）
DEMO_APP = {
    "name": "Telegram",
    "owner_email": "demo@signaldigest.local",
    "app_store_url": "https://apps.apple.com/us/app/telegram-messenger/id686449807",
    "country_codes": ["us"],
}
# 竞品：WhatsApp
DEMO_COMPETITOR = {
    "name": "WhatsApp",
    "app_store_url": "https://apps.apple.com/us/app/whatsapp-messenger/id310633997",
}
MAX_REVIEWS = 80  # 控制 LLM 分类成本与耗时


def _section_md(title: str, items: list) -> str:
    if not items:
        return ""
    lines = [f"### {title}", ""]
    for i, item in enumerate(items, 1):
        if isinstance(item, str):
            lines.append(f"{i}. {item}")
        elif isinstance(item, dict):
            text = item.get("title") or item.get("summary") or item.get("change") or ""
            detail = item.get("detail") or item.get("why") or ""
            evidence = item.get("evidence_review_ids") or item.get("evidence") or []
            lines.append(f"{i}. **{text}**")
            if detail:
                lines.append(f"   - {detail}")
            if evidence:
                lines.append(f"   - 证据 review ids: {evidence}")
        else:
            lines.append(f"{i}. {item}")
        lines.append("")
    return "\n".join(lines)


def report_to_markdown(report) -> str:
    """把 DigestReport 格式化为可读 Markdown。"""
    period = f"{report.period_start:%Y-%m-%d} ~ {report.period_end:%Y-%m-%d}"
    sections = report.sections or {}
    titles = {
        "top_changes": "Top Changes / 本周最重要变化",
        "new_complaints": "New Complaints / 新增投诉",
        "new_praise": "New Praise / 新增好评",
        "rating_movement": "Rating Movement / 评分变化",
        "release_impact": "Release Impact / 发版影响",
        "competitor_moves": "Competitor Moves / 竞品动向",
        "recommended_actions": "Recommended Actions / 建议行动",
        "confidence_notes": "Confidence Notes / 置信度提示",
    }
    parts = [
        f"# {report.title or 'SignalDigest Weekly Report'}",
        "",
        f"- **Period**: {period}",
        f"- **Status**: {report.status}",
        f"- **Model**: {report.llm_model or 'n/a'}",
        f"- **Tokens**: {report.tokens_used}",
        f"- **Evidence reviews**: {len(report.evidence_review_ids or [])} ids",
        "",
        "## Summary",
        "",
        report.summary or "_(empty)_",
        "",
    ]
    for key, title in titles.items():
        block = _section_md(title, sections.get(key, []))
        if block:
            parts.append(block)
    parts.append("## Raw sections JSON")
    parts.append("")
    parts.append("```json")
    parts.append(json.dumps(sections, ensure_ascii=False, indent=2))
    parts.append("```")
    return "\n".join(parts)


def main() -> Path:
    init_db()
    with Session(engine) as session:
        # 清理旧演示数据（同名 App）
        for old in session.exec(select(MonitoredApp).where(MonitoredApp.name == DEMO_APP["name"])).all():
            session.delete(old)
        session.commit()

        parsed = parse_app_url(DEMO_APP["app_store_url"])
        app = MonitoredApp(
            name=DEMO_APP["name"],
            owner_email=DEMO_APP["owner_email"],
            app_store_url=DEMO_APP["app_store_url"],
            app_store_id=parsed.app_store_id,
            country_codes=DEMO_APP["country_codes"],
        )
        session.add(app)
        session.commit()
        session.refresh(app)
        assert app.id is not None

        comp_parsed = parse_app_url(DEMO_COMPETITOR["app_store_url"])
        competitor = CompetitorApp(
            monitored_app_id=app.id,
            name=DEMO_COMPETITOR["name"],
            app_store_url=DEMO_COMPETITOR["app_store_url"],
            app_store_id=comp_parsed.app_store_id,
        )
        session.add(competitor)
        session.commit()

        print(f"[1/4] 创建监控 App: {app.name} (id={app.id}, app_store_id={app.app_store_id})")

        ingestor = get_ingestor(Platform.APP_STORE)
        raw = ingestor.fetch(
            app_identifier=app.app_store_id,
            country_codes=app.country_codes,
            max_reviews=MAX_REVIEWS,
        )
        inserted = persist_reviews(
            session, raw, source_kind=SourceKind.OWN, monitored_app_id=app.id
        )
        print(f"[2/4] 采集完成: fetched={len(raw)} inserted={inserted}")

        pending = get_unclassified_reviews(session, monitored_app_id=app.id)
        classified = classify_pending(session, pending)
        print(f"[3/4] 分类完成: {classified} 条")

        ctx = build_change_context(session, app.id)
        report = generate_digest(session, ctx)
        print(f"[4/4] 周报生成: id={report.id} title={report.title!r} tokens={report.tokens_used}")

    out_dir = Path(__file__).resolve().parent.parent / "tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"digest-report-{ts}.md"
    out_path.write_text(report_to_markdown(report), encoding="utf-8")
    print(f"\n周报已写入: {out_path}")
    return out_path


if __name__ == "__main__":
    main()
