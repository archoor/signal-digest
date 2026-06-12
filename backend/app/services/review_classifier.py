"""评论分类器（设计文档第 6.4 / 7.2 / 9.4）。

对单条评论打 sentiment / intent / priority 标签。

成本控制策略（第 9.4）：
- 默认用便宜模型（settings.llm_classifier_model）。
- 批量分类（一次请求处理 batch_size 条），减少请求数。
- LLM 失败或关闭时，自动降级到基于评分的规则分类，保证流程不中断。
"""

from __future__ import annotations

import json

from sqlmodel import Session, select

from app.config import get_settings
from app.core.logging import get_logger
from app.models.app_review import AppReview
from app.models.enums import Intent, Priority, Sentiment
from app.models.review_insight import ReviewInsight

logger = get_logger(__name__)


# ----------------------------- 规则兜底 -----------------------------

def rule_based_sentiment(rating: int | None) -> Sentiment:
    """基于评分的低成本兜底情绪判断。"""
    if rating is None:
        return Sentiment.NEUTRAL
    if rating <= 2:
        return Sentiment.NEGATIVE
    if rating >= 4:
        return Sentiment.POSITIVE
    return Sentiment.NEUTRAL


def classify_review_rule(review: AppReview) -> ReviewInsight:
    """纯规则分类（无 LLM 时使用）。"""
    sentiment = rule_based_sentiment(review.rating)
    priority = Priority.P1 if sentiment == Sentiment.NEGATIVE else Priority.NONE
    return ReviewInsight(
        review_id=review.id,
        sentiment=sentiment,
        intent=Intent.OTHER,
        feature_area=None,
        priority=priority,
        summary=None,
    )


# ----------------------------- 安全枚举解析 -----------------------------

def _safe_enum(enum_cls, value, default):
    """把 LLM 返回的字符串安全映射到枚举，非法值回落到 default。

    兼容大小写差异（如 Priority 的 P0/none）。
    """
    if value is None:
        return default
    raw = str(value).strip()
    for candidate in (raw, raw.lower(), raw.upper()):
        try:
            return enum_cls(candidate)
        except ValueError:
            continue
    return default


# ----------------------------- LLM 批量分类 -----------------------------

_CLASSIFIER_PROMPT = """你是 App 评论分类器。请对下面每条评论打标签，并严格输出 JSON。
对每条评论判断：
- sentiment: positive | neutral | negative | urgent
  （urgent 指严重崩溃 / 无法使用 / 数据丢失等需立即处理的问题）
- intent: bug | feature_request | pricing | usability | praise
  | competitor_comparison | other
- feature_area: 评论涉及的功能模块，简短英文短语，没有则 null
- priority: P0 | P1 | P2 | P3 | none（P0 最高，仅用于 urgent 严重问题）
- summary: 不超过 20 字的中文一句话概括

只输出 JSON 对象，格式：
{"results": [{"review_id": 1, "sentiment": "...", "intent": "...",
"feature_area": null, "priority": "...", "summary": "..."}]}
"""


def _build_batch_payload(reviews: list[AppReview], body_max: int) -> list[dict]:
    return [
        {
            "review_id": r.id,
            "rating": r.rating,
            "title": r.title,
            "body": (r.body or "")[:body_max],
        }
        for r in reviews
    ]


def _classify_batch_llm(reviews: list[AppReview]) -> dict[int, ReviewInsight]:
    """对一批评论调用 LLM 分类，返回 {review_id: ReviewInsight}。

    任何异常都向上抛出，由调用方决定是否降级。
    """
    settings = get_settings()
    from litellm import completion

    prompt = (
        _CLASSIFIER_PROMPT
        + "\n\n待分类评论：\n"
        + json.dumps(
            _build_batch_payload(reviews, settings.classifier_body_max_chars),
            ensure_ascii=False,
        )
    )
    resp = completion(
        model=settings.llm_classifier_model,
        api_key=settings.llm_api_key,
        api_base=settings.llm_api_base,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    data = json.loads(content)

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


# ----------------------------- 对外入口 -----------------------------

def get_unclassified_reviews(
    session: Session, monitored_app_id: int | None = None, limit: int = 200
) -> list[AppReview]:
    """查出尚未生成 ReviewInsight 的评论。"""
    classified_ids = select(ReviewInsight.review_id)
    stmt = select(AppReview).where(AppReview.id.not_in(classified_ids))
    if monitored_app_id is not None:
        stmt = stmt.where(AppReview.monitored_app_id == monitored_app_id)
    return list(session.exec(stmt.limit(limit)).all())


def classify_pending(session: Session, reviews: list[AppReview]) -> int:
    """批量分类并入库，返回新增 insight 数。

    启用 LLM 时按 batch_size 分批调用，单批失败自动降级为规则分类。
    """
    if not reviews:
        return 0

    settings = get_settings()
    use_llm = settings.enable_llm_classification and bool(settings.llm_api_key)
    count = 0

    if not use_llm:
        for review in reviews:
            session.add(classify_review_rule(review))
            count += 1
        session.commit()
        logger.info("规则分类完成：%d 条", count)
        return count

    batch_size = max(1, settings.classifier_batch_size)
    for start in range(0, len(reviews), batch_size):
        batch = reviews[start : start + batch_size]
        try:
            insights = _classify_batch_llm(batch)
        except Exception as exc:  # noqa: BLE001 - 单批失败降级，不中断整体
            logger.warning("LLM 分类失败，降级规则分类 err=%s", exc)
            insights = {}

        for review in batch:
            insight = insights.get(review.id) or classify_review_rule(review)
            session.add(insight)
            count += 1
        session.commit()

    logger.info("分类完成（LLM）：%d 条", count)
    return count
