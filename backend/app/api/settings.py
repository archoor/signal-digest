"""Settings 路由：读取 / 更新 LLM、邮件、调度等运行配置。"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.settings import (
    ProxyTestRequest,
    ProxyTestResponse,
    SettingsRead,
    SettingsUpdate,
)
from app.services.external_http import test_proxy_connectivity
from app.services.settings_store import settings_to_public, update_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
def get_runtime_settings() -> SettingsRead:
    return SettingsRead(**settings_to_public())


@router.patch("", response_model=SettingsRead)
def patch_runtime_settings(payload: SettingsUpdate) -> SettingsRead:
    data = update_settings(payload.model_dump(exclude_unset=True))

    # 调度参数变更后尝试热重载 cron（无需重启进程）。
    try:
        from app.scheduler.jobs import reload_scheduler_jobs

        reload_scheduler_jobs()
    except Exception:
        pass

    return SettingsRead(**data)


@router.post("/proxy-test", response_model=ProxyTestResponse)
def test_runtime_proxy(payload: ProxyTestRequest) -> ProxyTestResponse:
    """测试外网代理（或直连）能否访问 iTunes / Google Play。"""
    result = test_proxy_connectivity(payload.ingest_http_proxy)
    return ProxyTestResponse(
        ok=result.ok,
        mode=result.mode,
        proxy=result.proxy,
        message=result.message,
        checks=[
            {
                "name": c.name,
                "ok": c.ok,
                "latency_ms": c.latency_ms,
                "status_code": c.status_code,
                "error": c.error,
            }
            for c in result.checks
        ],
    )
