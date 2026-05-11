# 日本外国人变化趋势分析功能开发计划

本文档用于规划“日本外国人变化趋势数据分析”功能。当前阶段只做设计说明，不开始代码实现。

## 1. 功能目标

在现有日本宏观监控项目中新增一个专题模块，用于长期追踪日本外国人相关变化，重点回答：

- 在留外国人总数是否持续增加。
- 来源国结构是否发生变化。
- 在留资格是否从短期劳动力型向长期定居型转变。
- 外国人劳动者集中在哪些行业和工作类型。
- 外国人工资是否改善，名义工资与实际工资是否存在差异。
- 哪些都道府县对外国人依赖度更高。
- 日本是否正在从“临时接收外国劳动力”转向“长期定居型外国人口社会”。

## 2. 数据源规划

优先使用日本官方公开数据源。实现前需要先做一次“可自动化下载测试”，确认文件格式、下载 URL 是否稳定、字段是否可解析。

### 2.1 在留外国人数据

优先来源：

- 出入国在留管理庁：在留外国人統計
- e-Stat：在留外国人統計

目标字段：

```text
year
month
nationality
residence_status
prefecture
foreign_resident_count
```

重点维度：

- 总人数
- 国籍
- 在留资格
- 都道府县
- 年度或半年度时间序列

### 2.2 外国人劳动者数据

候选来源：

- 厚生労働省：外国人雇用状況の届出状況
- e-Stat 中相关劳动统计

目标字段：

```text
year
industry
nationality
residence_status
prefecture
foreign_worker_count
```

重点维度：

- 行业分布
- 都道府县分布
- 国籍结构
- 在留资格结构

### 2.3 工资数据

候选来源：

- 厚生労働省：賃金構造基本統計調査
- e-Stat：賃金構造基本統計調査
- 若无法稳定区分外国人，可先使用行业、职业或在留资格相关代理指标，并明确标注限制。

目标字段：

```text
year
nationality_or_worker_group
industry
occupation
nominal_wage
real_wage
```

工资分析需要与 CPI 联动：

- 名义工资：账面工资水平。
- 实际工资：扣除物价影响后的购买力。
- 若官方表无法直接给出实际工资，使用 CPI 派生计算，并在页面说明。

### 2.4 地区依赖度数据

需要把外国人数据与地区总人口或就业人口结合。

候选来源：

- 総務省：人口推計
- e-Stat：都道府县人口数据
- 厚生労働省：都道府县就业相关数据

目标派生字段：

```text
prefecture
foreign_resident_count
total_population
foreign_share_of_population
foreign_worker_count
total_workers
foreign_share_of_workers
```

## 3. 数据库设计

建议新增专题表，不混入现有宏观指标表，避免 GDP/CPI/JGB 与人口劳动专题耦合过深。

### 3.1 原始来源状态表

可复用现有 `source_status`，新增 source_name：

```text
Immigration Services Agency Foreign Residents
e-Stat Foreign Residents
MHLW Foreign Workers
MHLW Wage Survey
```

### 3.2 在留外国人事实表

建议表名：

```text
foreign_resident_observations
```

字段：

```text
id
date
year
month
nationality
residence_status
prefecture
value
unit
source_name
source_file
created_at
```

### 3.3 外国人劳动者事实表

建议表名：

```text
foreign_worker_observations
```

字段：

```text
id
date
year
industry
nationality
residence_status
prefecture
value
unit
source_name
source_file
created_at
```

### 3.4 外国人工资事实表

建议表名：

```text
foreign_wage_observations
```

字段：

```text
id
date
year
worker_group
industry
occupation
nominal_wage
real_wage
unit
source_name
source_file
created_at
```

### 3.5 专题分析结果表

建议表名：

```text
foreign_population_reports
```

字段：

```text
id
report_date
summary_label
summary_text
settlement_score
labor_dependency_score
wage_improvement_score
data_coverage
has_missing_data
created_at
```

## 4. 核心指标设计

### 4.1 总量趋势

```text
foreign_residents_total
foreign_residents_yoy
foreign_residents_cagr_5y
```

判断逻辑：

- 总人数连续增长：说明外国人规模扩张。
- YoY 放缓但总量高位：说明扩张仍在，但速度下降。
- YoY 转负：需观察政策、疫情、经济周期或统计口径变化。

### 4.2 来源国结构

```text
top_nationalities
nationality_share
nationality_share_change_5y
source_country_concentration
```

判断逻辑：

- 单一国家占比过高：劳动力来源集中风险更高。
- 来源国更加多元：说明接收结构扩展。
- 越南、尼泊尔、印度尼西亚、缅甸等占比变化需要重点观察。

### 4.3 在留资格结构

```text
technical_intern_share
specified_skilled_worker_share
engineer_humanities_international_share
permanent_resident_share
long_term_settlement_share
temporary_labor_share
settlement_transition_score
```

建议分类：

- 临时劳动力型：技能実習、短期滞在等。
- 工作签证型：特定技能、技術・人文知識・国際業務、技能等。
- 定居型：永住者、定住者、日本人の配偶者等、永住者の配偶者等。

判断逻辑：

- 技能実習占比下降、特定技能占比上升：说明制度从旧型实习向正式劳动力接收变化。
- 永住者、定住者占比上升：说明长期定居倾向增强。
- 工作签证和定居型同步上升：更接近“长期外国人口社会”。

### 4.4 行业集中度

```text
foreign_workers_by_industry
industry_share
industry_share_change_5y
industry_dependency_score
```

重点行业：

- 制造业
- 建设业
- 住宿・餐饮服务
- 介护
- 农业
- 批发零售

判断逻辑：

- 介护、建设、住宿餐饮占比上升：说明老龄化和服务业劳动力缺口更依赖外国人。
- 制造业占比高：说明生产部门依赖明显。

### 4.5 工资变化

```text
foreign_nominal_wage_yoy
foreign_real_wage_yoy
foreign_wage_minus_cpi
foreign_wage_gap_vs_total_workers
```

判断逻辑：

- 名义工资上升、实际工资不上升：工资改善可能被通胀抵消。
- 实际工资连续为正：外国劳动者购买力改善。
- 与全体劳动者工资差距缩小：待遇改善信号。
- 差距扩大：低工资劳动力依赖风险上升。

### 4.6 地区依赖度

```text
foreign_share_of_population_by_prefecture
foreign_share_of_workers_by_prefecture
prefecture_dependency_rank
prefecture_dependency_change_5y
```

判断逻辑：

- 外国人占总人口比例高：地区人口结构更国际化。
- 外国人劳动者占就业人口比例高：地区劳动力依赖更强。
- 地方县快速上升：可能反映农业、制造业、介护等劳动力短缺。

## 5. 分析框架

### 5.1 长期定居型社会信号

增强信号：

- 外国人总数长期增长。
- 永住者、定住者、家族滞在等长期居住相关资格占比上升。
- 技能実習占比下降，特定技能和专业工作签证占比上升。
- 外国人分布从少数大都市扩展到更多地方县。
- 工资和实际工资改善。

减弱信号：

- 增长主要集中在技能実習等临时劳动力资格。
- 工资改善弱，实际工资为负。
- 来源国过度集中。
- 地区和行业高度依赖低工资岗位。

### 5.2 劳动力依赖信号

增强信号：

- 外国人劳动者总数上升。
- 介护、建设、农业、住宿餐饮等行业占比上升。
- 老龄化严重地区的外国人劳动者占比上升。

风险信号：

- 行业集中度过高。
- 工资水平长期偏低。
- 特定国家来源占比过高。

## 6. Web UI 设计

建议新增导航入口：

```text
外国人趋势
```

页面结构：

### 6.1 总览页 `/foreign-residents`

模块：

- 总结判断
- 外国人总数趋势
- 来源国 Top 10
- 在留资格结构
- 行业分布
- 地区依赖度地图或排名
- 工资变化

### 6.2 图表详情页

复用当前图表详情能力：

- 图表
- 如何解读
- 表格数据
- 数据来源说明

### 6.3 数据源状态页

在现有 `/sources` 中加入外国人专题数据源状态。

## 7. ECharts 图表规划

建议第一阶段实现：

1. 外国人在留总数 YoY
2. 来源国 Top 10 占比变化
3. 在留资格结构堆叠图
4. 外国人劳动者行业分布
5. 都道府县外国人占比排名
6. 名义工资 vs 实际工资

地图可后置。第一阶段先用排名条形图，避免引入日本地图边界数据和额外复杂度。

## 8. 文件结构规划

建议新增：

```text
src/
  foreign_fetch.py
  foreign_clean.py
  foreign_indicators.py
  foreign_analyze.py
  foreign_pipeline.py
  web/
    templates/
      foreign_residents.html
      foreign_chart_detail.html
```

也可以先放在现有模块中，但长期建议独立文件，避免宏观政策分析和人口劳动专题混在一起。

## 9. 开发阶段

### 阶段 1：数据源自动化验证

目标：

- 下载官方样本文件到 `data/raw/source_tests/foreign_residents/`
- 确认 e-Stat 或官方 Excel/CSV 是否可稳定自动下载
- 记录每个数据源的下载 URL、文件格式、字段位置、编码

产出：

```text
docs/foreign-residents-source-test.md
```

### 阶段 2：在留外国人核心链路

目标：

- 自动下载在留外国人统计
- 清洗为结构化表
- 计算总人数、YoY、国籍结构、在留资格结构、都道府县分布
- 新增 `/foreign-residents` 总览页

### 阶段 3：外国人劳动者与行业

目标：

- 接入外国人雇用状況数据
- 分析行业结构和地区分布
- 增加行业依赖度判断

### 阶段 4：工资与实际购买力

目标：

- 接入工资相关官方数据
- 与 CPI 联动计算实际工资
- 分析外国人工资改善是否真实

### 阶段 5：综合判断模型

目标：

- settlement_score
- labor_dependency_score
- wage_improvement_score
- 输出“临时劳动力型”还是“长期定居型社会”倾向判断

## 10. 风险与限制

- 官方数据可能是 Excel、CSV、PDF 混合格式，自动化难度不同。
- e-Stat 部分下载链接可能带统计表 ID，需要先验证稳定性。
- 工资数据未必能直接区分外国人，需要谨慎处理口径。
- 在留资格名称可能有日文变体，需要建立标准化映射表。
- 都道府县、国籍名称需要标准化，避免同一国家或地区出现多个写法。
- 所有结论必须标明数据覆盖期和缺失项，避免过度解读。

## 11. 下一步建议

下一步不要直接做全量功能，先做“阶段 1：数据源自动化验证”。

优先验证：

1. 出入国在留管理庁或 e-Stat 在留外国人统计是否能稳定下载。
2. 是否能拿到国籍、在留资格、都道府县三个核心维度。
3. 厚生労働省外国人雇用状況是否能自动下载 Excel/CSV。
4. 工资数据是否能直接区分外国人；如果不能，确定替代口径。

只有完成数据源验证后，再进入数据库表和页面实现。

## 12. TodoList

### 阶段 1：数据源自动化验证

- [x] 确认出入国在留管理庁“在留外国人統計”的公开下载入口。
- [x] 确认 e-Stat“在留外国人統計”的统计表 ID、文件格式和下载 URL 是否稳定。
- [x] 下载样本文件到 `data/raw/source_tests/foreign_residents/`。
- [x] 记录每个样本文件的编码、sheet 名称、表头行、数据起始行。
- [x] 验证是否能稳定提取 `year`、`month`、`nationality`、`residence_status`、`prefecture`、`foreign_resident_count`。
- [x] 确认厚生労働省“外国人雇用状況の届出状況”的下载入口和文件格式。
- [x] 验证是否能提取行业、都道府县、国籍、在留资格维度。
- [x] 调查工资数据是否能直接区分外国人劳动者。
- [x] 输出 `docs/foreign-residents-source-test.md`。

### 阶段 2：在留外国人核心链路

- [x] 新增 `foreign_fetch.py`，实现官方文件下载。
- [x] 新增 `foreign_clean.py`，清洗在留外国人数据。
- [x] 新增在留外国人数据库表。
- [x] 写入结构化观测数据。
- [x] 计算外国人在留总数、YoY、5年 CAGR。
- [x] 计算来源国 Top 10 和占比变化。
- [x] 计算在留资格结构和长期定居型占比。
- [x] 增加数据源状态记录。

阶段 2 执行记录：

- 已新增 `foreign_resident_observations` 和 `foreign_resident_metrics` 两张数据库表。
- 已验证 e-Stat 在留外国人明细表可清洗为 444,173 条结构化观测，官方总数为 3,768,977 人。
- YoY 和 5 年 CAGR 的计算逻辑已实现；当前只下载到一个时期时不会生成同比和 CAGR，需要后续下载多期历史文件后自动产生。

### 阶段 3：Web 总览页

- [x] 新增导航入口“外国人趋势”。
- [x] 新增 `/foreign-residents` 页面。
- [x] 展示总结判断、数据覆盖期和缺失项提示。
- [x] 增加在留外国人总数趋势图。
- [x] 增加来源国结构图。
- [x] 增加在留资格结构图。
- [x] 复用图表详情页展示表格数据和解读说明。

阶段 3 执行记录：

- 已新增 `/foreign-residents` 专题页，页面从数据库动态读取在留外国人总数、长期定居型占比、来源国 Top 10、在留资格 Top 10。
- 已新增 `/api/foreign-residents` 和 `/api/foreign-residents/charts/{chart_key}`，供 ECharts 动态渲染。
- 已新增 `/foreign-residents/charts/{chart_key}` 图表详情页，复用表格和解释说明结构。
- 已更新导航栏，公开页面无需账号即可访问。

### 阶段 4：外国人劳动者与行业

- [x] 接入外国人雇用状況数据下载。
- [x] 清洗外国人劳动者行业分布。
- [x] 清洗外国人劳动者都道府县分布。
- [x] 计算行业占比和行业占比变化。
- [x] 增加行业集中度或劳动依赖度指标。
- [x] 在 Web 页面增加行业分布图和地区排名图。

阶段 4 执行记录：

- 已接入厚生労働省“外国人雇用状況の届出状況”年度 Excel。
- 已清洗行业 Top 10、都道府县 Top 10、行业占比、都道府县占比。
- 已新增 `industry_concentration_top3` 作为保守劳动依赖度代理指标。
- 当前行业和地区数据是每年 10 月末口径，不能与在留外国人明细的年月口径完全等同。

### 阶段 5：工资与购买力

- [x] 验证工资数据是否能区分外国人。
- [x] 若可区分，接入外国人工资数据。
- [x] 若不可区分，确定替代口径并在页面明确标注限制。
- [x] 计算名义工资同比。
- [x] 使用 CPI 计算或对照实际工资变化。
- [x] 计算工资减 CPI 指标。
- [x] 增加名义工资 vs 实际工资图表。

阶段 5 执行记录：

- 已接入 e-Stat 賃金構造基本統計調査“外国人労働者”年度 Excel。
- 已清洗外国人劳动者总体、特定技能、技能实习、身分に基づくもの等分组的现金工资水平。
- 当前自动下载只覆盖 2024 年样本，因此页面显示“工资水平”而不是严格同比改善。
- 名义工资同比、工资减 CPI 的代码口径保留为后续多期历史文件接入后的计算目标；当前页面明确标注单期数据限制。

### 阶段 6：综合判断模型

- [x] 设计 `settlement_score`。
- [x] 设计 `labor_dependency_score`。
- [x] 设计 `wage_improvement_score`。
- [x] 输出“临时劳动力型”或“长期定居型社会”倾向判断。
- [x] 为每个判断生成证据列表。
- [x] 在页面中明确显示置信度和数据缺口。

阶段 6 执行记录：

- 已在 `/foreign-residents` 页面展示定居化分数、劳动依赖分数、工资改善分数。
- 已输出保守综合判断和证据列表。
- 置信度目前按数据覆盖保守设置；由于多期历史数据尚未批量补齐，趋势判断不做过度推断。

### 阶段 7：验证与部署

- [x] 用 Docker Compose 跑完整数据管道。
- [x] 验证新增页面 HTTP 200。
- [x] 验证图表 API 返回表格数据。
- [x] 验证 `/sources` 能显示新增数据源状态。
- [x] 更新手动部署文档。
- [x] 更新 GitHub Actions 自动部署文档。
- [x] 记录首次真实数据运行结果和已知限制。

阶段 7 执行记录：

- 已执行 `docker compose run --rm app python run.py` 完整真实数据管道。
- 已验证 `/foreign-residents`、`/api/foreign-residents`、外国人专题图表 API 和 `/sources` 均返回 HTTP 200。
- 首次真实数据入库结果：在留外国人明细 444,173 条、在留外国人指标 42 条、外国人劳动者指标 41 条、外国人工资指标 69 条。
- 部署文档已补充外国人专题验证命令和已知限制。
