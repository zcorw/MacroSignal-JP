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

foreign_resident_observations = Table(
    "foreign_resident_observations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("date", String, nullable=False),
    Column("year", Integer, nullable=False),
    Column("month", Integer, nullable=False),
    Column("nationality", String, nullable=False),
    Column("nationality_code", String),
    Column("residence_status", String, nullable=False),
    Column("residence_status_code", String),
    Column("prefecture", String, nullable=False),
    Column("prefecture_code", String),
    Column("gender", String),
    Column("age_group", String),
    Column("age", String),
    Column("value", Integer, nullable=False),
    Column("unit", String, nullable=False),
    Column("source_name", String, nullable=False),
    Column("source_file", String, nullable=False),
    Column("created_at", String, nullable=False),
    UniqueConstraint(
        "date",
        "nationality",
        "residence_status",
        "prefecture",
        "gender",
        "age",
        "source_name",
        name="uq_foreign_resident_observation",
    ),
)

foreign_resident_metrics = Table(
    "foreign_resident_metrics",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("date", String, nullable=False),
    Column("metric_key", String, nullable=False),
    Column("dimension", String, nullable=False),
    Column("dimension_value", String, nullable=False),
    Column("value", Float),
    Column("unit", String, nullable=False),
    Column("source_name", String, nullable=False),
    Column("source_file", String, nullable=False),
    Column("created_at", String, nullable=False),
    UniqueConstraint(
        "date",
        "metric_key",
        "dimension",
        "dimension_value",
        "source_name",
        name="uq_foreign_resident_metric",
    ),
)

foreign_worker_metrics = Table(
    "foreign_worker_metrics",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("date", String, nullable=False),
    Column("metric_key", String, nullable=False),
    Column("dimension", String, nullable=False),
    Column("dimension_value", String, nullable=False),
    Column("value", Float),
    Column("unit", String, nullable=False),
    Column("source_name", String, nullable=False),
    Column("source_file", String, nullable=False),
    Column("created_at", String, nullable=False),
    UniqueConstraint(
        "date",
        "metric_key",
        "dimension",
        "dimension_value",
        "source_name",
        name="uq_foreign_worker_metric",
    ),
)

foreign_wage_metrics = Table(
    "foreign_wage_metrics",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("date", String, nullable=False),
    Column("metric_key", String, nullable=False),
    Column("dimension", String, nullable=False),
    Column("dimension_value", String, nullable=False),
    Column("value", Float),
    Column("unit", String, nullable=False),
    Column("source_name", String, nullable=False),
    Column("source_file", String, nullable=False),
    Column("created_at", String, nullable=False),
    UniqueConstraint(
        "date",
        "metric_key",
        "dimension",
        "dimension_value",
        "source_name",
        name="uq_foreign_wage_metric",
    ),
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
            "table_columns": [item["display_name"] for item, _ in values_by_series],
            "table_rows": table_rows,
            "source_note": "数据来自官方数据源或已标注的手动文件，按项目规则清洗计算。",
        }


FOREIGN_CHART_META = {
    "foreign_residents_total": {
        "title": "在留外国人总数趋势",
        "description": "观察日本在留外国人规模是否持续扩大。上升代表总人数增加，但需要结合在留资格结构判断是临时劳动力增加，还是长期定居增加。",
        "chart_type": "line",
        "source_note": "数据来自 e-Stat 在留外国人统计明细表，按国籍、在留资格、都道府县等维度汇总。",
    },
    "foreign_residents_by_nationality": {
        "title": "来源国 Top 10",
        "description": "观察主要来源国结构。某一国家占比快速上升，可能代表劳动力来源更集中；来源更分散通常代表接收结构更丰富。",
        "chart_type": "bar",
        "source_note": "人数和占比按最新一期在留外国人明细表汇总。",
    },
    "foreign_residents_by_status": {
        "title": "在留资格结构 Top 10",
        "description": "观察外国人从技能实习、特定技能等工作型资格，向永住者、定住者等长期定居型资格变化的程度。",
        "chart_type": "pie",
        "source_note": "在留资格口径来自 e-Stat 在留外国人统计明细表。",
    },
    "foreign_workers_by_industry": {
        "title": "外国人劳动者行业分布 Top 10",
        "description": "观察外国人劳动者集中在哪些行业。制造业、建设、住宿餐饮、护理等行业占比高，说明相关行业对外国劳动力依赖更明显。",
        "chart_type": "bar",
        "source_note": "数据来自厚生労働省“外国人雇用状況の届出状況”，年度 10 月末口径。",
    },
    "foreign_workers_by_prefecture": {
        "title": "外国人劳动者都道府县排名 Top 10",
        "description": "观察外国人劳动者集中在哪些地区。人数高不等于依赖度高，后续还需要结合当地总人口或就业人口计算比例。",
        "chart_type": "bar",
        "source_note": "数据来自厚生労働省“外国人雇用状況の届出状況”，年度 10 月末口径。",
    },
    "foreign_nominal_wage": {
        "title": "外国人工资水平",
        "description": "观察不同在留资格分组的外国人月度现金工资水平。工资更高通常意味着待遇更好，但不能直接等同于实际购买力改善。",
        "chart_type": "bar",
        "source_note": "数据来自 e-Stat 賃金構造基本統計調査“外国人労働者”表。当前为年度水平值，不是同比。",
    },
}


def foreign_residents_overview(engine: Engine) -> dict[str, Any]:
    with engine.connect() as conn:
        latest_date = conn.execute(
            select(func.max(foreign_resident_metrics.c.date))
        ).scalar_one_or_none()
        if latest_date is None:
            return {"available": False, "message": "还没有外国人在留数据。请先运行数据管线。"}

        metric_rows = conn.execute(
            select(foreign_resident_metrics).where(foreign_resident_metrics.c.date == latest_date)
        ).mappings().all()
        latest_metrics = [dict(row) for row in metric_rows]
        metric_lookup = {
            (row["metric_key"], row["dimension"], row["dimension_value"]): row for row in latest_metrics
        }
        total = metric_lookup.get(("foreign_residents_total", "total", "all"))
        long_term = metric_lookup.get(
            ("long_term_settlement_share", "residence_status_group", "long_term_settlement")
        )
        top_nationalities = [
            row for row in latest_metrics if row["metric_key"] == "foreign_residents_by_nationality"
        ]
        top_statuses = [
            row for row in latest_metrics if row["metric_key"] == "foreign_residents_by_status"
        ]
        top_nationalities = sorted(top_nationalities, key=lambda row: row["value"] or 0, reverse=True)
        top_statuses = sorted(top_statuses, key=lambda row: row["value"] or 0, reverse=True)

        source_status_row = conn.execute(
            select(source_status)
            .where(source_status.c.source_name == "e-Stat Foreign Residents")
            .order_by(desc(source_status.c.id))
            .limit(1)
        ).mappings().one_or_none()

        summary_label = foreign_residents_label(float(total["value"] or 0), float(long_term["value"] or 0) if long_term else None)
        summary_text = foreign_residents_summary(latest_date, total, long_term, top_nationalities, top_statuses)
        worker_latest = latest_metric_date(conn, foreign_worker_metrics)
        wage_latest = latest_metric_date(conn, foreign_wage_metrics)
        worker_metrics = metrics_for_date(conn, foreign_worker_metrics, worker_latest) if worker_latest else []
        wage_metrics = metrics_for_date(conn, foreign_wage_metrics, wage_latest) if wage_latest else []
        scores = foreign_policy_scores(latest_metrics, worker_metrics, wage_metrics)

        return {
            "available": True,
            "latest_date": latest_date,
            "worker_latest_date": worker_latest,
            "wage_latest_date": wage_latest,
            "summary_label": summary_label,
            "summary_text": summary_text,
            "scores": scores,
            "evidence": foreign_policy_evidence(total, long_term, top_nationalities, top_statuses, worker_metrics, wage_metrics, scores),
            "total": dict(total) if total else None,
            "long_term_share": dict(long_term) if long_term else None,
            "top_nationalities": top_nationalities,
            "top_statuses": top_statuses,
            "top_industries": sorted([row for row in worker_metrics if row["metric_key"] == "foreign_workers_by_industry"], key=lambda row: row["value"] or 0, reverse=True),
            "top_prefectures": sorted([row for row in worker_metrics if row["metric_key"] == "foreign_workers_by_prefecture"], key=lambda row: row["value"] or 0, reverse=True),
            "wage_groups": sorted([row for row in wage_metrics if row["metric_key"] == "foreign_nominal_wage"], key=lambda row: row["value"] or 0, reverse=True),
            "source_status": dict(source_status_row) if source_status_row else None,
            "charts": [
                foreign_residents_chart_payload(conn, "foreign_residents_total"),
                foreign_residents_chart_payload(conn, "foreign_residents_by_nationality"),
                foreign_residents_chart_payload(conn, "foreign_residents_by_status"),
                foreign_residents_chart_payload(conn, "foreign_workers_by_industry"),
                foreign_residents_chart_payload(conn, "foreign_workers_by_prefecture"),
                foreign_residents_chart_payload(conn, "foreign_nominal_wage"),
            ],
        }


def foreign_residents_label(total: float, long_term_share: float | None) -> str:
    if not total:
        return "数据仍不明确"
    if long_term_share is not None and long_term_share >= 45:
        return "长期定居型特征较强"
    if long_term_share is not None and long_term_share >= 30:
        return "劳动力接收与长期定居并存"
    return "仍需观察是否转向长期定居"


def foreign_residents_summary(
    latest_date: str,
    total: dict[str, Any] | None,
    long_term: dict[str, Any] | None,
    top_nationalities: list[dict[str, Any]],
    top_statuses: list[dict[str, Any]],
) -> str:
    total_value = int(total["value"]) if total and total["value"] is not None else None
    leader = top_nationalities[0]["dimension_value"] if top_nationalities else "未知"
    status_leader = top_statuses[0]["dimension_value"] if top_statuses else "未知"
    parts = [f"最新数据期为 {latest_date}。"]
    if total_value is not None:
        parts.append(f"在留外国人总数为 {total_value:,} 人。")
    parts.append(f"当前来源国人数最高的是 {leader}，在留资格人数最高的是 {status_leader}。")
    if long_term and long_term["value"] is not None:
        parts.append(f"长期定居型在留资格占比约 {float(long_term['value']):.1f}%。")
    parts.append("由于当前自动链路先接入最新一期数据，趋势判断需要后续补齐多期历史文件后再提高置信度。")
    return "".join(parts)


def latest_metric_date(conn: Any, table: Table) -> str | None:
    return conn.execute(select(func.max(table.c.date))).scalar_one_or_none()


def metrics_for_date(conn: Any, table: Table, date_value: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(select(table).where(table.c.date == date_value)).mappings().all()
    ]


def foreign_policy_scores(
    resident_metrics: list[dict[str, Any]],
    worker_metrics_rows: list[dict[str, Any]],
    wage_metrics_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    resident_lookup = {(row["metric_key"], row["dimension"], row["dimension_value"]): row for row in resident_metrics}
    long_term = resident_lookup.get(("long_term_settlement_share", "residence_status_group", "long_term_settlement"))
    industry_concentration = next((row for row in worker_metrics_rows if row["metric_key"] == "industry_concentration_top3"), None)
    all_wage = next(
        (
            row
            for row in wage_metrics_rows
            if row["metric_key"] == "foreign_nominal_wage" and row["dimension_value"] == "外国人労働者"
        ),
        None,
    )
    settlement_score = min(100.0, float(long_term["value"] or 0) * 2) if long_term else 30.0
    labor_dependency_score = min(100.0, float(industry_concentration["value"] or 0) * 1.4) if industry_concentration else 40.0
    wage_improvement_score = 50.0
    if all_wage and all_wage["value"] is not None:
        wage_improvement_score = 65.0 if float(all_wage["value"]) >= 275 else 45.0
    if settlement_score >= 70:
        label = "长期定居型社会倾向增强"
    elif labor_dependency_score >= 65:
        label = "仍偏劳动力补充型"
    else:
        label = "劳动力接收与定居化并存"
    confidence = "中" if worker_metrics_rows and wage_metrics_rows else "低"
    return {
        "settlement_score": settlement_score,
        "labor_dependency_score": labor_dependency_score,
        "wage_improvement_score": wage_improvement_score,
        "label": label,
        "confidence": confidence,
    }


def foreign_policy_evidence(
    total: dict[str, Any] | None,
    long_term: dict[str, Any] | None,
    top_nationalities: list[dict[str, Any]],
    top_statuses: list[dict[str, Any]],
    worker_metrics_rows: list[dict[str, Any]],
    wage_metrics_rows: list[dict[str, Any]],
    scores: dict[str, Any],
) -> list[str]:
    evidence: list[str] = []
    if total and total["value"] is not None:
        evidence.append(f"最新在留外国人总数为 {int(total['value']):,} 人，说明外国人口规模已经具有宏观观察意义。")
    if long_term and long_term["value"] is not None:
        evidence.append(f"长期定居型在留资格占比约 {float(long_term['value']):.1f}%，用于判断是否从临时接收转向长期居住。")
    if top_nationalities:
        evidence.append(f"来源国人数最高的是 {top_nationalities[0]['dimension_value']}，需要观察来源是否过度集中。")
    if top_statuses:
        evidence.append(f"人数最高的在留资格是 {top_statuses[0]['dimension_value']}，结构比总数更能说明政策性质。")
    top_industry = next((row for row in worker_metrics_rows if row["metric_key"] == "foreign_workers_by_industry"), None)
    if top_industry:
        evidence.append(f"外国人劳动者最多的行业是 {top_industry['dimension_value']}，显示行业层面的劳动力需求集中。")
    all_wage = next((row for row in wage_metrics_rows if row["metric_key"] == "foreign_nominal_wage" and row["dimension_value"] == "外国人労働者"), None)
    if all_wage:
        evidence.append(f"工资结构调查中外国人劳动者现金工资为 {float(all_wage['value']):.1f} 千日元；当前是水平值，不能直接当作同比改善。")
    evidence.append(f"综合判断为“{scores['label']}”，置信度为{scores['confidence']}；多期历史数据补齐前应保持保守。")
    return evidence


def foreign_residents_chart_payload(conn: Any, chart_key: str) -> dict[str, Any] | None:
    meta = FOREIGN_CHART_META.get(chart_key)
    if meta is None:
        return None
    if chart_key == "foreign_residents_total":
        rows = conn.execute(
            select(
                foreign_resident_metrics.c.date,
                foreign_resident_metrics.c.value,
            )
            .where(foreign_resident_metrics.c.metric_key == "foreign_residents_total")
            .where(foreign_resident_metrics.c.dimension == "total")
            .order_by(foreign_resident_metrics.c.date)
        ).mappings().all()
        dates = [row["date"] for row in rows]
        values = [row["value"] for row in rows]
        return {
            "chart_key": chart_key,
            "title": meta["title"],
            "description": meta["description"],
            "chart_type": meta["chart_type"],
            "dates": dates,
            "x_axis": dates,
            "series": [{"name": "在留外国人总数", "axis": "left", "unit": "人", "data": values}],
            "table_columns": ["在留外国人总数"],
            "table_rows": [
                {"date": row["date"], "period_label": row["date"], "values": {"在留外国人总数": row["value"]}}
                for row in rows
            ],
            "source_note": meta["source_note"],
        }

    metric_table = foreign_chart_table(chart_key)
    latest_date = conn.execute(
        select(func.max(metric_table.c.date)).where(
            metric_table.c.metric_key == chart_key
        )
    ).scalar_one_or_none()
    if latest_date is None:
        return None
    count_rows = conn.execute(
        select(metric_table)
        .where(metric_table.c.metric_key == chart_key)
        .where(metric_table.c.date == latest_date)
        .order_by(desc(metric_table.c.value))
    ).mappings().all()
    share_rows = conn.execute(
        select(metric_table)
        .where(metric_table.c.metric_key == f"{chart_key}_share")
        .where(metric_table.c.date == latest_date)
    ).mappings().all()
    share_by_value = {row["dimension_value"]: row["value"] for row in share_rows}
    labels = [row["dimension_value"] for row in count_rows]
    values = [row["value"] for row in count_rows]
    value_label = "工资" if chart_key == "foreign_nominal_wage" else "人数"
    value_unit = "千日元" if chart_key == "foreign_nominal_wage" else "人"
    table_columns = [value_label] if not share_rows else [value_label, "占比"]
    table_rows = [
        {
            "date": latest_date,
            "period_label": row["dimension_value"],
            "values": {
                value_label: row["value"],
                "占比": share_by_value.get(row["dimension_value"]),
            },
        }
        for row in count_rows
    ]
    return {
        "chart_key": chart_key,
        "title": meta["title"],
        "description": meta["description"],
        "chart_type": meta["chart_type"],
        "dates": [latest_date],
        "x_axis": labels,
        "series": [{"name": value_label, "axis": "left", "unit": value_unit, "data": values}],
        "table_columns": table_columns,
        "table_rows": table_rows,
        "source_note": meta["source_note"],
    }


def foreign_chart_table(chart_key: str) -> Table:
    if chart_key.startswith("foreign_workers_") or chart_key == "industry_concentration_top3":
        return foreign_worker_metrics
    if chart_key.startswith("foreign_nominal_wage") or chart_key.startswith("foreign_wage"):
        return foreign_wage_metrics
    return foreign_resident_metrics
