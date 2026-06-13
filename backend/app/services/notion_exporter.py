"""Notion 导出（设计文档第 8 章，可选）。

Notion 不作为正式数据库，仅作为人工审核工作台：
只写周报页面（含摘要、各 section、证据 review id），供运营审核。
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from sqlmodel import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.models.digest_report import DigestReport
from app.services.digest_delivery import SECTION_TITLES, item_to_text

logger = get_logger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
# Notion rich_text 单段最长 2000 字符；单次 create page 最多 100 个 block。
_RICH_TEXT_CHUNK = 2000
_MAX_CHILDREN = 100


class NotionExportError(Exception):
    """Notion API 调用失败。"""


def _normalize_database_id(raw: str) -> str:
    """把 URL 或带连字符的 ID 规范为 32 位 hex（Notion API 接受两种格式）。"""
    cleaned = raw.strip().split("?")[0].split("/")[-1]
    hex_only = re.sub(r"[^0-9a-fA-F]", "", cleaned)
    if len(hex_only) != 32:
        raise NotionExportError(f"无效的 Notion Database ID：{raw}")
    return f"{hex_only[:8]}-{hex_only[8:12]}-{hex_only[12:16]}-{hex_only[16:20]}-{hex_only[20:]}"


def _rich_text(content: str) -> list[dict[str, Any]]:
    """把长文本切成 Notion rich_text 数组。"""
    if not content:
        return [{"type": "text", "text": {"content": ""}}]
    parts: list[dict[str, Any]] = []
    for i in range(0, len(content), _RICH_TEXT_CHUNK):
        parts.append({"type": "text", "text": {"content": content[i : i + _RICH_TEXT_CHUNK]}})
    return parts


def _paragraph(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich_text(text)}}


def _heading2(text: str) -> dict[str, Any]:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _rich_text(text)}}


def _bullet(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(text)},
    }


def _item_evidence(item) -> list[int]:
    if isinstance(item, dict):
        raw = item.get("evidence_review_ids") or []
        return [int(x) for x in raw if x is not None]
    return []


def build_page_children(report: DigestReport) -> list[dict[str, Any]]:
    """把周报渲染为 Notion block 列表（页面正文）。"""
    blocks: list[dict[str, Any]] = []
    period = f"{report.period_start:%Y-%m-%d} ~ {report.period_end:%Y-%m-%d}"
    blocks.append(
        _paragraph(
            f"周期：{period} · 状态：{report.status.value} · App ID：{report.monitored_app_id}"
        )
    )

    if report.summary:
        blocks.append(_heading2("摘要"))
        blocks.append(_paragraph(report.summary))

    for key, title in SECTION_TITLES.items():
        items = report.sections.get(key, []) if report.sections else []
        if not items:
            continue
        blocks.append(_heading2(title))
        for item in items:
            text = item_to_text(item)
            ev = _item_evidence(item)
            if ev:
                text = f"{text}（证据 review: {', '.join(str(i) for i in ev)}）"
            blocks.append(_bullet(text))

    if report.llm_model:
        blocks.append(
            _paragraph(f"由 {report.llm_model} 生成，tokens：{report.tokens_used}")
        )

    return blocks[:_MAX_CHILDREN]


def _build_properties(report: DigestReport, title_property: str) -> dict[str, Any]:
    """数据库行属性：至少需要 Title 列（默认名 Name）。"""
    page_title = report.title or f"周报 #{report.id}"
    props: dict[str, Any] = {
        title_property: {"title": _rich_text(page_title[: _RICH_TEXT_CHUNK])},
    }

    settings = get_settings()
    if settings.notion_status_property:
        props[settings.notion_status_property] = {
            "select": {"name": report.status.value},
        }
    if settings.notion_period_property:
        props[settings.notion_period_property] = {
            "date": {"start": report.period_start.strftime("%Y-%m-%d")},
        }
    if settings.notion_report_id_property and report.id is not None:
        props[settings.notion_report_id_property] = {"number": report.id}

    return props


def _notion_request(
    method: str,
    path: str,
    *,
    api_key: str,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    url = f"{NOTION_API_BASE}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, url, headers=headers, json=json_body)
    except httpx.HTTPError as exc:
        raise NotionExportError(f"Notion 网络请求失败：{exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text
        try:
            detail = resp.json().get("message", detail)
        except Exception:  # noqa: BLE001
            pass
        raise NotionExportError(f"Notion API {resp.status_code}：{detail}")

    return resp.json()


def create_notion_page(report: DigestReport) -> str:
    """调用 Notion API 创建数据库页面，返回页面 URL。"""
    settings = get_settings()
    if not settings.notion_api_key or not settings.notion_reports_database_id:
        raise NotionExportError("未配置 NOTION_API_KEY 或 NOTION_REPORTS_DATABASE_ID")

    database_id = _normalize_database_id(settings.notion_reports_database_id)
    title_property = settings.notion_title_property or "Name"
    payload = {
        "parent": {"database_id": database_id},
        "properties": _build_properties(report, title_property),
        "children": build_page_children(report),
    }

    data = _notion_request("POST", "/pages", api_key=settings.notion_api_key, json_body=payload)
    page_url = data.get("url")
    if not page_url:
        raise NotionExportError("Notion 未返回页面 URL")
    return page_url


def export_digest_to_notion(
    report: DigestReport,
    session: Session | None = None,
    *,
    force: bool = False,
) -> str | None:
    """把周报导出到 Notion Weekly Reports 数据库，返回页面 URL。

    已导出且 force=False 时直接返回已有 URL。
    """
    settings = get_settings()
    if not settings.notion_api_key or not settings.notion_reports_database_id:
        logger.info("未配置 Notion，跳过导出 report_id=%s", report.id)
        return None

    if report.notion_page_url and not force:
        logger.info("周报已导出 Notion report_id=%s url=%s", report.id, report.notion_page_url)
        return report.notion_page_url

    page_url = create_notion_page(report)
    report.notion_page_url = page_url
    if session is not None:
        session.add(report)
        session.commit()
        session.refresh(report)
    logger.info("周报已导出 Notion report_id=%s url=%s", report.id, page_url)
    return page_url
