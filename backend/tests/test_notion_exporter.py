"""Notion 导出测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models.base import utcnow
from app.models.digest_report import DigestReport, empty_sections
from app.models.enums import DigestStatus
from app.services.notion_exporter import (
    NotionExportError,
    _normalize_database_id,
    build_page_children,
    create_notion_page,
    export_digest_to_notion,
)


def _make_report(**kwargs) -> DigestReport:
    sections = empty_sections()
    sections["top_changes"] = ["崩溃投诉增加"]
    defaults = dict(
        id=42,
        monitored_app_id=1,
        period_start=utcnow(),
        period_end=utcnow(),
        status=DigestStatus.DRAFT,
        title="测试周报",
        summary="摘要内容",
        sections=sections,
    )
    defaults.update(kwargs)
    return DigestReport(**defaults)


def test_normalize_database_id_from_url() -> None:
    raw = "https://www.notion.so/abc1234567890abcdef1234567890abc?v=..."
    assert _normalize_database_id(raw) == "abc12345-6789-0abc-def1-234567890abc"


def test_build_page_children_includes_sections() -> None:
    blocks = build_page_children(_make_report())
    types = [b["type"] for b in blocks]
    assert "heading_2" in types
    assert "bulleted_list_item" in types
    assert any("崩溃投诉增加" in b["bulleted_list_item"]["rich_text"][0]["text"]["content"] for b in blocks if b["type"] == "bulleted_list_item")


def test_export_skipped_without_config(monkeypatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "")
    monkeypatch.setenv("NOTION_REPORTS_DATABASE_ID", "")
    from app.config import reload_settings

    reload_settings()
    report = _make_report()
    assert export_digest_to_notion(report) is None


def test_export_returns_existing_url_without_force(monkeypatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setenv("NOTION_REPORTS_DATABASE_ID", "abc1234567890abcdef1234567890abc")
    from app.config import reload_settings

    reload_settings()
    report = _make_report(notion_page_url="https://www.notion.so/existing")
    with patch("app.services.notion_exporter.create_notion_page") as mock_create:
        url = export_digest_to_notion(report)
    assert url == "https://www.notion.so/existing"
    mock_create.assert_not_called()


@patch("app.services.notion_exporter._notion_request")
def test_create_notion_page(mock_request: MagicMock, monkeypatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "secret_test")
    monkeypatch.setenv(
        "NOTION_REPORTS_DATABASE_ID", "abc1234567890abcdef1234567890abc"
    )
    from app.config import reload_settings

    reload_settings()
    mock_request.return_value = {"url": "https://www.notion.so/new-page"}

    url = create_notion_page(_make_report())
    assert url == "https://www.notion.so/new-page"
    mock_request.assert_called_once()
    payload = mock_request.call_args.kwargs["json_body"]
    assert payload["parent"]["database_id"] == "abc12345-6789-0abc-def1-234567890abc"
    assert "Name" in payload["properties"]
    assert payload["children"]


def test_invalid_database_id_raises() -> None:
    with pytest.raises(NotionExportError):
        _normalize_database_id("not-a-valid-id")
