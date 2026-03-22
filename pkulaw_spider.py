from datetime import datetime
import json
from pathlib import Path
import re
import logging
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from helpers import normalize_text


logger = logging.getLogger('北大法宝爬虫')


def extract_title(driver) -> str:
    try:
        return normalize_text(driver.find_element(
            By.ID, "ArticleTitle").get_attribute("value"))
    except NoSuchElementException:
        logger.exception(
            "Failed to extract article title: element 'ArticleTitle' not found")
        return ""


def extract_metadata(driver) -> dict:
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
    title = extract_title(driver)
    metadata = extract_metadata(driver)
    content = extract_content(driver)
    return {"title": title, "metadata": metadata, "content": content}


def render_text_from_json(data: dict) -> str:
    parts = []

    title = data.get("title")
    if title:
        parts.append(title)
        parts.append("")

    metadata = data.get("metadata") or {}
    for key in ["制定机关", "发文字号", "公布日期", "施行日期", "时效性", "效力位阶", "法规类别"]:
        raw_value = metadata.get(key)
        if isinstance(raw_value, list):
            value = " ".join(item for item in raw_value if item).strip()
        else:
            value = (raw_value or "").strip()
        if value:
            parts.append(f"{key}：{value}")

    if metadata:
        parts.append("")

    def append_node_text(node: dict):
        node_type = (node.get("type") or "").strip()

        if node_type in {"编", "章", "节"}:
            title_text = (node.get("title") or "").strip()
            if title_text:
                parts.append(title_text)
                parts.append("")

            for child in node.get("children", []):
                append_node_text(child)
            return

        if node_type == "条":
            article_title = (node.get("title") or "").strip()
            if article_title:
                parts.append(article_title)

            for clause in node.get("clauses", []):
                clause_text = (clause.get("text") or "").strip()
                if clause_text:
                    parts.append(clause_text)

                for item in clause.get("items", []):
                    item_text = (item.get("text") or "").strip()
                    if item_text:
                        parts.append(item_text)

            parts.append("")
            return

        # Backward-compatible fallback for unknown object shapes.
        title_text = (node.get("title") or node.get("chapter_title")
                      or node.get("article_title") or "").strip()
        if title_text:
            parts.append(title_text)

        for paragraph in node.get("paragraphs", []):
            p = (paragraph or "").strip()
            if p:
                parts.append(p)

        for child in node.get("children", []):
            append_node_text(child)

        if title_text:
            parts.append("")

    for node in data.get("content") or data.get("chapters", []):
        append_node_text(node)

    text = "\n".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + "\n"


def fetch_data(url: str):
    # 初始化 Firefox WebDriver
    service = Service("/usr/sbin/geckodriver")  # geckodriver 的路径
    driver = webdriver.Firefox(service=service)
    try:
        driver.get(url)
        # 等待页面加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "content"))
        )

        # 按章节/条款/段落抓取结构化数据
        data = extract_data(driver)
        title = data.get("title")

        json_data = {
            "url": url,
            "title": title,
            "metadata": data.get("metadata"),
            "content": data.get("content"),
            "extracted_at": datetime.now().isoformat(timespec="seconds"),
        }

        content = render_text_from_json(json_data)

        # 调试：将页面源代码保存到本地文件，方便查看和调试
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        with open(temp_dir / "debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # 保存到本地文件
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        txt_path = output_dir / f"{title}.txt"
        txt_path.write_text(content, encoding="utf-8")

        json_path = output_dir / f"{title}.json"
        json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"成功保存法条内容到 {txt_path}")
        print(f"成功保存结构化 JSON 到 {json_path}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        driver.quit()


# 运行爬虫
if __name__ == "__main__":
    fetch_data(url="https://www.pkulaw.com/chl/6393f2e43412bddbbdfb.html")
