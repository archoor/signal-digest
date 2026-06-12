"""MonitoredApp 模型（设计文档第 6.1）。

用户自己的、需要监控的 App。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampMixin
from app.models.enums import MonitorStatus


class MonitoredApp(TimestampMixin, table=True):
    __tablename__ = "monitored_app"

    id: int | None = Field(default=None, primary_key=True)
    owner_email: str | None = Field(default=None, index=True)
    name: str

    app_store_id: str | None = Field(default=None, index=True)
    google_play_package: str | None = Field(default=None, index=True)
    app_store_url: str | None = None
    google_play_url: str | None = None

    # 抓取的国家列表，例如 ["us", "gb"]。
    country_codes: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    status: MonitorStatus = Field(default=MonitorStatus.ACTIVE, index=True)
    last_ingested_at: datetime | None = None

    # 发版窗口（第 4.5 / 7.4）：手动录入的最近发版日期。
    last_release_date: datetime | None = None
