# football-data.co.uk 字段速查

> 版本 v1.9 · 2026-11-10 · 依据官方 <https://www.football-data.co.uk/notes.txt>，并对 2026-11-07 实际下载的表头做了核对。
> **仓库已含 132 个原始 CSV 快照（`data/raw/`，已入库），clone 即用、无需重新下载**；本节 URL 仅用于快照更新 / 补漏，完整下载命令见根目录 README §3.2，字节级校验见 §3.4。
> **v1.3（M1 开工复核）**：补 §4 / §5 的全库读取实测（ragged 行、重复表头、整列缺失、空白行），并订正评估窗三列收盘赔率覆盖为 45 块满格 / 3 块共缺 5 场 / B6 有效 n = **16,728**。
> **v1.4（S1 读取器实测）**：订正「11 个文件行字段数多于表头」为「11 个文件行长 ≠ 表头（9 长 / 8 短，共 775 长行 + 1,331 短行）」；`0304_F1` 由「365 行 50 列」改为「380 场有效行 39–52 列、365 行不齐（208 短 / 157 长）」。实现见 `src/build_panel.py::read_raw()`，46,507 行 0 列错位。
> **v1.5（S1-r2 溢出实测）**：775 条长行的 **2,895 个溢出格 100% 为 `''`**（非空 0）；1,331 条短行缺的列**只有空串列名**（6,215 处），白名单 19 列 0 截断；775 条长行核心列全正常，排除整体右移。`read_raw()` 现对「溢出非空」零容忍，`selfcheck()` 第 6 项同步收紧，测试升至 10 条。
> **v1.6（S2 字段统一实测）**：全库 **243 个原始队名**、归一后 241；仅 2 组真实改名（N1 的 `Roda JC`→`Roda`、`Sparta`→`Sparta Rotterdam`），**不存在**旧稿举例的 `Man United` / `Manchester Utd` 变体；`Ajaccio` / `Ajaccio GFCO` 是同城两支不同队，禁止模糊匹配合并。日期 `dayfirst=True, format='mixed'` 0 NaT、ISO 范围 `2003-08-01 → 2025-05-25`；`FTR` 分布 H/D/A = 21,194 / 11,824 / 13,489 → `y=0/1/2`。归一表见 `configs/team_alias.csv`，实现见 `src/build_panel.py::clean_panel()`，自检日志见 `results/logs/s2_clean_2026-11-10.txt`。
> **v1.7（S3 建模总表）**：`data/processed/panel.parquet` 已交付，46,507 行 × **22 列**；`match_id` 唯一、`date` 为 ISO 字符串、`season` 为 `YYYY/YY`；T1.3-a 场次核查用「n 队满额 `n×(n−1)`」规则逐块断言 132 块，仅 `F1 2019/20`=279 / `N1 2019/20`=232 两个腰斩例外；评估窗 48 块 16,733 场、B6 有效 16,728。列清单见 §6，实现见 `src/build_panel.py::build_panel()`，自检日志见 `results/logs/s3_panel_2026-11-10.txt`。**`Max*` 不进 panel**，覆盖率矩阵仍直接读 raw。
> **v1.8（S4 切分契约）**：`configs/splits.json` 已交付（48 块 / 14,946 B，**入库**），train = 同联赛 `date < test_start`、test = 该联赛该季全部比赛，48 块 test 并集恰 16,733 场、`n_train ≥ 4,284`、`n_new_team ≤ 3`（历史累积口径，实测最大 2）。M2 harness 统一走 `src.splits.resolve_split(panel, block)`；`n_new_team` 与 `is_promoted_*`（上一季名单）不是同一个数。实现见 `src/splits.py`，自检日志见 `results/logs/s4_splits_2026-11-10.txt`。**评估窗口径不变**：1718–2425 × 6 = 48 块 / 16,733 场，B6 有效 16,728。
> **v1.9（S5 覆盖率矩阵实测订正）**：`src/coverage.py` 直接读 raw 产出 `results/coverage_matrix.csv`（132 行 × 18 列）与 `products/figures/fig_data_coverage.png`。四条事实：① `PSCH/PSCD/PSCA` 自 **2012/13** 才有，评估窗 45/48 块满格、另 3 块共缺 5 场；② 荷甲射门 **4 列** `HS/AS/HST/AST` 自 **2017/18** 起满格，此前 14 季全缺，但**半场比分 `HTHG/HTAG` 全库 22 季都有，不是射门列**；③ `MaxCH/MaxCD/MaxCA` 自 **2019/20** 起才有，6 联赛一致；④ **订正旧稿「评估窗射门 100% 可用」**：`2425_D1` 的 Union Berlin–Bochum（2024-12-14）缺 6 个射门/半场列，评估窗射门覆盖率 **16,732/16,733 = 0.999940**（比分与收盘赔率齐全，B6 有效 16,728 不变），任何以射门列为特征的 arm 须显式处理 NaN。`Max*` 不进 panel，所以覆盖率矩阵**不能从 panel 算**。逐格见 CSV，自检见 `results/logs/s5_coverage_2026-11-10.txt`。
> **命名口径（v1.2）**：市场基准 arm 为 `B6`，重校准市场为 `B6r`；提交版 Proposal 里的 `MK` / `MK*` 是同一物的旧名，映射表见 `docs/plans/Team-32-Proposal_v3.0.md` §4 末。`M0`–`M4` 一律不再作模型名。

## 1. 下载 URL

```
https://www.football-data.co.uk/mmz4281/{season}/{div}.csv
```

- `www` 会 302 跳到无 `www` 的域名，下载命令必须允许重定向（`curl -L` / `Invoke-WebRequest` 默认跟随）。
- `season`：4 位赛季码，起止年后两位拼接（`1617` = 2016/17，`1920` = 2019/20，`2021` = 2020/21，`2425` = 2024/25）。
- `div`：`E0` 英超、`SP1` 西甲、`I1` 意甲、`D1` 德甲、`F1` 法甲、`N1` 荷甲。
- 备选：每赛季打包 `https://football-data.co.uk/mmz4281/{season}/data.zip`。

## 2. 结果列

| 列 | 含义 |
|---|---|
| `Div` | 联赛代码 |
| `Date` | 比赛日期（老文件 `dd/mm/yy`，新文件 `dd/mm/yyyy`） |
| `HomeTeam` / `AwayTeam` | 主 / 客队名 |
| `FTHG` / `FTAG` | 全场主 / 客队进球 |
| `FTR` | 全场结果 `H` / `D` / `A` → 建模时映射为 `y = 0/1/2` |
| `HTHG` / `HTAG` / `HTR` | 半场比分与结果 |
| `HS` / `AS` | 射门数 |
| `HST` / `AST` | 射正数 |
| `HC` / `AC` | 角球 |
| `HF` / `AF` | 犯规 |
| `HY` / `AY` / `HR` / `AR` | 黄牌 / 红牌 |

## 3. 赔率列（本项目关键）

官方说明：**无 `C` 的是开市后采集的赔率；带 `C` 的才是收盘赔率**（例：`B365CH` = Bet365 收盘主胜赔率）。自 2019/20 起同时提供两套；Pinnacle 的收盘 H/D/A 可回溯到 2012/13。

| 用途 | 列名 | 备注 |
|---|---|---|
| **市场基准（主）** | `PSCH` / `PSCD` / `PSCA` | Pinnacle **收盘**赔率，本项目 `B6` 的唯一输入；`B6r` 由 `B6` 的概率重校准得到，不另读赔率列 |
| 稳健性基准 | `MaxCH` / `MaxCD` / `MaxCA` | 市场最高收盘价，2019/20 起可得，几乎无抽水 |
| 参考（勿误用） | `PSH` / `PSD` / `PSA` | Pinnacle **非收盘**赔率，不能当 `B6` |

> **评估窗实测（2026-11-08 全量复测）**：8 季 × 6 联赛 = 16,733 场中，`PSCH/PSCD/PSCA` 三列同时齐全 **16,728 场**；45 块满格，缺的 5 场分布在 `1718_SP1`（1）、`1718_N1`（3）、`1819_D1`（1），三列全空且 `B365H` 有值——**按项目规则 drop 不回填**，故 `B6` / `B6r` 有效 n = 16,728。
| 其他收盘 | `B365CH/CD/CA`、`AvgCH/CD/CA`、`BFECH/CD/CA` | 可选交叉核对 |
| 去抽水对照 | `MaxH/D/A`、`AvgH/D/A` | 非收盘的市场最大 / 平均 |

> ⚠️ 项目要审计的是**收盘线**，基准列必须用带 `C` 的一组；用非收盘赔率会系统性缩小「模型 vs 市场」的差距。

## 4. 表头实测（2026-11-07 核对）

| 文件 | 列数 | 含 `PSCH` |
|---|---|---|
| `1617/E0.csv` | 65 | 是 |
| `1920/E0.csv` | 106 | 是 |
| `2021/E0.csv` | 106 | 是 |
| `2425/E0.csv` | 120 | 是 |
| `2425/SP1.csv`、`I1`、`D1`、`F1`、`N1` | 119 | 是 |

**结论：按列名取数，绝不按列位置取数。** 列数随赛季与联赛变化。

全库 132 文件实测（2026-11-08）：表头列数 41–120；**2 种表头变体**（96 个文件无 `Time`、36 个有）；**11 个文件行长 ≠ 表头**（9 个含长行、8 个含短行、6 个兼有；共 775 长行 + 1,331 短行；`0304_F1` 表头 41 列、380 场有效行 39–52 列、365 行不齐）；**14 个文件表头有重复列名**；**54 个文件（0304–1112 × 6）根本没有 `PSCH/PSCD/PSCA` 列**；**7 个文件共 11 行全空白**（`46,518 → 46,507`）。

## 5. 已知读取坑

| 坑 | 处理 |
|---|---|
| 编码 | 老文件常见 `latin-1` / `cp1252`，较新文件可能带 UTF-8 BOM；先试 `utf-8-sig`，报错再回退 `latin-1`，并抽查 `Saint-Étienne` 等队名 |
| BOM | 部分文件首列为 `\ufeffDiv`，读取时显式去掉 |
| 日期混用 | `pd.to_datetime(..., dayfirst=True, format='mixed')`，逐条解析后抽查，警惕 `2024` 被解析成 `2024-01-01` |
| 队名 | 同义不同写，按 `configs/team_alias.csv` 统一后再做 Elo / 特征 |
| 赛季腰斩 | 法甲 2019/20 仅 279 场、荷甲 2019/20 仅 232 场；保留并在报告说明，不插补、不删赛季 |
| 覆盖率 | 荷甲 **2017/18 之前**（0304–1617）无射门 4 列；逐块逐列非空比例见 `results/coverage_matrix.csv`（S5 已交付），不静默跳过 |
| 行长不齐 | 11 个文件行长 ≠ 表头（9 长 / 8 短）；`csv.reader` **按名取列**（多余字段忽略、缺列补 NaN），**不要 `on_bad_lines='skip'`**（`0304_F1` 会静默丢 365 场）。`src/build_panel.py::read_raw()` 已落地；**r2**：2,895 个溢出格实测全空，非空即抛 `ValueError`，短行只缺空串列名列 |
| 表头重名 | 14 个文件有重复列名；整表 `concat` / `reindex` 会报错，只取白名单列 |
| 整列缺失 | `PSCH/PSCD/PSCA` 在 0304–1112 是「列不存在」；白名单缺列补 NaN，不要直接索引 |

## 6. `panel.parquet` 的 22 列（S3 / 2026-11-10 实测）

`python src/build_panel.py --stage s3` 从 132 个 raw 一键重跑产出，**不入库**（README §3.6）。列顺序即契约，46,507 行、按 `league, season, date, home, away` 排序。

| 组 | 列 | 说明 |
|---|---|---|
| identity（6） | `match_id`, `league`, `season`, `date`, `home`, `away` | `match_id = league\|season\|date\|home\|away`；`date` 为 ISO **字符串**、`season` 为 `YYYY/YY`、队名已按 `configs/team_alias.csv` 归一 |
| 结果（6） | `FTR`, `y`, `FTHG`, `FTAG`, `HTHG`, `HTAG` | `y = FTR.map(H=0,D=1,A=2)`；分布 21,194 / 11,824 / 13,489 |
| 射门（4） | `HS`, `AS`, `HST`, `AST` | 荷甲 2017/18 起才满格；**评估窗 0.999940**（`2425_D1` 缺 1 场，不是 100%；见 v1.9 订正） |
| 收盘赔率（3） | `PSCH`, `PSCD`, `PSCA` | 唯一市场基准；0304–1112 整列不存在 → 全 NaN；评估窗缺 3 块共 5 场，B6 有效 n = 16,728 |
| H3（3） | `is_promoted_home`, `is_promoted_away`, `matchday` | 只由季前名单 / 赛程构造，打乱赛后列后逐元素不变 |

> ⚠️ **保留 ≠ 可入模**：`FTR` / 比分 / 射门是**赛后观测**，留在 panel 里只为 `y` 审计与误差分析；任何 B0–B5b 的特征都不得包含它们，三列收盘赔率除 B6/B6r 外同样不得入模（`data_interface.md` §2）。`MaxCH/MaxCD/MaxCA` 与 `HTR` 等**不在 22 列内**，T1.4 覆盖率矩阵必须直接读 `data/raw/`。

---

*官方字段全表：<https://www.football-data.co.uk/notes.txt>；下载页：<https://www.football-data.co.uk/downloadm.php>。*
