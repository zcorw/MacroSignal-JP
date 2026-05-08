# 架构记录

## 当前状态

Stage 0 初步确认本项目采用 Python 数据管道架构。Stage 1 已确认系统部署在 VPS，通过定期命令自动运行。Stage 4 后更新范围：需要增加轻量 Web UI，并将清洗后的结构化数据保存到数据库，页面从数据库动态生成。

## 初步模块

- `src.config`：读取配置。
- `src.fetch_data`：下载官方数据或校验手动导入文件。
- `src.clean_data`：清洗、标准化和保存处理后数据。
- `src.indicators`：计算 YoY、3 个月变化、评分等派生指标。
- `src.analyze`：执行政策效果判断框架。
- `src.report`：生成结构化报告内容，并可选导出 Markdown。
- `src.storage`：保存清洗后的时序数据、指标快照、评分、报告段落、运行记录和图表配置。
- `src.pipeline`：串联定时批处理流程。
- `src.web` 或 `web/`：轻量 Web UI，展示最新报告、历史报告和图表。
- `run.py`：统一运行入口。

## 已确认技术栈

- FastAPI + Jinja2 提供公开只读 Web UI。
- SQLite + SQLAlchemy Core 保存清洗后数据、指标快照、评分、报告段落和运行记录。
- cron 调用 `python run.py` 执行数据管道。
- Docker Compose 管理 Web 服务和批处理容器。
- 宿主机 cron 调用 Docker Compose 执行批处理。

## 依赖策略

- 首版只使用 Python 生态和官方免费数据源。
- 不引入前端构建链、任务队列和独立数据库服务。
- 图表不预生成图片，Web 请求阶段读取数据库，浏览器用 ECharts 动态绘制。

## API 策略

- Jinja2 页面负责主要 HTML。
- 只读 JSON API 负责给 ECharts 和页面局部数据提供结构化数据。
- Web API 不提供写操作。

## 初步运行模式

- VPS 上安装 Python 3.11+ 和依赖。
- 使用 `python run.py` 串联下载、清洗、分析、画图和报告生成。
- 使用 cron 或等价调度器定期执行。
- 运行日志写入本地日志目录，报告按日期归档到 `outputs/reports/`。
- 数据库保存清洗后的结构化数据和报告内容，Web UI 直接从数据库动态生成页面。

## 调度策略

- 每天上午执行一次常规检查。
- 发布日若关键数据未成功下载，晚间执行补跑。
- 通过数据日期或文件哈希判断是否出现新数据，避免重复生成相同报告。
