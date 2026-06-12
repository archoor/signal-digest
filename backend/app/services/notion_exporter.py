"""Notion 导出（设计文档第 8 章，可选）。

Notion 不作为正式数据库，仅作为人工审核工作台：
只写 P0/P1 评论、每周报告、需人工确认的结论、客户试点状态。
"""

from __future__ import annotations

from app.config import get_settings
from app.core.logging import get_logger
from app.models.digest_report import DigestReport

logger = get_logger(__name__)


def export_digest_to_notion(report: DigestReport) -> str | None:
    """把周报导出到 Notion Weekly Reports 数据库，返回页面 URL。"""
    settings = get_settings()
    if not settings.notion_api_key or not settings.notion_reports_database_id:
        logger.info("未配置 Notion，跳过导出 report_id=%s", report.id)
        return None

    # TODO: 调用 Notion API 创建页面（第 8.1 / 8.3）。
    raise NotImplementedError("Notion 导出为可选功能，待接入 notion-client。")
