import os
import re
import shutil
from selenium.webdriver.firefox.service import Service


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def get_geckodriver_service() -> Service:
    """Return a selenium Service for geckodriver.

    Looks up `GECKODRIVER_PATH` env var first, then falls back to `shutil.which("geckodriver")`.
    Raises RuntimeError if not found.
    """
    gecko_path = os.getenv("GECKODRIVER_PATH") or shutil.which("geckodriver")
    if not gecko_path:
        raise RuntimeError(
            "未找到 geckodriver。请设置环境变量 GECKODRIVER_PATH 或将 geckodriver 安装并加入 PATH。"
        )
    return Service(gecko_path)
