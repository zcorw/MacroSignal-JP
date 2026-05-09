# Docker Compose 部署与定期任务

本文记录 VPS 上部署项目、启动 Web UI、创建定期任务和检查日志的命令流程。

## 1. 准备目录

假设项目部署到：

```bash
/opt/japan_macro_monitor
```

进入目录：

```bash
cd /opt/japan_macro_monitor
```

如果目录还不存在，需要先在 VPS 上手动创建一次，并把目录所有者改成部署用户。GitHub Actions 的 SSH 会话不能交互输入 sudo 密码，所以这一步不要放到 Actions 里执行：

```bash
sudo mkdir -p /opt/japan_macro_monitor
sudo chown $USER:$USER /opt/japan_macro_monitor
```

确保持久化目录存在：

```bash
mkdir -p data/raw data/manual data/processed logs
```

## 2. 构建镜像

批处理服务 `app` 使用 Compose profile，构建时需要带上 `--profile batch`：

```bash
docker compose --profile batch build
```

## 3. 首次初始化和真实数据运行

```bash
docker compose run --rm app python run.py --init-db
docker compose run --rm app python run.py
docker compose up -d web
```

验证：

```bash
docker compose ps
curl http://127.0.0.1:18000/
curl http://127.0.0.1:18000/api/latest
curl http://127.0.0.1:18000/api/charts/gdp_growth
```

## 4. 创建定期任务

### 4.1 确认 VPS 时区

建议 VPS 使用日本时间：

```bash
timedatectl
sudo timedatectl set-timezone Asia/Tokyo
timedatectl
```

### 4.2 编辑当前用户 cron

```bash
crontab -e
```

加入以下两行：

```cron
30 10 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py >> logs/cron.log 2>&1
30 20 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py --retry-missing >> logs/cron_retry.log 2>&1
```

含义：

- 每天 10:30 JST 执行常规真实数据下载和分析。
- 每天 20:30 JST 再补跑一次，用于处理官网延迟发布或上午下载失败。
- 日志分别写入 `logs/cron.log` 和 `logs/cron_retry.log`。

### 4.3 检查 cron

```bash
crontab -l
```

手动测试一次：

```bash
cd /opt/japan_macro_monitor
docker compose run --rm app python run.py
tail -n 100 logs/app.log
```

## 5. Nginx 反向代理

Web 容器只绑定宿主机 `127.0.0.1:18000`，公网访问建议使用 Nginx：

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

生产环境建议配置 HTTPS。

## 6. GitHub Actions 自动部署

`.github/workflows/deploy.yml` 会在 `main` 推送后通过 SSH 登录 VPS，拉取代码，构建镜像，初始化数据库，执行一次真实数据管道，并启动 Web。

需要在 GitHub Secrets 中配置：

```text
VPS_HOST       VPS IP 或域名
VPS_USER       SSH 用户名
VPS_SSH_KEY    私钥全文
VPS_REPO_URL   仓库 SSH 地址，例如 git@github.com:owner/repo.git
```

可选：

```text
VPS_PORT       SSH 端口，默认 22
VPS_APP_DIR    部署目录，默认 /opt/japan_macro_monitor
VPS_BRANCH     部署分支，默认 main
```

## 7. USDJPY 自动汇率与手动兜底

系统默认会调用汇率接口自动拉取 USD->JPY 汇率，并写入：

```bash
data/raw/fx_usdjpy.csv
```

若自动汇率源暂时失败，可放置手动兜底文件：

```bash
data/manual/usdjpy.csv
```

格式：

```csv
date,value,source,note
2026-05-01,153.24,manual_boj_export,BOJ Time-Series Data Search manual export
```

未提供手动文件时，系统仍会完成 GDP、CPI、工资和 JGB 分析；只有当自动源也失败时，报告才会降低弱日元相关判断权重。
