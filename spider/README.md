# labor-law-spider | 北大法宝爬虫

爬虫部分基于 Python + Selenium，用于抓取法律条文并导出结构化数据

**当前已包含的爬虫能力**：

- 抓取北大法宝法规页面内容
- 提取标题、元数据与分层法条结构
- 导出 `.json` 文件
- 保存调试用 HTML 页面源码，便于排查解析问题

**环境要求**：

- Python 3.8+
- Firefox 与 !!! **`geckodriver`** !!!
- 依赖见 `requirements.txt`

---

**快速开始**：

1. 激活虚拟环境：
   ```bash
   cd spider
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate  # Windows
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 在 `config/law_list.json` 中维护要抓取的北大法宝 URL 列表：
   ```json
   {
       "中华人民共和国劳动法(2018修正)": "https://www.pkulaw.com/chl/6393f2e43412bddbbdfb.html",
       "中华人民共和国劳动合同法(2012修正)": "https://www.pkulaw.com/chl/7ab5e7d605f859e6bdfb.html",
   }
   ```

4. 运行批量抓取：
   ```bash
   python main.py --headless
   ```

   脚本会在 Selenium 浏览器会话中依次抓取 `config/law_list.json` 里配置的 URL，并根据 `output/*.json` 中已保存的 `url` 字段自动跳过已抓取的法规。

注意：关于 `geckodriver` 路径，脚本会优先使用环境变量 `GECKODRIVER_PATH`，如果未设置则尝试在 `PATH` 中查找 `geckodriver`。

如果需要直接抓取单个 URL，也可以使用：

```bash
python spiders/law_spider.py --url https://www.pkulaw.com/chl/6393f2e43412bddbbdfb.html --headless
```

如果需要强制重新抓取 `config/law_list.json` 中的全部配置项，可以使用：

```bash
python main.py --headless --force
```

运行完成后，输出文件会写入 `data/`