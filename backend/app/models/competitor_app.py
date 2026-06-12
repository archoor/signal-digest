"""CompetitorApp 模型（设计文档第 6.2）。

挂在某个 MonitoredApp 下的 1-3 个竞品。
"""

from __future__ import annotations

from sqlmodel import Field

from app.models.base import TimestampMixin


class CompetitorApp(TimestampMixin, table=True):
    __tablename__ = "competitor_app"

    id: int | None = Field(default=None, primary_key=True)
    monitored_app_id: int = Field(foreign_key="monitored_app.id", index=True)
    name: str

    app_store_id: str | None = Field(default=None, index=True)
    google_play_package: str | None = Field(default=None, index=True)
    app_store_url: str | None = None
    google_play_url: str | None = None
