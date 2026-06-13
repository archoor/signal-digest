"""评论入库测试。"""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.review_normalizer import json_safe_payload


def test_json_safe_payload_datetime() -> None:
    dt = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
    out = json_safe_payload({"at": dt, "nested": [{"t": dt}]})
    assert out == {
        "at": "2026-06-13T12:00:00+00:00",
        "nested": [{"t": "2026-06-13T12:00:00+00:00"}],
    }
