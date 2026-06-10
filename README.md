# labor-law-lookup | 劳动法查询网页应用

`labor-law-lookup` 是一个面向劳动法律查询与检索的网页应用项目。

- 网页应用部分：Vite+
- 爬虫部分基于 Python + Selenium，用于抓取法律条文并导出结构化数据

**项目组成**：

- Vite+ 网页应用：提供用户界面，允许用户输入查询条件并展示查询结果
- Python 爬虫：负责抓取、解析并输出法律条文数据

**当前目录结构**：

- `spider/`：Python + Selenium 爬虫脚本与辅助函数