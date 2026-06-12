"""数据模型聚合导出（设计文档第 6 章）。

集中导入，确保 SQLModel.metadata 注册到所有表。
"""

from app.models.app_review import AppReview
from app.models.competitor_app import CompetitorApp
from app.models.digest_report import DigestReport
from app.models.monitored_app import MonitoredApp
from app.models.review_insight import ReviewInsight

__all__ = [
    "AppReview",
    "CompetitorApp",
    "DigestReport",
    "MonitoredApp",
    "ReviewInsight",
]
