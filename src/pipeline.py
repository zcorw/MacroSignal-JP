from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, insert

from src.config import AppConfig
from src.storage import (
    get_engine,
    init_db,
    metric_snapshots,
    replace_report,
    runs,
    series_observations,
    source_status,
)

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_pipeline(config: AppConfig, mode: str = "normal", retry_missing: bool = False) -> None:
    init_db(config.paths.database)
    engine = get_engine(config.paths.database)
    started_at = now_iso()
    logger.info("开始运行数据管道 mode=%s retry_missing=%s", mode, retry_missing)

    with engine.begin() as conn:
        run_id = conn.execute(
            insert(runs).values(started_at=started_at, status="success", trigger="manual" if mode == "sample" else "cron", message="")
        ).inserted_primary_key[0]

    if mode == "sample":
        load_sample_dataset(engine, int(run_id))
    else:
        # Starter package 先写入结构化失败状态，真实下载模块在后续迭代补齐。
        with engine.begin() as conn:
            conn.execute(
                insert(source_status).values(
                    run_id=run_id,
                    source_name="real_download_pipeline",
                    status="partial_success",
                    latest_data_date=None,
                    downloaded_at=now_iso(),
                    raw_path=None,
                    message="Starter package 已就绪；真实下载清洗模块待逐数据源实现。",
                )
            )
    logger.info("数据管道运行完成")


def load_sample_dataset(engine, run_id: int) -> None:
    created_at = now_iso()
    observations = [
        ("nominal_gdp_yoy", "2024-03-31", "2024Q1", "quarterly", 3.1, "%"),
        ("nominal_gdp_yoy", "2024-06-30", "2024Q2", "quarterly", 3.4, "%"),
        ("nominal_gdp_yoy", "2024-09-30", "2024Q3", "quarterly", 3.0, "%"),
        ("real_gdp_yoy", "2024-03-31", "2024Q1", "quarterly", 0.8, "%"),
        ("real_gdp_yoy", "2024-06-30", "2024Q2", "quarterly", 1.0, "%"),
        ("real_gdp_yoy", "2024-09-30", "2024Q3", "quarterly", 0.7, "%"),
        ("real_wage_yoy", "2024-07-31", "2024-07", "monthly", -1.0, "%"),
        ("real_wage_yoy", "2024-08-31", "2024-08", "monthly", -0.8, "%"),
        ("real_wage_yoy", "2024-09-30", "2024-09", "monthly", -0.6, "%"),
        ("cpi_yoy", "2024-07-31", "2024-07", "monthly", 2.8, "%"),
        ("cpi_yoy", "2024-08-31", "2024-08", "monthly", 2.7, "%"),
        ("cpi_yoy", "2024-09-30", "2024-09", "monthly", 2.6, "%"),
        ("real_consumption_yoy", "2024-03-31", "2024Q1", "quarterly", -0.3, "%"),
        ("real_consumption_yoy", "2024-06-30", "2024Q2", "quarterly", 0.2, "%"),
        ("real_consumption_yoy", "2024-09-30", "2024Q3", "quarterly", 0.4, "%"),
        ("private_investment_yoy", "2024-03-31", "2024Q1", "quarterly", 0.5, "%"),
        ("private_investment_yoy", "2024-06-30", "2024Q2", "quarterly", 0.9, "%"),
        ("private_investment_yoy", "2024-09-30", "2024Q3", "quarterly", 0.6, "%"),
        ("usdjpy", "2024-07-31", "2024-07", "monthly", 152.1, "JPY/USD"),
        ("usdjpy", "2024-08-31", "2024-08", "monthly", 154.3, "JPY/USD"),
        ("usdjpy", "2024-09-30", "2024-09", "monthly", 155.8, "JPY/USD"),
        ("jgb_10y", "2024-07-31", "2024-07", "monthly", 1.05, "%"),
        ("jgb_10y", "2024-08-31", "2024-08", "monthly", 1.16, "%"),
        ("jgb_10y", "2024-09-30", "2024-09", "monthly", 1.21, "%"),
    ]
    metrics = [
        ("2026-05-08", "real_gdp_yoy", 0.7, 1.0, 0.7, None, "偏弱改善"),
        ("2026-05-08", "nominal_gdp_yoy", 3.0, 3.4, 3.0, None, "名义增长偏高"),
        ("2026-05-08", "real_wage_yoy", -0.6, -0.8, -0.6, None, "仍承压"),
        ("2026-05-08", "cpi_yoy", 2.6, 2.7, 2.6, None, "仍偏高"),
        ("2026-05-08", "wage_minus_cpi", -3.2, -3.5, None, None, "购买力承压"),
        ("2026-05-08", "jgb_10y_change_3m", 16.0, None, None, 16.0, "未触发压力阈值"),
    ]
    report_payload = {
        "report_date": "2026-05-08",
        "report": {
            "report_date": "2026-05-08",
            "title": "日本宏观政策效果监控报告",
            "summary_label": "名义增长成分偏高",
            "summary_text": "当前数据更支持名义增长成分偏高的解释，真实增长证据仍需继续观察。实际工资尚未稳定转正，居民购买力改善证据不足。",
            "created_at": created_at,
            "data_coverage": "样例数据：GDP 2024Q3，CPI/工资 2024-09，JGB/USDJPY 2024-09",
            "has_missing_data": True,
            "exported_markdown_path": None,
        },
        "scores": {
            "real_growth_score": 46,
            "inflation_pressure_score": 68,
            "fiscal_stress_score": 54,
            "confidence_level": "中",
        },
        "sections": [
            {"section_key": "summary", "title": "总结判断", "body": "当前更像名义增长成分偏高，实际增长证据还不够强。", "sort_order": 1},
            {"section_key": "gdp", "title": "GDP 分析", "body": "名义 GDP 与实际 GDP 的差距提示价格因素贡献较多。", "sort_order": 2},
            {"section_key": "wage", "title": "工资与消费", "body": "实际工资仍为负，说明居民购买力仍承压。", "sort_order": 3},
        ],
        "evidence": [
            {"category": "inflation", "text": "名义 GDP 增速高于实际 GDP，通胀贡献偏高。", "metric_key": "nominal_gdp_yoy", "severity": "warning", "sort_order": 1},
            {"category": "real_growth", "text": "实际工资仍未稳定转正。", "metric_key": "real_wage_yoy", "severity": "warning", "sort_order": 2},
            {"category": "fiscal", "text": "JGB 10Y 三个月变化未触发明显压力阈值。", "metric_key": "jgb_10y_change_3m", "severity": "info", "sort_order": 3},
        ],
    }

    with engine.begin() as conn:
        conn.execute(delete(series_observations))
        conn.execute(delete(metric_snapshots))
        for row in observations:
            conn.execute(
                insert(series_observations).values(
                    series_key=row[0],
                    date=row[1],
                    period_label=row[2],
                    frequency=row[3],
                    value=row[4],
                    unit=row[5],
                    source_name="sample",
                    source_file="sample",
                    released_at="2026-05-08",
                    created_at=created_at,
                )
            )
        for row in metrics:
            conn.execute(
                insert(metric_snapshots).values(
                    snapshot_date=row[0],
                    metric_key=row[1],
                    latest_value=row[2],
                    previous_value=row[3],
                    yoy=row[4],
                    change_3m=row[5],
                    judgement=row[6],
                    source_coverage="sample",
                    created_at=created_at,
                )
            )
        for source_name in ["ESRI GDP", "e-Stat CPI", "e-Stat Monthly Labour Survey", "MOF JGB", "BOJ / USDJPY"]:
            conn.execute(
                insert(source_status).values(
                    run_id=run_id,
                    source_name=source_name,
                    status="success" if source_name != "BOJ / USDJPY" else "partial_success",
                    latest_data_date="2024-09",
                    downloaded_at=created_at,
                    raw_path="sample",
                    message="样例数据已写入。" if source_name != "BOJ / USDJPY" else "样例短期数据；长期序列可用手动 CSV 兜底。",
                )
            )
    replace_report(engine, report_payload)
