# 日本宏观政策效果监控器

用于监控日本积极财政、弱日元和再通胀政策是否带来真实实际增长，还是主要推高名义 GDP 与通胀。

## 功能

- 自动下载和清洗官方宏观数据。
- 将清洗后的结构化数据保存到 SQLite。
- 计算真实增长、通胀压力、财政压力等指标。
- 使用 FastAPI + Jinja2 提供公开只读 Web UI。
- 使用 ECharts 从数据库动态绘制图表。
- 使用 Docker Compose 管理 Web 服务和批处理容器。

## 快速开始

```bash
docker compose build
docker compose run --rm app python run.py --init-db
docker compose run --rm app python run.py --mode sample
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

写入样例数据：

```bash
docker compose run --rm app python run.py --mode sample
```

执行正常批处理：

```bash
docker compose run --rm app python run.py
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

## 部署与定期任务

Docker Compose、cron、Nginx 的完整部署过程见：

```text
docs/deployment.md
```

GitHub Actions 自动部署模板位于：

```text
.github/workflows/deploy.yml
```

需要在 GitHub Secrets 中配置 `VPS_HOST`、`VPS_USER`、`VPS_SSH_KEY` 和 `VPS_REPO_URL`。

## 数据源

首版优先使用官方免费数据源：

- ESRI Quarterly Estimates of GDP
- e-Stat National Accounts / GDP
- e-Stat Monthly Labour Survey
- e-Stat Consumer Price Index
- 总务省统计局 CPI
- 财务省 JGB 利率数据
- BOJ 统计数据

USDJPY 长期序列若暂未完成稳定自动化，可使用：

```text
data/manual/usdjpy.csv
```

格式：

```csv
date,value,source,note
2026-05-01,153.24,manual_boj_export,BOJ Time-Series Data Search 手动导出
```

## 项目结构

```text
src/
  config.py
  pipeline.py
  storage.py
  web/
    app.py
    templates/
    static/
data/
  raw/
  manual/
  processed/
  app.db
logs/
docs/
```

## 当前状态

这是 starter package。样例数据、数据库、Web UI、ECharts API 和 Docker Compose 已可运行；真实官方数据源的逐项下载和清洗模块将在后续实现。
