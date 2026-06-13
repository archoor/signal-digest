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

    # ---- 前端跨域（第 5.1 前端对接）----
    # 允许访问 API 的前端来源，逗号分隔；默认放行本地 Next.js dev server。
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- 采集（第 4 章）----
    # App Store RSS 默认抓取的国家列表，逗号分隔。
    default_country_codes: str = "us"
    # 单次 RSS 请求超时时间（秒）。
    ingest_http_timeout: float = 15.0
    # 外网 SOCKS5/HTTP 代理（采集与 App 搜索等共用；设置页可配置）。
    # 留空则直连。支持认证：socks5://user:pass@127.0.0.1:12080
    ingest_http_proxy: str | None = None
    # Google Play 抓取超时（秒），避免网络不通时长时间阻塞。
    ingest_google_play_timeout: float = 30.0

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
    # LLM 深度分析最低有效字数（过短评论仅规则分类，不调用 LLM）。
    classifier_min_body_chars: int = 20

    # ---- 邮件投递（第 5.2 / 7.3）----
    email_provider: str = "smtp"  # smtp | resend | postmark
    email_from: str = "SignalDigest <noreply@example.com>"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True  # 587 用 STARTTLS；若用 465 SSL 端口请置 false 并改端口
    resend_api_key: str | None = None
    # 周报接收邮箱（全局统一，在管理后台设置页配置）。
    digest_recipient_email: str | None = None

    # ---- Notion（第 8 章，可选）----
    notion_api_key: str | None = None
    notion_reports_database_id: str | None = None
    # 数据库 Title 列名，默认 Notion 新建库为 "Name"
    notion_title_property: str = "Name"
    # 可选列名：Status(select)、Period(date)、Report ID(number)；留空则不写入
    notion_status_property: str | None = None
    notion_period_property: str | None = None
    notion_report_id_property: str | None = None
    # 生成周报后自动导出到 Notion
    notion_auto_export: bool = False

    # ---- 调度（第 4.5 采集频率）----
    enable_scheduler: bool = True
    daily_ingest_hour: int = 6  # 每天采集时刻（本地时区，0-23）
    weekly_digest_weekday: int = 0  # 0=周一，每周周报生成日
    weekly_digest_hour: int = 8

    @property
    def country_code_list(self) -> list[str]:
        """把逗号分隔的国家配置解析为列表。"""
        return [c.strip().lower() for c in self.default_country_codes.split(",") if c.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的前端来源解析为列表。"""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取全局单例配置。"""
    return Settings()


def reload_settings() -> Settings:
    """清除缓存并重新加载配置（.env 更新后调用）。"""
    get_settings.cache_clear()
    return get_settings()
