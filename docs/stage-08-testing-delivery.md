# Stage 8. 测试与交付

## 已确认事实

- 项目部署在 VPS。
- 项目使用 Docker Compose 管理。
- 批处理通过 Docker Compose 管理的容器执行。
- Web UI 通过 FastAPI + Jinja2 + ECharts 动态展示。
- 数据保存到 SQLite。
- Web UI 公开只读，不做账号管理。
- 图表不预生成，ECharts 从 JSON API 获取结构化数据。
- 数据源以官方免费数据为主，部分 USDJPY 长期数据允许手动 CSV 兜底。

## 测试目标

- 确认数据源下载可用。
- 确认清洗后的结构化数据正确入库。
- 确认派生指标和评分可重复计算。
- 确认 Web UI 能从数据库动态展示报告和图表。
- 确认数据源失败时不会覆盖上一次成功结果。
- 确认 VPS 定时运行有日志和可追踪状态。

## 测试分层

### 1. 单元测试

重点覆盖纯函数和规则：

- 日期解析。
- YoY 计算。
- 3 个月变化计算。
- 评分阈值判断。
- 缺失数据降级逻辑。
- 手动 USDJPY CSV 校验。
- 中文展示名映射。

建议目录：

```text
tests/
  test_indicators.py
  test_analyze.py
  test_config.py
  test_manual_data.py
```

### 2. 数据源下载测试

目标：确认官方页面和样例文件仍可访问。

测试内容：

- ESRI GDP 页面可访问并能解析 CSV 链接。
- e-Stat GDP `file-download` 可下载。
- e-Stat CPI 能从筛选页面找到目标表或固定 `statInfId` 可下载。
- e-Stat 工资表可下载。
- MOF JGB 历史 CSV 可下载。
- BOJ / USDJPY 若自动化不可用，能正确提示手动兜底。

这类测试不应默认每次单元测试都联网执行，建议做成手动命令或 `--integration` 模式。

### 3. 数据库测试

目标：确认 schema 和写入查询稳定。

测试内容：

- 初始化 SQLite schema。
- 写入 `series_observations`。
- 对同一 `(series_key, date, source_name)` 做 upsert。
- 写入报告、章节、证据、评分。
- 查询最新报告。
- 查询 ECharts 图表 API 所需序列。

### 4. Web 测试

目标：确认公开页面和 JSON API 可用。

测试内容：

- `GET /` 返回 200。
- `GET /reports` 返回 200。
- `GET /reports/{report_id}` 返回 200。
- `GET /sources` 返回 200。
- `GET /api/latest` 返回结构化 JSON。
- `GET /api/charts/gdp_growth` 返回 ECharts 所需 JSON。
- 无报告数据时页面显示“暂无数据”，而不是报错。

### 5. 端到端冒烟测试

目标：确认最小流程可跑通。

流程：

1. 初始化数据库。
2. 使用样例 raw 文件或小型 fixture。
3. 执行 `python run.py --mode sample`。
4. 确认数据库有清洗后数据、指标、报告和评分。
5. 启动 Web 服务。
6. 打开首页和图表 API。

## 交付命令

### 本地初始化

```bash
docker compose build
docker compose run --rm app python run.py --init-db
docker compose run --rm app python run.py --mode sample
docker compose up -d web
```

Windows 本地开发同样优先使用 Docker Desktop：

```powershell
docker compose build
docker compose run --rm app python run.py --init-db
docker compose run --rm app python run.py --mode sample
docker compose up -d web
```

### VPS 定时执行

首版建议由宿主机 cron 调用 Docker Compose 批处理命令：

cron 示例：

```cron
30 10 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py >> logs/cron.log 2>&1
30 20 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py --retry-missing >> logs/cron_retry.log 2>&1
```

说明：

- 上午 10:30 JST 做常规检查。
- 晚上 20:30 JST 做发布日失败补跑。
- 实际 VPS 时区必须确认设置为 Asia/Tokyo，或 cron 使用对应 UTC 时间。
- `data/` 和 `logs/` 必须作为宿主机挂载目录持久化。

### Docker Compose 服务

建议 compose 至少包含两个服务：

```yaml
services:
  web:
    build: .
    command: uvicorn src.web.app:app --host 0.0.0.0 --port 8000
    ports:
      - "127.0.0.1:18000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  app:
    build: .
    command: python run.py
    profiles: ["batch"]
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

### Nginx 反向代理

建议公网访问通过 Nginx：

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:18000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

生产环境建议再配置 HTTPS。

## 失败处理验收

- 单个数据源失败时，其他数据源继续处理。
- `source_status` 记录失败摘要。
- Web UI 数据源状态页展示失败摘要。
- 如果没有足够数据生成新报告，不覆盖上一次成功报告。
- 如果使用手动 USDJPY 数据，首页和报告详情必须标注。
- 如果数据库为空，Web UI 显示空状态，不返回 500。

## 最小验收标准

首版完成时必须满足：

- `python run.py --init-db` 可初始化数据库。
- `python run.py --mode sample` 可用样例数据写入数据库。
- `python run.py` 可执行真实下载流程，允许部分数据源失败但必须记录。
- 首页能展示最新报告摘要、评分、关键证据。
- 历史报告页能列出报告。
- 报告详情页能展示章节和证据。
- 数据源状态页能展示每个数据源状态。
- ECharts 至少能动态展示 5 个首版图表。
- README 写明本地运行、VPS cron、Docker Compose、Nginx 和手动 USDJPY CSV 格式。
- README 写明 Docker Compose、本地运行、VPS cron、Nginx 和手动 USDJPY CSV 格式。

## 需要进入工程约定的规则

- 联网测试和单元测试分开。
- 所有失败都应结构化记录。
- Web UI 空数据状态必须可用。
- 生产部署不直接对公网暴露 uvicorn，应通过 Nginx 代理。
- cron 日志必须写入 `logs/`。
- Docker Compose 必须挂载 `data/` 和 `logs/` 持久化目录。
