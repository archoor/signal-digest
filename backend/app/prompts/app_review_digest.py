"""App Review Digest 的 Prompt 构造（设计文档第 9.2 / 9.3）。

硬约束：
- 不夸大低样本数据；评论太少时输出 confidence low。
- 不编造不存在的竞品变化。
- 每个 insight 必须绑定 evidence review ids。
- recommended actions 必须具体到产品 / 支持 / 增长 / ASO 动作。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.change_detector import ChangeContext

_OUTPUT_SCHEMA = {
    "title": "",
    "summary": "",
    "top_changes": [],
    "new_complaints": [],
    "new_praise": [],
    "rating_movement": [],
    "release_impact": [],
    "competitor_moves": [],
    "recommended_actions": [],
    "confidence_notes": [],
}

_SYSTEM_RULES = """你是一名资深 App 产品分析师。
请基于给定的评论数据，生成一份「What changed?」周报。
要求：
1. 聚焦本周相比上周发生了什么重要变化，而非静态情绪分析。
2. 不夸大低样本数据；如果评论量太少，请在 confidence_notes 中明确写出 confidence low。
3. 不要编造不存在的竞品变化。
4. 每条结论都要引用对应的 evidence review id（来自输入数据的 review id）。
5. recommended_actions 必须具体到产品、支持、增长或 ASO 动作，最多 3 条。
6. 严格输出 JSON，结构如下，不要输出多余文字。
"""


def _serialize_reviews(reviews, limit: int = 15) -> list[dict]:
    out = []
    for r in reviews[:limit]:
        out.append(
            {
                "review_id": r.id,
                "rating": r.rating,
                "title": r.title,
                "body": (r.body or "")[:280],
                "country": r.country,
                "app_version": r.app_version,
                "created_at": r.source_created_at.isoformat(),
            }
        )
    return out


def build_digest_prompt(ctx: ChangeContext) -> str:
    """组装完整 prompt 文本。"""
    payload = {
        "period": {
            "start": ctx.period_start.isoformat(),
            "end": ctx.period_end.isoformat(),
        },
        "current_window": {
            "review_count": ctx.current.review_count,
            "avg_rating": ctx.current.avg_rating,
            "rating_distribution": ctx.current.rating_distribution,
        },
        "previous_window": {
            "review_count": ctx.previous.review_count,
            "avg_rating": ctx.previous.avg_rating,
            "rating_distribution": ctx.previous.rating_distribution,
        },
        "own_reviews": _serialize_reviews(ctx.current_reviews),
        "competitor_reviews": _serialize_reviews(ctx.competitor_reviews),
    }

    return (
        _SYSTEM_RULES
        + "\n\n输出 JSON 结构：\n"
        + json.dumps(_OUTPUT_SCHEMA, ensure_ascii=False, indent=2)
        + "\n\n评论数据：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
