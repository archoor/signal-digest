"""评论分类与 LLM 深度分析（设计文档第 6.4 / 9.4）。

流程：
1. 规则分类（全部评论：情绪 / 优先级，不调 LLM）
2. 按批次 LLM  enrich：仅对有效字数 ≥ n 的好评/差评逐条生成「好在哪里 / 痛点」
"""

from __future__ import annotations

import json
import re
import threading

from sqlmodel import Session, select

from app.config import get_settings
from app.services.external_http import llm_proxy_env
from app.core.logging import get_logger
from app.models.app_review import AppReview
from app.models.enums import Intent, Priority, Sentiment
from app.models.review_insight import ReviewInsight

logger = get_logger(__name__)

SUMMARY_PLACEHOLDER_POSITIVE = "高分评论，具体优点待 LLM 补全"
SUMMARY_PLACEHOLDER_NEGATIVE = "低分评论，具体痛点待 LLM 补全"


# ----------------------------- 正文有效长度 -----------------------------


def effective_body_length(body: str | None) -> int:
    """有效字符数：去空白后保留字母、数字、CJK，用于过滤过短评论。"""
    if not body:
        return 0
    cleaned = re.sub(r"\s+", "", body.strip())
    meaningful = re.sub(r"[^\w]", "", cleaned, flags=re.UNICODE)
    return len(meaningful)


def is_placeholder_summary(summary: str | None) -> bool:
    if not summary:
        return True
    if summary in (SUMMARY_PLACEHOLDER_POSITIVE, SUMMARY_PLACEHOLDER_NEGATIVE):
        return True
    return "待 LLM 补全" in summary


def is_displayable_summary(summary: str | None) -> bool:
    """前端是否展示「好在哪里 / 痛点」分析框。"""
    return bool(summary) and not is_placeholder_summary(summary)


# ----------------------------- 规则兜底 -----------------------------


def rule_based_sentiment(rating: int | None) -> Sentiment:
    if rating is None:
        return Sentiment.NEUTRAL
    if rating <= 2:
        return Sentiment.NEGATIVE
    if rating >= 4:
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL


def classify_review_rule(review: AppReview) -> ReviewInsight:
    settings = get_settings()
    sentiment = rule_based_sentiment(review.rating)
    priority = Priority.P1 if sentiment == Sentiment.NEGATIVE else Priority.NONE
    summary: str | None = None

    if effective_body_length(review.body) >= settings.classifier_min_body_chars:
        if sentiment == Sentiment.POSITIVE:
            summary = SUMMARY_PLACEHOLDER_POSITIVE
        elif sentiment == Sentiment.NEGATIVE:
            summary = SUMMARY_PLACEHOLDER_NEGATIVE

    return ReviewInsight(
        review_id=review.id,
        sentiment=sentiment,
        intent=Intent.OTHER,
        feature_area=None,
        priority=priority,
        summary=summary,
    )


# ----------------------------- 安全枚举解析 -----------------------------


def _safe_enum(enum_cls, value, default):
    if value is None:
        return default
    raw = str(value).strip()
    for candidate in (raw, raw.lower(), raw.upper()):
        try:
            return enum_cls(candidate)
        except ValueError:
            continue
    return default


# ----------------------------- LLM 批量 enrich（好/不好原因） -----------------------------

_ENRICH_PROMPT = """你是 App 评论分析师。下面每条评论已标注为好评或差评。
请逐条输出中文分析，严格 JSON：
{"results": [{"review_id": 1, "summary": "50-80字：好评写具体优点，差评写具体痛点/不足"}]}

要求：
- 输入有几条，results 就必须有几条，review_id 与输入一致
- summary 要具体、可行动，避免空泛套话，不要照抄原文
- 好评 focus 用户认可什么；差评 focus 具体问题或不满
"""


def _review_kind_label(review: AppReview) -> str:
    rating = review.rating
    if rating is not None and rating >= 4:
        return "好评"
    if rating is not None and rating <= 2:
        return "差评"
    return "待分析"


def _build_enrich_payload(reviews: list[AppReview], body_max: int) -> list[dict]:
    return [
        {
            "review_id": r.id,
            "kind": _review_kind_label(r),
            "rating": r.rating,
            "title": r.title,
            "body": (r.body or "")[:body_max],
        }
        for r in reviews
    ]


def _enrich_batch_llm(reviews: list[AppReview]) -> dict[int, str]:
    """一批评论的 LLM 深度分析，返回 {review_id: summary}。"""
    settings = get_settings()
    from litellm import completion

    prompt = (
        _ENRICH_PROMPT
        + "\n\n待分析评论：\n"
        + json.dumps(
            _build_enrich_payload(reviews, settings.classifier_body_max_chars),
            ensure_ascii=False,
        )
    )
    with llm_proxy_env():
        resp = completion(
            model=settings.llm_classifier_model,
            api_key=settings.llm_api_key,
            api_base=settings.llm_api_base,
            timeout=settings.llm_timeout,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)

    out: dict[int, str] = {}
    for item in data.get("results", []):
        rid = item.get("review_id")
        summary = item.get("summary")
        if rid is not None and summary:
            out[int(rid)] = str(summary).strip()
    return out


def _is_llm_enrich_candidate(
    review: AppReview, insight: ReviewInsight, min_chars: int
) -> bool:
    """是否为好评/差评且有效字数足够、需要 LLM 分析。"""
    if effective_body_length(review.body) < min_chars:
        return False
    if not is_placeholder_summary(insight.summary):
        return False

    rating = review.rating
    if rating is not None and rating >= 4:
        return True
    if rating is not None and rating <= 2:
        return True
    if insight.sentiment in (Sentiment.NEGATIVE, Sentiment.URGENT):
        return True
    if insight.sentiment == Sentiment.POSITIVE:
        return True
    return False


# ----------------------------- 对外入口 -----------------------------


def get_unclassified_reviews(
    session: Session, monitored_app_id: int | None = None, limit: int = 500
) -> list[AppReview]:
    classified_ids = select(ReviewInsight.review_id)
    stmt = select(AppReview).where(AppReview.id.not_in(classified_ids))
    if monitored_app_id is not None:
        stmt = stmt.where(AppReview.monitored_app_id == monitored_app_id)
    return list(session.exec(stmt.limit(limit)).all())


def get_reviews_needing_enrichment(
    session: Session, monitored_app_id: int, *, limit: int = 500
) -> list[tuple[AppReview, ReviewInsight]]:
    """待 LLM enrich 的好评/差评（有效字数足够且 summary 仍为占位）。"""
    settings = get_settings()
    min_chars = settings.classifier_min_body_chars

    stmt = (
        select(AppReview, ReviewInsight)
        .join(ReviewInsight, ReviewInsight.review_id == AppReview.id)
        .where(AppReview.monitored_app_id == monitored_app_id)
        .order_by(AppReview.source_created_at.desc())
    )
    rows = list(session.exec(stmt).all())

    out: list[tuple[AppReview, ReviewInsight]] = []
    for review, insight in rows:
        if _is_llm_enrich_candidate(review, insight, min_chars):
            out.append((review, insight))
        if len(out) >= limit:
            break
    return out


def classify_pending(
    session: Session, reviews: list[AppReview], *, use_llm: bool | None = None
) -> int:
    """规则分类并入库（默认不调 LLM）。"""
    if not reviews:
        return 0

    # 兼容旧参数：仅当显式 use_llm=True 且配置齐全时走完整 LLM 分类（不推荐）
    settings = get_settings()
    if use_llm is None:
        use_llm = False
    count = 0

    def _add_insight(review: AppReview, insight: ReviewInsight) -> None:
        nonlocal count
        exists = session.exec(
            select(ReviewInsight.id).where(ReviewInsight.review_id == review.id)
        ).first()
        if exists:
            return
        session.add(insight)
        count += 1

    if use_llm and settings.enable_llm_classification and settings.llm_api_key:
        return _classify_pending_full_llm(session, reviews)

    for review in reviews:
        _add_insight(review, classify_review_rule(review))
    session.commit()
    logger.info("规则分类完成：%d 条", count)
    return count


def _classify_pending_full_llm(session: Session, reviews: list[AppReview]) -> int:
    """旧版全量 LLM 分类（保留兼容）。"""
    settings = get_settings()
    count = 0
    batch_size = max(1, settings.classifier_batch_size)

    def _add_insight(review: AppReview, insight: ReviewInsight) -> None:
        nonlocal count
        exists = session.exec(
            select(ReviewInsight.id).where(ReviewInsight.review_id == review.id)
        ).first()
        if exists:
            return
        session.add(insight)
        count += 1

    for start in range(0, len(reviews), batch_size):
        batch = reviews[start : start + batch_size]
        try:
            insights = _classify_batch_llm_legacy(batch)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 分类失败，降级规则分类 err=%s", exc)
            insights = {}

        for review in batch:
            insight = insights.get(review.id) or classify_review_rule(review)
            _add_insight(review, insight)
        session.commit()

    logger.info("分类完成（LLM）：%d 条", count)
    return count


_CLASSIFIER_PROMPT_LEGACY = """你是 App 评论分类器。请对下面每条评论打标签，并严格输出 JSON。
对每条评论判断：
- sentiment: positive | neutral | negative | urgent
- intent: bug | feature_request | pricing | usability | praise | competitor_comparison | other
- feature_area: 评论涉及的功能模块，简短英文短语，没有则 null
- priority: P0 | P1 | P2 | P3 | none
- summary: 50-80 字中文分析。好评写优点；差评写痛点

只输出 JSON：{"results": [{"review_id": 1, "sentiment": "...", "intent": "...",
"feature_area": null, "priority": "...", "summary": "..."}]}
"""


def _classify_batch_llm_legacy(reviews: list[AppReview]) -> dict[int, ReviewInsight]:
    settings = get_settings()
    from litellm import completion

    payload = [
        {
            "review_id": r.id,
            "rating": r.rating,
            "title": r.title,
            "body": (r.body or "")[: settings.classifier_body_max_chars],
        }
        for r in reviews
    ]
    prompt = _CLASSIFIER_PROMPT_LEGACY + "\n\n待分类评论：\n" + json.dumps(
        payload, ensure_ascii=False
    )
    with llm_proxy_env():
        resp = completion(
            model=settings.llm_classifier_model,
            api_key=settings.llm_api_key,
            api_base=settings.llm_api_base,
            timeout=settings.llm_timeout,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    data = json.loads(resp.choices[0].message.content or "{}")
    out: dict[int, ReviewInsight] = {}
    for item in data.get("results", []):
        rid = item.get("review_id")
        if rid is None:
            continue
        out[int(rid)] = ReviewInsight(
            review_id=int(rid),
            sentiment=_safe_enum(Sentiment, item.get("sentiment"), Sentiment.NEUTRAL),
            intent=_safe_enum(Intent, item.get("intent"), Intent.OTHER),
            feature_area=item.get("feature_area"),
            priority=_safe_enum(Priority, item.get("priority"), Priority.NONE),
            summary=item.get("summary"),
        )
    return out


def count_skipped_short_reviews(session: Session, monitored_app_id: int) -> int:
    """有 insight 但正文过短、仍为占位 summary 的评论数。"""
    settings = get_settings()
    stmt = (
        select(AppReview, ReviewInsight)
        .join(ReviewInsight, ReviewInsight.review_id == AppReview.id)
        .where(AppReview.monitored_app_id == monitored_app_id)
    )
    return sum(
        1
        for review, insight in session.exec(stmt).all()
        if is_placeholder_summary(insight.summary)
        and effective_body_length(review.body) < settings.classifier_min_body_chars
    )


def enrich_insights_llm(
    session: Session, monitored_app_id: int, *, limit: int = 500
) -> dict:
    """按批次对好评/差评做 LLM 深度分析，逐条更新 summary。"""
    settings = get_settings()
    if not settings.enable_llm_classification or not settings.llm_api_key:
        return {
            "enriched": 0,
            "batches": 0,
            "candidates": 0,
            "skipped_short": 0,
            "message": "未启用 LLM 或未配置 API Key",
        }

    candidates = get_reviews_needing_enrichment(session, monitored_app_id, limit=limit)
    batch_size = max(1, settings.classifier_batch_size)
    enriched = 0
    batches = 0
    errors: list[str] = []

    for start in range(0, len(candidates), batch_size):
        batch = candidates[start : start + batch_size]
        reviews = [r for r, _ in batch]
        try:
            summaries = _enrich_batch_llm(reviews)
            batches += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM enrich 批次失败 batch=%s err=%s", batches + 1, exc)
            errors.append(str(exc))
            continue

        for review, insight in batch:
            summary = summaries.get(review.id)
            if not summary:
                continue
            insight.summary = summary
            session.add(insight)
            enriched += 1
        try:
            session.commit()
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            logger.warning(
                "LLM enrich 批次入库失败 batch=%s app_id=%s err=%s",
                batches,
                monitored_app_id,
                exc,
            )
            errors.append(str(exc))
            continue
        logger.info(
            "LLM enrich 批次 %d 完成 app_id=%s 本批 %d 条",
            batches,
            monitored_app_id,
            len(summaries),
        )

    skipped_short = count_skipped_short_reviews(session, monitored_app_id)

    message = f"已完成 {batches} 个批次，LLM 分析 {enriched} 条评论。"
    if skipped_short:
        message += f" {skipped_short} 条过短评论未调用 LLM。"
    if errors:
        message += f" 部分批次失败：{errors[0][:80]}"

    return {
        "enriched": enriched,
        "batches": batches,
        "candidates": len(candidates),
        "skipped_short": skipped_short,
        "message": message,
    }


def dedupe_review_insights(session: Session, *, monitored_app_id: int | None = None) -> int:
    """删除同一 review 的重复 insight，保留 summary 最完整的一条。"""
    from sqlalchemy import func

    scope_review_ids: set[int] | None = None
    if monitored_app_id is not None:
        scope_review_ids = set(
            session.exec(
                select(AppReview.id).where(
                    AppReview.monitored_app_id == monitored_app_id
                )
            ).all()
        )

    dup_review_ids = session.exec(
        select(ReviewInsight.review_id)
        .group_by(ReviewInsight.review_id)
        .having(func.count() > 1)
    ).all()
    if scope_review_ids is not None:
        dup_review_ids = [rid for rid in dup_review_ids if rid in scope_review_ids]

    removed = 0
    for review_id in dup_review_ids:
        rows = list(
            session.exec(
                select(ReviewInsight)
                .where(ReviewInsight.review_id == review_id)
                .order_by(ReviewInsight.id)
            ).all()
        )
        rows.sort(
            key=lambda row: (
                is_displayable_summary(row.summary),
                not is_placeholder_summary(row.summary),
                row.id or 0,
            ),
            reverse=True,
        )
        for row in rows[1:]:
            session.delete(row)
            removed += 1

    if removed:
        session.commit()
        logger.info(
            "去重 review_insight：删除 %d 条重复记录 app_id=%s",
            removed,
            monitored_app_id,
        )
    return removed


def classify_app_sync(
    session: Session, monitored_app_id: int, *, review_limit: int = 500
) -> dict:
    """规则分类（同步、快速），统计待 enrich 数量，不阻塞 LLM。"""
    settings = get_settings()
    dedupe_review_insights(session, monitored_app_id=monitored_app_id)
    pending = get_unclassified_reviews(session, monitored_app_id, limit=review_limit)
    classified = classify_pending(session, pending, use_llm=False)
    candidates = get_reviews_needing_enrichment(
        session, monitored_app_id, limit=review_limit
    )
    skipped_short = count_skipped_short_reviews(session, monitored_app_id)

    enrich_queued = False
    parts = [f"规则分类 {classified} 条"]
    if not settings.enable_llm_classification or not settings.llm_api_key:
        parts.append("未启用 LLM 或未配置 API Key，跳过深度分析")
    elif not candidates:
        parts.append("暂无待 LLM 分析的评论")
    else:
        enrich_queued = True
        parts.append(f"已后台排队 {len(candidates)} 条待 LLM 分析，请稍后刷新查看")
    if skipped_short:
        parts.append(f"{skipped_short} 条过短评论未分析")

    return {
        "classified": classified,
        "enriched": 0,
        "batches": 0,
        "candidates": len(candidates),
        "skipped_short": skipped_short,
        "enrich_queued": enrich_queued,
        "message": "。".join(parts) + "。",
    }


def run_enrich_insights_background(
    monitored_app_id: int, *, review_limit: int = 500
) -> None:
    """后台按批次 LLM enrich（独立 DB 会话，避免阻塞 HTTP）。"""
    from app.db import engine

    with Session(engine) as session:
        try:
            result = enrich_insights_llm(session, monitored_app_id, limit=review_limit)
            logger.info(
                "后台 LLM enrich 完成 app_id=%s enriched=%s batches=%s",
                monitored_app_id,
                result.get("enriched"),
                result.get("batches"),
            )
        except Exception:  # noqa: BLE001
            logger.exception("后台 LLM enrich 失败 app_id=%s", monitored_app_id)


_enrich_lock = threading.Lock()
_enrich_running: set[int] = set()


def enqueue_enrich_insights(monitored_app_id: int, *, review_limit: int = 500) -> bool:
    """在独立守护线程中启动 LLM enrich；同一 App 不重复排队。返回是否已启动新任务。"""
    with _enrich_lock:
        if monitored_app_id in _enrich_running:
            logger.info("LLM enrich 已在运行，跳过重复排队 app_id=%s", monitored_app_id)
            return False
        _enrich_running.add(monitored_app_id)

    def _run() -> None:
        try:
            run_enrich_insights_background(monitored_app_id, review_limit=review_limit)
        finally:
            with _enrich_lock:
                _enrich_running.discard(monitored_app_id)

    threading.Thread(
        target=_run,
        daemon=True,
        name=f"enrich-app-{monitored_app_id}",
    ).start()
    return True


def classify_and_enrich_app(
    session: Session, monitored_app_id: int, *, review_limit: int = 500
) -> dict:
    """规则分类 + 同步 LLM enrich（CLI/脚本用，HTTP 请用 classify_app_sync + 后台任务）。"""
    pending = get_unclassified_reviews(session, monitored_app_id, limit=review_limit)
    classified = classify_pending(session, pending, use_llm=False)
    enrich_result = enrich_insights_llm(session, monitored_app_id, limit=review_limit)
    return {
        "classified": classified,
        **enrich_result,
    }
