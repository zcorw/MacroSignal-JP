from __future__ import annotations

import logging
from pathlib import Path

import requests

from src.config import AppConfig, load_config
from src.fetch_data import DownloadedFile, download_file

logger = logging.getLogger(__name__)

ESTAT_FOREIGN_RESIDENTS_TABLE_DATA = (
    "https://www.e-stat.go.jp/stat-search/file-download?fileKind=0&statInfId=000040292372"
)
MHLW_FOREIGN_WORKERS_2024 = "https://www.mhlw.go.jp/content/11655000/001389472.xlsx"
ESTAT_FOREIGN_WAGES_2024 = "https://www.e-stat.go.jp/stat-search/file-download?fileKind=4&statInfId=000040247905"


def download_foreign_sources(config: AppConfig) -> list[DownloadedFile]:
    raw_dir = config.paths.raw_dir / "foreign_residents"
    raw_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": config.download.user_agent})

    return [
        download_file(
            session,
            ESTAT_FOREIGN_RESIDENTS_TABLE_DATA,
            raw_dir / "estat_foreign_residents_latest.xlsx",
            "e-Stat Foreign Residents",
            config,
        ),
        download_file(
            session,
            MHLW_FOREIGN_WORKERS_2024,
            raw_dir / "mhlw_foreign_workers_latest.xlsx",
            "MHLW Foreign Workers",
            config,
        ),
        download_file(
            session,
            ESTAT_FOREIGN_WAGES_2024,
            raw_dir / "estat_foreign_wages_latest.xlsx",
            "e-Stat Foreign Wages",
            config,
        ),
    ]


def main() -> None:
    config = load_config()
    for result in download_foreign_sources(config):
        path = str(result.path) if result.path else "-"
        print(f"{result.source_name}: {result.status} {path} {result.message}")


if __name__ == "__main__":
    main()
