from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Observation:
    series_key: str
    date: str
    period_label: str
    frequency: str
    value: float | None
    unit: str
    source_name: str
    source_file: str
    released_at: str | None = None


def clean_downloaded_files(raw_dir: Path, manual_dir: Path) -> list[Observation]:
    observations: list[Observation] = []
    observations.extend(clean_esri_gdp(raw_dir))
    observations.extend(clean_cpi(raw_dir / "estat_cpi_latest.xlsx"))
    observations.extend(clean_real_wage(raw_dir / "estat_real_wage_latest.xlsx"))
    observations.extend(clean_jgb(raw_dir / "mof_jgb_historical.csv"))
    observations.extend(clean_manual_usdjpy(manual_dir / "usdjpy.csv"))
    return observations


def clean_esri_gdp(raw_dir: Path) -> list[Observation]:
    specs = [
        (raw_dir / "esri_nominal_sa.csv", {"nominal_gdp": 1}, "ESRI GDP nominal", "billions_jpy"),
        (
            raw_dir / "esri_real_sa.csv",
            {
                "real_gdp": 1,
                "real_private_consumption": 2,
                "real_private_investment": 6,
                "real_public_demand": 8,
            },
            "ESRI GDP real",
            "billions_chained_jpy",
        ),
        (raw_dir / "esri_deflator_sa.csv", {"gdp_deflator": 1}, "ESRI GDP deflator", "index"),
    ]
    out: list[Observation] = []
    for path, columns, source_name, unit in specs:
        if not path.exists():
            continue
        df = pd.read_csv(path, encoding="cp932", header=None, dtype=str)
        current_year: int | None = None
        for _, row in df.iloc[7:].iterrows():
            parsed = parse_esri_quarter(str(row.iloc[0]), current_year)
            if parsed is None:
                continue
            current_year, period_label, period_date = parsed
            for series_key, column in columns.items():
                value = parse_float(row.iloc[column])
                if value is None:
                    continue
                out.append(
                    Observation(
                        series_key=series_key,
                        date=period_date,
                        period_label=period_label,
                        frequency="quarterly",
                        value=value,
                        unit=unit,
                        source_name=source_name,
                        source_file=str(path),
                    )
                )
    return out


def parse_esri_quarter(label: str, current_year: int | None) -> tuple[int, str, str] | None:
    text = label.strip()
    if not text or text.lower() == "nan" or "Calendar" in text or "Quarter" in text:
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            current_year = int(left.strip())
        except ValueError:
            return None
        quarter_text = right
    else:
        quarter_text = text
    if current_year is None:
        return None
    quarter_map = {
        "1-3": (1, "03-31"),
        "4-6": (2, "06-30"),
        "7-9": (3, "09-30"),
        "10-12": (4, "12-31"),
    }
    normalized = quarter_text.replace(".", "").replace(" ", "").strip()
    if normalized not in quarter_map:
        return None
    quarter, suffix = quarter_map[normalized]
    return current_year, f"{current_year}Q{quarter}", f"{current_year}-{suffix}"


def clean_cpi(path: Path) -> list[Observation]:
    if not path.exists():
        return []
    out: list[Observation] = []
    xls = pd.ExcelFile(path)
    df = pd.read_excel(path, sheet_name=xls.sheet_names[0], header=None)
    column_map = {
        "cpi_all_items": 8,
        "cpi_less_fresh_food": 9,
        "cpi_less_fresh_food_energy": 10,
    }
    for _, row in df.iloc[10:].iterrows():
        yyyymm = row.iloc[1]
        if pd.isna(yyyymm):
            continue
        try:
            yyyymm_int = int(float(yyyymm))
        except ValueError:
            continue
        year = yyyymm_int // 100
        month = yyyymm_int % 100
        if not 1 <= month <= 12:
            continue
        period_date = month_end(year, month)
        for series_key, column in column_map.items():
            value = parse_float(row.iloc[column]) if column < len(row) else None
            if value is None:
                continue
            out.append(
                Observation(
                    series_key=series_key,
                    date=period_date,
                    period_label=f"{year}-{month:02d}",
                    frequency="monthly",
                    value=value,
                    unit="index",
                    source_name="e-Stat CPI",
                    source_file=str(path),
                )
            )
    return out


def clean_real_wage(path: Path) -> list[Observation]:
    if not path.exists():
        return []
    df = pd.read_excel(path, header=None)
    out: list[Observation] = []
    for _, row in df.iterrows():
        year_value = parse_float(row.iloc[0])
        month_value = parse_float(row.iloc[1])
        if year_value is None or month_value is None:
            continue
        year = int(year_value)
        month = int(month_value)
        if not 1 <= month <= 12:
            continue
        period_date = month_end(year, month)
        index_value = parse_float(row.iloc[2])
        yoy = parse_float(row.iloc[3])
        if index_value is not None:
            out.append(Observation("real_wage_index", period_date, f"{year}-{month:02d}", "monthly", index_value, "index", "e-Stat Real Wage", str(path)))
        if yoy is not None:
            out.append(Observation("real_wage_yoy", period_date, f"{year}-{month:02d}", "monthly", yoy, "%", "e-Stat Real Wage", str(path)))
    return out


def clean_jgb(path: Path) -> list[Observation]:
    if not path.exists():
        return []
    df = pd.read_csv(path, encoding="utf-8-sig", header=1)
    out: list[Observation] = []
    for _, row in df.iterrows():
        raw_date = row.get("Date")
        if pd.isna(raw_date):
            continue
        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        if pd.isna(parsed_date):
            continue
        date_str = parsed_date.date().isoformat()
        for series_key, column in {"jgb_10y": "10Y", "jgb_20y": "20Y", "jgb_30y": "30Y"}.items():
            value = parse_float(row.get(column))
            if value is None:
                continue
            out.append(Observation(series_key, date_str, date_str, "daily", value, "%", "MOF JGB", str(path)))
    return out


def clean_manual_usdjpy(path: Path) -> list[Observation]:
    if not path.exists():
        return []
    df = pd.read_csv(path)
    out: list[Observation] = []
    for _, row in df.iterrows():
        parsed_date = pd.to_datetime(row.get("date"), errors="coerce")
        value = parse_float(row.get("value"))
        if pd.isna(parsed_date) or value is None:
            continue
        date_str = parsed_date.date().isoformat()
        source = str(row.get("source") or "manual_usdjpy")
        out.append(Observation("usdjpy", date_str, date_str, "daily", value, "JPY/USD", source, str(path)))
    return out


def parse_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"***", "-", "nan"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    if math.isnan(result):
        return None
    return result


def month_end(year: int, month: int) -> str:
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()
