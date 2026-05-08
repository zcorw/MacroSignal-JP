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

METRIC_LABELS = {
    "real_gdp_yoy": "实际 GDP 同比",
    "nominal_gdp_yoy": "名义 GDP 同比",
    "gdp_deflator_yoy": "GDP 平减指数同比",
    "real_wage_yoy": "实际工资同比",
    "nominal_wage_yoy": "名义工资同比",
    "cpi_yoy": "CPI 同比",
    "wage_minus_cpi": "工资减 CPI",
    "real_consumption_yoy": "民间消费同比",
    "private_investment_yoy": "企业设备投资同比",
    "jgb_10y_change_3m": "10年期国债收益率 3个月变化",
    "jgb_30y_change_3m": "30年期国债收益率 3个月变化",
    "usdjpy_change_3m": "美元兑日元 3个月变化",
}

METRIC_HELP = {
    "real_gdp_yoy": "扣除物价影响后的经济产出变化。正数通常说明真实产出比去年同期增加。",
    "nominal_gdp_yoy": "没有扣除物价影响的 GDP 增长。它可能来自真实产出增加，也可能来自涨价。",
    "gdp_deflator_yoy": "用 GDP 自身计算的整体价格变化。数值高时，名义 GDP 增长里价格贡献更大。",
    "real_wage_yoy": "扣除通胀后的工资变化。正数代表工资购买力改善。",
    "nominal_wage_yoy": "工资账面金额变化，未扣除通胀。本项目当前用实际工资加 CPI 做保守近似。",
    "cpi_yoy": "消费者物价指数同比。衡量居民日常购买商品和服务的价格变化。",
    "wage_minus_cpi": "名义工资增速减 CPI。正数代表工资大致跑赢物价，负数代表购买力承压。",
    "real_consumption_yoy": "扣除物价影响后的民间消费变化。用于观察居民是否真的多消费。",
    "private_investment_yoy": "企业设备投资同比。改善通常比单纯涨价更能支持中长期真实增长。",
    "jgb_10y_change_3m": "日本10年期国债收益率三个月变化，单位为基点。快速上升可能代表市场要求更高补偿。",
    "jgb_30y_change_3m": "日本30年期国债收益率三个月变化，长端利率对财政信任更敏感。",
    "usdjpy_change_3m": "美元兑日元三个月变化。上升通常代表日元贬值，可能推高进口成本。",
}


def metric_label(key: str) -> str:
    return METRIC_LABELS.get(key, key)


def metric_help(key: str) -> str:
    return METRIC_HELP.get(key, "该指标用于辅助判断日本宏观政策效果。")


def format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


templates.env.filters["metric_label"] = metric_label
templates.env.filters["metric_help"] = metric_help
templates.env.filters["format_number"] = format_number


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
