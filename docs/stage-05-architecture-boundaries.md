# Stage 5. 架构与模块边界

## 已确认事实

- 项目部署在 VPS。
- 需要定时自动下载、清洗、分析和生成报告。
- 需要轻量 Web UI 快速查看报告和图表。
- Web UI 公开只读，不需要账号管理。
- 需要将清洗后的结构化数据保存到数据库。
- Web UI 直接从数据库动态生成页面。
- Markdown 报告可以作为可选导出或归档，而不是 Web UI 的主要数据来源。
- 用户偏经济小白，因此报告与 UI 要结论清晰、解释充分。

## 已确认技术栈

- 语言：Python 3.11+。
- 数据处理：pandas。
- HTTP 下载：requests。
- HTML 解析：beautifulsoup4。
- Excel 读取：openpyxl。
- 配置：pyyaml。
- 图表：ECharts 浏览器端动态绘制。
- Web 后端：FastAPI。
- 模板渲染：Jinja2。
- 数据库：SQLite。
- 数据库访问：SQLAlchemy Core。
- Web 服务：uvicorn。
- 定时执行：VPS cron。
- 常驻服务：Docker Compose 管理 uvicorn 进程。

## 总体架构

项目分为两条路径：

1. 数据管道路径：
   - cron 调用 `python run.py`。
   - 下载官方数据。
   - 清洗并保存标准化数据。
   - 计算指标和评分。
   - 将清洗后的时序数据、指标、评分、报告段落、运行状态写入 SQLite。
   - 可选导出 Markdown 报告用于归档。

2. Web 展示路径：
   - uvicorn 常驻运行 FastAPI。
   - FastAPI 从 SQLite 读取清洗后数据、指标、评分、报告段落、数据源状态。
   - FastAPI 提供图表所需的结构化数据。
   - 使用 Jinja2 动态渲染公开只读页面，浏览器用 ECharts 绘制图表。

## 推荐目录结构

```text
japan_macro_monitor/
  README.md
  requirements.txt
  config.yaml
  run.py
  data/
    raw/
    manual/
    processed/
    app.db
  logs/
  outputs/
    charts/
    reports/
  src/
    __init__.py
    config.py
    fetch_data.py
    clean_data.py
    indicators.py
    analyze.py
    report.py
    storage.py
    pipeline.py
    logging_setup.py
    web/
      __init__.py
      app.py
      routes.py
      templates/
      static/
  docs/
  notebooks/
```

## 模块边界

### `src.config`

- 读取 `config.yaml`。
- 提供路径、数据源 URL、阈值、调度策略和报告配置。
- 不执行下载和业务计算。

### `src.fetch_data`

- 下载官方数据。
- 保存原始文件到 `data/raw/`。
- 对每个数据源输出下载结果、文件路径、状态、错误摘要。
- 不做复杂清洗和业务判断。

### `src.clean_data`

- 读取原始文件和手动文件。
- 标准化字段名、日期、单位、频率。
- 保存到 `data/processed/`。
- 不计算评分。

### `src.indicators`

- 计算 YoY、3 个月变化、差值等派生指标。
- 输出统一指标表。
- 不生成文字结论。

### `src.analyze`

- 根据指标计算三类评分：
  - `real_growth_score`
  - `inflation_pressure_score`
  - `fiscal_stress_score`
- 生成结论标签、关键证据和置信度。
- 不负责 Markdown 排版和图表绘制。

### `src.report`

- 生成结构化报告内容。
- 组织总结、核心仪表盘、GDP、工资消费、投资、通胀、市场压力和结论。
- 输出报告段落、摘要、证据和风险提示。
- 可选导出 Markdown 文件用于归档。

### `src.storage`

- 管理 SQLite schema。
- 保存清洗后的时序数据、指标快照、评分、报告段落、运行记录、数据源状态和图表配置。
- 提供 Web UI 查询所需的只读函数。

### `src.pipeline`

- 串联完整流程。
- 控制是否有新数据、是否生成报告、失败时如何降级。
- 写入运行日志和数据库运行记录。

### `src.web`

- FastAPI 应用。
- Jinja2 模板渲染。
- 公开只读页面：
  - `/`
  - `/reports`
  - `/reports/{report_id}`
  - `/sources`
- 不执行数据下载或分析。

## 数据库表初稿

### `runs`

- `id`
- `started_at`
- `finished_at`
- `status`
- `trigger`
- `message`

### `source_status`

- `id`
- `run_id`
- `source_name`
- `status`
- `latest_data_date`
- `downloaded_at`
- `raw_path`
- `message`

### `series_observations`

- `id`
- `series_key`
- `date`
- `period`
- `frequency`
- `value`
- `unit`
- `source_name`
- `source_file`
- `created_at`

### `metric_snapshots`

- `id`
- `snapshot_date`
- `metric_key`
- `latest_value`
- `previous_value`
- `yoy`
- `change_3m`
- `judgement`
- `source_coverage`

### `analysis_reports`

- `id`
- `report_date`
- `title`
- `summary_label`
- `summary_text`
- `created_at`
- `data_coverage`
- `has_missing_data`
- `exported_markdown_path`

### `report_sections`

- `id`
- `report_id`
- `section_key`
- `title`
- `body`
- `sort_order`

### `report_evidence`

- `id`
- `report_id`
- `category`
- `text`
- `metric_key`
- `severity`

### `scores`

- `id`
- `report_id`
- `real_growth_score`
- `inflation_pressure_score`
- `fiscal_stress_score`
- `confidence_level`

### `chart_series`

- `id`
- `chart_key`
- `series_key`
- `display_name`
- `unit`
- `axis`
- `sort_order`

## 运行与部署边界

- `python run.py`：批处理入口，适合 cron。
- `uvicorn src.web.app:app --host 0.0.0.0 --port 8000`：Web UI 服务。
- cron 只负责数据管道，不直接重启 Web 服务。
- Docker Compose 负责 Web 服务常驻和重启。
- 日志写入 `logs/`，公开 UI 只展示摘要。

## 安全与公开访问约束

- 不做账号管理。
- 不提供写操作接口。
- 不在 UI 暴露服务器绝对路径、环境变量、密钥和异常堆栈。
- 数据源错误在 UI 中显示为摘要，详细错误只写日志。
- 若未来需要公开互联网访问，建议通过 Nginx 反向代理并启用 HTTPS。

## 需要进入项目约定的规则

- Web 层不得调用下载、清洗、分析函数。
- 数据管道可以写数据库，Web UI 只读数据库。
- 清洗后的结构化数据必须入库，Web UI 不以 Markdown 文件或预生成图片作为主要数据来源。
- 图表由 Web UI 使用 ECharts 基于数据库数据动态绘制。
- 所有路径从配置读取，不在模块中硬编码绝对路径。
- 数据源更新检测应使用数据日期、文件元信息或内容哈希。
- 报告生成失败不能覆盖上一次成功报告。
