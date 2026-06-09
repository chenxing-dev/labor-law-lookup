"""
北大法宝爬虫
Author: 陈刑
Description:
    该脚本使用 Selenium 模拟浏览器行为，抓取北大法宝法律条文页面的内容，并将其结构化为 JSON 格式，同时导出纯文本版本。
    它能够提取法律条文的标题、元数据（如制定机关、发文字号、公布日期等）以及正文内容（包括编、章、节、条、款、项等层级结构）。
    爬取的数据会保存到本地的 `data` 目录下，分别以法律条文标题命名的 `.json` 文件。
Usage:
    python law_spider.py [--headless] [--force]
    python law_spider.py --url <目标页面URL> [--headless]
Example:
    python law_spider.py --headless
    python law_spider.py --url https://www.pkulaw.com/chl/6393f2e43412bddbbdfb.html --headless
"""

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from selenium import webdriver
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

try:
    from .helpers import normalize_text, get_geckodriver_service
    from .urls import PKULAW_URLS
except ImportError:
    from helpers import normalize_text, get_geckodriver_service
    from urls import PKULAW_URLS


logger = logging.getLogger('北大法宝爬虫')


def normalize_configured_urls(
        raw_urls: dict[str, str] | list[str] | tuple[str, ...] | None
) -> list[tuple[str, str]]:
    """Normalize configured URLs into a deduplicated label/url list."""
    if not raw_urls:
        return []

    pairs = raw_urls.items() if isinstance(raw_urls, dict) else ((url, url)
                                                                 for url in raw_urls)
    configured_urls = []
    seen = set()

    for raw_label, raw_url in pairs:
        label = normalize_text(str(raw_label or ""))
        url = normalize_text(str(raw_url or ""))
        if not url or url in seen:
            continue
        seen.add(url)
        configured_urls.append((label or url, url))

    return configured_urls


def load_existing_output_urls(data_dir: Path | None = None) -> set[str]:
    """Return URLs that already exist in previously exported JSON files."""
    output_dir = data_dir or Path("data")
    if not output_dir.exists():
        return set()

    existing_urls = set()
    for json_path in output_dir.glob("*.json"):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Skipping unreadable JSON file: %s", json_path)
            continue

        if not isinstance(payload, dict):
            continue

        url = normalize_text(str(payload.get("url") or ""))
        if url:
            existing_urls.add(url)

    return existing_urls


def get_pending_configured_urls(force: bool = False) -> list[tuple[str, str]]:
    """Load configured PKULaw URLs and skip laws already exported to data/."""
    configured_urls = normalize_configured_urls(PKULAW_URLS)
    if not configured_urls:
        raise ValueError("spiders/urls.py 中没有配置任何 PKULaw URL")

    if force:
        return configured_urls

    existing_urls = load_existing_output_urls()
    pending_urls = []

    for label, url in configured_urls:
        if url in existing_urls:
            print(f"跳过已抓取法规：{label}")
            continue
        pending_urls.append((label, url))

    return pending_urls


def extract_title(driver) -> str:
    """提取法律条文的标题"""
    try:
        return normalize_text(driver.find_element(
            By.ID, "ArticleTitle").get_attribute("value"))
    except NoSuchElementException:
        logger.exception(
            "Failed to extract article title: element 'ArticleTitle' not found")
        return ""


def extract_metadata(driver) -> dict:
    """提取法律条文的元数据，如制定机关、发文字号、公布日期等"""
    metadata = {}

    boxes = driver.find_elements(By.CSS_SELECTOR, ".fields .box")
    for box in boxes:
        label_elements = box.find_elements(By.CSS_SELECTOR, "strong")
        if not label_elements:
            continue

        label = normalize_text(label_elements[0].text).rstrip("：")

        row_text = normalize_text(box.text)
        value = normalize_text(row_text.replace(label + "：", "", 1))
        if not value:
            continue

        if label == "法规类别":
            metadata[label] = [part for part in value.split(" ") if part]
        else:
            metadata[label] = value

    return metadata


def extract_content(driver) -> list:
    """提取法律条文的正文内容，构建层级结构（编、章、节、条、款、项）"""
    heading_anchor_re = re.compile(r"sort\d+_(bian|zhang|jie)_(\d+)$")
    article_anchor_re = re.compile(r"tiao_(\d+)$")
    clause_anchor_re = re.compile(r"tiao_\d+_kuan_(\d+)$")
    item_anchor_re = re.compile(r"tiao_\d+_kuan_\d+_xiang_(\d+)$")

    try:
        content = driver.find_element(By.CSS_SELECTOR, "div.content")
    except NoSuchElementException:
        logger.exception(
            "Failed to extract content: element 'div.content' not found")
        return []

    content_nodes = []
    heading_stack = []

    def add_heading_to_stack(node_type: str, title: str, index: int | None, level: int):
        heading = {
            "type": node_type,
            "index": index,
            "title": title,
            "children": [],
        }

        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()

        if heading_stack:
            heading_stack[-1][1]["children"].append(heading)
        else:
            content_nodes.append(heading)

        heading_stack.append((level, heading))

    def append_article(article: dict):
        if heading_stack:
            heading_stack[-1][1]["children"].append(article)
        else:
            content_nodes.append(article)

    def parse_index(anchor_name: str | None, pattern: re.Pattern) -> int | None:
        if not anchor_name:
            return None
        match = pattern.search(anchor_name)
        if not match:
            return None
        return int(match.group(1))

    nodes = content.find_elements(By.CSS_SELECTOR, "p.navzhang, div.tiao-wrap")
    for node in nodes:
        node_class = node.get_attribute("class") or ""

        if "navzhang" in node_class:
            heading_title = normalize_text(node.text)
            if not heading_title:
                continue

            anchor_name = ""
            heading_anchor_nodes = node.find_elements(
                By.CSS_SELECTOR, "a[name]")
            if heading_anchor_nodes:
                anchor_name = normalize_text(
                    heading_anchor_nodes[0].get_attribute("name") or "")

            heading_type = "节"
            heading_level = 3
            heading_index = None

            anchor_match = heading_anchor_re.search(anchor_name)
            if anchor_match:
                type_key = anchor_match.group(1)
                heading_index = int(anchor_match.group(2))
                if type_key == "bian":
                    heading_type, heading_level = "编", 1
                elif type_key == "zhang":
                    heading_type, heading_level = "章", 2
                else:
                    heading_type, heading_level = "节", 3
            elif "编" in heading_title:
                heading_type, heading_level = "编", 1
            elif "章" in heading_title:
                heading_type, heading_level = "章", 2
            elif "节" in heading_title:
                heading_type, heading_level = "节", 3

            add_heading_to_stack(heading_type, heading_title,
                                 heading_index, heading_level)
            continue

        article_title_elements = node.find_elements(
            By.CSS_SELECTOR, "span.navtiao")
        article_title = normalize_text(
            article_title_elements[0].text if article_title_elements else "")
        if not article_title:
            continue

        article_anchor_name = ""
        if article_title_elements:
            article_anchor_nodes = article_title_elements[0].find_elements(
                By.CSS_SELECTOR, "a[name]"
            )
            if article_anchor_nodes:
                article_anchor_name = normalize_text(
                    article_anchor_nodes[0].get_attribute("name") or ""
                )

        article = {
            "type": "条",
            "index": parse_index(article_anchor_name, article_anchor_re),
            "title": article_title,
            "clauses": [],
        }

        clause_wrap_nodes = node.find_elements(
            By.XPATH,
            "./div[contains(@class, 'kuan-wrap')]",
        )

        for clause_pos, clause_wrap_node in enumerate(clause_wrap_nodes, start=1):
            clause_title_nodes = clause_wrap_node.find_elements(
                By.XPATH, "./div[contains(@class, 'kuan-content')]"
            )
            clause_text = normalize_text(
                clause_title_nodes[0].text if clause_title_nodes else "")

            if clause_text.startswith(article_title):
                clause_text = normalize_text(clause_text[len(article_title):])

            clause = {
                "type": "款",
                "index": clause_pos,
                "text": clause_text,
                "items": [],
            }

            clause_anchor_nodes = clause_wrap_node.find_elements(
                By.CSS_SELECTOR, ".kuan-content a[name]"
            )
            if clause_anchor_nodes:
                clause_anchor_name = normalize_text(
                    clause_anchor_nodes[0].get_attribute("name") or ""
                )
                clause["index"] = parse_index(
                    clause_anchor_name, clause_anchor_re) or clause_pos

            item_nodes = clause_wrap_node.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'xiang-wrap')]/div[contains(@class, 'xiang-content')]",
            )
            for item_pos, item_node in enumerate(item_nodes, start=1):
                item_text = normalize_text(item_node.text)
                if not item_text:
                    continue

                item_anchor_nodes = item_node.find_elements(
                    By.CSS_SELECTOR, "a[name]")
                item_anchor_name = normalize_text(
                    item_anchor_nodes[0].get_attribute(
                        "name") if item_anchor_nodes else ""
                )
                clause["items"].append(
                    {
                        "type": "项",
                        "index": parse_index(item_anchor_name, item_anchor_re) or item_pos,
                        "text": item_text,
                    }
                )

            if clause["text"] or clause["items"]:
                article["clauses"].append(clause)

        if not article["clauses"]:
            paragraph_nodes = node.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'kuan-wrap')]/div[contains(@class, 'kuan-content')]"
                " | .//div[contains(@class, 'xiang-wrap')]/div[contains(@class, 'xiang-content')]",
            )

            for clause_pos, paragraph_node in enumerate(paragraph_nodes, start=1):
                paragraph = normalize_text(paragraph_node.text)
                if not paragraph:
                    continue

                if paragraph.startswith(article_title):
                    paragraph = normalize_text(paragraph[len(article_title):])

                if paragraph:
                    article["clauses"].append(
                        {
                            "type": "款",
                            "index": clause_pos,
                            "text": paragraph,
                            "items": [],
                        }
                    )

        append_article(article)

    return content_nodes


def extract_data(driver) -> dict:
    """从页面中提取标题、元数据和正文内容，构建结构化数据"""
    title = extract_title(driver)
    metadata = extract_metadata(driver)
    content = extract_content(driver)
    return {"title": title, "metadata": metadata, "content": content}


def save_law_data(driver, url: str) -> str:
    """抓取当前法规页面并保存 JSON 文件。"""
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "content"))
    )

    data = extract_data(driver)
    title = data.get("title")
    if not title:
        raise RuntimeError(f"页面缺少法规标题: {url}")

    json_data = {
        "url": url,
        "title": title,
        "metadata": data.get("metadata"),
        "content": data.get("content"),
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
    }

    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    with open(temp_dir / "debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / f"{title}.json"
    json_path.write_text(
        json.dumps(json_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"成功保存结构化 JSON 到 {json_path}")
    return title


def fetch_data(
    url: str | None = None,
    urls: list[tuple[str, str]] | None = None,
    headless: bool = False,
    force: bool = False,
):
    """抓取指定 URL 或配置文件中的多个 URL，并保存为 JSON 和纯文本文件。"""
    requested_urls = None
    if not url:
        requested_urls = urls if urls is not None else get_pending_configured_urls(
            force=force)
        if not requested_urls:
            print("没有需要抓取的新法规。")
            return

    options = webdriver.FirefoxOptions()
    if headless:
        options.add_argument("-headless")
    service = get_geckodriver_service()
    driver = WebDriver(service=service, options=options)
    try:
        if url:
            save_law_data(driver, url)
            return

        failures = []
        for label, requested_url in requested_urls:
            try:
                logger.info("Scraping '%s' from URL: %s", label, requested_url)
                save_law_data(driver, requested_url)
            except Exception as exc:  # pylint: disable=broad-except
                failures.append((label, str(exc)))
                print(f"抓取失败：{label} -> {exc}")

        if failures and len(failures) == len(requested_urls):
            raise RuntimeError("所有法规抓取均失败")

        if failures:
            print("以下法规未成功抓取：")
            for failed_label, reason in failures:
                print(f"- {failed_label}: {reason}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"发生错误: {e}")
    finally:
        driver.quit()


def main() -> None:
    """爬虫主函数，解析命令行参数并执行抓取任务"""
    parser = argparse.ArgumentParser(
        prog="law_spider.py",
        description="抓取北大法宝法律条文页面并导出结构化 JSON 与纯文本",
    )
    parser.add_argument(
        "--url",
        help="要抓取的完整页面 URL；不传时默认读取 spiders/urls.py 中配置的 URL 列表",
    )
    parser.add_argument("--headless", action="store_true",
                        help="以无头模式运行浏览器（不显示界面）")
    parser.add_argument(
        "--force",
        action="store_true",
        help="忽略 data/ 中已存在的 URL 记录，强制重新抓取 spiders/urls.py 中的配置项",
    )

    args = parser.parse_args()

    fetch_data(url=args.url, headless=args.headless, force=args.force)


if __name__ == "__main__":
    main()
