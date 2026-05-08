# 官方数据源自动化下载测试

测试日期：2026-05-08  
本地目录：`data/raw/source_tests/`

## 测试范围

已按需求列表测试以下官方入口：

- ESRI Quarterly Estimates of GDP
- e-Stat National Accounts / GDP
- e-Stat Monthly Labour Survey
- e-Stat Consumer Price Index
- 总务省统计局 CPI
- 财务省 JGB / 国债利率数据
- 日本银行 BOJ 统计数据

## 已下载到本地的样例文件

### 页面快照

- `data/raw/source_tests/pages/esri_gdp.html`
- `data/raw/source_tests/pages/esri_gdp_timeseries.html`
- `data/raw/source_tests/pages/estat_gdp.html`
- `data/raw/source_tests/pages/estat_cpi_files.html`
- `data/raw/source_tests/pages/estat_cpi_2020base_page1.html`
- `data/raw/source_tests/pages/estat_cpi_2026_03.html`
- `data/raw/source_tests/pages/estat_labour.html`
- `data/raw/source_tests/pages/estat_labour_query_wage_dataset.html`
- `data/raw/source_tests/pages/estat_labour_query_real_wage_dataset.html`
- `data/raw/source_tests/pages/stat_cpi.html`
- `data/raw/source_tests/pages/mof_jgb.html`
- `data/raw/source_tests/pages/mof_interest_rate.html`
- `data/raw/source_tests/pages/boj_statistics.html`
- `data/raw/source_tests/pages/boj_flat_download.html`
- `data/raw/source_tests/pages/boj_fx_daily.html`
- `data/raw/source_tests/pages/boj_fx_list.html`

### 数据文件

- `data/raw/source_tests/downloads/esri_gaku-mk2542_nominal_sa.csv`
- `data/raw/source_tests/downloads/esri_gaku-jk2542_real_sa.csv`
- `data/raw/source_tests/downloads/esri_def-qk2542_deflator_sa.csv`
- `data/raw/source_tests/downloads/estat_gdp_000040385257.csv`
- `data/raw/source_tests/downloads/estat_cpi_000040444343.xlsx`
- `data/raw/source_tests/downloads/estat_labour_nominal_wage_000032189720.xls`
- `data/raw/source_tests/downloads/estat_labour_real_wage_000040277086.xlsx`
- `data/raw/source_tests/downloads/stat_cpi_2020base-list.xlsx`
- `data/raw/source_tests/downloads/stat_cpi_2020base-list.pdf`
- `data/raw/source_tests/downloads/mof_jgb_current.csv`
- `data/raw/source_tests/downloads/mof_jgb_historical.csv`
- `data/raw/source_tests/downloads/boj_cgpi_m_en.zip`

## 自动化可行性结论

| 数据源 | 自动化结论 | 说明 |
| --- | --- | --- |
| ESRI GDP | 可自动化 | 英文入口页能解析最新 `Time series table`，二级页面列出大量 CSV。CSV 可直接下载，但内容编码偏日文环境，后续应按 CP932/Shift-JIS 优先读取。 |
| e-Stat GDP | 可自动化 | 指定 `statInfId=000040385257` 可通过 `file-download` 直接下载 CSV，无需 API key。 |
| e-Stat CPI | 可自动化，但需要筛选规则 | CPI 入口需要逐层筛选 `toukei`、`tstat`、年月和数据表；最终 `statInfId` 的 Excel 文件可直接下载。需要在配置中固定目标表或实现页面解析。 |
| 总务省统计局 CPI | 部分可自动化 | 入口页可下载说明性 Excel/PDF。正式指数数据更适合走 e-Stat 的 CPI 文件，统计局页面可作为来源说明和备用入口。 |
| e-Stat Monthly Labour Survey | 可自动化，但需要筛选规则 | 名义工资、实际工资等表可通过搜索页找到 `statInfId`，Excel 可直接下载。需要为首版固定“现金給与総額”“実質賃金指数”等目标表。 |
| 财务省 JGB 利率 | 可自动化 | 当前月和历史 JGB 利率 CSV 可直接下载，包含 1Y 到 40Y，到 10Y/20Y/30Y 的需求可直接覆盖。 |
| BOJ 统计 | 部分可自动化 | BOJ flat files 可下载 ZIP，例如 CGPI。外汇 USDJPY 的长期序列指向 BOJ Time-Series Data Search；网页只列近 70 个营业日 PDF，长期 CSV/API 仍需进一步确认。 |

## 推荐首版数据接入策略

1. GDP：优先使用 ESRI CSV；e-Stat GDP 作为交叉验证或备用。
2. CPI：优先使用 e-Stat CPI 2020-base 月报 Excel；总务省页面作为说明来源。
3. 工资：使用 e-Stat Monthly Labour Survey Excel，首版固定名义工资和实际工资核心表。
4. JGB：直接使用财务省 `jgbcme_all.csv` 历史数据。
5. USDJPY：首版建议提供两条路径：
   - 自动抓取 BOJ 近 70 个营业日 PDF/页面作为官方短期数据来源；
   - 长期序列暂留手动文件导入，或在后续确认 BOJ Time-Series Data Search 的稳定下载接口后自动化。

## 需要后续确认或设计的点

- e-Stat CPI 和 Monthly Labour Survey 的具体目标表需要固定，避免每次运行抓到不同 `statInfId`。
- ESRI GDP CSV 需要统一编码处理，建议读取时依次尝试 `utf-8-sig`、`cp932`。
- BOJ USDJPY 长期数据是否必须只用官方 BOJ；若允许非官方镜像或市场数据 API，自动化会简单很多，但会偏离“优先官方数据源”约束。
- e-Stat API 页面明确提示 API 请求需要 application ID；首版应优先使用无 key 的 `file-download` 路径。

## 测试命令摘要

- 入口页下载：`curl -L -A "Mozilla/5.0 MacroSignal-JP source probe" ...`
- e-Stat 文件下载：`https://www.e-stat.go.jp/.../stat-search/file-download?statInfId=...&fileKind=...`
- 财务省 JGB 历史数据：`https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv`
