# Stage 6. 外部依赖与成本控制

## 已确认事实

- 项目部署在 VPS。
- 数据源优先使用官方免费来源。
- 不需要账号管理。
- Web UI 公开只读。
- 清洗后的结构化数据需要保存到 SQLite。
- 页面直接从数据库动态生成，Markdown 仅作为可选导出或归档。

## 已确认决策

- 首版不使用付费 API。
- 首版不使用复杂消息队列、任务队列或前端构建链。
- 首版数据库使用 SQLite，降低部署和维护成本。
- 定时任务使用 VPS cron，不引入 Celery、Redis 或 APScheduler 常驻调度。
- Web 服务使用 FastAPI + Jinja2 + uvicorn。
- 如需公网部署，建议通过 Nginx 反向代理和 HTTPS，但应用本身不内置账号体系。

## Python 依赖

### 必需依赖

- `pandas`：表格与时间序列处理。
- `requests`：下载官方页面和文件。
- `beautifulsoup4`：解析 HTML 页面中的下载链接。
- `openpyxl`：读取 `.xlsx` 文件。
- `pyyaml`：读取 `config.yaml`。
- `fastapi`：Web UI 后端。
- `uvicorn`：ASGI 服务。
- `jinja2`：服务端 HTML 模板。
- `sqlalchemy`：SQLite schema 和查询。

### 建议依赖

- `python-dotenv`：VPS 环境变量和本地配置辅助。
- `lxml`：加速 HTML/XML 解析；如果安装困难可不用。

### 暂不引入

- `React` / `Next.js` / `Vue`：首版不需要复杂前端构建。
- `PostgreSQL`：SQLite 足够支撑单机只读展示。
- `Redis` / `Celery`：cron 足够支撑定时批处理。
- `Playwright` / Selenium：首版避免浏览器自动化，除非官方数据源无法通过 HTTP 下载。
- 付费市场数据 API：与“优先官方数据源、低成本”目标不一致。

## 数据源成本策略

- GDP：ESRI 和 e-Stat 官方免费数据。
- CPI：e-Stat 和总务省统计局官方免费数据。
- 工资：e-Stat Monthly Labour Survey 官方免费数据。
- JGB：财务省官方免费 CSV。
- BOJ：官方页面和可下载 flat files。
- USDJPY：优先 BOJ 官方路径；若长期序列接口短期无法稳定自动化，首版使用 `data/manual/usdjpy.csv` 兜底，并在页面中标注来源和更新时间。

## VPS 成本策略

- 适合低配 VPS。
- 批处理按日运行，不常驻消耗大量 CPU。
- Web UI 使用服务端渲染，页面轻量。
- 图表不预生成 PNG，Web UI 从数据库读取结构化数据后用 ECharts 动态绘制。
- SQLite 文件本地保存，减少数据库服务维护成本。

## 网络与失败控制

- 下载请求应设置 timeout。
- 每个数据源独立失败，不应导致全部流程崩溃。
- 数据源失败时写入 `source_status`，页面展示可读摘要。
- 关键数据发布日允许晚间补跑。
- 不覆盖上一次成功报告。

## 可配置项

建议放入 `config.yaml`：

- 数据目录、输出目录、日志目录、数据库路径。
- 各数据源 URL 和启用状态。
- 下载 timeout、重试次数、User-Agent。
- 指标阈值和评分权重。
- 是否导出 Markdown。
- 图表展示配置，例如图表标题、指标序列、坐标轴和默认时间范围。
- Web UI 标题、公开说明文本。

## 需要进入工程约定的规则

- 除官方数据下载外，不依赖外部网络服务生成报告。
- 所有外部 URL 必须集中配置或集中定义，避免散落在业务代码中。
- 网络失败必须被记录为结构化状态。
- 不引入新依赖，除非能明确降低复杂度或风险。
- 手动数据兜底必须在 UI 和报告中标注。
