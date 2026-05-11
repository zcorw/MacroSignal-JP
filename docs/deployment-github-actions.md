# GitHub Actions 自动部署

本文记录通过 GitHub Actions 自动部署到 VPS 的配置方式。

建议先完成 `docs/deployment-manual.md` 中的基础准备，确认 VPS 能手动运行项目后，再启用自动部署。

## 1. VPS 前置准备

安装基础依赖：

```bash
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

退出 SSH 后重新登录，让 docker 组权限生效。

创建部署目录并授权给部署用户：

```bash
sudo mkdir -p /opt/japan_macro_monitor
sudo chown $USER:$USER /opt/japan_macro_monitor
```

GitHub Actions 的 SSH 会话不能交互输入 sudo 密码，所以这一步需要提前在 VPS 上手动执行。

如果仓库使用 SSH 地址，确保 VPS 信任 GitHub 主机指纹：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keyscan -H github.com >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
```

当前 workflow 也会自动执行这一步；这里保留命令用于手动排查。

## 2. SSH 密钥

在 Windows 上可以生成一组专用于部署的 SSH 密钥：

```powershell
ssh-keygen -t ed25519 -C "github-actions-japan-macro-monitor" -f "$HOME\.ssh\japan_macro_monitor_deploy_key"
```

把公钥添加到 VPS：

```bash
cat ~/.ssh/japan_macro_monitor_deploy_key.pub
```

将输出内容追加到 VPS 的：

```bash
~/.ssh/authorized_keys
```

私钥全文用于 GitHub Secret：`VPS_SSH_KEY`。

## 3. GitHub Secrets

在 GitHub 仓库中进入：

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

必须配置：

```text
VPS_HOST       VPS IP 或域名
VPS_USER       SSH 用户名
VPS_SSH_KEY    私钥全文
VPS_REPO_URL   仓库 SSH 地址，例如 git@github.com:owner/repo.git
```

可选配置：

```text
VPS_PORT       SSH 端口，默认 22
VPS_APP_DIR    部署目录，默认 /opt/japan_macro_monitor
VPS_BRANCH     部署分支，默认 main
```

## 4. 自动部署流程

`.github/workflows/deploy.yml` 会在 `main` 推送后执行：

1. SSH 登录 VPS。
2. 准备 GitHub `known_hosts`。
3. 如果部署目录为空，执行 `git clone`。
4. 如果部署目录已存在但不是 Git 仓库，执行 `git init` 并绑定远端。
5. `git fetch origin <branch>`。
6. `git reset --hard origin/<branch>`。
7. 创建运行目录：`data/raw`、`data/manual`、`data/processed`、`logs`、`outputs`。
8. 构建 Docker 镜像。
9. 初始化数据库。
10. 执行一次真实数据管道。
11. 启动 Web 服务。

## 5. 手动触发

可以在 GitHub 页面手动运行：

```text
Actions -> Deploy to VPS -> Run workflow
```

也可以推送到 `main` 触发：

```bash
git push origin main
```

## 6. 验证部署

在 VPS 上检查：

```bash
cd /opt/japan_macro_monitor
docker compose ps
docker compose logs --tail 100 web
curl http://127.0.0.1:18000/
curl http://127.0.0.1:18000/api/latest
```

## 7. 常见错误

### sudo 需要密码

错误示例：

```text
sudo: a terminal is required to read the password
```

处理方式：不要在 Actions 中执行 sudo。提前在 VPS 手动创建目录并授权：

```bash
sudo mkdir -p /opt/japan_macro_monitor
sudo chown $USER:$USER /opt/japan_macro_monitor
```

### 目标目录非空

错误示例：

```text
fatal: destination path already exists and is not an empty directory
```

当前 workflow 已支持非空目录：如果目录不是 Git 仓库，会在目录内执行 `git init` 并绑定远端。

### Host key verification failed

错误示例：

```text
Host key verification failed.
fatal: could not read from remote repository.
```

处理方式：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keyscan -H github.com >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
```
