from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import load_config
from src.storage import (
    chart_payload,
    foreign_residents_chart_payload,
    foreign_residents_overview,
    get_engine,
    get_report,
    latest_report,
    list_reports,
    list_sources,
)

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


FOREIGN_CHART_GUIDES = {
    "foreign_residents_total": [
        {
            "name": "在留外国人总数",
            "up": "上升代表日本境内持有在留资格的外国人总数增加，通常说明外国人口规模扩大。",
            "down": "下降可能来自离境增加、签证政策变化、劳动力需求下降，或统计时间点差异。",
            "watch": "只看总数不够，还要看在留资格结构。总数增加但技能实习占比过高，更像劳动力短缺补充；永住者、定住者占比上升，才更接近长期定居社会。",
        }
    ],
    "foreign_residents_by_nationality": [
        {
            "name": "来源国人数和占比",
            "up": "某一国家人数或占比上升，代表该来源国在日本外国人结构中的重要性提高。",
            "down": "占比下降不一定代表人数减少，也可能只是其他来源国增长更快。",
            "watch": "如果 Top 1 或 Top 3 来源国占比过高，日本的外国劳动力和人口来源会更集中，受单一国家政策、汇率和就业偏好的影响更大。",
        }
    ],
    "foreign_residents_by_status": [
        {
            "name": "在留资格结构",
            "up": "永住者、定住者、日本人配偶者等占比上升，说明长期居住和家庭定居特征增强；特定技能上升说明正式劳动力接收扩大。",
            "down": "技能实习占比下降可能代表旧式临时劳动力制度弱化，但需要看特定技能是否接上。",
            "watch": "重点比较技能实习、特定技能、技术人文国际业务、永住者和定住者。它们分别对应临时劳动力、正式工作签证、高技能/白领就业和长期定居。",
        }
    ],
    "foreign_workers_by_industry": [
        {
            "name": "行业分布",
            "up": "某行业人数上升或占比高，代表该行业更依赖外国劳动力补充。",
            "down": "某行业占比下降可能代表需求减弱，也可能只是其他行业吸收外国劳动者更快。",
            "watch": "制造业、建设、住宿餐饮、护理相关行业尤其重要。行业集中度高时，政策变化会更直接影响这些行业。",
        }
    ],
    "foreign_workers_by_prefecture": [
        {
            "name": "地区排名",
            "up": "某都道府县人数高，说明当地吸收外国劳动者规模大。",
            "down": "人数下降可能代表当地需求变化、迁移变化或企业雇用变化。",
            "watch": "人数排名不是依赖度排名。更严格的依赖度需要除以当地总就业人口或总人口，后续阶段可继续细化。",
        }
    ],
    "foreign_nominal_wage": [
        {
            "name": "名义工资水平",
            "up": "工资水平更高通常代表待遇较好，但如果物价涨得更快，实际购买力仍可能没有改善。",
            "down": "工资水平较低的群体更容易受到通胀和生活成本上升冲击。",
            "watch": "当前表是年度工资水平，不是同比增速。判断改善需要连续多年同口径数据。",
        }
    ],
}


def foreign_chart_guide(chart_key: str) -> list[dict[str, str]]:
    return FOREIGN_CHART_GUIDES.get(chart_key, [])


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


@app.get("/foreign-residents", response_class=HTMLResponse)
def foreign_residents_page(request: Request):
    return templates.TemplateResponse(
        request,
        "foreign_residents.html",
        {"overview": foreign_residents_overview(engine)},
    )


@app.get("/charts/{chart_key}", response_class=HTMLResponse)
def chart_detail_page(request: Request, chart_key: str):
    payload = chart_payload(engine, chart_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="chart_not_found")
    return templates.TemplateResponse(request, "chart_detail.html", {"chart": payload, "guide": chart_guide(chart_key)})


@app.get("/foreign-residents/charts/{chart_key}", response_class=HTMLResponse)
def foreign_chart_detail_page(request: Request, chart_key: str):
    with engine.connect() as conn:
        payload = foreign_residents_chart_payload(conn, chart_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="chart_not_found")
    return templates.TemplateResponse(
        request,
        "chart_detail.html",
        {
            "chart": payload,
            "guide": foreign_chart_guide(chart_key),
            "back_href": "/foreign-residents",
            "back_label": "返回外国人趋势",
            "api_base": "/api/foreign-residents/charts",
        },
    )


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


@app.get("/api/foreign-residents")
def api_foreign_residents():
    return foreign_residents_overview(engine)


@app.get("/api/foreign-residents/charts/{chart_key}")
def api_foreign_chart(chart_key: str):
    with engine.connect() as conn:
        payload = foreign_residents_chart_payload(conn, chart_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="chart_not_found")
    return payload
