# Stage 9. 最终 Starter Package

## 已确认事实

- 项目使用 Docker Compose 管理。
- Web UI 公开只读，不做账号管理。
- 清洗后的结构化数据保存到 SQLite。
- Web UI 从数据库动态生成页面。
- 图表使用 ECharts 动态绘制，不预生成 PNG。
- 定期任务由 VPS cron 调用 Docker Compose 批处理命令。

## 已生成文件

- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `config.yaml`
- `run.py`
- `README.md`
- `docs/deployment.md`
- `src/config.py`
- `src/logging_setup.py`
- `src/storage.py`
- `src/pipeline.py`
- `src/web/app.py`
- `src/web/templates/*.html`
- `src/web/static/charts.js`
- `src/web/static/styles.css`

## 当前能力

- 初始化 SQLite schema。
- 写入样例结构化数据。
- 写入样例报告、评分、证据和数据源状态。
- FastAPI 页面展示最新报告、历史报告、报告详情和数据源状态。
- JSON API 输出 ECharts 图表数据。
- Docker Compose 构建、运行批处理和启动 Web。

## 定期任务文档

已在 `docs/deployment.md` 中记录完整流程：

- 确认或设置 VPS 时区为 Asia/Tokyo。
- 使用 `crontab -e` 创建定期任务。
- 上午 10:30 JST 执行常规检查。
- 晚上 20:30 JST 执行补跑。
- 使用 `crontab -l` 验证任务已安装。
- 手动执行 Docker Compose 批处理命令验证。
- 查看 `logs/cron.log`、`logs/cron_retry.log` 和 `logs/app.log`。

## 后续实现重点

1. 将真实数据源下载逻辑接入 `src.fetch_data`。
2. 将 ESRI/e-Stat/MOF/BOJ 原始文件清洗为 `series_observations`。
3. 实现真实指标计算和评分。
4. 将报告段落从样例文本改为基于真实指标生成。
5. 补充单元测试、数据库测试和 Web API 测试。
