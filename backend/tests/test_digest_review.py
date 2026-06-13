"""周报审核状态流转测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_digest_status_transition_rejects_sent_via_patch() -> None:
    client = TestClient(create_app())
    digests = client.get("/api/digests").json()
    if not digests:
        return
    digest_id = digests[0]["id"]
    resp = client.patch(
        f"/api/digests/{digest_id}",
        json={"status": "sent"},
    )
    assert resp.status_code == 400


def test_list_digests_filter_by_status() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/digests", params={"status": "draft"})
    assert resp.status_code == 200
    for item in resp.json():
        assert item["status"] == "draft"
