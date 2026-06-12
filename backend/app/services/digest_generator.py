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

logger = get_logger(__name__)


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

        resp = completion(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            api_base=settings.llm_api_base,
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
        logger.error("LLM 周报生成失败 app_id=%s err=%s", ctx.monitored_app_id, exc)
        summary = f"周报生成失败：{exc}"

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
    return report
