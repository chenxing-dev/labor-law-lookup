"""
Base Selenium 爬虫
"""

import os
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.webdriver import WebDriver

import shutil


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


def create_firefix_driver(headless: bool = True) -> WebDriver:
    """Create and return a Firefox WebDriver with the given headless setting."""
    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("-headless")
    service = get_geckodriver_service()
    driver = WebDriver(service=service, options=options)
    return driver
