from __future__ import annotations

import argparse

from src.config import load_config
from src.logging_setup import setup_logging
from src.pipeline import run_pipeline
from src.storage import init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="日本宏观政策效果监控器")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--init-db", action="store_true", help="初始化数据库")
    parser.add_argument("--mode", choices=["normal", "sample"], default="normal", help="运行模式")
    parser.add_argument("--retry-missing", action="store_true", help="发布日失败补跑")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.paths.logs_dir)

    if args.init_db:
        init_db(config.paths.database)
        return

    run_pipeline(config, mode=args.mode, retry_missing=args.retry_missing)


if __name__ == "__main__":
    main()
