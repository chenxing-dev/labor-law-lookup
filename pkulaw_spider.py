from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
        # 提取法律文书的内容
        content = driver.find_element(By.CLASS_NAME, "content").text
        title = WebDriverWait(driver, 10).until(
            lambda d: d.find_element(
                By.ID, "ArticleTitle").get_attribute("value").strip()
        )

        # 调试：将页面源代码保存到本地文件，方便查看和调试
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        with open(temp_dir / "debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # 保存到本地文件
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{title}.txt"
        output_path.write_text(content, encoding='utf-8')
        print(f"成功保存法条内容到 {output_path}")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        driver.quit()


# 运行爬虫
if __name__ == "__main__":
    fetch_data(url="https://www.pkulaw.com/chl/6393f2e43412bddbbdfb.html")
