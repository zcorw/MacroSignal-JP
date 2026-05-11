# 部署文档入口

部署分为两种方式，请按你的实际使用场景选择：

- 手动部署：见 `docs/deployment-manual.md`
- GitHub Actions 自动部署：见 `docs/deployment-github-actions.md`

建议先完成一次手动部署，确认 Docker、目录权限、Nginx 和定时任务正常后，再接入 GitHub Actions 自动部署。

## 共同约定

默认部署目录：

```bash
/opt/japan_macro_monitor
```

默认 Web 访问：

```text
http://127.0.0.1:18000/
```

运行数据目录：

```text
data/
logs/
outputs/
```

不要把生产数据放在仓库源码同名路径之外的临时位置；项目运行数据应保留在上述目录内。
