"""运行配置读写：将可管理项持久化到 backend/.env 并热重载 Settings。"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import Settings, get_settings, reload_settings

# Settings 字段 -> .env 键名
FIELD_TO_ENV: dict[str, str] = {
    "llm_model": "LLM_MODEL",
    "llm_classifier_model": "LLM_CLASSIFIER_MODEL",
    "llm_api_key": "LLM_API_KEY",
    "llm_api_base": "LLM_API_BASE",
    "llm_timeout": "LLM_TIMEOUT",
    "enable_llm_classification": "ENABLE_LLM_CLASSIFICATION",
    "classifier_batch_size": "CLASSIFIER_BATCH_SIZE",
    "classifier_body_max_chars": "CLASSIFIER_BODY_MAX_CHARS",
    "email_provider": "EMAIL_PROVIDER",
    "email_from": "EMAIL_FROM",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_user": "SMTP_USER",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_use_tls": "SMTP_USE_TLS",
    "resend_api_key": "RESEND_API_KEY",
    "digest_recipient_email": "DIGEST_RECIPIENT_EMAIL",
    "ingest_http_proxy": "INGEST_HTTP_PROXY",
    "enable_scheduler": "ENABLE_SCHEDULER",
    "daily_ingest_hour": "DAILY_INGEST_HOUR",
    "weekly_digest_weekday": "WEEKLY_DIGEST_WEEKDAY",
    "weekly_digest_hour": "WEEKLY_DIGEST_HOUR",
}

ENV_TO_FIELD = {v: k for k, v in FIELD_TO_ENV.items()}

# 密钥字段：GET 脱敏；PATCH 留空表示不修改。
SECRET_FIELDS = frozenset({"llm_api_key", "smtp_password", "resend_api_key"})

# 可清空的字符串字段：PATCH 传 null 时写入空值。
NULLABLE_STRING_FIELDS = frozenset(
    {
        "llm_api_base",
        "smtp_host",
        "smtp_user",
        "digest_recipient_email",
        "ingest_http_proxy",
    }
)

MANAGED_FIELDS = frozenset(FIELD_TO_ENV.keys())

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def env_file_path() -> Path:
    """backend/.env 路径（与 uvicorn 工作目录一致）。"""
    return Path(__file__).resolve().parents[2] / ".env"


def _serialize_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _apply_env_updates(updates: dict[str, str]) -> None:
    """按 KEY=VALUE 更新 .env；保留注释与其它未管理键。"""
    path = env_file_path()
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    out: list[str] = []

    for line in lines:
        m = _ENV_LINE.match(line.strip())
        if m and m.group(1) in remaining:
            key = m.group(1)
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)

    if remaining:
        if out and out[-1].strip():
            out.append("")
        out.append("# ===== 由管理后台更新 =====")
        for key, val in remaining.items():
            out.append(f"{key}={val}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def settings_to_public(settings: Settings | None = None) -> dict:
    """返回可安全暴露给前端的配置（密钥仅标记是否已设置）。"""
    s = settings or get_settings()
    data: dict = {"env_file": str(env_file_path())}

    for field in MANAGED_FIELDS:
        val = getattr(s, field)
        if field in SECRET_FIELDS:
            data[f"{field}_set"] = bool(val)
        else:
            data[field] = val

    return data


def update_settings(updates: dict) -> dict:
    """合并更新可管理配置，写回 .env 并热重载。"""
    current = get_settings()
    env_updates: dict[str, str] = {}

    for field, value in updates.items():
        if field not in MANAGED_FIELDS:
            continue
        if field in SECRET_FIELDS and value == "":
            continue
        if value is None:
            if field in NULLABLE_STRING_FIELDS:
                env_updates[FIELD_TO_ENV[field]] = ""
            continue

        if field in SECRET_FIELDS:
            env_updates[FIELD_TO_ENV[field]] = str(value)
        elif isinstance(value, bool):
            env_updates[FIELD_TO_ENV[field]] = _serialize_value(value)
        elif isinstance(value, (int, float)):
            env_updates[FIELD_TO_ENV[field]] = _serialize_value(value)
        else:
            env_updates[FIELD_TO_ENV[field]] = _serialize_value(value)

    if env_updates:
        _apply_env_updates(env_updates)

    reloaded = reload_settings()
    return settings_to_public(reloaded)
