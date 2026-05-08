from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from src.clean_data import Observation


def calculate_indicators(observations: list[Observation]) -> list[Observation]:
    out: list[Observation] = list(observations)
    frame = pd.DataFrame([asdict(item) for item in observations])
    if frame.empty:
        return out

    yoy_specs = {
        "real_gdp": ("real_gdp_yoy", 4),
        "nominal_gdp": ("nominal_gdp_yoy", 4),
        "gdp_deflator": ("gdp_deflator_yoy", 4),
        "real_private_consumption": ("real_consumption_yoy", 4),
        "real_private_investment": ("private_investment_yoy", 4),
        "cpi_all_items": ("cpi_yoy", 12),
    }
    for source_key, (target_key, periods) in yoy_specs.items():
        out.extend(pct_change_observations(frame, source_key, target_key, periods))

    out.extend(change_observations(frame, "jgb_10y", "jgb_10y_change_3m", 63, multiplier=100.0, unit="bp"))
    out.extend(change_observations(frame, "jgb_30y", "jgb_30y_change_3m", 63, multiplier=100.0, unit="bp"))
    out.extend(pct_change_observations(frame, "usdjpy", "usdjpy_change_3m", 63))

    # e-Stat 稳定下载到的是实际工资最新表；名义工资同比暂用“实际工资同比 + CPI 同比”保守近似。
    out.extend(estimated_nominal_wage_yoy(out))
    out.extend(wage_minus_cpi(out))
    return out


def pct_change_observations(frame: pd.DataFrame, source_key: str, target_key: str, periods: int) -> list[Observation]:
    subset = frame[frame["series_key"] == source_key].sort_values("date")
    if subset.empty:
        return []
    values = pd.to_numeric(subset["value"], errors="coerce")
    pct = values.pct_change(periods=periods) * 100.0
    out: list[Observation] = []
    for (_, row), value in zip(subset.iterrows(), pct):
        if pd.isna(value):
            continue
        out.append(
            Observation(
                series_key=target_key,
                date=row["date"],
                period_label=row["period_label"],
                frequency=row["frequency"],
                value=round(float(value), 3),
                unit="%",
                source_name=f"derived:{source_key}",
                source_file=row["source_file"],
                released_at=row.get("released_at"),
            )
        )
    return out


def change_observations(frame: pd.DataFrame, source_key: str, target_key: str, periods: int, multiplier: float, unit: str) -> list[Observation]:
    subset = frame[frame["series_key"] == source_key].sort_values("date")
    if subset.empty:
        return []
    values = pd.to_numeric(subset["value"], errors="coerce")
    change = (values - values.shift(periods)) * multiplier
    out: list[Observation] = []
    for (_, row), value in zip(subset.iterrows(), change):
        if pd.isna(value):
            continue
        out.append(Observation(target_key, row["date"], row["period_label"], row["frequency"], round(float(value), 3), unit, f"derived:{source_key}", row["source_file"], row.get("released_at")))
    return out


def latest_by_key(observations: list[Observation], key: str) -> Observation | None:
    values = [item for item in observations if item.series_key == key and item.value is not None]
    if not values:
        return None
    return sorted(values, key=lambda item: item.date)[-1]


def latest_matching_date(observations: list[Observation], key: str, date_value: str) -> Observation | None:
    values = [item for item in observations if item.series_key == key and item.date == date_value and item.value is not None]
    if not values:
        return None
    return values[-1]


def estimated_nominal_wage_yoy(observations: list[Observation]) -> list[Observation]:
    real = latest_by_key(observations, "real_wage_yoy")
    if real is None:
        return []
    cpi = latest_matching_date(observations, "cpi_yoy", real.date) or latest_by_key(observations, "cpi_yoy")
    if cpi is None:
        return []
    value = (real.value or 0.0) + (cpi.value or 0.0)
    return [Observation("nominal_wage_yoy", real.date, real.period_label, "monthly", round(value, 3), "%", "derived:real_wage_plus_cpi", real.source_file)]


def wage_minus_cpi(observations: list[Observation]) -> list[Observation]:
    nominal = latest_by_key(observations, "nominal_wage_yoy")
    if nominal is None:
        return []
    cpi = latest_matching_date(observations, "cpi_yoy", nominal.date) or latest_by_key(observations, "cpi_yoy")
    if cpi is None:
        return []
    value = (nominal.value or 0.0) - (cpi.value or 0.0)
    return [Observation("wage_minus_cpi", nominal.date, nominal.period_label, "monthly", round(value, 3), "%pt", "derived:nominal_wage_minus_cpi", nominal.source_file)]
