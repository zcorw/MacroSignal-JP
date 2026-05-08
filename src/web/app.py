from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import load_config
from src.storage import chart_payload, get_engine, get_report, latest_report, list_reports, list_sources

config = load_config()
engine = get_engine(config.paths.database)

app = FastAPI(title=config.raw["web"]["title"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    bundle = latest_report(engine)
    return templates.TemplateResponse(request, "index.html", {"bundle": bundle})


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    return templates.TemplateResponse(request, "reports.html", {"reports": list_reports(engine)})


@app.get("/reports/{report_id}", response_class=HTMLResponse)
def report_detail(request: Request, report_id: int):
    bundle = get_report(engine, report_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return templates.TemplateResponse(request, "report_detail.html", {"bundle": bundle})


@app.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request):
    return templates.TemplateResponse(request, "sources.html", {"sources": list_sources(engine)})


@app.get("/api/latest")
def api_latest():
    return latest_report(engine) or {"report": None, "scores": None, "sections": [], "evidence": [], "metrics": []}


@app.get("/api/reports")
def api_reports():
    return {"reports": list_reports(engine)}


@app.get("/api/reports/{report_id}")
def api_report_detail(report_id: int):
    bundle = get_report(engine, report_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return bundle


@app.get("/api/sources")
def api_sources():
    return {"sources": list_sources(engine)}


@app.get("/api/charts/{chart_key}")
def api_chart(chart_key: str):
    payload = chart_payload(engine, chart_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="图表不存在")
    return payload
