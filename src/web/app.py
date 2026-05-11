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

CHART_GUIDES = {
    "gdp_growth": [
        {
            "name": "名义 GDP YoY",
            "up": "上升代表按当前价格计算的经济规模增长更快，可能来自真实产出增加，也可能来自物价上涨。",
            "down": "下降代表账面经济规模增长放慢；如果仍高于实际 GDP，说明价格因素仍在支撑名义增长。",
            "watch": "重点和实际 GDP YoY 对比。两者差距越大，越要警惕“看起来增长、实际产出改善有限”。",
        },
        {
            "name": "实际 GDP YoY",
            "up": "上升代表扣除物价影响后，真实产出改善更明显，是判断真实增长的核心指标。",
            "down": "下降代表真实产出放慢；如果转负，说明经济实际产出比去年同期减少。",
            "watch": "如果实际 GDP 为正且连续多个季度改善，真实增长证据才更扎实。",
        },
    ],
    "wage_vs_cpi": [
        {
            "name": "实际工资 YoY",
            "up": "上升代表工资购买力改善，居民同样工资能买到更多商品和服务。",
            "down": "下降代表工资购买力变弱；若长期为负，消费恢复通常缺少基础。",
            "watch": "重点看是否稳定高于 0，而不是单月偶然转正。",
        },
        {
            "name": "CPI YoY",
            "up": "上升代表居民生活成本上涨更快，食品、能源和服务价格压力可能加大。",
            "down": "下降代表通胀压力缓和；但过低或转负也可能说明需求疲弱。",
            "watch": "如果 CPI 高于工资增长，居民实际购买力会被挤压。",
        },
    ],
    "private_consumption": [
        {
            "name": "民间消费 YoY",
            "up": "上升代表居民实际消费改善，是判断政策是否惠及家庭部门的重要信号。",
            "down": "下降代表居民消费走弱，可能来自实际工资不足、物价压力或信心下降。",
            "watch": "如果工资改善但消费没有改善，说明居民可能仍偏谨慎。",
        },
    ],
    "private_investment": [
        {
            "name": "企业设备投资 YoY",
            "up": "上升代表企业更愿意扩产、更新设备或投资生产能力，有利于中长期真实增长。",
            "down": "下降代表企业投资意愿走弱，可能说明需求预期不足或融资成本压力上升。",
            "watch": "持续为正比单季度跳升更重要，因为设备投资波动较大。",
        },
    ],
    "market_pressure": [
        {
            "name": "USDJPY",
            "up": "上升代表 1 美元能兑换更多日元，也就是日元贬值。日元贬值会推高进口能源、食品和原材料成本。",
            "down": "下降代表日元升值，进口成本压力通常缓和，但也可能压制出口企业换算收益。",
            "watch": "如果 USDJPY 上升同时 CPI 上升，要警惕输入型通胀。",
        },
        {
            "name": "JGB 10Y",
            "up": "上升代表日本长期国债收益率上行，市场要求更高利率补偿，可能反映通胀、加息或财政信任压力。",
            "down": "下降代表长期利率压力缓和，但也可能反映增长预期偏弱或避险需求。",
            "watch": "如果 10年和30年收益率都快速上升，财政压力信号更强。",
        },
    ],
}


def chart_guide(chart_key: str) -> list[dict[str, str]]:
    return CHART_GUIDES.get(chart_key, [])


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


@app.get("/charts/{chart_key}", response_class=HTMLResponse)
def chart_detail_page(request: Request, chart_key: str):
    payload = chart_payload(engine, chart_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="chart_not_found")
    return templates.TemplateResponse(request, "chart_detail.html", {"chart": payload, "guide": chart_guide(chart_key)})


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
