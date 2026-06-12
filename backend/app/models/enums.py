"""领域枚举。

设计文档第 18 节决策：架构保留 source_type / platform 的扩展能力，
首期只启用 app + (app_store | google_play)。
"""

from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    """信号来源大类。首期仅 APP，预留 CREATOR（视频站）。"""

    APP = "app"
    CREATOR = "creator"  # 预留：Phase 4 视频站评论分析


class Platform(StrEnum):
    """具体平台。首期仅启用 APP_STORE / GOOGLE_PLAY。"""

    APP_STORE = "app_store"
    GOOGLE_PLAY = "google_play"
    YOUTUBE = "youtube"  # 预留
    TIKTOK = "tiktok"  # 预留
    BILIBILI = "bilibili"  # 预留


class SourceKind(StrEnum):
    """评论归属：自己的 App 还是竞品。"""

    OWN = "own"
    COMPETITOR = "competitor"


class MonitorStatus(StrEnum):
    """监控 App 状态。"""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class Sentiment(StrEnum):
    """评论情绪（第 6.4 ReviewInsight）。"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


class Intent(StrEnum):
    """评论意图（第 6.4）。"""

    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    PRICING = "pricing"
    USABILITY = "usability"
    PRAISE = "praise"
    COMPETITOR_COMPARISON = "competitor_comparison"
    OTHER = "other"


class Priority(StrEnum):
    """优先级（第 6.4）。"""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    NONE = "none"


class DigestStatus(StrEnum):
    """周报状态（第 6.5 / 8.3 审核流程）。"""

    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
