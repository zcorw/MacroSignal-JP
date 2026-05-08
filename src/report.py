from __future__ import annotations

from datetime import datetime

from src.analyze import AnalysisResult


def to_report_payload(result: AnalysisResult) -> dict:
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "report_date": result.report_date,
        "report": {
            "report_date": result.report_date,
            "title": result.title,
            "summary_label": result.summary_label,
            "summary_text": result.summary_text,
            "created_at": created_at,
            "data_coverage": result.data_coverage,
            "has_missing_data": result.has_missing_data,
            "exported_markdown_path": None,
        },
        "scores": {
            "real_growth_score": result.real_growth_score,
            "inflation_pressure_score": result.inflation_pressure_score,
            "fiscal_stress_score": result.fiscal_stress_score,
            "confidence_level": result.confidence_level,
        },
        "sections": result.sections,
        "evidence": result.evidence,
        "metrics": result.metrics,
    }
