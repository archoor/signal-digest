"""LLM 周报生成（设计文档第 7.3 / 9 章）。

把 ChangeContext 组装成 prompt，调 LiteLLM 产出固定结构的 digest JSON，
落库为 DigestReport。每个 insight 必须绑定 evidence review ids。
"""

from __future__ import annotations

import json

from sqlmodel import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.models.digest_report import DigestReport, empty_sections
from app.models.enums import DigestStatus
from app.prompts.app_review_digest import build_digest_prompt
from app.services.change_detector import ChangeContext
from app.services.notion_exporter import NotionExportError, export_digest_to_notion

logger = get_logger(__name__)


def build_fallback_digest(ctx: ChangeContext) -> tuple[str, str, dict]:
    """LLM 不可用时的规则兜底周报（基于统计 + 抽样评论）。"""
    sections = empty_sections()
    cur, prev = ctx.current, ctx.previous
    avg_delta = None
    if cur.avg_rating is not None and prev.avg_rating is not None:
        avg_delta = round(cur.avg_rating - prev.avg_rating, 2)

    summary_parts = [
        f"本周 {cur.review_count} 条评论",
        f"上周 {prev.review_count} 条",
    ]
    if cur.avg_rating is not None:
        summary_parts.append(f"本周均分 {cur.avg_rating}")
    if avg_delta is not None:
        summary_parts.append(f"较上周 {'+' if avg_delta >= 0 else ''}{avg_delta}")
    summary = "；".join(summary_parts) + "。（规则兜底报告，LLM 未参与）"

    title = "本周评论变化摘要（规则兜底）"

    if cur.review_count != prev.review_count:
        sections["top_changes"].append(
            {
                "change": f"评论量 {prev.review_count} → {cur.review_count}",
                "evidence_review_ids": [r.id for r in ctx.current_reviews[:3] if r.id],
            }
        )
    if avg_delta is not None and abs(avg_delta) >= 0.1:
        sections["rating_movement"].append(
            {
                "change": f"平均评分 {prev.avg_rating} → {cur.avg_rating}（{avg_delta:+.2f}）",
                "evidence_review_ids": [r.id for r in ctx.current_reviews[:3] if r.id],
            }
        )

    negatives = sorted(
        [r for r in ctx.current_reviews if r.rating is not None and r.rating <= 2],
        key=lambda r: r.rating,
    )[:5]
    for r in negatives:
        pain = (r.body or "")[:80]
        sections["new_complaints"].append(
            {
                "title": (r.title or r.body[:60]),
                "pain_point": f"低分反馈：{pain}",
                "detail": f"★{r.rating} | review_id={r.id}",
                "evidence_review_ids": [r.id],
            }
        )

    positives = [r for r in ctx.current_reviews if r.rating is not None and r.rating >= 4][:5]
    for r in positives:
        strength = (r.body or "")[:80]
        sections["new_praise"].append(
            {
                "title": (r.title or r.body[:60]),
                "strength": f"用户认可：{strength}",
                "detail": f"★{r.rating} | review_id={r.id}",
                "evidence_review_ids": [r.id],
            }
        )

    if negatives:
        sections["recommended_actions"].append(
            "优先排查低分评论中的崩溃/登录/支付类问题，对照 review_id 追溯证据。"
        )
    if cur.review_count < 10:
        sections["confidence_notes"].append("confidence low：本周样本量较少，结论仅供参考。")

    return title, summary, sections


def generate_digest(session: Session, ctx: ChangeContext) -> DigestReport:
    """生成并保存一份周报（draft 状态，待人工审核）。"""
    settings = get_settings()
    prompt = build_digest_prompt(ctx)

    sections = empty_sections()
    title = ""
    summary = ""
    tokens_used = 0

    try:
        from litellm import completion
        from app.services.external_http import llm_proxy_env

        with llm_proxy_env():
            resp = completion(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                api_base=settings.llm_api_base,
                timeout=settings.llm_timeout,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        title = data.get("title", "")
        summary = data.get("summary", "")
        for key in sections:
            sections[key] = data.get(key, [])
        usage = getattr(resp, "usage", None)
        tokens_used = getattr(usage, "total_tokens", 0) if usage else 0
    except Exception as exc:  # noqa: BLE001 - 周报生成失败不应中断调度
        logger.error("LLM 周报生成失败 app_id=%s err=%s，使用规则兜底", ctx.monitored_app_id, exc)
        title, summary, sections = build_fallback_digest(ctx)
        summary = f"{summary} 原始错误：{exc}"

    evidence_ids = [r.id for r in ctx.current_reviews if r.id is not None][:20]

    report = DigestReport(
        monitored_app_id=ctx.monitored_app_id,
        period_start=ctx.period_start,
        period_end=ctx.period_end,
        status=DigestStatus.DRAFT,
        title=title,
        summary=summary,
        sections=sections,
        evidence_review_ids=evidence_ids,
        llm_model=settings.llm_model,
        tokens_used=tokens_used,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    logger.info("周报已生成 report_id=%s app_id=%s", report.id, ctx.monitored_app_id)

    if settings.notion_auto_export:
        try:
            export_digest_to_notion(report, session)
        except NotionExportError as exc:
            logger.warning("Notion 自动导出失败 report_id=%s err=%s", report.id, exc)

    return report
