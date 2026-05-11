from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    desc,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

runs = Table(
    "runs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("started_at", String, nullable=False),
    Column("finished_at", String),
    Column("status", String, nullable=False),
    Column("trigger", String, nullable=False),
    Column("message", Text),
)

source_status = Table(
    "source_status",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", Integer, ForeignKey("runs.id"), nullable=False),
    Column("source_name", String, nullable=False),
    Column("status", String, nullable=False),
    Column("latest_data_date", String),
    Column("downloaded_at", String),
    Column("raw_path", String),
    Column("message", Text),
)

series_observations = Table(
    "series_observations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("series_key", String, nullable=False),
    Column("date", String, nullable=False),
    Column("period_label", String),
    Column("frequency", String, nullable=False),
    Column("value", Float),
    Column("unit", String),
    Column("source_name", String, nullable=False),
    Column("source_file", String),
    Column("released_at", String),
    Column("created_at", String, nullable=False),
    UniqueConstraint("series_key", "date", "source_name", name="uq_series_date_source"),
)

metric_snapshots = Table(
    "metric_snapshots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("snapshot_date", String, nullable=False),
    Column("metric_key", String, nullable=False),
    Column("latest_value", Float),
    Column("previous_value", Float),
    Column("yoy", Float),
    Column("change_3m", Float),
    Column("judgement", String),
    Column("source_coverage", Text),
    Column("created_at", String, nullable=False),
    UniqueConstraint("snapshot_date", "metric_key", name="uq_snapshot_metric"),
)

analysis_reports = Table(
    "analysis_reports",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("report_date", String, nullable=False, unique=True),
    Column("title", String, nullable=False),
    Column("summary_label", String, nullable=False),
    Column("summary_text", Text, nullable=False),
    Column("created_at", String, nullable=False),
    Column("data_coverage", Text),
    Column("has_missing_data", Boolean, nullable=False, default=False),
    Column("exported_markdown_path", String),
)

report_sections = Table(
    "report_sections",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("report_id", Integer, ForeignKey("analysis_reports.id"), nullable=False),
    Column("section_key", String, nullable=False),
    Column("title", String, nullable=False),
    Column("body", Text, nullable=False),
    Column("sort_order", Integer, nullable=False),
    UniqueConstraint("report_id", "section_key", name="uq_report_section"),
)

report_evidence = Table(
    "report_evidence",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("report_id", Integer, ForeignKey("analysis_reports.id"), nullable=False),
    Column("category", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("metric_key", String),
    Column("severity", String),
    Column("sort_order", Integer, nullable=False),
)

scores = Table(
    "scores",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("report_id", Integer, ForeignKey("analysis_reports.id"), nullable=False, unique=True),
    Column("real_growth_score", Float),
    Column("inflation_pressure_score", Float),
    Column("fiscal_stress_score", Float),
    Column("confidence_level", String, nullable=False),
)

chart_definitions = Table(
    "chart_definitions",
    metadata,
    Column("chart_key", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("description", Text),
    Column("default_range", String),
    Column("chart_type", String, nullable=False),
    Column("sort_order", Integer, nullable=False),
)

chart_series = Table(
    "chart_series",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("chart_key", String, ForeignKey("chart_definitions.chart_key"), nullable=False),
    Column("series_key", String, nullable=False),
    Column("display_name", String, nullable=False),
    Column("unit", String),
    Column("axis", String, nullable=False),
    Column("sort_order", Integer, nullable=False),
    UniqueConstraint("chart_key", "series_key", name="uq_chart_series"),
)


def get_engine(db_path: Path | str) -> Engine:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", future=True)


def init_db(db_path: Path | str) -> None:
    engine = get_engine(db_path)
    metadata.create_all(engine)
    seed_chart_definitions(engine)


def seed_chart_definitions(engine: Engine) -> None:
    definitions = [
        ("gdp_growth", "名义 GDP YoY vs 实际 GDP YoY", "比较名义增长和扣除价格后的真实增长。", "10y", "line", 1),
        ("wage_vs_cpi", "实际工资 YoY vs CPI YoY", "观察工资购买力是否改善。", "10y", "line", 2),
        ("private_consumption", "民间消费 YoY", "观察居民消费恢复情况。", "10y", "line", 3),
        ("private_investment", "企业设备投资 YoY", "观察企业设备投资意愿。", "10y", "line", 4),
        ("market_pressure", "USDJPY 与 JGB 10Y", "观察弱日元和长期利率压力。", "5y", "dual_axis_line", 5),
    ]
    series = [
        ("gdp_growth", "nominal_gdp_yoy", "名义 GDP YoY", "%", "left", 1),
        ("gdp_growth", "real_gdp_yoy", "实际 GDP YoY", "%", "left", 2),
        ("wage_vs_cpi", "real_wage_yoy", "实际工资 YoY", "%", "left", 1),
        ("wage_vs_cpi", "cpi_yoy", "CPI YoY", "%", "left", 2),
        ("private_consumption", "real_consumption_yoy", "民间消费 YoY", "%", "left", 1),
        ("private_investment", "private_investment_yoy", "企业设备投资 YoY", "%", "left", 1),
        ("market_pressure", "usdjpy", "USDJPY", "JPY/USD", "left", 1),
        ("market_pressure", "jgb_10y", "JGB 10Y", "%", "right", 2),
    ]
    with engine.begin() as conn:
        for row in definitions:
            conn.execute(
                insert(chart_definitions)
                .values(
                    chart_key=row[0],
                    title=row[1],
                    description=row[2],
                    default_range=row[3],
                    chart_type=row[4],
                    sort_order=row[5],
                )
                .prefix_with("OR REPLACE")
            )
        conn.execute(delete(chart_series))
        for row in series:
            conn.execute(
                insert(chart_series).values(
                    chart_key=row[0],
                    series_key=row[1],
                    display_name=row[2],
                    unit=row[3],
                    axis=row[4],
                    sort_order=row[5],
                )
            )


def replace_report(engine: Engine, payload: dict[str, Any]) -> int:
    with engine.begin() as conn:
        existing = conn.execute(
            select(analysis_reports.c.id).where(analysis_reports.c.report_date == payload["report_date"])
        ).scalar_one_or_none()
        if existing is not None:
            conn.execute(delete(report_evidence).where(report_evidence.c.report_id == existing))
            conn.execute(delete(report_sections).where(report_sections.c.report_id == existing))
            conn.execute(delete(scores).where(scores.c.report_id == existing))
            conn.execute(delete(analysis_reports).where(analysis_reports.c.id == existing))

        report_id = conn.execute(insert(analysis_reports).values(**payload["report"])).inserted_primary_key[0]
        conn.execute(insert(scores).values(report_id=report_id, **payload["scores"]))
        for section in payload["sections"]:
            conn.execute(insert(report_sections).values(report_id=report_id, **section))
        for evidence in payload["evidence"]:
            conn.execute(insert(report_evidence).values(report_id=report_id, **evidence))
        return int(report_id)


def latest_report(engine: Engine) -> dict[str, Any] | None:
    with engine.connect() as conn:
        report = conn.execute(select(analysis_reports).order_by(desc(analysis_reports.c.report_date)).limit(1)).mappings().first()
        if report is None:
            return None
        return report_bundle(conn, int(report["id"]))


def report_bundle(conn: Any, report_id: int) -> dict[str, Any]:
    report = conn.execute(select(analysis_reports).where(analysis_reports.c.id == report_id)).mappings().one()
    score = conn.execute(select(scores).where(scores.c.report_id == report_id)).mappings().one_or_none()
    sections = conn.execute(
        select(report_sections).where(report_sections.c.report_id == report_id).order_by(report_sections.c.sort_order)
    ).mappings().all()
    evidence = conn.execute(
        select(report_evidence).where(report_evidence.c.report_id == report_id).order_by(report_evidence.c.sort_order)
    ).mappings().all()
    metrics = conn.execute(
        select(metric_snapshots).where(metric_snapshots.c.snapshot_date == report["report_date"]).order_by(metric_snapshots.c.metric_key)
    ).mappings().all()
    return {
        "report": dict(report),
        "scores": dict(score) if score else None,
        "sections": [dict(row) for row in sections],
        "evidence": [dict(row) for row in evidence],
        "metrics": [dict(row) for row in metrics],
    }


def list_reports(engine: Engine) -> list[dict[str, Any]]:
    stmt = (
        select(
            analysis_reports.c.id,
            analysis_reports.c.report_date,
            analysis_reports.c.summary_label,
            analysis_reports.c.summary_text,
            analysis_reports.c.data_coverage,
            analysis_reports.c.has_missing_data,
            scores.c.real_growth_score,
            scores.c.inflation_pressure_score,
            scores.c.fiscal_stress_score,
        )
        .join(scores, scores.c.report_id == analysis_reports.c.id, isouter=True)
        .order_by(desc(analysis_reports.c.report_date))
    )
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings().all()]


def get_report(engine: Engine, report_id: int) -> dict[str, Any] | None:
    with engine.connect() as conn:
        exists = conn.execute(select(analysis_reports.c.id).where(analysis_reports.c.id == report_id)).scalar_one_or_none()
        if exists is None:
            return None
        return report_bundle(conn, report_id)


def list_sources(engine: Engine) -> list[dict[str, Any]]:
    subq = select(func.max(source_status.c.id).label("id")).group_by(source_status.c.source_name).subquery()
    stmt = select(source_status).where(source_status.c.id.in_(select(subq.c.id))).order_by(source_status.c.source_name)
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(stmt).mappings().all()]


def chart_payload(engine: Engine, chart_key: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        chart = conn.execute(select(chart_definitions).where(chart_definitions.c.chart_key == chart_key)).mappings().one_or_none()
        if chart is None:
            return None
        configured = conn.execute(
            select(chart_series).where(chart_series.c.chart_key == chart_key).order_by(chart_series.c.sort_order)
        ).mappings().all()
        label_by_date: dict[str, str] = {}
        values_by_series: list[tuple[dict[str, Any], dict[str, float | None]]] = []
        for item in configured:
            rows = conn.execute(
                select(series_observations.c.period_label, series_observations.c.date, series_observations.c.value)
                .where(series_observations.c.series_key == item["series_key"])
                .order_by(series_observations.c.date)
            ).mappings().all()
            series_values: dict[str, float | None] = {}
            for row in rows:
                date_key = str(row["date"])
                label_by_date[date_key] = str(row["period_label"] or row["date"])
                series_values[date_key] = row["value"]
            values_by_series.append((dict(item), series_values))

        dates = sorted(label_by_date)
        labels = [label_by_date[date_key] for date_key in dates]
        series_payload = []
        for item, series_values in values_by_series:
            series_payload.append(
                {
                    "name": item["display_name"],
                    "axis": item["axis"],
                    "unit": item["unit"],
                    "data": [series_values.get(date_key) for date_key in dates],
                }
            )
        table_rows = []
        for date_key, label in zip(dates, labels):
            values = {}
            for item, series_values in values_by_series:
                values[item["display_name"]] = series_values.get(date_key)
            table_rows.append({"date": date_key, "period_label": label, "values": values})
        return {
            "chart_key": chart["chart_key"],
            "title": chart["title"],
            "description": chart["description"],
            "chart_type": chart["chart_type"],
            "dates": dates,
            "x_axis": labels,
            "series": series_payload,
            "table_rows": table_rows,
            "source_note": "数据来自官方数据源或已标注的手动文件，按项目规则清洗计算。",
        }
