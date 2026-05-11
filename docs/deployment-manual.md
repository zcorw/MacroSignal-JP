# 手动部署

本文记录在 VPS 上手动部署项目、启动 Web UI、配置 cron 定时任务和 Nginx 反向代理的流程。

## 1. 准备 VPS

安装基础依赖：

```bash
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

把当前用户加入 `docker` 组：

```bash
sudo usermod -aG docker $USER
```

退出 SSH 后重新登录，让 docker 组权限生效。

## 2. 准备目录

默认部署目录：

```bash
/opt/japan_macro_monitor
```

如果目录还不存在，需要手动创建一次，并把所有者改成部署用户：

```bash
sudo mkdir -p /opt/japan_macro_monitor
sudo chown $USER:$USER /opt/japan_macro_monitor
```

进入目录：

```bash
cd /opt/japan_macro_monitor
```

## 3. 获取代码

如果目录为空：

```bash
git clone <your-repo-url> /opt/japan_macro_monitor
cd /opt/japan_macro_monitor
```

如果目录已存在但还不是 Git 仓库：

```bash
cd /opt/japan_macro_monitor
git init
git remote add origin <your-repo-url>
git fetch origin main
git reset --hard origin/main
```

如果使用 SSH 仓库地址，例如 `git@github.com:owner/repo.git`，先确保 VPS 信任 GitHub 主机指纹：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keyscan -H github.com >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
```

## 4. 准备运行目录

```bash
mkdir -p data/raw data/manual data/processed logs outputs
```

## 5. 构建镜像

批处理服务 `app` 使用 Compose profile，构建时需要带上 `--profile batch`：

```bash
docker compose --profile batch build
```

## 6. 初始化并运行一次

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
curl http://127.0.0.1:18000/foreign-residents
curl http://127.0.0.1:18000/api/foreign-residents
```

外国人趋势专题会随 `docker compose run --rm app python run.py` 一起下载和清洗以下官方数据：

- e-Stat 在留外国人統計
- 厚生労働省 外国人雇用状況の届出状況
- e-Stat 賃金構造基本統計調査 外国人労働者

数据下载现在采用“动态发现最新文件 + 备用链接”的方式：

- e-Stat：先访问对应统计搜索页，解析最新 `file-download` 链接，并用文件结构校验确认是否为目标表。
- 厚生労働省：先访问外国人雇用状况索引页，选择最新“令和 X 年 10 月末”结果页，再解析 XLSX 附件。
- 如果官方页面结构临时变化导致动态发现失败，程序会退回到代码内保留的备用链接，并在 `/sources` 中记录状态信息。

首次真实数据运行后，可重点检查：

```bash
curl http://127.0.0.1:18000/api/foreign-residents/charts/foreign_residents_total
curl http://127.0.0.1:18000/api/foreign-residents/charts/foreign_workers_by_industry
curl http://127.0.0.1:18000/api/foreign-residents/charts/foreign_nominal_wage
```

已知限制：

- 外国人雇用数据是每年 10 月末口径。
- 外国人工资数据当前为年度水平值；在多期历史工资文件接入前，不应把单期工资水平解释为工资同比改善。
- 在留外国人、外国人雇用、工资三类数据发布时间和统计口径不同，页面会以保守方式展示置信度。

## 7. 配置 cron 定时任务

保守做法是不修改整台 VPS 的系统时区，只查看当前时区：

```bash
timedatectl
```

如果这台 VPS 只运行本项目，也可以手动把系统时区设为日本时间；但这会影响整台机器的本地时间、cron、系统日志和其他服务：

```bash
sudo timedatectl set-timezone Asia/Tokyo
```

多服务 VPS 建议不要改系统时区，而是在 cron 中使用 `CRON_TZ=Asia/Tokyo`。

编辑当前用户 cron：

```bash
crontab -e
```

加入以下内容：

```cron
CRON_TZ=Asia/Tokyo
30 10 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py >> logs/cron.log 2>&1
30 20 * * * cd /opt/japan_macro_monitor && docker compose run --rm app python run.py --retry-missing >> logs/cron_retry.log 2>&1
```

含义：

- 每天 10:30 JST 执行常规真实数据下载和分析。
- 每天 20:30 JST 再补跑一次，用于处理官网延迟发布或上午下载失败。
- 日志分别写入 `logs/cron.log` 和 `logs/cron_retry.log`。
- `CRON_TZ=Asia/Tokyo` 只影响后续 cron 行的执行时区，不需要修改整台 VPS 的系统时区。

检查 cron：

```bash
crontab -l
```

手动测试一次：

```bash
cd /opt/japan_macro_monitor
docker compose run --rm app python run.py
tail -n 100 logs/app.log
```

## 8. Nginx 反向代理

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

## 9. USDJPY 汇率兜底

系统默认会自动拉取 USD->JPY 汇率，并写入：

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
