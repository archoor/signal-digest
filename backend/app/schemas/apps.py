"""Apps / Competitors 的请求与响应模型（设计文档第 10.1 / 10.2）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MonitorStatus


class CompetitorCreate(BaseModel):
    name: str
    app_store_url: str | None = None
    google_play_url: str | None = None


class CompetitorRead(BaseModel):
    id: int
    monitored_app_id: int
    name: str
    app_store_id: str | None
    google_play_package: str | None
    app_store_url: str | None
    google_play_url: str | None


class MonitoredAppCreate(BaseModel):
    name: str
    owner_email: str | None = None
    app_store_url: str | None = None
    google_play_url: str | None = None
    country_codes: list[str] = Field(default_factory=lambda: ["us"])


class MonitoredAppUpdate(BaseModel):
    name: str | None = None
    owner_email: str | None = None
    country_codes: list[str] | None = None
    status: MonitorStatus | None = None
    last_release_date: datetime | None = None


class MonitoredAppRead(BaseModel):
    id: int
    name: str
    owner_email: str | None
    app_store_id: str | None
    google_play_package: str | None
    app_store_url: str | None
    google_play_url: str | None
    country_codes: list[str]
    status: MonitorStatus
    last_ingested_at: datetime | None
    last_release_date: datetime | None
