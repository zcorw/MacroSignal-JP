# Stage 7. API 与数据约定

## 已确认事实

- 清洗后的结构化数据必须保存到 SQLite。
- Web UI 直接从数据库动态生成页面。
- 图表使用 ECharts 在浏览器端动态绘制。
- Web UI 公开只读，不提供写操作接口。
- Markdown 仅作为可选归档，不作为页面主要来源。

## 已确认决策

- 数据库存储标准化时序数据、指标快照、评分、证据、报告段落、数据源状态和运行记录。
- Web 页面使用 Jinja2 渲染基础 HTML。
- 图表数据通过只读 JSON API 提供给 ECharts。
- 所有指标名和序列名使用英文 snake_case，UI 展示时再映射为中文。
- 日期统一使用 ISO 格式。

## 命名规范

### 序列命名 `series_key`

使用英文 snake_case：

- `real_gdp`
- `nominal_gdp`
- `real_private_consumption`
- `real_private_investment`
- `real_public_demand`
- `real_exports`
- `real_imports`
- `gdp_deflator`
- `cpi_all_items`
- `cpi_less_fresh_food`
- `cpi_less_fresh_food_energy`
- `cpi_food`
- `cpi_energy`
- `nominal_wage_index`
- `real_wage_index`
- `usdjpy`
- `jgb_10y`
- `jgb_20y`
- `jgb_30y`
- `boj_policy_rate`

### 派生指标命名 `metric_key`

- `real_gdp_yoy`
- `nominal_gdp_yoy`
- `gdp_deflator_yoy`
- `real_wage_yoy`
- `nominal_wage_yoy`
- `cpi_yoy`
- `wage_minus_cpi`
- `real_consumption_yoy`
- `private_investment_yoy`
- `jgb_10y_change_3m`
- `jgb_30y_change_3m`
- `usdjpy_change_3m`
- `real_growth_score`
- `inflation_pressure_score`
- `fiscal_stress_score`

## 频率与日期规范

- `daily`：日频，例如 JGB、USDJPY。
- `monthly`：月频，例如 CPI、工资。
- `quarterly`：季频，例如 GDP。
- `annual`：年频，仅作为辅助。

日期字段：

- `date`：该观测值对应的期末日期，格式 `YYYY-MM-DD`。
- `period_label`：面向展示的期间标签，例如 `2026Q1`、`2026-03`。
- `released_at`：官方发布日期或文件更新日期，格式 `YYYY-MM-DD` 或完整时间。
- `created_at` / `updated_at`：系统写入时间，使用 ISO datetime。

## SQLite 表结构

### `runs`

记录每次批处理运行。

字段：

- `id INTEGER PRIMARY KEY`
- `started_at TEXT NOT NULL`
- `finished_at TEXT`
- `status TEXT NOT NULL`：`success` / `partial_success` / `failed`
- `trigger TEXT NOT NULL`：`cron` / `manual`
- `message TEXT`

### `source_status`

记录每个数据源在某次运行中的状态。

字段：

- `id INTEGER PRIMARY KEY`
- `run_id INTEGER NOT NULL`
- `source_name TEXT NOT NULL`
- `status TEXT NOT NULL`
- `latest_data_date TEXT`
- `downloaded_at TEXT`
- `raw_path TEXT`
- `message TEXT`

### `series_observations`

保存清洗后的标准化时序数据。

字段：

- `id INTEGER PRIMARY KEY`
- `series_key TEXT NOT NULL`
- `date TEXT NOT NULL`
- `period_label TEXT`
- `frequency TEXT NOT NULL`
- `value REAL`
- `unit TEXT`
- `source_name TEXT NOT NULL`
- `source_file TEXT`
- `released_at TEXT`
- `created_at TEXT NOT NULL`

唯一约束：

- `(series_key, date, source_name)`

### `metric_snapshots`

保存某个报告日期对应的指标快照。

字段：

- `id INTEGER PRIMARY KEY`
- `snapshot_date TEXT NOT NULL`
- `metric_key TEXT NOT NULL`
- `latest_value REAL`
- `previous_value REAL`
- `yoy REAL`
- `change_3m REAL`
- `judgement TEXT`
- `source_coverage TEXT`
- `created_at TEXT NOT NULL`

唯一约束：

- `(snapshot_date, metric_key)`

### `analysis_reports`

保存报告主记录。

字段：

- `id INTEGER PRIMARY KEY`
- `report_date TEXT NOT NULL UNIQUE`
- `title TEXT NOT NULL`
- `summary_label TEXT NOT NULL`
- `summary_text TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `data_coverage TEXT`
- `has_missing_data INTEGER NOT NULL DEFAULT 0`
- `exported_markdown_path TEXT`

### `report_sections`

保存报告章节。

字段：

- `id INTEGER PRIMARY KEY`
- `report_id INTEGER NOT NULL`
- `section_key TEXT NOT NULL`
- `title TEXT NOT NULL`
- `body TEXT NOT NULL`
- `sort_order INTEGER NOT NULL`

唯一约束：

- `(report_id, section_key)`

### `report_evidence`

保存关键证据。

字段：

- `id INTEGER PRIMARY KEY`
- `report_id INTEGER NOT NULL`
- `category TEXT NOT NULL`：`real_growth` / `inflation` / `fiscal` / `data_quality`
- `text TEXT NOT NULL`
- `metric_key TEXT`
- `severity TEXT`：`info` / `warning` / `risk`
- `sort_order INTEGER NOT NULL`

### `scores`

保存三类评分。

字段：

- `id INTEGER PRIMARY KEY`
- `report_id INTEGER NOT NULL UNIQUE`
- `real_growth_score REAL`
- `inflation_pressure_score REAL`
- `fiscal_stress_score REAL`
- `confidence_level TEXT NOT NULL`

### `chart_definitions`

保存图表定义。

字段：

- `chart_key TEXT PRIMARY KEY`
- `title TEXT NOT NULL`
- `description TEXT`
- `default_range TEXT`：例如 `5y`、`10y`、`all`
- `chart_type TEXT NOT NULL`：`line` / `bar` / `dual_axis_line`
- `sort_order INTEGER NOT NULL`

### `chart_series`

保存图表与数据序列的关系。

字段：

- `id INTEGER PRIMARY KEY`
- `chart_key TEXT NOT NULL`
- `series_key TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `unit TEXT`
- `axis TEXT NOT NULL`：`left` / `right`
- `sort_order INTEGER NOT NULL`

唯一约束：

- `(chart_key, series_key)`

## 首版图表定义

### `gdp_growth`

- 标题：名义 GDP YoY vs 实际 GDP YoY
- 类型：双线图
- 序列：
  - `nominal_gdp_yoy`
  - `real_gdp_yoy`

### `wage_vs_cpi`

- 标题：实际工资 YoY vs CPI YoY
- 类型：双线图
- 序列：
  - `real_wage_yoy`
  - `cpi_yoy`

### `private_consumption`

- 标题：民间消费 YoY
- 类型：线图
- 序列：
  - `real_consumption_yoy`

### `private_investment`

- 标题：企业设备投资 YoY
- 类型：线图
- 序列：
  - `private_investment_yoy`

### `market_pressure`

- 标题：USDJPY 与 JGB 10Y
- 类型：双轴线图
- 序列：
  - `usdjpy`
  - `jgb_10y`

## Web 路由

### 页面路由

- `GET /`：最新报告首页。
- `GET /reports`：历史报告列表。
- `GET /reports/{report_id}`：报告详情。
- `GET /sources`：数据源状态。

### JSON API

- `GET /api/latest`：最新报告摘要、评分、关键证据。
- `GET /api/reports`：报告列表。
- `GET /api/reports/{report_id}`：报告详情结构化数据。
- `GET /api/sources`：数据源状态。
- `GET /api/charts/{chart_key}`：ECharts 图表数据。

## `/api/charts/{chart_key}` 返回结构

示例：

```json
{
  "chart_key": "gdp_growth",
  "title": "名义 GDP YoY vs 实际 GDP YoY",
  "unit": "%",
  "x_axis": ["2024Q1", "2024Q2", "2024Q3"],
  "series": [
    {
      "name": "名义 GDP YoY",
      "axis": "left",
      "unit": "%",
      "data": [3.1, 3.4, 3.0]
    },
    {
      "name": "实际 GDP YoY",
      "axis": "left",
      "unit": "%",
      "data": [0.8, 1.0, 0.7]
    }
  ],
  "source_note": "数据来自 ESRI / e-Stat，按项目规则清洗计算。"
}
```

## `config.yaml` 结构

```yaml
paths:
  raw_dir: data/raw
  manual_dir: data/manual
  processed_dir: data/processed
  database: data/app.db
  logs_dir: logs

download:
  timeout_seconds: 60
  retries: 2
  user_agent: MacroSignal-JP/0.1

features:
  export_markdown: true
  use_manual_usdjpy: true

scoring:
  thresholds:
    jgb_10y_change_3m_bp: 50
    jgb_30y_change_3m_bp: 75
    usdjpy_change_3m_pct: 5
    nominal_real_gdp_gap_pct: 2

web:
  title: 日本宏观政策效果监控器
  public_readonly: true
```

## 手动 USDJPY CSV 格式

路径：`data/manual/usdjpy.csv`

格式：

```csv
date,value,source,note
2026-05-01,153.24,manual_boj_export,BOJ Time-Series Data Search 手动导出
2026-05-02,153.80,manual_boj_export,BOJ Time-Series Data Search 手动导出
```

规则：

- `date` 必须为 `YYYY-MM-DD`。
- `value` 为 USDJPY，即 1 美元兑多少日元。
- `source` 必须填写。
- `note` 可为空，但建议记录下载方式。
- 使用手动数据时，Web UI 和报告必须标注。

## 需要进入工程约定的规则

- 所有入库指标必须有 `series_key` 或 `metric_key`。
- UI 不直接展示英文 key，必须映射为中文名称。
- JSON API 只读，不提供写接口。
- 图表 API 返回结构必须稳定，方便 ECharts 复用。
- 所有日期必须使用 ISO 格式。
