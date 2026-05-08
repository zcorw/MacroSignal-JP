# 日本宏观政策效果监控器

用于监控日本积极财政、弱日元和再通胀政策是否带来真实实际增长，还是主要推高名义 GDP 与通胀。

## 当前能力

- 自动下载官方数据并保存到 `data/raw/`。
- 清洗后写入 SQLite：`data/app.db`。
- 动态计算核心指标、评分和文字判断。
- 使用 FastAPI + Jinja2 提供公开只读 Web UI。
- 使用 ECharts 从数据库动态绘图，不预生成图片。
- 使用 Docker Compose 管理 Web 服务和批处理任务。

## 快速开始

```bash
docker compose --profile batch build
docker compose run --rm app python run.py --init-db
docker compose run --rm app python run.py
docker compose up -d web
```

访问：

```text
http://127.0.0.1:18000/
```

## 常用命令

初始化数据库：

```bash
docker compose run --rm app python run.py --init-db
```

执行真实数据下载、清洗、分析和入库：

```bash
docker compose run --rm app python run.py
```

写入样例数据：

```bash
docker compose run --rm app python run.py --mode sample
```

启动 Web：

```bash
docker compose up -d web
```

查看日志：

```bash
docker compose logs -f web
tail -n 100 logs/app.log
```

## 已接入数据源

- ESRI Quarterly Estimates of GDP：自动发现并下载 GDP 时间序列 CSV。
- e-Stat National Accounts / GDP：下载官方文件，作为 GDP 官方来源留档。
- e-Stat Consumer Price Index：自动下载 CPI 最新 Excel。
- e-Stat Monthly Labour Survey：自动下载实际工资最新 Excel。
- MOF JGB historical yield：自动下载国债收益率 CSV。
- USDJPY：当前采用 `data/manual/usdjpy.csv` 手动兜底；缺失时系统会继续运行并降低相关判断权重。

USDJPY 手动文件格式：

```csv
date,value,source,note
2026-05-01,153.24,manual_boj_export,BOJ Time-Series Data Search manual export
```

## 输出

页面动态读取 SQLite，不再依赖预生成 Markdown 报告或图片。核心页面包括：

- `/` 最新判断与图表
- `/reports` 历史报告
- `/sources` 数据源状态
- `/api/latest` 最新报告 JSON
- `/api/charts/{chart_key}` ECharts 数据

## 定期任务与部署

VPS、cron、GitHub Actions、Nginx 的完整流程见：

```text
docs/deployment.md
```
