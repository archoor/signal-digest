"""仅重新生成周报（使用库中已有评论），写入 tmp/。

用法（backend 目录）：
    $env:PYTHONPATH='.'; uv run python scripts/regenerate_digest.py
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.db import engine
from app.models.monitored_app import MonitoredApp
from app.services.change_detector import build_change_context
from app.services.digest_generator import generate_digest

# 复用 run_e2e_demo 的 Markdown 格式化
_demo_path = Path(__file__).resolve().parent / "run_e2e_demo.py"
_spec = importlib.util.spec_from_file_location("run_e2e_demo", _demo_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["run_e2e_demo"] = _mod
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
report_to_markdown = _mod.report_to_markdown


def main() -> Path:
    with Session(engine) as session:
        app = session.exec(
            select(MonitoredApp).where(MonitoredApp.name == "Telegram")
        ).first()
        if not app or app.id is None:
            raise SystemExit("未找到 Telegram 监控 App，请先运行 scripts/run_e2e_demo.py")

        ctx = build_change_context(session, app.id)
        report = generate_digest(session, ctx)
        print(f"周报: id={report.id} title={report.title!r} tokens={report.tokens_used}")

    out_dir = Path(__file__).resolve().parent.parent / "tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"digest-report-{ts}.md"
    out_path.write_text(report_to_markdown(report), encoding="utf-8")
    print(f"周报已写入: {out_path}")
    return out_path


if __name__ == "__main__":
    main()
