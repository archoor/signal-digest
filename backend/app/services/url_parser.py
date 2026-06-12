"""App URL 解析（设计文档第 7.1 onboarding）。

从用户粘贴的 App Store / Google Play 链接中解析出 app_store_id / google_play_package。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# App Store: https://apps.apple.com/us/app/xxx/id123456789
_APP_STORE_ID = re.compile(r"/id(\d+)")
# Google Play: https://play.google.com/store/apps/details?id=com.foo.bar
_GOOGLE_PLAY_PKG = re.compile(r"[?&]id=([a-zA-Z0-9_.]+)")


@dataclass(slots=True)
class ParsedAppUrl:
    app_store_id: str | None = None
    google_play_package: str | None = None


def parse_app_url(url: str) -> ParsedAppUrl:
    """解析单个 App 链接。

    返回的字段二者通常只有一个有值；无法识别时返回空对象。
    """
    result = ParsedAppUrl()
    if not url:
        return result

    if "apps.apple.com" in url or "itunes.apple.com" in url:
        m = _APP_STORE_ID.search(url)
        if m:
            result.app_store_id = m.group(1)
    elif "play.google.com" in url:
        m = _GOOGLE_PLAY_PKG.search(url)
        if m:
            result.google_play_package = m.group(1)
    return result
