"""Settings API 的请求与响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsRead(BaseModel):
    """可管理运行配置（密钥字段仅返回是否已设置）。"""

    env_file: str

    # LLM
    llm_model: str
    llm_classifier_model: str
    llm_api_base: str | None
    llm_timeout: float
    llm_api_key_set: bool
    enable_llm_classification: bool
    classifier_batch_size: int
    classifier_body_max_chars: int

    # 邮件
    email_provider: str
    email_from: str
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password_set: bool
    smtp_use_tls: bool
    resend_api_key_set: bool
    digest_recipient_email: str | None

    # 采集
    default_country_codes: str
    ingest_http_timeout: float
    ingest_google_play_timeout: float
    ingest_http_proxy: str | None

    # 调度
    enable_scheduler: bool
    daily_ingest_hour: int
    weekly_digest_weekday: int
    weekly_digest_hour: int

    # Notion（周报导出，功能对接后生效）
    notion_api_key_set: bool
    notion_reports_database_id: str | None
    notion_title_property: str
    notion_status_property: str | None
    notion_period_property: str | None
    notion_report_id_property: str | None
    notion_auto_export: bool


class SettingsUpdate(BaseModel):
    """PATCH 可管理配置；密钥留空表示不修改。"""

    llm_model: str | None = None
    llm_classifier_model: str | None = None
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    llm_timeout: float | None = None
    enable_llm_classification: bool | None = None
    classifier_batch_size: int | None = Field(default=None, ge=1, le=100)
    classifier_body_max_chars: int | None = Field(default=None, ge=100, le=5000)

    email_provider: str | None = None
    email_from: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool | None = None
    resend_api_key: str | None = None
    digest_recipient_email: str | None = None
    default_country_codes: str | None = None
    ingest_http_timeout: float | None = Field(default=None, ge=1, le=300)
    ingest_google_play_timeout: float | None = Field(default=None, ge=1, le=600)
    ingest_http_proxy: str | None = None

    enable_scheduler: bool | None = None
    daily_ingest_hour: int | None = Field(default=None, ge=0, le=23)
    weekly_digest_weekday: int | None = Field(default=None, ge=0, le=6)
    weekly_digest_hour: int | None = Field(default=None, ge=0, le=23)

    notion_api_key: str | None = None
    notion_reports_database_id: str | None = None
    notion_title_property: str | None = None
    notion_status_property: str | None = None
    notion_period_property: str | None = None
    notion_report_id_property: str | None = None
    notion_auto_export: bool | None = None


class ProxyTestRequest(BaseModel):
    """代理连通性测试；传入表单中的代理地址（无需先保存）。"""

    ingest_http_proxy: str | None = None


class ProxyCheckRead(BaseModel):
    name: str
    ok: bool
    latency_ms: int | None = None
    status_code: int | None = None
    error: str | None = None


class ProxyTestResponse(BaseModel):
    ok: bool
    mode: str  # proxy | direct
    proxy: str | None = None
    message: str
    checks: list[ProxyCheckRead]
