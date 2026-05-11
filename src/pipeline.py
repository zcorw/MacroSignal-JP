from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy import delete, insert, update
from sqlalchemy.engine import Engine

from src.analyze import analyze
from src.clean_data import Observation, clean_downloaded_files
from src.config import AppConfig
from src.fetch_data import DownloadedFile, download_all
from src.foreign_clean import (
    ForeignResidentMetric,
    ForeignResidentObservation,
    ForeignWageMetric,
    ForeignWorkerMetric,
    clean_foreign_residents,
)
from src.foreign_fetch import download_foreign_sources
from src.indicators import calculate_indicators
from src.report import to_report_payload
from src.storage import (
    foreign_resident_metrics,
    foreign_resident_observations,
    foreign_wage_metrics,
    foreign_worker_metrics,
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
    trigger = "sample" if mode == "sample" else "cron"
    logger.info("开始运行数据管道 mode=%s retry_missing=%s", mode, retry_missing)

    with engine.begin() as conn:
        run_id = conn.execute(
            insert(runs).values(started_at=started_at, status="running", trigger=trigger, message="")
        ).inserted_primary_key[0]

    try:
        if mode == "sample":
            download_results = [DownloadedFile("sample", "success", None, "2024-09", "写入内置样例数据")]
            raw_observations = sample_observations()
            foreign_observations: list[ForeignResidentObservation] = []
            foreign_metrics: list[ForeignResidentMetric] = []
            foreign_worker_metrics_items: list[ForeignWorkerMetric] = []
            foreign_wage_metrics_items: list[ForeignWageMetric] = []
        else:
            stage_started = perf_counter()
            logger.info("开始下载宏观数据")
            download_results = download_all(config)
            logger.info("宏观数据下载完成，耗时 %.1f 秒", perf_counter() - stage_started)

            stage_started = perf_counter()
            logger.info("开始下载外国人专题数据")
            download_results.extend(download_foreign_sources(config))
            logger.info("外国人专题数据下载完成，耗时 %.1f 秒", perf_counter() - stage_started)

            stage_started = perf_counter()
            logger.info("开始清洗宏观数据")
            raw_observations = clean_downloaded_files(config.paths.raw_dir, config.paths.manual_dir)
            logger.info("宏观数据清洗完成：%d 条原始观测，耗时 %.1f 秒", len(raw_observations), perf_counter() - stage_started)

        stage_started = perf_counter()
        logger.info("开始计算宏观派生指标")
        all_observations = calculate_indicators(raw_observations)
        logger.info("宏观派生指标计算完成：%d 条总观测，耗时 %.1f 秒", len(all_observations), perf_counter() - stage_started)

        if mode != "sample":
            stage_started = perf_counter()
            logger.info("开始清洗外国人专题数据；在留外国人明细文件较大，此步骤可能需要数分钟")
            (
                foreign_observations,
                foreign_metrics,
                foreign_worker_metrics_items,
                foreign_wage_metrics_items,
            ) = clean_foreign_residents(config.paths.raw_dir, all_observations)
            logger.info(
                "外国人专题数据清洗完成：在留明细 %d 条，在留指标 %d 条，劳动者指标 %d 条，工资指标 %d 条，耗时 %.1f 秒",
                len(foreign_observations),
                len(foreign_metrics),
                len(foreign_worker_metrics_items),
                len(foreign_wage_metrics_items),
                perf_counter() - stage_started,
            )

        stage_started = perf_counter()
        logger.info("开始生成宏观分析报告")
        result = analyze(all_observations)
        payload = to_report_payload(result)
        logger.info("宏观分析报告生成完成，耗时 %.1f 秒", perf_counter() - stage_started)

        stage_started = perf_counter()
        logger.info("开始写入数据库")
        persist_run(
            engine,
            int(run_id),
            all_observations,
            result.metrics,
            download_results,
            foreign_observations,
            foreign_metrics,
            foreign_worker_metrics_items,
            foreign_wage_metrics_items,
        )
        replace_report(engine, payload)
        logger.info("数据库写入完成，耗时 %.1f 秒", perf_counter() - stage_started)

        with engine.begin() as conn:
            conn.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(
                    finished_at=now_iso(),
                    status="success",
                    message=f"完成：{len(raw_observations)} 条原始观测，{len(all_observations)} 条含派生指标观测。",
                )
            )
        logger.info("数据管道运行完成")
    except Exception as exc:
        logger.exception("数据管道运行失败")
        with engine.begin() as conn:
            conn.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(finished_at=now_iso(), status="failed", message=str(exc))
            )
        raise


def persist_run(
    engine: Engine,
    run_id: int,
    observations: list[Observation],
    metrics: list[dict],
    download_results: list[DownloadedFile],
    foreign_observations: list[ForeignResidentObservation] | None = None,
    foreign_metrics_items: list[ForeignResidentMetric] | None = None,
    foreign_worker_metrics_items: list[ForeignWorkerMetric] | None = None,
    foreign_wage_metrics_items: list[ForeignWageMetric] | None = None,
) -> None:
    created_at = now_iso()
    foreign_observations = foreign_observations or []
    foreign_metrics_items = foreign_metrics_items or []
    foreign_worker_metrics_items = foreign_worker_metrics_items or []
    foreign_wage_metrics_items = foreign_wage_metrics_items or []
    logger.info(
        "准备数据库批量写入：宏观观测 %d，宏观指标 %d，在留明细 %d，在留指标 %d，劳动者指标 %d，工资指标 %d",
        len(observations),
        len(metrics),
        len(foreign_observations),
        len(foreign_metrics_items),
        len(foreign_worker_metrics_items),
        len(foreign_wage_metrics_items),
    )
    with engine.begin() as conn:
        conn.execute(delete(series_observations))
        conn.execute(delete(metric_snapshots))
        conn.execute(delete(foreign_resident_observations))
        conn.execute(delete(foreign_resident_metrics))
        conn.execute(delete(foreign_worker_metrics))
        conn.execute(delete(foreign_wage_metrics))
        logger.info("开始序列化数据库写入行")
        observation_rows = [asdict(item) | {"created_at": created_at} for item in observations]
        metric_rows = [metric | {"created_at": created_at} for metric in metrics]
        foreign_observation_rows = [asdict(item) | {"created_at": created_at} for item in foreign_observations]
        foreign_metric_rows = [asdict(item) | {"created_at": created_at} for item in foreign_metrics_items]
        foreign_worker_metric_rows = [asdict(item) | {"created_at": created_at} for item in foreign_worker_metrics_items]
        foreign_wage_metric_rows = [asdict(item) | {"created_at": created_at} for item in foreign_wage_metrics_items]
        logger.info("数据库写入行序列化完成")

        bulk_insert(conn, series_observations, observation_rows)
        bulk_insert(conn, metric_snapshots, metric_rows)
        bulk_insert(conn, foreign_resident_observations, foreign_observation_rows)
        bulk_insert(conn, foreign_resident_metrics, foreign_metric_rows)
        bulk_insert(conn, foreign_worker_metrics, foreign_worker_metric_rows)
        bulk_insert(conn, foreign_wage_metrics, foreign_wage_metric_rows)
        for item in download_results:
            conn.execute(
                insert(source_status).values(
                    run_id=run_id,
                    source_name=item.source_name,
                    status=item.status,
                    latest_data_date=item.latest_data_date,
                    downloaded_at=created_at,
                    raw_path=str(item.path) if item.path else None,
                    message=item.message,
                )
            )


def bulk_insert(conn, table, rows: list[dict], chunk_size: int = 5000) -> None:
    if not rows:
        return
    logger.info("写入表 %s：%d 行", table.name, len(rows))
    stmt = insert(table).prefix_with("OR REPLACE")
    for start in range(0, len(rows), chunk_size):
        conn.execute(stmt, rows[start : start + chunk_size])


def sample_observations() -> list[Observation]:
    return [
        Observation("nominal_gdp", "2023-09-30", "2023Q3", "quarterly", 565000, "billions_jpy", "sample", "sample"),
        Observation("nominal_gdp", "2024-09-30", "2024Q3", "quarterly", 582000, "billions_jpy", "sample", "sample"),
        Observation("real_gdp", "2023-09-30", "2023Q3", "quarterly", 548000, "billions_chained_jpy", "sample", "sample"),
        Observation("real_gdp", "2024-09-30", "2024Q3", "quarterly", 552000, "billions_chained_jpy", "sample", "sample"),
        Observation("gdp_deflator", "2023-09-30", "2023Q3", "quarterly", 103.1, "index", "sample", "sample"),
        Observation("gdp_deflator", "2024-09-30", "2024Q3", "quarterly", 105.8, "index", "sample", "sample"),
        Observation("real_private_consumption", "2023-09-30", "2023Q3", "quarterly", 290000, "billions_chained_jpy", "sample", "sample"),
        Observation("real_private_consumption", "2024-09-30", "2024Q3", "quarterly", 291000, "billions_chained_jpy", "sample", "sample"),
        Observation("real_private_investment", "2023-09-30", "2023Q3", "quarterly", 87000, "billions_chained_jpy", "sample", "sample"),
        Observation("real_private_investment", "2024-09-30", "2024Q3", "quarterly", 88000, "billions_chained_jpy", "sample", "sample"),
        Observation("real_wage_yoy", "2024-09-30", "2024-09", "monthly", -0.6, "%", "sample", "sample"),
        Observation("cpi_yoy", "2024-09-30", "2024-09", "monthly", 2.6, "%", "sample", "sample"),
        Observation("jgb_10y", "2024-06-30", "2024-06-30", "daily", 1.05, "%", "sample", "sample"),
        Observation("jgb_10y", "2024-09-30", "2024-09-30", "daily", 1.21, "%", "sample", "sample"),
        Observation("jgb_30y", "2024-06-30", "2024-06-30", "daily", 2.15, "%", "sample", "sample"),
        Observation("jgb_30y", "2024-09-30", "2024-09-30", "daily", 2.30, "%", "sample", "sample"),
        Observation("usdjpy", "2024-06-30", "2024-06-30", "daily", 152.1, "JPY/USD", "sample", "sample"),
        Observation("usdjpy", "2024-09-30", "2024-09-30", "daily", 155.8, "JPY/USD", "sample", "sample"),
    ]
