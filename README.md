# 北大法宝爬虫

**目的**：构建一个爬虫，从北大法宝获取有关法律法规的数据。

**目录结构**：

- `spiders/`：包含爬虫脚本的目录
- `docs/`：文档存储目录
- `tests/`：自动化测试脚本的目录

**功能列表**：

- 模拟登录北大法宝，无需人工操作
- 爬取并解析页面内容：分类法律法规、智能整合
- 生成一个常用法律手册

**环境要求**：

- Python 3.8+
- 依赖：Scrapy、Requests、BeautifulSoup4

---
**快速开始**：

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   ```
2. 安装必要依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行爬虫：
   ```bash
   scrapy crawl example_spider
   ```