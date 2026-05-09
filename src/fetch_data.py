from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.config import AppConfig

logger = logging.getLogger(__name__)

ESRI_TOP = "https://www.esri.cao.go.jp/en/sna/sokuhou/sokuhou_top.html"
ESTAT_GDP = "https://www.e-stat.go.jp/en/stat-search/file-download?statInfId=000040385257&fileKind=1"
ESTAT_CPI_LATEST = "https://www.e-stat.go.jp/en/stat-search/file-download?statInfId=000040444343&fileKind=4"
ESTAT_REAL_WAGE_LATEST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040277086&fileKind=4"
MOF_JGB_HISTORICAL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
FX_ENDPOINT_TEMPLATE = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{version}/v1/currencies/usd.json"
FX_SOURCE = "fawazahmed0/currency-api"


@dataclass(frozen=True)
class DownloadedFile:
    source_name: str
    status: str
    path: Path | None
    latest_data_date: str | None
    message: str


def download_all(config: AppConfig) -> list[DownloadedFile]:
    raw_dir = config.paths.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": config.download.user_agent})

    results: list[DownloadedFile] = []
    results.extend(download_esri_gdp(session, raw_dir, config))
    results.append(download_file(session, ESTAT_GDP, raw_dir / "estat_gdp.csv", "e-Stat GDP", config))
    results.append(download_file(session, ESTAT_CPI_LATEST, raw_dir / "estat_cpi_latest.xlsx", "e-Stat CPI", config))
    results.append(download_file(session, ESTAT_REAL_WAGE_LATEST, raw_dir / "estat_real_wage_latest.xlsx", "e-Stat Real Wage", config))
    results.append(download_file(session, MOF_JGB_HISTORICAL, raw_dir / "mof_jgb_historical.csv", "MOF JGB", config))
    results.append(download_usdjpy(session, raw_dir / "fx_usdjpy.csv", config))
    if not (raw_dir / "fx_usdjpy.csv").exists():
        results.append(check_manual_usdjpy(config))
    return results


def download_file(
    session: requests.Session,
    url: str,
    path: Path,
    source_name: str,
    config: AppConfig,
) -> DownloadedFile:
    try:
        response = session.get(url, timeout=config.download.timeout_seconds)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        logger.info("下载成功 %s -> %s", source_name, path)
        return DownloadedFile(source_name, "success", path, None, "下载成功")
    except Exception as exc:
        logger.exception("下载失败 %s", source_name)
        return DownloadedFile(source_name, "failed", None, None, f"下载失败：{exc}")


def download_esri_gdp(session: requests.Session, raw_dir: Path, config: AppConfig) -> list[DownloadedFile]:
    try:
        top = session.get(ESRI_TOP, timeout=config.download.timeout_seconds)
        top.raise_for_status()
        soup = BeautifulSoup(top.text, "html.parser")
        link = None
        for anchor in soup.find_all("a", href=True):
            if "Time series table" in anchor.get_text(" ", strip=True):
                link = urljoin(ESRI_TOP, anchor["href"])
                break
        if link is None:
            raise RuntimeError("未找到 ESRI Time series table 链接")

        page = session.get(link, timeout=config.download.timeout_seconds)
        page.raise_for_status()
        page_soup = BeautifulSoup(page.text, "html.parser")
        targets = {
            "esri_nominal_sa.csv": re.compile(r"/gaku-mk\d+\.csv$"),
            "esri_real_sa.csv": re.compile(r"/gaku-jk\d+\.csv$"),
            "esri_deflator_sa.csv": re.compile(r"/def-qk\d+\.csv$"),
        }
        results: list[DownloadedFile] = []
        for filename, pattern in targets.items():
            href = None
            for anchor in page_soup.find_all("a", href=True):
                if pattern.search(anchor["href"]):
                    href = urljoin(link, anchor["href"])
                    break
            if href is None:
                results.append(DownloadedFile(f"ESRI {filename}", "failed", None, None, "未找到 CSV 链接"))
                continue
            results.append(download_file(session, href, raw_dir / filename, f"ESRI {filename}", config))
        return results
    except Exception as exc:
        logger.exception("ESRI GDP 下载失败")
        return [DownloadedFile("ESRI GDP", "failed", None, None, f"下载失败：{exc}")]


def download_usdjpy(session: requests.Session, path: Path, config: AppConfig) -> DownloadedFile:
    today = date.today()
    candidate_dates = [today - timedelta(days=offset) for offset in range(180, -1, -7)]
    rows: list[tuple[str, float]] = []
    errors = 0

    for day in candidate_dates:
        result = fetch_usdjpy_for_version(session, day.isoformat(), config)
        if result is None:
            errors += 1
            continue
        rows.append(result)

    latest = fetch_usdjpy_for_version(session, "latest", config)
    if latest is not None and all(row[0] != latest[0] for row in rows):
        rows.append(latest)

    rows = sorted({row[0]: row for row in rows}.values(), key=lambda item: item[0])
    if len(rows) < 2:
        return DownloadedFile(
            "USDJPY FX API",
            "failed",
            None,
            None,
            f"自动汇率下载失败或数据不足，失败请求数：{errors}",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("date,value,source,note\n")
        for rate_date, value in rows:
            handle.write(f"{rate_date},{value:.8f},{FX_SOURCE},USD to JPY from currency-api\n")
    return DownloadedFile("USDJPY FX API", "success", path, rows[-1][0], f"下载 USDJPY 汇率 {len(rows)} 条")


def fetch_usdjpy_for_version(session: requests.Session, version: str, config: AppConfig) -> tuple[str, float] | None:
    url = FX_ENDPOINT_TEMPLATE.format(version=version)
    try:
        response = session.get(url, timeout=config.download.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        rate_date = str(payload.get("date") or version)
        rate = payload.get("usd", {}).get("jpy")
        if rate is None:
            return None
        return rate_date, float(rate)
    except Exception:
        logger.debug("USDJPY 汇率下载跳过 version=%s", version, exc_info=True)
        return None


def check_manual_usdjpy(config: AppConfig) -> DownloadedFile:
    manual = config.paths.manual_dir / "usdjpy.csv"
    if not manual.exists():
        return DownloadedFile(
            "Manual USDJPY",
            "partial_success",
            None,
            None,
            "自动 USDJPY 下载失败，且未提供 data/manual/usdjpy.csv；页面和报告会降低相关结论权重。",
        )
    return DownloadedFile("Manual USDJPY", "success", manual, None, "自动 USDJPY 下载失败，使用手动 USDJPY CSV")
