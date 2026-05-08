from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PathsConfig:
    raw_dir: Path
    manual_dir: Path
    processed_dir: Path
    database: Path
    logs_dir: Path


@dataclass(frozen=True)
class DownloadConfig:
    timeout_seconds: int
    retries: int
    user_agent: str


@dataclass(frozen=True)
class FeatureConfig:
    export_markdown: bool
    use_manual_usdjpy: bool


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig
    download: DownloadConfig
    features: FeatureConfig
    raw: dict[str, Any]


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    paths = data["paths"]
    download = data["download"]
    features = data["features"]
    return AppConfig(
        paths=PathsConfig(
            raw_dir=Path(paths["raw_dir"]),
            manual_dir=Path(paths["manual_dir"]),
            processed_dir=Path(paths["processed_dir"]),
            database=Path(paths["database"]),
            logs_dir=Path(paths["logs_dir"]),
        ),
        download=DownloadConfig(
            timeout_seconds=int(download["timeout_seconds"]),
            retries=int(download["retries"]),
            user_agent=str(download["user_agent"]),
        ),
        features=FeatureConfig(
            export_markdown=bool(features["export_markdown"]),
            use_manual_usdjpy=bool(features["use_manual_usdjpy"]),
        ),
        raw=data,
    )
