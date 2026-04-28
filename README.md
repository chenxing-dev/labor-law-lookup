# labor-law-lookup

`labor-law-lookup` 是一个面向劳动法律查询与检索的桌面应用项目。

- 桌面应用部分基于 Tauri，用于劳动法查询、检索与信息展示
- 爬虫部分基于 Python + Selenium，用于抓取法律条文并导出结构化数据

**项目组成**：

- Tauri 桌面应用：承载劳动法查询与展示功能
- Python 爬虫：负责抓取、解析并输出法律条文数据

**当前目录结构**：

- `spiders/`：Python + Selenium 爬虫脚本与辅助函数
- `data/`：抓取后生成的本地数据文件
- `requirements.txt`：Python 依赖列表

**爬虫模块**：

- `spiders/pkulaw_spider.py`：抓取北大法宝法规页面并生成输出文件
- `spiders/helpers.py`：爬虫使用的文本清洗辅助函数

**当前已包含的爬虫能力**：

- 抓取北大法宝法规页面内容
- 提取标题、元数据与分层法条结构
- 导出 `.json` 和 `.txt` 两种结果文件
- 保存调试用 HTML 页面源码，便于排查解析问题

**环境要求**：

- Python 3.8+
- Firefox 与 `geckodriver`
- 依赖见 `requirements.txt`

---

**快速开始**：

1. 克隆仓库：
   ```bash
   git clone https://github.com/chenxing-dev/labor-law-lookup.git
   cd labor-law-lookup
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 激活虚拟环境（可选）：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate  # Windows
   ```
4. 运行爬虫：
   ```bash
   python spiders/law_spider.py
   ```

运行完成后，输出文件会写入 `data/`，调试页面源码会写入 `temp/debug.html`。