# Docker Compose 部署与定期任务

本文档记录 VPS 上部署项目、启动 Web UI、创建定期任务和检查日志的命令流程。

## 1. 准备目录

假设项目部署到：

```bash
/opt/japan_macro_monitor
```

进入目录：

```bash
cd /opt/japan_macro_monitor
```

确保持久化目录存在：

```bash
mkdir -p data/raw data/manual data/processed logs
```

## 2. 构建镜像

```bash
docker compose build
```

## 3. 初始化数据库

```bash
docker compose run --rm app python run.py --init-db
```

## 4. 写入样例数据并验证

```bash
docker compose run --rm app python run.py --mode sample
```

启动 Web UI：

```bash
docker compose up -d web
```

查看服务状态：

```bash
docker compose ps
```

本机验证：

```bash
curl http://127.0.0.1:18000/
curl http://127.0.0.1:18000/api/latest
curl http://127.0.0.1:18000/api/charts/gdp_growth
```

## 5. 创建定期任务

### 5.1 确认 VPS 时区

建议 VPS 使用日本时间：

```bash
timedatectl
```

如果不是 `Asia/Tokyo`，可设置：

```bash
sudo timedatectl set-timezone Asia/Tokyo
```

再次确认：

```bash
timedatectl
```

### 5.2 编辑当前用户 cron

```bash
crontab -e
```

加入以下两行：

```cron
30 10 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py >> logs/cron.log 2>&1
30 20 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py --retry-missing >> logs/cron_retry.log 2>&1
```

含义：

- 每天 10:30 JST 执行常规检查。
- 每天 20:30 JST 执行补跑，用于处理官网延迟发布或上午下载失败。
- 日志分别写入 `logs/cron.log` 和 `logs/cron_retry.log`。

### 5.3 查看已安装的 cron

```bash
crontab -l
```

确认输出中包含：

```cron
30 10 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py >> logs/cron.log 2>&1
30 20 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py --retry-missing >> logs/cron_retry.log 2>&1
```

### 5.4 手动执行一次定期任务命令

```bash
cd /opt/japan_macro_monitor
docker compose run --rm app python run.py
```

检查日志：

```bash
tail -n 100 logs/app.log
```

## 6. Nginx 反向代理

Web 容器只绑定到宿主机 `127.0.0.1:18000`，公网访问建议使用 Nginx。

示例配置：

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

## 7. 常用维护命令

查看 Web 日志：

```bash
docker compose logs -f web
```

重启 Web：

```bash
docker compose restart web
```

停止服务：

```bash
docker compose down
```

重新构建并启动：

```bash
docker compose build
docker compose up -d web
```

查看批处理日志：

```bash
tail -n 100 logs/cron.log
tail -n 100 logs/cron_retry.log
tail -n 100 logs/app.log
```

## 8. 手动 USDJPY 数据

如果 BOJ 长期 USDJPY 自动化接口尚未接入，可放置：

```bash
data/manual/usdjpy.csv
```

格式：

```csv
date,value,source,note
2026-05-01,153.24,manual_boj_export,BOJ Time-Series Data Search 手动导出
```

使用手动数据时，Web UI 和报告必须标注来源。

## 9. GitHub Actions 自动部署

仓库内提供 `.github/workflows/deploy.yml`。当 `main` 分支有推送时，GitHub Actions 会通过 SSH 登录 VPS，拉取最新代码，并执行：

```bash
docker compose build
docker compose run --rm app python run.py --init-db
docker compose up -d web
```

### 9.1 VPS 准备

在 VPS 上安装基础依赖：

```bash
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

将部署用户加入 docker 组：

```bash
sudo usermod -aG docker $USER
```

退出 SSH 后重新登录，使 docker 组权限生效。

创建部署目录：

```bash
sudo mkdir -p /opt/japan_macro_monitor
sudo chown $USER:$USER /opt/japan_macro_monitor
```

### 9.2 创建 SSH key

在本地或安全机器上生成部署 key：

```bash
ssh-keygen -t ed25519 -C "github-actions-japan-macro-monitor" -f ./japan_macro_monitor_deploy_key
```

把公钥加入 VPS：

```bash
ssh-copy-id -i ./japan_macro_monitor_deploy_key.pub user@your-vps-host
```

或手动追加到 VPS：

```bash
cat japan_macro_monitor_deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 9.3 GitHub Secrets

在 GitHub 仓库中进入：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

添加：

```text
VPS_HOST       VPS IP 或域名
VPS_USER       SSH 用户名
VPS_SSH_KEY    私钥内容，即 japan_macro_monitor_deploy_key 文件全文
VPS_REPO_URL   仓库 SSH 地址，例如 git@github.com:owner/repo.git
```

如果仓库是私有仓库，VPS 也必须能读取该仓库。常见做法：

- 在 GitHub 仓库中添加一把只读 Deploy Key，并把对应私钥放到 VPS 的部署用户 `~/.ssh/`。
- 或将 `VPS_REPO_URL` 设置为带只读 token 的 HTTPS 地址。此方式要谨慎管理 token 权限。

可选：

```text
VPS_PORT       SSH 端口，默认 22
VPS_APP_DIR    部署目录，默认 /opt/japan_macro_monitor
VPS_BRANCH     部署分支，默认 main
```

### 9.4 首次部署

推送到 `main`：

```bash
git push origin main
```

或在 GitHub Actions 页面手动运行：

```text
Actions -> Deploy to VPS -> Run workflow
```

### 9.5 验证部署

在 VPS 上检查：

```bash
cd /opt/japan_macro_monitor
docker compose ps
docker compose logs --tail 100 web
curl http://127.0.0.1:18000/
```
