from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.clean_data import Observation
from src.indicators import latest_by_key


@dataclass(frozen=True)
class AnalysisResult:
    report_date: str
    title: str
    summary_label: str
    summary_text: str
    real_growth_score: float
    inflation_pressure_score: float
    fiscal_stress_score: float
    confidence_level: str
    sections: list[dict]
    evidence: list[dict]
    metrics: list[dict]
    has_missing_data: bool
    data_coverage: str


def analyze(observations: list[Observation]) -> AnalysisResult:
    today = date.today().isoformat()
    latest = {key: latest_by_key(observations, key) for key in metric_keys()}

    real_growth_score = score_real_growth(latest)
    inflation_pressure_score = score_inflation(latest)
    fiscal_stress_score = score_fiscal(latest)
    missing = [key for key in ["real_gdp_yoy", "cpi_yoy", "real_wage_yoy", "jgb_10y_change_3m"] if latest.get(key) is None]
    confidence = "低" if len(missing) >= 2 else "中" if missing else "高"

    label = choose_label(real_growth_score, inflation_pressure_score, fiscal_stress_score, missing)
    summary = build_summary(label, latest, missing)
    evidence = build_evidence(latest, missing)
    sections = build_sections(latest, missing, label)
    metrics = build_metric_rows(latest, today)
    coverage = build_coverage(latest)

    return AnalysisResult(
        report_date=today,
        title="日本宏观政策效果监控报告",
        summary_label=label,
        summary_text=summary,
        real_growth_score=real_growth_score,
        inflation_pressure_score=inflation_pressure_score,
        fiscal_stress_score=fiscal_stress_score,
        confidence_level=confidence,
        sections=sections,
        evidence=evidence,
        metrics=metrics,
        has_missing_data=bool(missing),
        data_coverage=coverage,
    )


def metric_keys() -> list[str]:
    return [
        "real_gdp_yoy",
        "nominal_gdp_yoy",
        "gdp_deflator_yoy",
        "real_wage_yoy",
        "nominal_wage_yoy",
        "cpi_yoy",
        "wage_minus_cpi",
        "real_consumption_yoy",
        "private_investment_yoy",
        "jgb_10y_change_3m",
        "jgb_30y_change_3m",
        "usdjpy_change_3m",
    ]


def value(latest: dict[str, Observation | None], key: str) -> float | None:
    item = latest.get(key)
    return item.value if item else None


def score_real_growth(latest: dict[str, Observation | None]) -> float:
    score = 0.0
    score += 25 if positive(value(latest, "real_gdp_yoy")) else 0
    score += 25 if positive(value(latest, "real_wage_yoy")) else 0
    score += 20 if positive(value(latest, "real_consumption_yoy")) else 0
    score += 15 if positive(value(latest, "private_investment_yoy")) else 0
    score += 10 if non_negative(value(latest, "wage_minus_cpi")) else 0
    jgb = value(latest, "jgb_10y_change_3m")
    score += 5 if jgb is not None and jgb <= 50 else 0
    nominal = value(latest, "nominal_gdp_yoy")
    real = value(latest, "real_gdp_yoy")
    deflator = value(latest, "gdp_deflator_yoy")
    if nominal is not None and real is not None and deflator is not None and nominal - real > 2 and deflator > 2:
        score = min(score, 75)
    return score


def score_inflation(latest: dict[str, Observation | None]) -> float:
    score = 0.0
    if above(value(latest, "gdp_deflator_yoy"), 2.0):
        score += 20
    if above(value(latest, "cpi_yoy"), 2.0):
        score += 20
    if value(latest, "wage_minus_cpi") is not None and (value(latest, "wage_minus_cpi") or 0) < 0:
        score += 20
    if above(value(latest, "usdjpy_change_3m"), 5.0):
        score += 15
    nominal = value(latest, "nominal_gdp_yoy")
    real = value(latest, "real_gdp_yoy")
    if nominal is not None and real is not None and nominal - real > 2:
        score += 25
    return min(score, 100.0)


def score_fiscal(latest: dict[str, Observation | None]) -> float:
    score = 0.0
    if above(value(latest, "jgb_10y_change_3m"), 50):
        score += 30
    if above(value(latest, "jgb_30y_change_3m"), 75):
        score += 30
    if above(value(latest, "jgb_10y_change_3m"), 0) and above(value(latest, "jgb_30y_change_3m"), 0):
        score += 20
    if above(value(latest, "usdjpy_change_3m"), 5):
        score += 10
    if score_inflation(latest) >= 60:
        score += 10
    return min(score, 100.0)


def choose_label(real_score: float, inflation_score: float, fiscal_score: float, missing: list[str]) -> str:
    if len(missing) >= 2:
        return "数据不足，需继续观察"
    if fiscal_score >= 70:
        return "财政压力需警惕"
    if inflation_score >= 60 and real_score < 60:
        return "名义增长成分偏高"
    if real_score >= 70 and inflation_score >= 45:
        return "实际改善但名义成分偏高"
    if real_score >= 70 and inflation_score < 45:
        return "真实增长证据增强"
    if inflation_score >= 60:
        return "通胀压力上升"
    return "数据仍不明确"


def build_summary(label: str, latest: dict[str, Observation | None], missing: list[str]) -> str:
    parts = [f"当前规则判断为“{label}”。"]
    real = value(latest, "real_gdp_yoy")
    nominal = value(latest, "nominal_gdp_yoy")
    wage = value(latest, "real_wage_yoy")
    cpi = value(latest, "cpi_yoy")
    if real is not None and nominal is not None:
        parts.append(f"实际 GDP YoY 为 {real:.2f}%，名义 GDP YoY 为 {nominal:.2f}%，两者差距用于判断价格因素贡献。")
        if nominal - real > 2:
            parts.append("名义增速明显高于实际增速，说明不能把全部名义 GDP 改善直接理解为真实增长。")
    if wage is not None and cpi is not None:
        parts.append(f"实际工资 YoY 为 {wage:.2f}%，CPI YoY 为 {cpi:.2f}%，居民购买力仍是关键观察点。")
    if missing:
        parts.append(f"缺失或不足的关键指标包括：{', '.join(missing)}，相关结论需要降级处理。")
    return "".join(parts)


def build_evidence(latest: dict[str, Observation | None], missing: list[str]) -> list[dict]:
    rows: list[dict] = []
    order = 1
    nominal = value(latest, "nominal_gdp_yoy")
    real = value(latest, "real_gdp_yoy")
    if nominal is not None and real is not None:
        severity = "warning" if nominal - real > 2 else "info"
        rows.append({"category": "inflation", "text": f"名义 GDP YoY 与实际 GDP YoY 差距为 {nominal - real:.2f} 个百分点。", "metric_key": "nominal_gdp_yoy", "severity": severity, "sort_order": order})
        order += 1
    wage = value(latest, "real_wage_yoy")
    if wage is not None:
        severity = "warning" if wage < 0 else "info"
        rows.append({"category": "real_growth", "text": f"实际工资 YoY 为 {wage:.2f}%，用于判断居民购买力是否改善。", "metric_key": "real_wage_yoy", "severity": severity, "sort_order": order})
        order += 1
    jgb = value(latest, "jgb_10y_change_3m")
    if jgb is not None:
        severity = "risk" if jgb > 50 else "info"
        rows.append({"category": "fiscal", "text": f"JGB 10Y 三个月变化为 {jgb:.1f}bp。", "metric_key": "jgb_10y_change_3m", "severity": severity, "sort_order": order})
        order += 1
    for key in missing:
        rows.append({"category": "data_quality", "text": f"{key} 数据缺失或不足，相关判断需降级。", "metric_key": key, "severity": "warning", "sort_order": order})
        order += 1
    return rows


def build_sections(latest: dict[str, Observation | None], missing: list[str], label: str) -> list[dict]:
    return [
        {"section_key": "summary", "title": "总结判断", "body": build_summary(label, latest, missing), "sort_order": 1},
        {"section_key": "gdp", "title": "GDP 分析", "body": "实际 GDP 是扣除价格影响后的产出，名义 GDP 没有扣除价格变化。若名义 GDP 增速明显高于实际 GDP，同时 GDP deflator 较高，应更谨慎地把增长解释为价格推动，而不是真实产出改善。", "sort_order": 2},
        {"section_key": "wage_consumption", "title": "工资与消费", "body": "实际工资代表扣除通胀后的购买力。若实际工资仍为负，居民消费恢复通常缺少坚实基础；若民间消费同比转正且工资改善，真实增长证据才更强。", "sort_order": 3},
        {"section_key": "investment", "title": "投资与生产力", "body": "企业设备投资同比改善通常比单纯价格上涨更能支持中期真实增长。当前框架优先观察民间设备投资是否连续改善。", "sort_order": 4},
        {"section_key": "market", "title": "市场压力", "body": "JGB 长端收益率和 USDJPY 用于观察财政信任、货币压力和输入型通胀。若日元持续贬值且长端收益率快速上行，应提高对通胀税和财政压力的警惕。", "sort_order": 5},
    ]


def build_metric_rows(latest: dict[str, Observation | None], snapshot_date: str) -> list[dict]:
    rows = []
    for key in metric_keys():
        item = latest.get(key)
        if item is None:
            continue
        rows.append(
            {
                "snapshot_date": snapshot_date,
                "metric_key": key,
                "latest_value": item.value,
                "previous_value": None,
                "yoy": item.value if key.endswith("_yoy") else None,
                "change_3m": item.value if key.endswith("_change_3m") else None,
                "judgement": judgement_for(key, item.value),
                "source_coverage": item.period_label,
            }
        )
    return rows


def build_coverage(latest: dict[str, Observation | None]) -> str:
    labels = sorted({item.period_label for item in latest.values() if item is not None and item.period_label})
    return "、".join(labels[-8:])


def judgement_for(key: str, val: float | None) -> str:
    if val is None:
        return "缺失"
    if key == "wage_minus_cpi":
        return "工资跑赢 CPI" if val >= 0 else "工资落后 CPI"
    if key == "gdp_deflator_yoy":
        return "价格贡献偏高" if val > 2 else "价格压力温和"
    if key.endswith("_yoy"):
        return "同比为正" if val > 0 else "同比为负"
    if key.endswith("_change_3m"):
        return "压力明显" if val > 50 else "未触发阈值"
    return "可用"


def positive(val: float | None) -> bool:
    return val is not None and val > 0


def non_negative(val: float | None) -> bool:
    return val is not None and val >= 0


def above(val: float | None, threshold: float) -> bool:
    return val is not None and val > threshold
