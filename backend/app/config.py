"""应用配置。

通过环境变量 / `.env` 注入，统一用 pydantic-settings 管理。
设计文档对应：第 5.2 节技术栈、第 9 节 LLM、第 4 节采集。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。

    所有字段均可通过同名大写环境变量覆盖，例如 `DATABASE_URL`。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 基础 ----
    app_name: str = "SignalDigest"
    environment: str = "development"  # development | production
    debug: bool = True

    # ---- 数据库（开发用 SQLite，生产换 Postgres 连接串）----
    database_url: str = "sqlite:///./signaldigest.db"

    # ---- 采集（第 4 章）----
    # App Store RSS 默认抓取的国家列表，逗号分隔。
    default_country_codes: str = "us"
    # 单次 RSS 请求超时时间（秒）。
    ingest_http_timeout: float = 15.0

    # ---- LLM（第 9 章，统一走 LiteLLM）----
    # LiteLLM 模型名，如 openai/gpt-4o-mini、deepseek/deepseek-chat、anthropic/claude-3-5-sonnet。
    llm_model: str = "openai/gpt-4o-mini"
    # 日常轻量分类用的便宜模型（第 9.4 成本控制）。
    llm_classifier_model: str = "openai/gpt-4o-mini"
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    llm_timeout: float = 120.0  # LiteLLM 请求超时（秒）

    # ---- 评论分类（第 6.4 / 9.4）----
    # 是否启用 LLM 分类；关闭时仅用基于评分的规则兜底，零成本。
    enable_llm_classification: bool = True
    # 单次喂给 LLM 的评论条数（成本与上下文长度保护）。
    classifier_batch_size: int = 20
    # 单条评论正文截断长度，避免超长评论拉高 token。
    classifier_body_max_chars: int = 600

    # ---- 邮件投递（第 5.2 / 7.3）----
    email_provider: str = "smtp"  # smtp | resend | postmark
    email_from: str = "SignalDigest <noreply@example.com>"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True  # 587 用 STARTTLS；若用 465 SSL 端口请置 false 并改端口
    resend_api_key: str | None = None

    # ---- Notion（第 8 章，可选）----
    notion_api_key: str | None = None
    notion_reports_database_id: str | None = None

    # ---- 调度（第 4.5 采集频率）----
    enable_scheduler: bool = True
    daily_ingest_hour: int = 6  # 每天采集时刻（本地时区，0-23）
    weekly_digest_weekday: int = 0  # 0=周一，每周周报生成日
    weekly_digest_hour: int = 8

    @property
    def country_code_list(self) -> list[str]:
        """把逗号分隔的国家配置解析为列表。"""
        return [c.strip().lower() for c in self.default_country_codes.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取全局单例配置。"""
    return Settings()
