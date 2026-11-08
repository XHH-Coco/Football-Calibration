# Football-Calibration

> **Team 32 · DSC5001C63 Statistical Machine Learning I · 课程项目代码仓库**

| 项目 | 内容 |
|---|---|
| 仓库 | `Football-Calibration` |
| 课程 | DSC5001C63 Statistical Machine Learning I（Semester A 2026/27，Instructor: Kangning Cui） |
| 团队 | Team 32（5 人） |
| 选题 | *Do football betting markets know more than a model can learn? Auditing the closing line for calibration and information* |
| 依据文档 | **`docs/plans/Team-32-Proposal_v3.0.md`（唯一执行蓝本）**、`docs/plans/08_小组分工实施方案_v1.3.md`（唯一在库分工方案）、`docs/plans/data_interface.md` v1.3；`docs/plans/Team-32-Proposal.pdf` 保留为 10/30 提交凭据 |
| **Python 版本** | **3.14.7 / 3.14.10 均可**（本机 conda 环境 `DSC5001_Project` = 3.14.10，见 §5） |
| 数据快照 | `data/raw/` **已入库**：132 个 CSV / 约 14 MB，clone 即用，无需重新下载（§3） |
| 提交物 | Report + 10 页 Slides + ≤ 8 分钟全员录像 + 源码附录，2026-11-29 |
| 本文档版本 | **v2.3 · 2026-11-08** |

---

## 0. 首次克隆后必须做的三件事

```bash
git clone <仓库地址>
cd Football-Calibration
```

| # | 做什么 | 详见 |
|---|---|---|
| 1 | 准备 **Python 3.14.7 或 3.14.10**（本机用 conda 环境 `DSC5001_Project`），按 §5.2 装齐 **8 个**已锁定依赖（**B5a/B5b 用 sklearn 内置 HGB，不新增第三方 GBM 库**，见 §5.2 D1） | §5.1 |
| 2 | **无需下载数据集**：`data/raw/` 的 132 个原始 CSV 已随仓库提供；确认文件齐全并跑一次 SHA256 校验（**S0 自检已于 11/08 实测通过，7/7 PASS，见 §3.4 与 `results/logs/s0_selfcheck_2026-11-08.txt`**） | §3.4 |
| 3 | 若使用 Agent / AI 编码工具，先补全 `.gitignore` 再提交任何代码 | §4.2 |

> 提交前自检：`git status` 里 `data/raw/*.csv` 应无改动；`data/interim/`、`data/processed/`、`data/external/` 下不应出现待提交文件；也不应出现 `CHARGED/`、`.workbuddy/`、`scripts/` 或任何 agent 生成物。

---

## 1. 项目简介

足球只是实验场，真正的问题是**「预测概率能不能信」**。保险定价、信贷审批、医疗辅助决策靠的都是概率而非类别标签，一个分类还行但概率乱给的模型在这些场景里是危险的。

本项目把博彩公司的**收盘赔率**当作最灵敏的测量仪器而不是对手：去抽水后的市场概率是公开可得的三分类预测里最强的一个，我们审计它是否校准（RQ1），并问一个只用赛前信息的透明模型能否追上它、差距集中在哪、差距来自信息优势还是可修复的校准缺陷（RQ2）。对外假设统一为 **H1–H4**（市场校准 / 模型追不上 / 差距局部化 / 信息而非校准），详见 `Team-32-Proposal_v3.0.md` §2。模型阶梯统一用 **`B0` 先验 → `B1` Elo → `B2` 有序 logit → `B3` 独立 Poisson → `B4` Dixon–Coles（主炮）→ `B5a` 同信息 GBM → `B5b` 全特征 GBM → `B6` 市场 → `B6r` 重校准市场**，共 9 个 arm；其中 B4→B5a 只换模型、B5a→B5b 只换信息，是仅有的两级单因素对照（记为 C1/C2，不占假设编号）。`M1`–`M5` 只指成员，提交版 Proposal 的 `M0`–`M4`/`MK`/`MK*` 映射表见 v3.0 §4 末。

评估协议：**expanding-window rolling origin**，8 个目标赛季 × 6 联赛 = **48 个块**、16,733 场评估比赛，每块只评估一次；主指标 **log loss**，辅以 Brier / RPS、可靠性曲线、校准斜率与截距、ECE；所有区间用 **48 块簇 bootstrap（10,000 次）**并附 **design effect**。**不使用 accuracy。全项目唯一等价边际 ±0.02 nats**（提交版曾用 ±0.01，48 簇下不可分辨，已统一）；H4 用 90% 区间上界 < 25% 判定。负结果同样是设计内的成功结论，判定规则在跑数前写死，事后不得修改。

> 本课工具落点：W3 Bootstrap（簇重采样区间 + design effect）、W5 样条 / GAM 与 W7 局部平滑（**主推断**：H1 可靠性曲线、H3 轮次 sweep；附录 A1 的 γ 趋势为描述性补充）。接口与防泄漏红线见 `docs/plans/data_interface.md`。

---

## 2. 仓库目录结构

> **本文件（§2.1 + §2.2）是目录结构的唯一书面说明。后续任何目录改动，必须同步修改这里（§2.4）。**

### 2.1 当前项目文件结构（**v2.0 / 2026-11-08**）

```
Football-Calibration/
├── .gitattributes                   # 禁止 Git 转换原始 CSV 换行符（§3.4）
├── .gitignore                       # 版本控制忽略规则（§4）
├── LICENSE
├── README.md                        # 本文件
│
├── data/                            # 数据：raw/ 已入库，其余子目录不入库
│   ├── raw/                         #   ★ 132 个原始 CSV（0304_*…2425_*）已入库，约 14 MB，文件不逐个列出
│   ├── interim/                     #   清洗 / 合并过程中的中间文件
│   ├── processed/                   #   panel.parquet、features*.parquet 等建模输入
│   ├── external/                    #   外部补充原始数据（队名别名原表、城市坐标等）
│   └── .gitkeep
│
├── configs/                         # 小型、必须入库的契约与配置
│   ├── README.md                    #   configs 的写入规则
│   ├── raw_manifest.csv             #   132 个原始 CSV 的 URL / 字节数 / SHA256 / 下载时间（T1.1 冻结凭据）
│   └── .gitkeep
│
├── src/                             # 全部可复用 Python 源码
│   ├── models/                      #   B0–B6 + B6r 各 arm 实现
│   ├── eval/                        #   harness / metrics / devig / bootstrap
│   └── .gitkeep
│
├── tests/                           # pytest 单测（含 test_leakage.py）
│   └── .gitkeep
│
├── results/                         # 代码直接产出、可重跑重建的中间数值结果
│   ├── preds/                       #   各模型 48 块预测 CSV（统一 schema）
│   ├── logs/                        #   收敛表、参数轨迹、S0 自检记录（*.log 忽略）
│   └── .gitkeep
│
├── analysis/                        # H1–H4 / 消融分析 notebook
│   └── .gitkeep
│
├── docs/                            # 模板、参考、方案类文件（入库）
│   ├── plans/                       #   方案 / 约定 / 变更记录（只放当前版本，历史版本归档于仓库外 old_docs/）
│   │   ├── Team-32-Proposal.pdf         #     2026-10-30 提交凭据（保留不改）
│   │   ├── Team-32-Proposal_v3.0.md     #     ★ 唯一执行蓝本（H1–H4 + B↔M 映射 + Revision notes）
│   │   ├── 08_小组分工实施方案_v1.3.md  #     ★ 当前唯一分工方案（v1.2 已归档至 old_docs/）
│   │   ├── 09_分工方案评审_v1.0.md        #     v1.1 的 19 项问题清单与实测复核（决策项已全部闭环）
│   │   ├── data_interface.md        #     v1.4：统一预测 schema、match_id / ISO 日期、标签重排、防泄漏红线
│   │   ├── CHANGELOG_structure.md   #     目录结构变更记录
│   │   ├── CHANGELOG_data.md        #     数据变更日志（11/10 由 M1 创建，T1.10）
│   │   └── roles/                   #     五份组员分工卡（可单独分发）
│   │       ├── README.md            #       索引 + 交接时点 + 跨人红线
│   │       ├── M1_数据工程与复现.md
│   │       ├── M2_评估与推断.md
│   │       ├── M3_结构化统计模型.md
│   │       ├── M4_机器学习与特征.md
│   │       └── M5_分析与统稿.md
│   ├── templates/                   #   图表清单 / 结果表 / 报告章节 模板
│   │   ├── figure_list_template.md
│   │   ├── results_table_template.md
│   │   └── report_section_template.md
│   ├── references/                  #   字段说明、文献与口径摘录
│   │   └── football_data_fields.md
│   ├── data_profile_v1.1.html       #   扩展口径 132 文件全量剖析（T1.1 交付口径，在库唯一版本）
│   └── .gitkeep
│
├── products/                        # 面向交付 / 展示的最终产物（入库，定稿后冻结）
│   ├── figures/                     #   fig01–fig08 等图片
│   ├── tables/                      #   排版完成的成品表格
│   ├── poster/                      #   Poster
│   ├── report/                      #   report.pdf 及源稿 report.md
│   ├── slides/                      #   slides.pdf（10 页）及源稿
│   ├── video/                       #   8 分钟录像（大文件默认忽略，§4.3）
│   └── .gitkeep
│
└── appendix/                        # 源码附录复现包
    ├── requirements.txt             #   依赖锁定清单（必须与 README §5.2 一致）
    └── .gitkeep
```

**说明**

- 当前为空的目录都放了一个空的 `.gitkeep` 占位文件，保证 `clone` 后结构完整；目录里出现第一个正式文件后可删除对应 `.gitkeep`（删了也要按 §2.4 同步本文件）。**`data/raw/` 已有 132 个正式文件，其 `.gitkeep` 已删除**；结构树中该目录的 132 个 CSV 不逐个列出，完整清单见 `configs/raw_manifest.csv`。
- **版本文件只留最新一份**：`docs/`（含 `docs/plans/`、数据集剖析报告等）中同一份文档只保留当前版本（文件名带版本号）。被取代的旧版移入项目根目录 `old_docs/`（仓库外，不入库、不进 Git 历史），保留原文件名以便追查。目前已归档：`08_小组分工实施方案_v1.0.md`、`v1.1.md`、**`v1.2.md`**、`data_profile_v1.0.html`。**例外**：`Team-32-Proposal.pdf` 是 10/30 已提交的计分凭据，v3.0 以新增 Markdown 形式并存，不覆盖 PDF。**v1.1 中的数值（约 45,000 场 / 17,000 场 / B0 ≈ 1.03–1.05 / B365 基准）已作废，不要再引用。**
- 上表只列出**当前已存在**的文件；唯一例外是 `docs/plans/CHANGELOG_data.md`，已标注 11/10 由 M1 的 T1.10 创建，创建后无需再改结构树。`src/` 下的脚本、`configs/` 下的 `splits.json` / `team_alias.csv` / `feature_whitelist_b5a.csv`、`appendix/` 下的 `run_all.sh` / `MANIFEST.md` 等由各组员按分工方案产出后再补进结构树。**路径口径以 `08_小组分工实施方案_v1.3.md` §5.2 为准**：必须全组一致的小文件放 `configs/`（与原始数据分离，便于 review 与 diff），会被报告引用的成品放 `products/`。`data/raw/` 自 v1.6 起已入库，该目录只放 132 个原始 CSV，不放契约文件。`raw_manifest.csv` 已于 2026-11-07 按分工方案 T1.1 随 132 个 CSV 下载生成（§3.3 冻结要求）；数据集剖析报告在库只有 `data_profile_v1.1.html`（扩展口径 132 文件），其主口径 54 文件的历史版 `v1.0` 已归档至 `old_docs/`，两者评估窗同为 48 块。

### 2.2 目录职责表

| 目录 | 放什么 | 不放什么 | 入库 | 主责 |
|---|---|---|---|---|
| `data/` | `raw/`：**132 个原始 CSV 快照（已入库）**；`interim/` `processed/` `external/`：可由代码重建的大文件 | 原始 CSV 之外的任何数据；需要版本控制的小型契约表（放 `configs/`） | **仅 `raw/` ✅**，其余 ❌ | M1 |
| `configs/` | 小而必须全组一致的契约：`splits.json`、`team_alias.csv`、`feature_whitelist_b5a.csv`、`raw_manifest.csv` | 大体量数据 | ✅ | M1 / M4 |
| `src/` | 全部可复用 Python 源码 | 一次性脚本、agent 自动脚本（放 `scripts/`，已忽略） | ✅ | 全员 |
| `tests/` | pytest 单测，尤其 `test_leakage.py` | — | ✅ | M1 / M2 |
| `results/` | 可重跑重建的机器可读中间数值：预测 CSV、收敛表、参数轨迹 | 已排版、会被报告引用的成品 | ✅（默认） | M2 / M3 / M4 |
| `analysis/` | H1–H4、消融的 notebook | 成品图 / 成品表 | ✅ | M2 / M3 / M4 / M5 |
| `docs/` | **模板、参考文件、方案类文件**：Proposal v3.0（唯一蓝本）+ 提交版 PDF、分工方案 v1.3（当前权威）、方案评审、`plans/roles/` 五份组员分工卡、接口约定、结构变更记录、各类模板、字段速查、数据集剖析报告（HTML） | 代码、数据、实验结果 | ✅ | M5 |
| `products/` | **产物类文件**：实验生成的图片、成品表格、Poster、Report、Slides、录像 | 中间数值、临时草稿 | ✅（大文件除外） | M5 |
| `appendix/` | 复现包脚本与清单 | 生成好的 `appendix.zip` | ✅ | M1 |

### 2.3 `docs/` 与 `products/` 的边界（判断规则）

- **`docs/`** = 写给人看的**过程性文字**：模板、参考资料、方案、约定。改动不影响任何数字。
- **`products/`** = **拿去交付 / 展示的成品**：图、表、poster、report、slides、录像。
- **`results/` vs `products/` 的唯一判据**：*这个文件会不会被 Report / Slides / Poster 直接引用？*
  - 不会 → 留在 `results/`，可以随时重跑覆盖；
  - 会 → 导出 / 复制到 `products/` 对应子目录，并在 `docs/plans/CHANGELOG_structure.md` 记一笔。
- 报告里引用的结论性数字，一律从 `products/tables/` 的成品表取，不要从 `results/` 的临时文件手工抄。
- **唯一入库的数据目录是 `data/raw/`**（原始 CSV 快照）。`data/` 其余子目录仍不入库；图、表、poster、report 等成品仍一律走 `products/`，不要因为「数据能入库了」就往 `data/` 里塞产物。

### 2.4 目录结构变更的强制同步规则

> **谁改目录，谁在同一个 PR 里改 README。**

1. 新增 / 删除 / 重命名任何一级或二级目录，或新增结构树中列出的文件，必须同步更新 §2.1 结构树与 §2.2 职责表；
2. 同时在 `docs/plans/CHANGELOG_structure.md` 追加一行（日期 / README 版本 / 变更 / 操作人 / PR）；
3. 若变更影响忽略规则，同步修改根目录 `.gitignore` 并在 §4.1 说明；
4. README 顶部「本文档版本」递增（v1.0 → v1.1 …），并在 §7 修订记录登记；
5. PR review 时把「README 与实际目录一致」列为检查项，可用 `git ls-files | sort` 与 §2.1 逐行比对。

---

## 3. 数据集（`data/raw/` 已入库）

### 3.1 来源与范围

| 项 | 内容 |
|---|---|
| 数据源 | [football-data.co.uk](https://www.football-data.co.uk/) — 公开下载，免注册、免 API key |
| 文件形式 | 每个「联赛 × 赛季」一个 CSV，比赛级 |
| URL 模板 | `https://www.football-data.co.uk/mmz4281/{season}/{div}.csv`（`www` 会 302 到无 `www`，下载命令必须允许重定向） |
| 赛季编码 | 4 位，起止年后两位拼接：`1617` = 2016/17、`1920` = 2019/20、`2021` = 2020/21、`2425` = 2024/25 |
| 联赛代码 | `E0` 英超 · `SP1` 西甲 · `I1` 意甲 · `D1` 德甲 · `F1` 法甲 · `N1` 荷甲 |
| **主口径（Proposal，评估口径）** | 2016/17–2024/25：`1617 1718 1819 1920 2021 2122 2223 2324 2425` × 6 = **54 个 CSV**；18,865 场，2016/17 作初始训练块，评估 48 块共 16,733 场。是 132 个文件中最近 9 季的子集 |
| **扩展口径（分工方案 T1.1，下载口径）** | 2003/04–2024/25：`0304 … 2425` × 6 = **132 个 CSV**，已全量下载；实测 46,507 场（分工方案预估「约 45,000」应以实测值替换）。主口径外的 14 季只作训练历史 |
| **仓库内快照（2026-11-07 起）** | `data/raw/` 下 **132 个 CSV 已入库**，共 **14,341,191 字节（约 13.7 MiB）**，最大单文件 197 KB；`configs/raw_manifest.csv` 记录每个文件的 URL / 字节数 / SHA256 / 下载时间，已逐行校验通过（0 不一致）。**组员 clone 后无需重新下载** |
| 基准列 | Pinnacle **收盘**赔率 `PSCH / PSCD / PSCA`；`MaxCH / MaxCD / MaxCA`（市场最高收盘价）作稳健性基准，2019/20 起可得 |
| 目标 | `FTR` 三分类 H / D / A → `y ∈ {0,1,2}` |

> **`data/raw/` 已入库（2026-11-07 起）**：132 个原始 CSV 共约 14 MB，体积可控且远低于 GitHub 单文件 100 MB 限制，因此改为随仓库分发——**组员 clone 后直接可用，不必再各自下载**，也避免源站改版导致各人快照不一致。`data/interim/`、`data/processed/`、`data/external/` 仍不入库（可由代码重建）。§3.2 的下载命令**仅在需要重建 / 补漏 / 更新快照时**才执行；任何对 `data/raw/` 的改动都必须走 PR 并同步 `configs/raw_manifest.csv`。

### 3.2 下载方式（仅用于重建 / 补漏 / 更新快照）

> **首次 clone 不需要执行本节。** 仓库已含全部 132 个 CSV。只有以下情形才需要重下：① 源站改版需更新快照；② `missing.csv` 出现缺失；③ 在干净环境验证 §3.4 的校验和。
> **重下会改动已入库文件，必须走 PR 并同步 `configs/raw_manifest.csv`，禁止私自覆盖后直接 commit。**

**A. Git Bash / macOS / Linux（重建完整 132 个文件）**

```bash
mkdir -p data/raw
BASE="https://www.football-data.co.uk/mmz4281"
SEASONS=(0304 0405 0506 0607 0708 0809 0910 1011 1112 1213 1314 1415 1516 \
         1617 1718 1819 1920 2021 2122 2223 2324 2425)
DIVS=(E0 SP1 I1 D1 F1 N1)
: > data/missing.csv                 # 放在 data/ 根，已被忽略，不入库
for s in "${SEASONS[@]}"; do
  for d in "${DIVS[@]}"; do
    curl -fSL --retry 3 --retry-delay 2 -o "data/raw/${s}_${d}.csv" "$BASE/$s/$d.csv" \
      || echo "$BASE/$s/$d.csv" >> data/missing.csv
    sleep 1
  done
done
ls data/raw/*.csv | wc -l          # 应为 132
```

- 只需 Proposal 主口径时，把 `SEASONS` 换成后 9 季 `1617 … 2425`（54 个文件）；但**不要因此删掉仓库里其余 78 个 CSV**，它们是训练历史。
- **注意 2020/21 的赛季码就是 `2021`（20+21）**，不要漏掉或另写。
- `curl -f` 让 404 显式失败并记入 `missing.csv`，**不要静默跳过**；请求间隔 1 秒，别把源站打爆。
- `missing.csv` 放在 `data/` 根（被 `/data/*` 忽略），避免污染已入库的 `data/raw/`。

**B. Windows PowerShell**

```powershell
$base    = "https://www.football-data.co.uk/mmz4281"
$seasons = @("0304","0405","0506","0607","0708","0809","0910","1011","1112","1213","1314","1415","1516",
             "1617","1718","1819","1920","2021","2122","2223","2324","2425")
$divs    = @("E0","SP1","I1","D1","F1","N1")
New-Item -ItemType Directory -Force data/raw | Out-Null
foreach ($s in $seasons) {
  foreach ($d in $divs) {
    try {
      Invoke-WebRequest -Uri "$base/$s/$d.csv" -OutFile "data/raw/${s}_${d}.csv" -ErrorAction Stop
    } catch {
      "$base/$s/$d.csv" | Out-File -Append -Encoding utf8 data/missing.csv
    }
    Start-Sleep -Seconds 1
  }
}
```

**C. 按赛季打包（备选）**：官网另提供 `https://football-data.co.uk/mmz4281/{season}/data.zip`，含该赛季全部联赛 CSV；解压后同样放 `data/raw/`。压缩包本身不入库（`*.zip` 已忽略）。

**下载失败留痕**：`data/missing.csv` 是 T1.1 的审计凭据——132 个 URL 中任何 404 / 超时 / 空文件都要写一行（含原因），**不许静默跳过**。当前该文件**只有表头、0 条数据**，表示 2026-11-07 核验的 132/132 全部成功、0 缺失（与 `configs/raw_manifest.csv` 132 行 SHA256 互相印证）。空文件与「根本没做检查」在验收上不是一回事：G1 验收项 #1 的判据即「`missing.csv` 为空或每条有原因」。该文件自 v1.9 起显式放行入库；此后只在 §3.2 重建 / 补漏时追加记录。

### 3.3 字段与已知坑

| 坑 | 处理 |
|---|---|
| 编码 | 老文件常见 `latin-1` / `cp1252`，较新文件可能带 UTF-8 BOM；先试 `utf-8-sig`，报错再回退 `latin-1`，抽查 `Saint-Étienne` 等队名。132 文件实测仅 `0405_E0.csv` 为 `cp1252`，其余 131 个为 UTF-8 族 |
| BOM | 部分文件首列是 `\ufeffDiv`（如 2425 的非英超联赛），读取时显式去掉 |
| 日期 | 老文件 `dd/mm/yy`、新文件 `dd/mm/yyyy` 混用（**单文件内不混合**：73 个文件两位年、29 个四位年）；`pd.to_datetime(..., dayfirst=True, format='mixed')` 实测全库 0 NaT、范围 `2003-08-01 → 2025-05-25`。**落盘一律 ISO `YYYY-MM-DD`**，见 `data_interface.md` §1.0 |
| 列名随赛季变化 | 2016/17 为 65 列、2019/20 起约 106 列、2024/25 达 119–120 列（随联赛不同）；**按列名取数，绝不按位置取**。表头另有 2 种变体（96 个无 `Time` 列、36 个有） |
| **行字段数不齐（r3 实测）** | **11 个文件**行字段数多于表头（行末多余空字段），裸 `pd.read_csv` 直接抛 `ParserError: Expected N fields`。用 `csv.reader` 按表头列名取数并截断；**禁止 `on_bad_lines='skip'`**——`0304_F1.csv` 会一次静默丢 365 场真实比赛 |
| **表头重复列名（r3 实测）** | **14 个文件**表头含重复列名（含空串 `''`），整表 `pd.concat` / `reindex` 会抛 `InvalidIndexError` / `ValueError`。只按白名单列构造 DataFrame，详见 M1 分工卡 T1.2-a 参考实现 |
| **整列缺失与空白行（r3 实测）** | `PSCH/PSCD/PSCA` 在 **54 个文件**里是「列不存在」而非「值为空」（0304–1112 共 9 季 × 6），须按白名单补 NaN；另有 **7 个文件共 11 行全空白**，显式 drop 后 `46,518 → 46,507` |
| 收盘 vs 非收盘 | 无 `C` 的是开市后采集的赔率，带 `C` 的才是收盘。基准必须用 `PSCH/PSCD/PSCA`，**不能用 `PSH/PSD/PSA`**，否则会系统性缩小「模型 vs 市场」的差距 |
| 队名 | `Man United` / `Manchester Utd` 等同义写法，先按 `configs/team_alias.csv` 统一再做 Elo |
| 覆盖率 | 实测荷甲 **2017/18 前**（0304–1617 共 14 季）无射门列，1718 起齐备；西甲 / 意甲 / 法甲 0304、0405 两季亦缺。法甲 2019/20 仅 279 场、荷甲 2019/20 仅 232 场（赛季腰斩）。如实保留，不插补、不删赛季 |
| 冻结 | `configs/raw_manifest.csv`（132 行 URL / 字节数 / SHA256 / 下载时间）已入库并逐行校验通过；`data/raw/` 现已随仓库分发，**此后不要联网重下**。确需更新须走 PR、重算 manifest 并通知全组。**因此 T1.1 已交付完毕，无需实现 `src/download.py`**：复现包从已入库的 raw 起跑，只在补漏 / 更新快照时按 §3.2 的纯 shell 命令重建，详见 `docs/plans/roles/M1_数据工程与复现.md` T1.1 |

字段全表见 `docs/references/football_data_fields.md`，官方说明 <https://www.football-data.co.uk/notes.txt>。

### 3.4 一致性校验（clone 后建议跑一次）

数据入库后，**Git 本身保证所有人拿到同一 commit 的同一份字节**；`configs/raw_manifest.csv` 是第二重校验，用于发现换行符被改写、文件被误覆盖等情况。

```bash
# Git Bash / macOS / Linux
git status --short data/raw          # 应无输出（工作区干净）
python - <<'PY'
import csv, hashlib
rows = list(csv.DictReader(open('configs/raw_manifest.csv', newline='', encoding='utf-8-sig')))
bad = []
for r in rows:
    b = open('data/raw/' + r['file'], 'rb').read()
    if len(b) != int(r['bytes']) or hashlib.sha256(b).hexdigest() != r['sha256']:
        bad.append(r['file'])
print(f'checked {len(rows)} files, mismatches = {len(bad)}', bad[:5])
PY
```

Windows PowerShell 不支持上面的 heredoc，可把 Python 段保存为 `scripts/check_raw.py` 后运行（`scripts/` 已被忽略），或用 `Get-FileHash -Algorithm SHA256` 逐文件对照 manifest。

> **为什么需要 `.gitattributes`**：源站 CSV 是 **CRLF + UTF-8 BOM**。若某台机器设了 `core.autocrlf=true`，Git 会在 checkout 时改写换行符，文件字节随之变化，manifest 的 SHA256 就会全部失配。根目录 `.gitattributes` 把 `data/raw/*.csv` 标为 `-text`，强制按字节存取、不做 EOL 转换，**不要删这条规则**。

校验不通过时，先查 `git config core.autocrlf` 与本地编辑器是否改写了换行符；确实需要更新快照时走 PR 并同步 manifest，**不要擅自更新 manifest 或私自覆盖已入库的 CSV**。

> ✅ **S0 实测（2026-11-08 20:16，M1）**：上述校验连同 Git 状态、132 文件数与总字节、`data/missing.csv`、`2425_E0.csv` 抽样、Python / 8 个依赖版本、`.gitattributes` 共 **7 项全部 PASS**；本机 `core.autocrlf=true`，因 `-text` 规则 SHA256 仍 0 失配，正说明该规则不可删。逐项明细与环境快照见 `results/logs/s0_selfcheck_2026-11-08.txt`，交付状态见 `docs/plans/roles/M1_数据工程与复现.md` §3.1。

### 3.5 ⚠️ 两份依据文档的口径差异（待组内确认）

> **2026-11-08 起口径已统一，本节不再是待办清单。** 组内确认「Proposal 并非不能改，有缺陷可以改」，按「假设体系用提交版 H1–H4、实验设计用分工方案的 B0–B6」合并成单一蓝本：`Team-32-Proposal_v3.0.md` + `08_小组分工实施方案_v1.3.md`。U3 闭环，接口冻结不再被命名问题阻塞。

| 项目 | 定稿口径 | 依据 |
|---|---|---|
| 研究问题 / 假设 | **RQ1/RQ2 + H1–H4**（市场校准、模型追不上、差距局部化、信息而非校准） | v3.0 §1–§2 |
| 模型命名 | **`B0`–`B6` + `B6r`** 共 9 个 arm；`M1`–`M5` 只指成员；`preds_{B0..B6,B6r}.csv`、`model` 列同值 | v3.0 §4 / `data_interface.md` §1 |
| 阶梯 | B4→B5a 只换模型、B5a→B5b 只换信息（C1/C2）；B1→B2、B2→B3 不做归因 | v1.3 §0.3 |
| 降级内容 | 原 H1「结构 vs 灵活」→ C1/C2；原 H2a/H2b → 描述性误差分析与稳健性；原 H3 主场优势 → **附录 A1**（不做因果主张） | v1.3 §0.4 |
| 阈值 | **唯一等价边际 ±0.02 nats**；H4 用 90% 区间上界 < 25% | v3.0 §2 / §5 |
| 防泄漏新增 | B6r 两参数只在 train 段**且 `PSCH` 三列齐全**的比赛上拟合（`PSCH` 自 2012/13 才有），每折 `n_fit` 记日志；`is_promoted_*` / `matchday` 只由季前名单与赛程构造 | `data_interface.md` §2 |
| 数据窗口 | 下载 132 CSV / 46,507 场；评估窗 1718–2425 = 48 块 / 16,733 场；B6 有效 n = 16,728（3 块共 5 场缺三列收盘赔率：`1718_SP1` 1 / `1718_N1` 3 / `1819_D1` 1，drop 不回填） | §3.1 / v1.3 §5.5 |
| 报告要求 | B↔M 映射表 + *Evolution of the proposal* 段（100–150 字）；给 instructor 的简短报备并入 U2 确认信 | v3.0 Revision notes |

> **为什么要改 Proposal 而不是写 deviation 说明**：提交版 §4 的 M4 用 M2 的信息集却与 M3 做归因（违反讲义「一次只改一个因素」），H1 把可靠性曲线方向写反，MK\* 的 in-sample 边界未落到 train 段；这些是实质设计缺陷，不是命名差异。Proposal 只占 2 分且已于 11/01 截止，17 分的报告不应被它绑住；v3.0 保留 RQ1/RQ2 与 H1–H4 主线未变，属计划迭代而非换题。**提交版 PDF 不覆盖**，作为提交凭据保留。

### 3.6 可再生派生物的交付约定（2026-11-07 定）

| 文件 | 是否入库 | 11/08 怎么交给 M2/M3/M4 | 判定规则 |
|---|---|---|---|
| `data/processed/panel.parquet`（46,507 行建模总表） | ❌ **不入库**（`.gitignore` 全局 `*.parquet` + `/data/processed/*`） | **全组各自运行 `src/build_panel.py` 一键重跑生成**；群里发的副本仅供救急，不作权威版本 | 契约是「同一脚本 → 同一张表」，不是「传同一个二进制」；T1.7 干净环境复现也以脚本重跑为准。**不要为此放行 parquet** |
| `configs/splits.json`、`configs/team_alias.csv`、`configs/feature_whitelist_b5a.csv` | ✅ 入库 | 随 Git 分发 | KB 级、纯文本、可 diff 的小契约（§2.2） |
| `data/missing.csv` | ✅ 入库 | 随 Git 分发 | 只有表头 = 0 缺失的审计凭据（§3.2） |

> **判定规则**：入库的是**原始输入 + 契约**，不入库的是**可由代码重建的派生物**。派生物若各人不一致，应靠 `build_panel.py` 与断言查出来，而不是靠传同一个文件掩盖差异。

**`y` 编码与类别顺序**（详见 `data_interface.md` §1.1）：`FTR` 的 `H/D/A` → `y = 0/1/2` 直接写进 `panel.parquet`，概率列恒为 `p_home, p_draw, p_away` 且 **`p_home` 在第一列**，`build_panel.py` 内写成断言。此口径已预置，**M1 不必等 M2 在 11/09 给口径**，M2 于接口冻结时签字确认即可。 **模型内部标签顺序自由**（B2 有序 logit 常用 客胜=0 / 平=1 / 主胜=2，HGB 按 `classes_`），但**落盘前必须重排成 `p_home,p_draw,p_away` 并写断言**；详见 `data_interface.md` §1.1（v1.3 新增）。

---

## 4. 版本控制与 `.gitignore`

### 4.1 已忽略的内容（摘要）

| 类别 | 规则 |
|---|---|
| **数据** | **`data/raw/*.csv` 与 `data/missing.csv` 不忽略（已入库）**；`data/` 其余内容（仅 `.gitkeep` 保留）；`*.parquet / *.feather / *.pkl / *.h5 / *.npy / *.db / *.pt` 等大文件（详见 §3.6） |
| **项目约定** | `CHARGED/`（含大小写变体） |
| **Agent 自动生成** | `.workbuddy/`、`.tools/`、`scripts/`、`.claude/`、`.cursor/`、`.codex/`、`.aider*`、`.continue/`、`.windsurf/`、`.roo/`、`.kiro/`、`.gemini/`、`.qwen/`、`.trae/`、`.cline/`、`.serena/`、`.agent/`、`.mcp/`、`AGENTS.local.md`、`CLAUDE.local.md` |
| **Python** | `__pycache__/`、`*.pyc`、`*.egg-info/`、`build/ dist/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`.coverage`、`htmlcov/`、`.ipynb_checkpoints/`、`.venv/ venv/ env/` |
| **密钥 / IDE / OS** | `.env*`、`*.pem`、`*.key`、`secrets/`、`.idea/`、`.vscode/`、`.DS_Store`、`Thumbs.db` |
| **日志 / 临时** | `*.log`、`/logs/`、`*.tmp`、`*.bak`、`/tmp/`、`temp/`、`.cache/`、`cache/` |
| **大体积成品** | `*.zip`、`*.mp4`、`*.mov`、`*.avi`、`*.mkv` 等 |

> `.gitignore` v1.1 起 `data/raw/` 由「忽略」改为「入库」，配套新增根目录 `.gitattributes`（`data/raw/*.csv -text`，防止 CRLF 被转换导致 SHA256 失配）。**两者都不要回退**，详见 §3.4。
>
> `.gitignore` **v1.2** 起额外放行 `data/missing.csv`（T1.1 的 0 缺失审计凭据，见 §3.2）；`panel.parquet` 仍不入库（§3.6）。

> 刻意**不**忽略 `*.csv` / `*.json` / `*.xlsx` / `*.pdf` / `*.png`：`data/raw/` 的原始快照、`configs/` 的契约表、`results/` 的预测表、`docs/` 的方案、`products/` 的成品图与 PDF 都需要入库。

### 4.2 使用 Agent 的组员：必须自行补全 `.gitignore`（强制）

> **如果组员使用 Agent / AI 编码工具，该组员有责任把该工具在仓库内生成的、不需要参与版本控制的所有文件或文件夹，自行逐条补进根目录 `.gitignore`，并把这次修改一起提交。**

操作要求：

1. 首次启用该工具后，先跑 `git status` 与 `git status --ignored`，确认新出现的目录 / 文件；
2. 把其中属于「工具缓存、本地配置、自动脚本、临时产物」的路径**逐条**加入 `.gitignore` 对应小节；不要用一条 `*` 通配糊过去，避免误伤正式文件；
3. 若出现清单里没有的新工具目录，同时在本 README §4.1 的 Agent 清单补一行；
4. 提交前自检：`git status` 中不出现任何 agent 生成物；
5. **`scripts/` 已整体忽略**，它是留给 agent 自动脚本的目录。需要版本控制的脚本请放 `src/` 或 `appendix/`，不要放 `scripts/`；如确需把某个 `scripts/` 纳入版本控制，必须先改 `.gitignore` 并在组内说明。

### 4.3 大文件与压缩包

`products/video/` 的录像、`appendix.zip` 等默认不入库（GitHub 单文件 100 MB 限制，且录像属于提交平台的交付物）。若组内决定纳入版本控制，二选一：① 配置 Git LFS；② 删除 `.gitignore` 中对应规则。**无论哪种，都要同步更新 §2.1 与 §4.1 的说明。**

---

## 5. Python 环境与依赖版本

### 5.1 运行时

**本项目统一使用 Python `3.14.x`：`3.14.7` 与 `3.14.10` 均可。**

本机开发环境为 conda 环境 **`DSC5001_Project`**（`D:\Miniconda3\envs\DSC5001_Project`，Python **3.14.10**）；干净复现环境另用 `python -m venv .venv` 按 §5.2 装依赖，两者互不冲突。

```bash
conda activate DSC5001_Project      # 本机开发
python --version                    # 3.14.7 或 3.14.10 均可
python -m venv .venv                # 干净复现环境，.venv 已被忽略
source .venv/bin/activate           # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r appendix/requirements.txt
```

> ✅ **兼容性已实测（2026-11-07）**：Python 3.14.10 下 §5.2 全部 8 个直接依赖均有 `cp314` wheel，安装后均可正常 `import`。仍按原规则：**不要私自更换 Python 版本**；确需变更先组内确认，再同步 §5.2 与 `appendix/requirements.txt`。
>
> ⚠️ **S0 实测提醒（2026-11-08）**：本机命令行默认 `python` 指向 WorkBuddy 内置 **3.13.14**，且未安装项目依赖，直接 `python src/build_panel.py` 或 `pytest -q` 会报 `ModuleNotFoundError`——这不是依赖没装好，而是用错了解释器。开跑前先 `conda activate DSC5001_Project`，并用 `python -c "import sys; print(sys.executable)"` 确认路径为 `D:\Miniconda3\envs\DSC5001_Project\python.exe`。

### 5.2 依赖版本登记表（唯一权威清单）

> **规则：后续安装任何 Python 包或组件，都必须在合并 PR 之前，把「确切版本」加到这张表里，并同步写入 `appendix/requirements.txt`（`包名==x.y.z` 格式）。禁止只写「最新版」或 `>=x`。**

| 组件 | 精确版本 | 类型 | 用途 | 登记日期 | 登记人 |
|---|---|---|---|---|---|
| Python | `3.14.7` / `3.14.10` | 运行时 | 全项目统一解释器（本机 `DSC5001_Project` = 3.14.10） | 2026-11-07 | — |
| pandas | `3.1.1` | 第三方包 | 读 132 个 CSV、字段统一、拼总表（T1.2 / T1.3） | 2026-11-07 | M1 |
| numpy | `2.5.4` | 第三方包 | 数值计算、随机种子与数组运算（全员） | 2026-11-07 | M1 |
| pyarrow | `26.0.1` | 第三方包 | Parquet 读写，产出 `data/processed/panel.parquet`（T1.3） | 2026-11-07 | M1 |
| pytest | `9.2.0` | 第三方包 | 泄漏测试与场次断言（T1.3-a / T1.6） | 2026-11-07 | M1 |
| matplotlib | `3.11.2` | 第三方包 | 覆盖率矩阵图与报告成品图（T1.4 / M5） | 2026-11-07 | M1 |
| scipy | `1.18.1` | 第三方包 | 去抽水、Dixon–Coles 极大似然优化、统计检验（M2 / M3） | 2026-11-07 | M1 |
| scikit-learn | `1.9.1` | 第三方包 | 指标实现交叉核对；**`HistGradientBoostingClassifier` 为 B5a / B5b 的 GBM 实现（D1，零新增依赖）**（M2 / M4） | 2026-11-07 | M1 |
| statsmodels | `0.15.0` | 第三方包 | 有序 logit B2、市场校准斜率与截距、H3 固定效应回归（M2 / M3 / M5） | 2026-11-07 | M1 |

登记格式要求：

- 版本必须精确到 `x.y.z`（含补丁号），例如 `pandas==3.1.1`，不写 `pandas>=2.0`；
- 每行写明用途、登记日期与登记人；同一组件升级版本时**新增一行**并注明替换了哪个版本，不覆盖历史；
- `appendix/requirements.txt` 必须与本表的**第三方包行逐行一致**（Python 行是运行时，不写入该文件），`run_all.sh` 的冷启动复现以该文件为准；
- 装包后确认该包在 Python 3.14.x 下可正常 `import`；
- 本表只登记**直接依赖**；间接依赖由 pip 解析，T1.7 复现包另附一份 `pip freeze` 全量快照备查。
> **D1 决策（2026-11-08，README v2.1）**：B5a / B5b 的梯度提升统一用 **scikit-learn 1.9.1 内置的 `HistGradientBoostingClassifier`**（`loss='log_loss'`、`early_stopping=True`、必须传 `sample_weight`），**不引入 LightGBM / XGBoost / CatBoost，依赖总数保持 8 个**。
> 原稿参数 `num_leaves` / `n_estimators` / `objective='multiclass'` 对应改为 `max_leaf_nodes` / `max_iter` / `loss='log_loss'`，见分工方案 v1.3 §3.4 D1 决策。
> 理由：C1/C2 锁的是「同一实现 + 同一权重 + 同一超参」而非某个特定库；Python 3.14 较新，第三方 GBM 会带来额外间接依赖并污染 T1.7 的冷启动复现。

### 5.3 复现包

`appendix/` 存放 `requirements.txt`、`run_all.sh`、`MANIFEST.md`（哪个数字出自哪个脚本）。三者与 §5.2 的表保持一致，由 M1 维护；附录需在干净环境 30 分钟内产出与仓库一致的主表。

---

## 6. 协作约定（摘要）

- 每次合并走 PR，至少 1 人 review，跨工作包优先（分工方案 §4.4）；
- 冻结标签：`data-v1.0`(11/10)、`harness-v1.0`(11/13)、`code-v1.0`(11/24)、`report-v1.0`(11/28)；
- 统一预测文件 schema 与防泄漏红线见 `docs/plans/data_interface.md`，术语口径与图表清单见 `docs/templates/figure_list_template.md`；
- 负结果即成功；**唯一等价边际 ±0.02 nats** 等判定规则在跑数前写死，不得事后修改；
- 模型命名、假设编号、阶梯口径以 `Team-32-Proposal_v3.0.md` + `08_小组分工实施方案_v1.3.md` 为唯一依据，任何新文档不得再引入 `M0`–`M4` / `MK` 作为模型名。

## 7. 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-11-07 | 首版：建立仓库目录骨架、`.gitignore`、README 结构说明、数据集下载方式、Python 3.14.7 与依赖版本登记规则、目录结构变更同步规则 |
| v1.1 | 2026-11-07 | 新增 `configs/raw_manifest.csv`（主口径 54 个 CSV 的校验和冻结凭据）与 `docs/data_profile_v1.0.html`（数据集规模 / 结构 / 文件间关系剖析报告）；同步 §2.1 结构树、§2.2 职责表，登记 §3.5 下载执行状态与场数交叉验证结论 |
| v1.2 | 2026-11-07 | 按分工方案 T1.1 补齐下载至 132 个 CSV，`raw_manifest.csv` 扩为 132 行并逐行校验；新增 `docs/data_profile_v1.1.html`（扩展口径全量剖析）；§3.1 / §3.2 / §3.3 / §3.5 明确「132 下载口径 + 48 块评估口径」不冲突，修正荷甲射门列起始年份与编码实测结论；v1.0 报告加版本提示条 |
| v1.3 | 2026-11-07 | 新增 `docs/plans/08_小组分工实施方案_v1.2.md`（当时权威，数值经 132 个 CSV 实测校正）、`docs/plans/09_分工方案评审_v1.0.md`（v1.1 的 19 项问题）、`docs/plans/roles/`（M1–M5 五份分工卡 + 索引）；v1.1 标为历史版本；同步 §2.1 结构树与 §2.2 职责表 |
| v1.4 | 2026-11-07 | **`docs/` 改为只保留各文件最新版本**：历史版 `08_小组分工实施方案_v1.1.md` 移出仓库至项目根 `old_docs/`（与 `v1.0` 同处，仓库外、不入库）；§2.1 结构树删去历史版本行并新增版本归档规则；§3.5 口径差异表改以 v1.2 为对照（市场基准与数据窗口两项已对齐，仅剩命名/编号待定）；同步顶部依据文档与版本号 |
| v1.5 | 2026-11-07 | 历史版 `docs/data_profile_v1.0.html`（主口径 54 文件剖析）移入 `old_docs/`，`docs/` 剖析报告只剩 `data_profile_v1.1.html`；§2.1 结构树、§2.2 说明与 §3.5 执行状态同步改为单一份报告的表述；版本归档规则扩至 `docs/` 全域（含 HTML）；删除项目根重复留档 `08_小组分工实施方案_v1.1.md`（md5 与 `old_docs/` 归档件一致） |
| v1.6 | 2026-11-07 | **`data/raw/` 132 个原始 CSV 改为入库**（14,341,191 字节，clone 即用、组员无需各自下载）：`.gitignore` 升 v1.1 放开 `data/raw/`，删除 `data/raw/.gitkeep`；新增根目录 `.gitattributes`（`data/raw/*.csv -text`）防止 CRLF 被转换导致 132 行 SHA256 失配。同步 §0 首次克隆步骤与自检、§2.1 结构树与说明、§2.2 职责表、§2.3 边界、§3 全节（标题 / 来源范围 / 下载改为「仅重建时用」/ 一致性校验 / 执行状态）、§4.1 忽略清单；并修正 `configs/README.md`、M1 分工卡、分工方案 v1.2 §5.2 中「不入库 / 全员自行下载」的旧表述 |
| v1.7 | 2026-11-07 | Python 运行时由固定 `3.14.7` 放宽为 `3.14.x`（3.14.7 / 3.14.10 均可），登记本机 conda 环境 `DSC5001_Project`；§5.2 登记 8 个直接依赖精确版本（pandas 3.1.1 / numpy 2.5.4 / pyarrow 26.0.1 / pytest 9.2.0 / matplotlib 3.11.2 / scipy 1.18.1 / scikit-learn 1.9.1 / statsmodels 0.15.0），同步 `appendix/requirements.txt`；**明确 T1.1 已交付、无需 `src/download.py`**，复现包从已入库 raw 起跑、不联网重下（重建入口 §3.2）；同步 M1 分工卡与 `08_分工方案_v1.2 §3.1` 的 T1.1 行 |
| v1.8 | 2026-11-07 | **契约文件口径统一（非目录变更）**：§2.2 与 `configs/README.md` 中的 `feature_whitelist.csv` 统一为 **`feature_whitelist_b5a.csv`**（与 §2.1 结构树、分工方案 v1.2 T4.5 / §5.2、M4 分工卡一致），`configs/README.md` 补明四列 `feature / source / allowed / sample_weight_rule` 与「M4 产出、M3 会签」；`splits.json` 冻结时点由 `configs/README.md` 的 11/10 `data-v1.0` 改为 **11/09 接口冻结**（11/10 标签仅作复核），与 `roles/README.md`、M1 分工卡一致。同步 `docs/plans/CHANGELOG_structure.md` |
| v1.9 | 2026-11-07 | **开工前口径全部落地**：① 新增 **§3.6 可再生派生物的交付约定**——`panel.parquet` 明确不入库，11/08 靠全组各自跑 `src/build_panel.py` 生成；`configs/` 契约与 `data/missing.csv` 入库；② `y` 编码 / 类别顺序按 `data_interface.md` §1.1 预置（`H/D/A→0/1/2`、`p_home` 第一列、写成断言），M1 不等 11/09；③ 新建 `data/missing.csv`（仅表头 = 0 缺失留痕），`.gitignore` 升 **v1.2** 放行该文件并同步 §4.1；④ `configs/README.md`、M1–M4 分工卡同步交付方式；⑤ `09_评审 §6` 把已闭环的「市场基准列」改为已定；⑥ `08_分工方案 §4.2` 新增 **§4.2-a 未决事项登记表**（U1/U2 搁置、U3 命名另案），同步 `roles/README.md` 与 M5 分工卡 |
| v2.0 | 2026-11-08 | **假设体系与执行蓝本统一**：新增 `docs/plans/Team-32-Proposal_v3.0.md`（唯一执行蓝本，修 5 处实质缺陷：H1 曲线方向、M4/M3 归因、H1 预注册判定、B6r 防泄漏与 H4 区间、H3 联合估计证伪条件；含 B↔M 映射与 evolution 段）；分工方案 `v1.2` → **`v1.3`**（旧版归档 `old_docs/`），假设换 H1–H4、命名统一 B0–B6 + B6r、原 H1 降 C1/C2、主场优势降附录 A1、M1 补 `is_promoted_*`/`matchday`、M2 补 T2.10–T2.13、工时 M2 52h / M3 30h（总量 206h 不变）；五份 M 分工卡升 v1.1、`data_interface.md` 升 v1.2、`configs/README.md` 与 `roles/README.md` 同步、`09_评审 §6` 决策项全部闭环；§1 / §2.1 / §2.2 / **§3.5 整节重写** / §5.2 / §6 / §7 同步。**`.gitignore` 不变（仍 v1.2）** |
| v2.1 | 2026-11-08 | **D1 定案 + 两处契约补丁（零新增依赖）**：① B5a/B5b 的 GBM 改用 scikit-learn 1.9.1 内置 `HistGradientBoostingClassifier`，全仓清除 `LightGBM` / `num_leaves` / `n_estimators` 口径，§0 与 §5.2 明确依赖仍为 8 个；② `data_interface.md` 升 **v1.3**：§1.1 增加「内部有序标签 → 落盘 `p_home,p_draw,p_away` 重排」硬规则与断言示例、§2 增加 B6r 拟合样本边界（`PSCH` 自 2012/13 才有，只用 train 段三列齐全比赛，每折 `n_fit` 记日志）；③ 分工方案 `v1.3-r2`、M2/M4 分工卡升 v1.2、Proposal v3.0 补实现注记、`results_table_template.md` 与 `CHANGELOG_structure.md` 同步。**`.gitignore` 不变（仍 v1.2），`requirements.txt` 不变（仍 8 行）** |
| v2.2 | 2026-11-08 | **M1 开工前全量复核 132 CSV（非目录变更，`requirements.txt` / `.gitignore` 均不变）**：① **数据事实订正**——评估窗三列收盘赔率缺 5 场（3 块：`1718_SP1` 1 / `1718_N1` 3 / `1819_D1` 1），B6 / B6r 有效 n 由 16,730 改为 **16,728**，全仓同步；② §3.3 补 4 个实测读取坑（11 个 ragged 文件 / 14 个重复表头文件 / 54 个缺 `PSCH` 列文件 / 11 行全空白，并给出 `csv.reader` 按名取列的处理口径）、日期改 ISO 并附全库 0 NaT 实测；③ `data_interface.md` 升 **v1.4**（新增 §1.0 `match_id` / ISO 日期 / `season` 契约，preds schema 增 `match_id` 列）；④ M1 分工卡升 **v1.2**（T1.2-a 稳健读取器 + 参考实现、T1.10 数据冻结、`n_train ≥ 4,284`、H3 两列 alias 优先与首季规则、覆盖率矩阵读 raw、Windows venv 注意）；⑤ 分工方案 `v1.3-r3`（§5.1 train 池限同联赛、§5.4 补 11/09 签字人）、`football_data_fields.md` v1.3、`configs/README.md`、`roles/README.md` v1.3、结果表模板、M2 卡、`09_评审` 数值订正警示同步；§2.1 结构树新增 `docs/plans/CHANGELOG_data.md` |
| v2.3 | 2026-11-08 | **S0 环境与快照自检交付（非目录变更，`requirements.txt` / `.gitignore` 均不变）**：新增入库产物 `results/logs/s0_selfcheck_2026-11-08.txt`（7 项 PASS 明细）；M1 分工卡升 **v1.3**（§3.1 S0 交付记录、§5 产物表、§6 验收项 1、§7 坑 8）、`roles/README.md` 升 **v1.4**（§1 交付状态速览）、`CHANGELOG_structure.md` 登记；README 同步 §0 / §2.1 / §3.4（S0 实测结论）/ §5.1（默认解释器提醒）/ §7。**S0 不新增正式脚本，下一步 S1 写 `read_raw()`** |

---

*README 是目录结构的唯一书面说明；改动目录请回到 §2.4。*
