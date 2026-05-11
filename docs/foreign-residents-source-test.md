# 日本外国人数据源自动化验证

测试日期：2026-05-11  
本地目录：`data/raw/source_tests/foreign_residents/`

## 1. 结论

第一阶段验证结论：核心链路可以自动化。

- 在留外国人：e-Stat 已提供可直接下载的 Excel 明细表，字段覆盖 `nationality`、`residence_status`、`prefecture`、`foreign_resident_count`，年份和月份可从表名、sheet 名或下载参数派生。
- 外国人劳动者：厚生労働省“外国人雇用状況の届出状況”提供年度 Excel，能覆盖国籍、在留资格、都道府县、行业维度，但同一 workbook 内不同表格结构不一致，清洗时需要按 sheet 单独解析。
- 外国人工资：e-Stat“賃金構造基本統計調査 / 外国人労働者”提供 Excel，可直接区分外国人劳动者及在留资格区分，并包含现金工资、所定内工资、奖金、劳动者数。实际工资需要后续结合 CPI 派生。
- 后续实现不建议依赖 e-Stat API key；首版优先使用无 key 的 `file-download?fileKind=...&statInfId=...` 文件下载。

## 2. 已下载样本

| 样本文件 | 来源 | 下载方式 | 结果 |
| --- | --- | --- | --- |
| `estat_foreign_residents_2024_12_table01.xlsx` | e-Stat 在留外国人統計，第 1 表 | `fileKind=0&statInfId=000040292366` | 成功，210 KB |
| `estat_foreign_residents_2024_12_table_data.xlsx` | e-Stat 在留外国人統計テーブルデータ | `fileKind=0&statInfId=000040292372` | 成功，15.8 MB |
| `mhlw_foreign_workers_2024.xlsx` | 厚生労働省 外国人雇用状況の届出状況 | 直接下载年度 Excel | 成功，131 KB |
| `estat_wage_foreign_workers_2024_table01.xlsx` | e-Stat 賃金構造基本統計調査 / 外国人労働者 | `fileKind=4&statInfId=000040247905` | 成功，34 KB |
| `estat_wage_foreign_worker_residence_status_reference.pdf` | e-Stat / 厚生労働省 参考 PDF | `fileKind=2&statInfId=000040028730` | 成功，42 KB，仅作参考 |

## 3. 数据源检查

### 3.1 在留外国人统计

官方入口：

- 出入国在留管理庁统计入口：`https://www.moj.go.jp/isa/policies/statistics/index.html`
- e-Stat 在留外国人統計：`https://www.e-stat.go.jp/stat-search/files?toukei=00250012&tstat=000001018034`
- e-Stat 明细表样本：`https://www.e-stat.go.jp/stat-search/files?cycle=1&layout=dataset&stat_infid=000040292372&tclass1=000001060399&toukei=00250012&tstat=000001018034`

`estat_foreign_residents_2024_12_table01.xlsx`：

| 项目 | 结果 |
| --- | --- |
| 文件格式 | Excel xlsx |
| 编码 | Excel 工作簿，无需文本编码 |
| sheet | `24-12-01m` |
| 行列规模 | 8244 行 x 5 列 |
| 表头行 | 第 4 行 |
| 数据起始行 | 第 5 行 |
| 字段 | `時点`、`州`、`国籍・地域`、`在留資格`、`在留外国人数` |
| 适用性 | 适合做全国国籍 x 在留资格分析，不含都道府县 |

`estat_foreign_residents_2024_12_table_data.xlsx`：

| 项目 | 结果 |
| --- | --- |
| 文件格式 | Excel xlsx |
| 编码 | Excel 工作簿，无需文本编码 |
| sheet | `PVT`、`令和6年12月末` |
| 明细 sheet 规模 | 444174 行 x 7 列 |
| 表头行 | 第 1 行 |
| 数据起始行 | 第 2 行 |
| 字段 | `国籍・地域`、`在留資格`、`性別`、`年齢（５歳階級）`、`年齢`、`都道府県`、`在留外国人数` |
| 适用性 | 首版主数据源，能稳定映射项目目标字段 |

字段映射建议：

| 项目字段 | 官方字段 | 处理方式 |
| --- | --- | --- |
| `year` | sheet 名 / 调查年月 / `令和6年12月末` | 转换为西历 `2024` |
| `month` | sheet 名 / 调查年月 / `令和6年12月末` | 转换为 `12` |
| `nationality` | `国籍・地域` | 去掉前缀代码后保留名称，代码可另存 |
| `residence_status` | `在留資格` | 去掉前缀代码后保留名称，代码可另存 |
| `prefecture` | `都道府県` | 去掉前缀代码后保留名称，代码可另存 |
| `foreign_resident_count` | `在留外国人数` | 转为整数 |

### 3.2 外国人雇用状况

官方入口：

- 厚生労働省：`https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/koyou/gaikokujin/gaikokujin-koyou/06.html`
- 2024 年样本 Excel：`https://www.mhlw.go.jp/content/11655000/001389472.xlsx`

`mhlw_foreign_workers_2024.xlsx`：

| 项目 | 结果 |
| --- | --- |
| 文件格式 | Excel xlsx |
| 编码 | Excel 工作簿，无需文本编码 |
| sheet | `別表一覧`、`別表１` 到 `別表９`、`参考-1` 到 `参考-7` |
| 时间点 | `令和６年10月末時点`，可转为 `2024-10` |
| 解析方式 | 不同 sheet 表头不同，建议按 sheet 建立解析器 |

关键 sheet：

| sheet | 内容 | 表头/数据起始 | 可提取维度 |
| --- | --- | --- | --- |
| `別表１` | 国籍别 x 在留资格别外国人劳动者数 | 第 4-5 行复合表头，第 6 行起数据 | 国籍、在留资格、劳动者数 |
| `別表２` | 都道府县别事业所数和外国人劳动者数 | 第 4-5 行复合表头，第 6 行起数据 | 都道府县、劳动者数 |
| `別表３` | 都道府县别 x 在留资格别外国人劳动者数 | 第 3-4 行复合表头，第 5 行起数据 | 都道府县、在留资格、劳动者数 |
| `別表４` | 行业别事业所数和外国人劳动者数 | 第 3-4 行复合表头，第 5 行起数据 | 行业、劳动者数 |
| `別表５` | 都道府县别 x 行业别外国人劳动者数 | 第 3-4 行复合表头，第 5 行起数据 | 都道府县、行业、劳动者数 |
| `別表６` | 在留资格别 x 行业别外国人劳动者数 | 第 4-5 行复合表头，第 6 行起数据 | 在留资格、行业、劳动者数 |
| `別表７` | 国籍别 x 行业别外国人劳动者数 | 第 4-5 行复合表头，第 6 行起数据 | 国籍、行业、劳动者数 |
| `別表９` | 都道府县别 x 特定产业领域别外国人劳动者数，仅特定技能 | 第 4 行表头，第 5 行起数据 | 都道府县、特定技能行业、劳动者数 |

限制：

- 该来源是每年 10 月末时点，不是月度数据。
- 直接下载 URL 可能随年度变化，后续下载器应从官方页面解析最新 Excel 链接，而不是只固定 `001389472.xlsx`。

### 3.3 外国人工资

官方入口：

- e-Stat 賃金構造基本統計調査：`https://www.e-stat.go.jp/stat-search/files?cycle=0&layout=dataset&month=0&stat_infid=000040247905&tclass1=000001224440&tclass2=000001225782&tclass3=000001225791&toukei=00450091&tstat=000001011429&year=20240`

`estat_wage_foreign_workers_2024_table01.xlsx`：

| 项目 | 结果 |
| --- | --- |
| 文件格式 | Excel xlsx |
| 编码 | Excel 工作簿，无需文本编码 |
| sheet | `第1表` |
| 行列规模 | 163 行 x 12 列 |
| 表头行 | 第 7-9 行复合表头 |
| 数据起始行 | 第 10 行 |
| 字段 | 年龄、勤続年数、所定内実労働時間数、超過実労働時間数、きまって支給する現金給与額、所定内給与額、年間賞与その他特別給与額、労働者数 |
| 分组 | 外国人労働者、専門的・技術的分野（特定技能を除く）、特定技能、身分に基づくもの、技能実習、留学（資格外活動）、その他 |

字段映射建议：

| 项目字段 | 官方字段 | 处理方式 |
| --- | --- | --- |
| `year` | 页面/文件调查年月 | `2024` |
| `worker_group` | 区分列中的在留资格区分 | 需要识别父级分组 |
| `industry` | 区分列中的行业行 | 对行业行填充，否则为空或 `産業・企業規模計` |
| `nominal_wage` | `きまって支給する現金給与額` 或 `所定内給与額` | 首版建议同时保存两个字段，页面默认解释清楚 |
| `real_wage` | 无官方直接列 | 用 CPI 派生，必须标注为计算值 |
| `worker_count` | `労働者数` | 单位为 `十人`，保存时可转换成人数 |

限制：

- 该来源是年度调查，不是月度。
- 表内 `X` 表示保密或不适合公开，`-` 表示无数据；清洗时需要转为空值并保留原始标记。
- 外国人实态调查 PDF 可作为解释来源，但首版结构化工资数据优先使用 e-Stat Excel。

## 4. 自动化可行性判断

| 目标字段/问题 | 可行性 | 推荐来源 |
| --- | --- | --- |
| 在留外国人总数 | 可自动化 | e-Stat 在留外国人統計テーブルデータ |
| 国籍结构 | 可自动化 | e-Stat 明细表、MHLW 別表１/７ |
| 在留资格结构 | 可自动化 | e-Stat 明细表、MHLW 別表１/３/６ |
| 都道府县分布 | 可自动化 | e-Stat 明细表、MHLW 別表２/３/５ |
| 行业分布 | 可自动化 | MHLW 別表４/５/６/７/９ |
| 外国人工资 | 可自动化 | e-Stat 賃金構造基本統計調査 外国人労働者 |
| 实际工资 | 可派生 | 外国人工资 + 项目已有 CPI |
| 工作类型 | 部分可自动化 | 工资结构表有雇用形态，MHLW 年报有派遣/请负相关列，但口径需要说明 |

## 5. 下一阶段实现建议

阶段 2 可以进入代码实现，建议顺序如下：

1. 新增 `src/foreign_fetch.py`，固定下载上述三个主样本来源，并保留页面解析入口。
2. 新增 `src/foreign_clean.py`，优先清洗 e-Stat 在留外国人明细表，写入 SQLite。
3. 新增数据库表：`foreign_resident_observations`、`foreign_worker_observations`、`foreign_wage_observations`。
4. 前端先做一个“外国人趋势”专题页面，优先展示总量、国籍、在留资格、都道府县、工资五类图表。
5. 解释文本必须标明频率差异：在留外国人多为半年/月次公开口径，外国人雇用是每年 10 月末，工资是年度调查。

## 6. 测试命令摘要

本阶段使用以下方式验证：

```powershell
Invoke-WebRequest -Uri 'https://www.e-stat.go.jp/stat-search/file-download?fileKind=0&statInfId=000040292372' -OutFile 'data/raw/source_tests/foreign_residents/estat_foreign_residents_2024_12_table_data.xlsx'
Invoke-WebRequest -Uri 'https://www.mhlw.go.jp/content/11655000/001389472.xlsx' -OutFile 'data/raw/source_tests/foreign_residents/mhlw_foreign_workers_2024.xlsx'
Invoke-WebRequest -Uri 'https://www.e-stat.go.jp/stat-search/file-download?fileKind=4&statInfId=000040247905' -OutFile 'data/raw/source_tests/foreign_residents/estat_wage_foreign_workers_2024_table01.xlsx'
```

结构检查使用 `openpyxl` 读取 sheet、行列规模、表头行和样例行。
