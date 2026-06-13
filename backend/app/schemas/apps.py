"""Apps / Competitors 的请求与响应模型（设计文档第 10.1 / 10.2）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import MonitorStatus


class AppSearchResultRead(BaseModel):
    name: str
    developer: str | None = None
    icon_url: str | None = None
    app_store_id: str | None = None
    app_store_url: str | None = None
    google_play_package: str | None = None
    google_play_url: str | None = None
    platforms: list[str] = Field(default_factory=list)


class CompetitorCreate(BaseModel):
    name: str
    app_store_id: str | None = None
    google_play_package: str | None = None
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
    app_store_id: str | None = None
    google_play_package: str | None = None
    app_store_url: str | None = None
    google_play_url: str | None = None
    country_codes: list[str] = Field(default_factory=lambda: ["us"])

    @model_validator(mode="after")
    def require_platform_id(self) -> MonitoredAppCreate:
        if not self.app_store_id and not self.google_play_package:
            if not self.app_store_url and not self.google_play_url:
                raise ValueError("至少配置 App Store 或 Google Play 其中一个平台")
        return self


class MonitoredAppUpdate(BaseModel):
    name: str | None = None
    app_store_id: str | None = None
    google_play_package: str | None = None
    app_store_url: str | None = None
    google_play_url: str | None = None
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
