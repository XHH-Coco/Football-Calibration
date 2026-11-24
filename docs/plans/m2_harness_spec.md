# M2 评估框架规格与预注册判定规则（`src/eval/` 接口契约）

> **版本 v1.5 · 2026-11-24 · 状态：实现已落地（H1/H2/H4 支持、H3 描述性、C1 差异可分但实际等价、C2 实际等价）；待签字（M2 主签 + M4/M5 会签，11/13 `harness-v1.0` 冻结前；M3 已于 2026-11-11 会签）**
> 主责 M2 · 备份人 M1 · 依据 `08_小组分工实施方案_v1.3.md` §3.2 / §5.1 / §5.3 / §5.5、`Team-32-Proposal_v3.0.md` §2 / §5、`docs/plans/data_interface.md` v1.7
> **本文件是「尺子」的唯一书面说明。** 冻结之后只修 bug，不改口径；改口径须 M2 主签 + M5 会签并在 `CHANGELOG_structure.md` 记一笔。
> **本文件不含任何代码**：§3 是模块与函数签名契约，§7 是跑数前必须落进代码分支的判定规则。
> v1.4 是**订正版**（不是改口径）：把「宽度比 3–5 倍」这条写错的验收标准改成由 `deff` 决定的形式（§3.4）；补齐规范早已要求、实现却没给的返回值（§7.7）；H3 主版回到预注册的 `min(matchday_home, matchday_away)`（§7.4）；H1 增列逐类斜率（§7.2）。判定阈值与四分支结构一字未动。
> v1.5 是**订正版**（不是改口径）：等价带内部再分两格（§7.6）——区间不含 0 说明方向可辨、只是差距小于实用边际，与「真测不出方向」不是一回事。阈值 ±0.02 与四个分支的名字都不变。

---

## 0. 一句话与边界

**M2 只做两件事**：给 9 个 arm 用**同一把尺子**打分（§3–§6），并把 H1–H4 / C1 的判定**在跑数之前写成代码分支**（§7）。

| 属于 M2 | 不属于 M2 |
|---|---|
| `src/eval/` 六个模块、`harness.inner_split()`、B6 / B6r 的构造与预测文件、`results/table_main.csv`、`fig07`、四个判定 notebook、全部区间与 design effect | **任何 arm 的 `fit` / `predict` 实现**（B0–B5b 属 M3/M4）、`configs/splits.json` 与 `panel.parquet` 的生成（M1）、判定阈值的设定（来自蓝本，M2 只实现不改） |

三条不可越界的硬约束（违反即结论作废，见 `data_interface.md` §2）：

1. **重采样单位是 `configs/splits.json` 的 48 个块，不是 16,733 场比赛。**
2. **配对差一律先按 `match_id` 内连接，再逐场相减。**
3. **B6r 的两个参数只在当折 train 段、且 `PSCH/PSCD/PSCA` 三列齐全的比赛上拟合。**

---

## 1. 施工前基线已实测（2026-11-11，本机）

`python src/build_panel.py --stage s3` → **12/12 PASS**，`panel.parquet` 46,507 × 22（不入库）。随后四个数全部对上文档：

| 检查 | 实测 | 文档期望（`data_interface.md` §3 / M2 卡 §3） | 判读 |
|---|---|---|---|
| 全押 1/3 | **1.0986** | ln 3 = 1.098612 | 指标口径（底数为 e、负号）正确 |
| B0 expanding 联赛频率（48 块 pooled） | **1.0743**，逐块 **1.027–1.115** | 1.074 ± 0.005；逐块 1.03–1.12 | 无泄漏、无当季混入 |
| B6 比例法去抽水 | **0.9585**（n = **16,728**，隐含抽水均值 2.74%） | 0.96–0.98，n = 16,728 | 天花板成立，5 场 drop 数正确 |
| B3 / B4（M3 已交） | **0.9986 / 0.9903** | 与 M3 §4.2 逐位一致 | 预测文件可直接进入评估；B4 自 2026-11-24 起用固定超参 (ξ=0.0019, ρ=0) |

> 观感数（**不作判定**）：B4 − B6 = **0.0354 nats**（pooled，未配对、未加区间），已大于 ±0.02 的等价边际 → H2(b) 方向可期，但必须等 48 块配对 + 簇区间才算判。
> 复现：`python scripts/m2_smoke.py`（`scripts/` 已被 `.gitignore` 忽略，不入库）。

---

## 2. 交付物与时点

| # | 产物 | 路径 | 冻结 / 截止 |
|---|---|---|---|
| 1 | 评估框架 | `src/eval/harness.py` | **11/13 `harness-v1.0`** |
| 2 | 指标层 + 单测 | `src/eval/metrics.py`、`tests/test_metrics.py` | 11/13 |
| 3 | 去抽水 + 单测、B6 预测 | `src/eval/devig.py`、`tests/test_devig.py`、`results/preds/preds_B6.csv` | 11/15 |
| 4 | 簇 bootstrap + design effect | `src/eval/bootstrap.py`（含 `design_effect`）、单测 | 11/20 |
| 5 | 判定层（预注册规则） | `src/eval/decisions.py`、`tests/test_decisions.py` | **11/13 前写好并冻结**（跑数前） |
| 6 | 市场差距与 H2 | `src/eval/market_gap.py`、`results/market_gap.csv`、`products/figures/fig07_market_gap.png` | 11/22 |
| 7 | 校准与 H1 | `src/eval/calibration.py`、`analysis/h1_market.ipynb` | 11/22 |
| 8 | B6r 与 H4 | `src/eval/recalibrate.py`、`results/preds/preds_B6r.csv`、`analysis/h4_information.ipynb` | 11/22 |
| 9 | H3 定位 | `analysis/h3_localisation.ipynb` | 11/22 |
| 10 | C1 受控比较 | `analysis/c1_model_class.ipynb` | **11/17 之后**（依赖 B5a） |
| 11 | 主推断表 | `results/table_main.csv`（**9 行 + deff**，列定义见 §8.1） | 11/24 |

**外部依赖（M2 无法自足的部分）**

| 依赖 | 提供者 | 需要时点 | 当前 |
|---|---|---|---|
| `preds_B0..B2`、`preds_B5a`、`preds_B5b` | M4 | G1（11/17） | ⏳ 未到 |
| `preds_B3`、`preds_B4` | M3 | — | ✅ 已交（16,733 行，schema 已验） |
| `preds_B6`、`preds_B6r` | **M2** | 11/15 / 11/22 | 🔨 本文件 §3.3 |
| `is_promoted_*`、`matchday`（H3 指示变量） | M1 | — | ✅ 在 panel 内 |

---

## 3. 模块与函数签名契约（`src/eval/`）

> 目的：M3/M4 **只调一个函数、只认一套 schema**，不各自造轮子。以下签名是冻结项；参数名可改，语义不可改。

### 3.1 `metrics.py` — 一把尺子

| 函数 | 入参 | 返回 | 硬性要求 |
|---|---|---|---|
| `log_loss(p, y)` | `p: (n,3)` 概率矩阵、`y: (n,)` ∈{0,1,2} | 逐场 `−(log p_true)` 向量 | 与 `sklearn.metrics.log_loss` 差 **< 1e-9**；全 1/3 → 1.0986 |
| `brier(p, y)` | 同上 | 逐场 `Σ_k (p_k − 1{y=k})²` | 范围 [0,2] |
| `rps(p, y)` | 同上 | 逐场累积式排序概率分 | 类别按 **H→D→A 有序**（`y` 的 0/1/2 即顺序） |
| `murphy_decomposition(p, y, bins=10)` | 同上 | `(reliability, resolution, uncertainty, within_bin_var)` **四项** | `reliability − resolution + uncertainty + within_bin_var` ≈ `mean(brier)`（v1.4：连续预测下教科书的三项恒等式不成立，加箱内方差才精确） |
| `ece(p, y, bins=10)` | 同上 | 标量 | 单元用 **实测频率**加权，不是等权 |
| `reliability_curve(p, y, n_bins=10)` / `reliability_curve_smooth(p, y, grid=64, bandwidth=None, min_ess=20)` | 同上 | 曲线表（`class, pred_mean, obs_freq, count` / `class, pred, bandwidth, smoothed_freq, ess`） | 硬分箱与**高斯核局部平滑**两版都要（H1 主图用平滑版）；v1.4：带宽 `bandwidth=None` 一律按 **Scott 规则逐类** `h_k = 1.06·sd(p_k)·n^{-1/5}`（下限 0.01），且网格取 1%–99% 分位、逐点 `ess = (Σw)²/Σw² ≥ 20` 才出点——否则窄带宽会在平局类的稀疏尾部炸出竖直尖峰 |
| `bias_vs_pred(p, y, ...)` | 同上 | `pred − freq` 对 `pred` 的曲线 | H1「低概率区在对角线下方」的落点（§7.2） |

**聚合口径（全项目统一，最容易分歧的一条）**

- 主指标是 **pooled over matches**：`LL = Σ_i ℓ_i / n`，**不是**先算 48 个折各自的 LL 再取平均。
- 折/块级数值只用于配对差与 bootstrap（§5），以及报告里明确标注「描述性」的分联赛 / 分赛季表。
- 概率 clip 下限 `1e-15`（只防 `log 0`，不改排序）；`y` 与三列必须同源同序（`data_interface.md` §1.1）。

### 3.2 `devig.py` — B6 唯一入口

| 函数 | 算法 | 备注 |
|---|---|---|
| `proportional(o)` | `p_i = (1/o_i) / Σ_j (1/o_j)` | **B6 主基准** |
| `power(o)` | 解 `k` 使 `Σ_i (1/o_i)^k = 1`（`brentq`，k ∈ **[1, 100]**） | 抽水视为乘性。**根必在 `(1, ∞)`**：`b_i=1/o_i<1` ⇒ 和式对 k 严格递减，且 `k=1` 处等于 `B>1`、`k→∞` 趋于 0。本面板实测 `k ∈ [1.001, 1.207]`；v1.4 前的 `[1e-3, 10]` 数值等价但下界不成立（`B<1` 时会返回负 k） |
| `shin(o)` | 对 z（内幕交易比例）一维求根，按 Štrumbelj (2014) 的目标函数 | 三法中最依赖假设 |
| `check_odds(o)` | 过滤 `o_i > 1`，任一列 ≤1 或 NaN → 该场丢弃并计数 | **禁止回填** |

- 输入**只读** `PSCH / PSCD / PSCA`（`PSH/PSD/PSA` 是开盘、`B365*` 是别家、`MaxC*` 只作稳健性）。
- 三法各自 `Σp = 1`（1e-12）；任一场两法差 > 0.05 → 逐场打印审计（`results/logs/b6_devig_disagreement.csv`）。
- `preds_B6.csv`：**n = 16,728**（48 块中 3 块共 5 场缺三列赔率：`1718_SP1` 1 / `1718_N1` 3 / `1819_D1` 1），schema 11 列、`model="B6"`。**这是「行数 = 该块 test 场次」的唯一例外**，理由与 n 值写进表注。
- 另两法（power / Shin）的逐场概率落 `results/logs/b6_devig_{power,shin}.csv`，供 H1 三法对照与 T2.9 稳健性。

### 3.3 `harness.py` — 主循环与内层验证

| 接口 | 语义 | 约束 |
|---|---|---|
| `run_arm(arm, fit, predict, blocks=None)` | 外层 48 块：`resolve_split(panel, block)` → `fit(train_df, sample_weight=None)` → `predict(test_df) -> (n,3)` → 追加 | **每 arm 只落一个文件** `results/preds/preds_{arm}.csv`（含全部 48 块） |
| `inner_split(train)` | 从该块 train 中切出 `(inner_train, inner_valid)` | `inner_valid` = **train 内最后一个完整赛季**（与 M3 `tune_b4.py` 现有本地兜底同构；`tune_b4.py` 已预留 `from src.eval.harness import inner_split` 自动切换，签名即 `inner_split(train)`）；断言 `max(inner_train.date) < min(inner_valid.date)` 且外层 test 严格更晚 |
| `check_pred(df, n_expected)` | 四条硬校验：三列和 = 1（1e-9）、`y ∈ {0,1,2}`、`match_id` 非空且唯一、行数 = `n_expected` | 落盘前必须调用；失败即抛异常 |

**⚠️ 需要 M3 会签的一处重构（本文件唯一触及他人代码的条目）**：M3 的 `src/models/run_b4.py` 目前自带 `PRED_COLS` 与 `check_pred()`，`tests/test_pred_schema.py` 正在 import 它。schema 只能有一个真相源 → **上提到 `src/eval/harness.py`，`run_b4.py` 改为 import**。M2 出 PR，M3 review 会签。**必须在 11/13 之前合**，否则 9 个 arm 会带着两套 schema 进入 G1。

**schedule / 计时验收**：9 个 arm 的空壳（常数概率）单折 < 20 分钟；`fit` 只收 `(train_df, sample_weight=None)`，`sample_weight` 供 B4→B5a 的权重同步使用（`data_interface.md` §2 对照一致性）。

### 3.4 `bootstrap.py` / `design_effect.py` — 区间

| 接口 | 语义 |
|---|---|
| `block_deltas(df_a, df_b, keys)` | 按 `match_id` 内连接 → 逐场 `δ_i = ℓ_a,i − ℓ_b,i` → 按 (league, season) 聚成 48 组，返回 `(δ_b (48,), n_b (48,), n_paired)` |
| `cluster_bootstrap(values, weights, B=10_000, alpha=0.10, seed=20261110)` | 有放回抽 48 个块（同一块可重复），重算加权 pooled 统计量，返回 `(point, lo, hi, se_boot)` |
| `cluster_robust_se(values, weights, G=48)` | 块稳健标准误（解析式，与 bootstrap 交叉核对） |
| `design_effect(values, weights)` | `deff = Var_cluster / Var_iid` |
| `iid_bootstrap(block, B=10_000, alpha=0.10, seed=20261110)` | **仅作对照**，按「比赛」重抽样（错误做法），用来跑宽度比自检；v1.4 起统一这个名字（旧文档写的 `iid_resample_ci` 不存在） |
| `width_ratio(block, ...)` / `selfcheck_text(frames, ...)` | 宽度比 + 生成 `bootstrap_selfcheck.txt` 正文（验收项 7 的证据） |

**精确算法（冻结，避免各人写出不同区间）**

- 点估计（配对差）：`Δ̂ = Σ_b n_b δ_b / Σ_b n_b`（按场加权 pooled，**不是 48 块均值的简单平均**）。
- 重抽样后的统计量：`Δ̂* = Σ_b n_b* δ_b* / Σ_b n_b*`，其中重复抽中的块按重复次数累加 `n_b*`。
- 区间：分位法 `[q(α/2), q(1−α/2)]`，**不做偏差校正**（写明这一点，避免与他人复算不一致）。
- 主区间 `α = 0.10`（90%）；H2 判据 (a) 另用 `α = 0.05`（95%）。
- 块稳健 SE：`Var_cluster(Δ̂) = G/(G−1) · Σ_b (n_b/N)² (δ_b − Δ̂)²`，`N = Σ_b n_b`，`G = 48`。
- 对照 iid SE：`Var_iid(Δ̂) = s²/N`，`s²` 为逐场 δ 的样本方差。
- **自检断言（v1.4 订正）**：块级与逐场重采样的 90% 区间宽度比满足 **`ratio ≈ √deff` 且 `ratio > 1`**，并逐行核对 `|ratio² − deff| / deff < 25%`。
  **原文写的「∈ [3, 5]」是错的**：宽度比不是自由参数，它由 `deff` 唯一决定；而本面板的 `deff` 只有 1.31–2.28（B0 1.32 / B6 1.51 / B4 2.08 / B4−B6 2.28），对应 `ratio` 1.15–1.49。要 3–5 倍须 `deff` 9–25，等于假设同一块内 ≈349 场比赛几乎完全同质——那与「同赛季比赛共享球队状态与裁判尺度」的建模前提自相矛盾。
  证据落盘 `results/logs/bootstrap_selfcheck.txt`（种子、B、48 块、逐 arm/逐配对的 `deff`、两种宽度、`ratio`、`ratio²` vs `√deff` 偏差与逐行判定），由 `python -m src.eval.run_m2` 第 [4] 步生成，任一行为 `FAIL` 即让流水线抛异常。
- 种子固定 `20261110`（`appendix/seed.py::DEFAULT_SEED`）；`B = 10,000`。

### 3.5 `market_gap.py` / `calibration.py` / `recalibrate.py`

| 模块 | 做什么 | 关键约束 |
|---|---|---|
| `market_gap.py` | 对 8 个 arm（B0–B5b + B6r，B6 作分母）算 `ΔLL = LL(arm) − LL(B6)` 与 `ΔBrier`，三种去抽水下各一遍 | 任意一臂为负 → **先查泄漏**再报告；三法必须同号同量级 |
| `calibration.py` | 对 B6 做 one-vs-rest logistic 重校准：每结果类别估 `a_k, b_k`，报 pooled 斜率 / 截距、尾箱偏差 | 主报**按块场数加权的 pooled 斜率**，并另给「抽中块堆叠后单次拟合」作稳健性；一阶符号断言见 §7.2 |
| `recalibrate.py` | 两参数 temperature-and-bias logit 映射做 B6r：`softmax(c · logit p_B6 + d)` | 参数**只在当折 train 段且赔率三列齐全的比赛**上拟合 → 应用到 test；每折 `n_fit` 落 `results/logs/b6r_n_fit.csv`；**断言 train∩test = ∅** |

B6r 的具体口径（写成断言，不是注释）：

1. 拟合样本 = 该折 `train_df` 中 `PSCH/PSCD/PSCA` 三列齐全的比赛（收盘价自 2012/13 才有，前 9 季整列不存在）。
2. 两参数**两个**（`c` 温度、`d` 偏置），不做逐联赛分别拟合（48 折 × 6 联赛会过拟合，且 H4 的分母 gap 按 pooled 定义）。
3. `preds_B6r.csv` 与 B6 **同一批 16,728 场**（同一条 drop 规则），`model="B6r"`。
4. 若某折 `n_fit < 500` → 该折记 `n_fit` 并照常跑，但在日志标注「重校准估计不稳」（前几折会出现，属预期）。

---

## 4. 数据契约（在 `data_interface.md` 之上，M2 追加部分）

| 项 | 约定 |
|---|---|
| 预测文件 | 11 列固定顺序：`match_id, league, season, date, home, away, model, p_home, p_draw, p_away, y`；一 arm 一文件；B3/B4/B5* 16,733 行，**B6/B6r 16,728 行** |
| 配对 | `match_id` 内连接；`n_paired` 写进每张表注（B6 相关一律 16,728） |
| 块归属 | 以 `configs/splits.json` 的 48 块为准；用 `(league, season)` 把逐场记录归组，**不从 preds 文件里自造块** |
| `y` 与列序 | `H/D/A → 0/1/2`，`p_home` 必须在三列之首；各模型内部标签顺序自由，落盘前重排（`data_interface.md` §1.1） |
| 重跑 | 每个块的目标赛季**只预测一次**；重跑须在 `results/logs/` 记原因 |

---

## 5. 推断协议（一句话版）

> 所有主张都是**同一批比赛上的逐场配对差**；区间来自 **48 个 (联赛, 赛季) 块**的簇 bootstrap（10,000 次）；每个区间旁附 **design effect**；48 簇下可检测差约 **0.02 nats**，因此任何小于该量的"差异"都不宣称。

分联赛 / 分赛季拆分、H3 的轮次 sweep、附录 A1 的 γ 轨迹，**跑数前已声明为描述性**，事后不得因某个子集好看而升格为主推断。

---

## 6. 报告措辞模板（与区间一致，M5 直接取用）

| 区间情形 | 允许的写法 | 禁止的写法 |
|---|---|---|
| 90% 区间完全落在 (−0.02, +0.02) | 「实际等价（区间完全落在 ±0.02 的等价边际内）」 | 「无差异」 |
| 90% 区间完全在 +0.02 以上（或 −0.02 以下） | 「点估计 Δ = x（90% CI a–b），方向明确且超出等价边际」 | 「显著优于」（不报区间时） |
| 区间跨边界，或宽度 > 0.04 | 「**只报估计与区间，不作实用性宣称**；点估计为 x」；若区间**不含 0**，必须同时写明「差异可分，但上界越过 ±0.02 等价边际」（C1 就属这一格） | 「没有差异」「不显著」「分辨率不足」（在区间不含 0 时用这四个字自相矛盾） |
| 作为分母的 gap < 0.01 nats | 改报**绝对差**并说明比值不稳 | 硬算相对变化百分比 |

---

## 7. 预注册判定规则（**跑数前写死，冻结项**）

### 7.1 常量（唯一来源，`src/eval/decisions.py` 顶部）

| 常量 | 值 | 出处 |
|---|---|---|
| `EQUIV_MARGIN` | **0.02 nats** | 全项目唯一等价边际（提交版曾用 ±0.01，48 簇下不可分辨） |
| `CI_MAIN` | **0.90** | 主区间 |
| `CI_H2A` | **0.95** | H2 判据 (a) |
| `H4_REL_THRESHOLD` | **0.25** | H4 相对变化 25% |
| `H4_MIN_DENOM` | **0.01 nats** | 分母过小的护栏 |

### 7.2 H1 — 市场 under-dispersed（斜率 > 1）

- **判定量**：三种去抽水下 B6 的 one-vs-rest 重校准斜率 `b_k`（报 pooled 斜率），以及尾箱偏差。
- **主判据**：`b_proportional ≤ 1` → **H1 被证伪**；`b > 1` 且 90% 区间下界 > 1 → 支持。
- **逐类斜率（v1.4 必报项）**：主斜率是三类斜率的块内平均，会把「只有某一类 under-dispersed」稀释掉，因此除主斜率外必须同时报**逐类斜率 + 90% 簇区间**（`results/logs/h1_slope_by_class.csv`，由 `h1_slope_by_class()` 生成）。实测：只有**客胜类**在三种去抽水下都 > 1（prop 1.087 / power 1.044 / shin 1.054），平局类在 power 下跨 1。
- **措辞约束（v1.4）**：三种去抽水的结论是「**方向一致、量级依赖去抽水口径**」（比例法 1.086 / Shin 1.052 / power 1.030，后者区间跨 1）。禁止写「市场显著保守」这类无限定语的句子；必须同时说明次判据暴露的 confound——**比例法的偏差本身最大，而比例法去抽水已知会残留 favorite–longshot bias**，故「斜率 > 1」里有多少来自市场、多少来自方法，本设计分不开；H2/H4 不受影响（三法 gap 差 < 2e-4）。
- **次判据（预注册排序）**：`|b−1|_proportional − |b−1|_Shin` 的 90% 区间**下界 > 0** 才宣称「比例法偏差最大」；否则三法只作描述性对照。三法声明为**同一稳健性族**，不做多重比较校正。
- **符号断言（必须写进代码）**：`b > 1` ⇒ 可靠性曲线在**低概率区位于对角线下方**、高概率区位于上方。**提交版此处写反**，照文字写断言会得到反号结论。

### 7.3 H2 — 透明模型追不上市场，且残差不可忽略

记 `Δ_46 = LL(B4) − LL(B6)`（**正 = 模型更差**），`n_paired = 16,728`。

| 判据 | 规则 |
|---|---|
| **(a) B4 不优于 B6** | `Δ_46` 的 **95%** 簇区间**整体 > 0**（区间下界 > 0）→ 支持「B4 未追上」；**区间上界 < 0**（B4 明确更好）→ 该判据被证伪，且**先查泄漏**；区间跨 0 → 「未测出差异，也不排除等价」 |
| **(b) 差距实际非零** | `Δ_46` 的 **90%** 区间**完全落在 ±0.02 之外** → 支持「差距实际非零」；**完全落在 ±0.02 之内** → 被证伪（等价）；跨边界或宽于 0.04 → 分辨率不足 |

- 稳健性：三种去抽水 × 8 arm 的 `ΔLL` 与 `ΔBrier` 必须**同号同量级**（`market_gap.csv`、`fig07_market_gap`）。
- `ΔBrier` 与 `ΔLL` 结论不一致时，以 log loss（主指标）判定，并如实报告分歧。

### 7.4 H3 — 差距局部化

- **模型**：逐场 `gap_i = ℓ_B4,i − ℓ_B6,i`（正 = 模型更差）对
  `β1·promoted_i + β2·early_i + 联赛×赛季固定效应` 回归（OLS）。
  `promoted_i = is_promoted_home ∨ is_promoted_away`；`early_i = 1{min(matchday_home, matchday_away) ≤ 6}`
  （**敏感性**：`max(...)` 与「仅用主队 matchday」两版作描述性对照，正文只报主版）。
- **轮次来源（v1.4 修正）**：两队 matchday 均由 panel 自身算出——同联赛同赛季同队按日期累计出场数 +1（`localisation.team_matchday()`），0 缺失。旧实现只用主队 matchday 并标成「已声明局限」，属**无必要偏离预注册**：两口径 early 标记不同的场次 1,025 场，early 系数 −0.0114（min，主版）vs −0.0108（仅主队），结论不变。三版对照落 `results/logs/h3_sensitivity.csv`。
- **判定**：`β1 > 0` 且 `β2 > 0`，**且各自 90% 簇区间下界均 > 0** → 支持；**任一区间跨 0** → 两个系数都只作描述，既不宣称成立也不宣称证伪（提交版「任一 ≤ 0 即证伪」与联合估计矛盾，已修正）。
- 轮次窗 1–3 / 1–6 / 1–10 的 sweep 是**跑数前声明的描述性稳健曲线**，不携带显著性主张，不进主推断。
- 指示变量只能来自季前名单与赛程（M1 的 T1.9 打乱测试已保证）。

### 7.5 H4 — 差距是信息不是校准

记 `gap_B6 = LL(B4) − LL(B6)`、`gap_B6r = LL(B4) − LL(B6r)`，`rel = (gap_B6r − gap_B6) / gap_B6`。

| 情形 | 判定 |
|---|---|
| `gap_B6 < 0.01` | 改报**绝对差** `gap_B6r − gap_B6` 与区间，声明比值不稳 |
| `rel` 的 90% 区间**上界 < 0.25** | **支持 H4**（重校准只解释了不到 25% 的差距 → 差距主要是信息） |
| `rel` 的 90% 区间**下界 > 0.25** | **证伪 H4** |
| 其他（跨 25%，或区间宽到无法分辨） | 只报估计与区间，不下判定，写明分辨率不足 |

- 前提断言：B6r 参数 train-only（§3.5）+ 每折 `n_fit` 已记录；`preds_B6r.csv` 与 B6 同一批 16,728 场。
- **oracle 上界（v1.4 补充证据）**：另跑一支「用 test 标签拟合」的重校准——**逐块**（48 组 `c, d`，共 96 个自由度）拟合后在同一批 test 上评估。它不是可上线的模型（含过拟合），作用是把「我们的 B6r 恰好没拟合好」这个异议提前堵死：实测市场 LL 只能从 0.958536 改善到 0.955763（+0.00277），gap 反而从 0.0317 涨到 0.0345，`rel = +8.7% ≪ 25%`。即**即使允许作弊，校准也只能解释不到 8% 的差距**。落盘 `results/logs/h4_oracle_bound.csv`（`recalibrate.oracle_bound()`）。

### 7.6 C1 / C2 — 受控比较（不是假设）

- `Δ_C1 = LL(B5a) − LL(B4)`（正 = B4 更好）；`Δ_C2 = LL(B5b) − LL(B5a)`。
- 五个标签**必须同时存在于代码里**（不是只写在文档）；前两行共用同一个「落在等价带内」的几何分支，靠「区间是否跨 0」再分一次：

| 90% 区间位置 | 判定 | 含义 |
|---|---|---|
| 落在 (−0.02, +0.02) 内，**且跨 0** | 实际等价 | 连方向都测不出：模型类/信息集的变化确实没留下痕迹 |
| 落在 (−0.02, +0.02) 内，**但不跨 0** | **差异可分但实际等价** | 方向可辨（区间不含 0），只是差距小于实用边际 0.02 |
| 完全在 +0.02 以上 | 前一级更好 | 差距大到值得说 |
| 完全在 −0.02 以下 | 后一级更好 | 同上 |
| 跨过 ±0.02 边界，或宽度 > 0.04 | 只报估计，不下结论 | 跨过边界的标「跨边界」；宽到测不出的标「分辨率不足」 |

- 报告里**不写「H1 成立」**这类措辞（C1/C2 是结果不是假设）。**已判（2026-11-11 出数、v1.4 措辞订正）**：C1 **跨边界，不下结论**（Δ=+0.0158，90% CI 0.0109–0.0209 —— **区间不含 0，差异可分**，但上界越过 +0.02 的等价边际，故只报估计、不作实用性宣称；旧措辞「分辨率不足」与「区间不含 0」自相矛盾）、C2 实际等价（Δ=−0.0028，90% CI −0.0062~+0.0005，**跨 0**）。2026-11-24 B4 改常量超参后重算，判定未变。**同日深夜 B5 也改为固定超参后，C1 变成 +0.0055（0.0009–0.0099）→ 分支从「跨边界」变为「差异可分但实际等价」**，C2 变成 −0.0015（−0.0032~+0.0001），仍为实际等价。当时阈值与实现未动，改的只是被喂进去的 arm。**但随后发现一处名实不符**：`controlled_verdict` 把所有落在 ±0.02 内的都标「实际等价」，而报告正文一直按「区间是否跨 0」区分两种情形（`sens_b5_grid._branch` 早就是五分支）⇒ 2026-11-24 把实现改成五分支，C1 现标「差异可分但实际等价」、C2 标「实际等价」。这是**订正而非改口径**：阈值、分支名字、判定结果都没变，变的只是标签的精度。
- 第四分支在代码里的实现要求：`controlled_verdict` 必须区分两种跨边界——(i) 区间不含 0（差异可分）→ `跨边界，不下结论`；(ii) 区间跨 0（真的测不出）→ `分辨率不足，不下结论`。判定**阈值与四分支结构不变**，只是把理由说准。

### 7.7 判定层实现要求

- 每个 `*_verdict(...)` 返回 **dict**：`{"decision", "reason", "interval": [lo, hi] | None, "n_paired": int | None}`。四个键**恒存在**（不适用的值写 `None`），可直接落 CSV；H2 另带 `interval_95` 与 `point`，H3 另带 `intervals = {promoted: [lo,hi], early: [lo,hi]}`。全部判定由 `run_m2` 汇总成 `results/logs/m2_verdicts.csv`（8 行：H1 主/次、H2、H3 ×2、H4、C1、C2），M5 的「报告 §5 数字可倒查」因此变成一条 join 而不是人眼抽 5 个。
- 判定阈值集中在 §7.1，**函数体内不得出现裸数字**；`tests/test_decisions.py` 用构造的极端区间把 4×5 个分支全部走一遍。
- 判定规则在 `harness` 冻结的同一次提交里定稿；之后任何改动须 M2 主签 + M5 会签，并在报告里说明。

---

## 8. 表结构（M5 直接取数，列名冻结）

### 8.1 `results/table_main.csv` — 9 行

| 列 | 含义 |
|---|---|
| `arm` | `B0 B1 B2 B3 B4 B5a B5b B6 B6r`（9 行，固定顺序） |
| `n_matches` | 该 arm 的有效场数（B6/B6r 16,728，其余 16,733） |
| `log_loss, ll_lo90, ll_hi90, se_cluster, deff` | 主指标 + 90% 簇区间 + 块稳健 SE + design effect（**每行都要有，不允许裸点估计**） |
| `brier, rps` | 辅指标（点估计） |
| `delta_vs_B4, delta_vs_B4_lo90, delta_vs_B4_hi90` | 与 B4 的配对差及区间 |
| `delta_vs_B6, delta_vs_B6_lo90, delta_vs_B6_hi90, n_paired_vs_B6` | 与 B6 的配对差及区间；`arm = B6` 行留空 |

### 8.2 其余产物

| 文件 | 内容 |
|---|---|
| `results/market_gap.csv` | `arm × devig_method × {delta_ll, lo90, hi90, delta_brier}`，8 arm × 3 法 |
| `products/figures/fig07_market_gap.png` | 三法 × 8 arm 的 gap 森林图 |
| `results/logs/b6r_n_fit.csv` | 每折 `n_fit`（B6r 拟合样本数） |
| `results/logs/b6_devig_disagreement.csv` | 两法差 > 0.05 的场次审计 |
| `results/logs/bootstrap_selfcheck.txt` | 块级 vs 逐场区间宽度比、deff、种子与 B（由 `selfcheck_text()` 生成，逐行 PASS/FAIL） |
| `results/logs/h1_slope_by_class.csv` | 三法 × 三类校准斜率 + 90% 簇区间（H1 口径依赖的证据，v1.4） |
| `results/logs/h3_sensitivity.csv` | `min` / `max` / 仅主队三种 `early` 定义的系数对照（v1.4） |
| `results/logs/h4_oracle_bound.csv` | 逐块用 test 标签拟合的 oracle 上界（LL、gap、rel、c/d 范围，v1.4） |
| `results/logs/m2_verdicts.csv` | 全部判定一行一条：`hypothesis, decision, point, lo, hi, n_paired, detail`（v1.4） |

---

## 9. 验收映射（M2 卡 §6 的 12 项 → 本文件落点）

| 验收项 | 本文件对应 | 判定方式 |
|---|---|---|
| 1 `log_loss` 与 sklearn 差 < 1e-9 | §3.1 | 自动：`tests/test_metrics.py` |
| 2 全 1/3 → 1.0986；B0 → 1.074±0.005 | §1 已实测 | 自查（已完成） |
| 3 B0 48 块 16,733 行、三概率和 1 | §3.3 `check_pred` | 自动：`tests/test_pred_schema.py` |
| 4 9 个空壳 arm 单折 < 20 分钟 | §3.3 | 自查（计时） |
| 5 `inner_split` 验证集严格早于外层 test | §3.3 | 断言 |
| 6 三种去抽水各自和为 1、互差 < 0.01 | §3.2 | 自动：`tests/test_devig.py` |
| 7 块级 vs 逐场区间宽度比 `≈ √deff` 且 > 1（实测 1.15–1.49） | §3.4 | 自动 + `bootstrap_selfcheck.txt`（逐行 PASS/FAIL，FAIL 即中断） |
| 8 C1 四分支在代码里 | §7.6 | code review（M5） |
| 9 `table_main.csv` 每行有区间与 deff | §8.1 | 检查 9 行 |
| 10 H2 表 3 法 × 8 臂同号同量级 | §7.3 | 人眼 + 备注 |
| 11 报告 §5 数字可在 `table_main.csv` / `m2_verdicts.csv` 找到 | §7.7 倒查 | 抽 5 个（M5），区间与 `n_paired` 已结构化 |
| 12 「显著/不显著」措辞与区间一致 | §6 措辞模板 | 全文搜（M5） |

---

## 10. 已知风险与本文件的对策

| 风险 | 触发信号 | 对策（本文件已写死） |
|---|---|---|
| 按场重采样 → 假显著 | 区间窄得可疑 | §3.4 断言 `ratio ≈ √deff > 1`（实测 1.15–1.49）；`deff` 随行落盘，`bootstrap_selfcheck.txt` 逐行判定 |
| 配对行数不对 | `n_paired` ≠ 16,728 | §4 强制内连接 + 表注写 `n_paired` |
| 两套 schema 并存 | 9 个 arm 在 G1 对不齐 | §3.3 上提 `PRED_COLS` / `check_pred`，**11/13 前合** |
| B6r 用 test 拟合 | H4 的 rel 异常变小 | §3.5 train-only 断言 + `n_fit` 日志 |
| 先看外层结果再改内层网格 | 选参随结果漂移 | §3.3 `inner_split` 单一入口；判定规则 §7 跑数前冻结 |
| 把「区间太宽」写成「无差异」 | 全文出现「没测出差异=等价」 | §6 措辞模板 + 验收项 12 |
| 依赖 M4 的 5 条预测延迟 | G1 前 `preds_B0..B2/B5a/B5b` 缺失 | 空壳先跑通 harness（验收项 4），真值到货只换 `fit`/`predict` |

---

## 11. 签字区

| 角色 | 会签内容 | 状态 |
|---|---|---|
| **M2（主签）** | 本文件 §3 接口签名、§7 判定规则、§8 表结构 | ☐ 待签（11/13 前） |
| **M3（会签）** | ① `PRED_COLS` / `check_pred` 上提到 `src/eval/harness.py`（`run_b4.py` 改 import）；② `inner_split()` 与 `tune_b4.py` 现用「train 内最后一个完整赛季」口径一致 | ✅ 2026-11-11 会签（在 `939e3da` 上实测：全量 `pytest -q tests/` **183 passed**；`python -m src.models.run_b4` 重跑 48 折，`preds_B3.csv` / `preds_B4.csv` 与入库版**逐字节相同**，`convergence.csv` / `xi_rho_by_block.csv` 仅 `elapsed_s` 不同；两处 `inner_split()` 实现同构，切换后 48 折结果不变） |
| **M4（会签）** | ① 5 个 arm 的 `fit(train_df, sample_weight=None)` / `predict_proba(test_df)` 签名；② `feature_whitelist_b5a.csv` 与本文件 §4 的 schema 无冲突 | ☐ 待签 |
| **M1（知会）** | `match_id` / ISO 日期 / 块归属口径未变（沿用 `data_interface.md` §1.0、`splits.json`） | ☐ 待知会 |
| **M5（会签）** | §6 措辞模板与 §8.1 表列名满足报告 §5 取数需求 | ☐ 待签 |

> **v1.4 订正项的签字要求**：①–⑧ 中只有 §3.4（宽度比口径）属于**口径订正**，必须 M2 主签 + M5 会签；其余是实现回填（把代码已做的事写对）与新增产物，M2 主签即可。签字栏沿用上表，不另开表；未签之前，v1.4 的结论一律按「M2 复核版」引用，不得当作冻结口径。

---

## 12. 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-11-11 | 首版：模块与函数签名契约（§3）、推断协议（§5）、预注册判定规则（§7）、`table_main.csv` 列定义（§8.1）、验收映射（§9）、签字区（§11）；附施工前基线实测（§1）。**不含代码**；冻结时点 11/13 与新 `harness-v1.0` 同步。 |
| v1.1 | 2026-11-11 | 落地登记（契约不变）：§2 交付物 4 明确 design effect 并入 `bootstrap.py`；§3.3 `inner_split(train)` 签名与 M3 `tune_b4.py` 一致。实现已完成：`src/eval/` 十模块、`preds_B6.csv` / `preds_B6r.csv`、`table_main.csv`、`market_gap.csv`、`fig07`、四个执行过的 notebook、9 个测试文件。H1/H2/H4 支持、H3 只作描述、C1 待 M4 的 B5a。 |
| v1.2 | 2026-11-11 | **M3 会签（契约不变）**：§11 M3 两行由 ☐ 改为 ✅，依据是在 `939e3da` 上的实测——全量 **183 passed**；用 `harness.inner_split()` 重跑 48 折后 `preds_B3.csv` / `preds_B4.csv` 与入库版逐字节相同（两个 log 仅 `elapsed_s` 变化），即 `PRED_COLS` / `check_pred` 上提与内层切分切换均为行为中性。**M2 主签与 M4/M5 会签仍待签。** |
| v1.3 | 2026-11-11 | **C1/C2 判定落地（契约不变）**：§7.6 补实测结论——C1 分辨率不足（Δ=+0.0142，90% CI 0.0078–0.0207）、C2 实际等价（Δ=−0.0053，90% CI −0.0093~−0.0015）；`decisions.py` 把 `c1_verdict` 重构为通用 `controlled_verdict(before, after, …)` 并新增 `c2_verdict`（修掉 C2 复用 C1 标签的隐患）；`table_main.csv` 补齐 9 行、`market_gap.csv` 扩到 8 arm × 3 法、`c1_model_class.ipynb` 写入真实结果。 |
| v1.4 | 2026-11-23 | **复核后订正（阈值与四分支结构未动）**：① §3.4 宽度比口径由「∈[3,5]」改为「`ratio ≈ √deff` 且 > 1」，实测 1.15–1.49，并补 `selfcheck_text()` 与 `bootstrap_selfcheck.txt`（验收项 7 此前无证据）；② §7.2 增列逐类斜率（`h1_slope_by_class.csv`）与「方向一致、量级依赖口径」的措辞约束；③ §7.4 H3 主版回到预注册的 `min(matchday_home, matchday_away)`（`team_matchday()` 由 panel 自算，0 缺失）+ `h3_sensitivity.csv`；④ §7.5 补 oracle 上界（逐块 test 标签拟合，rel +7.9% ≪ 25%）；⑤ §7.6 第四分支拆成「跨边界（区间不含 0）」与「分辨率不足（跨 0）」；⑥ §7.7 返回值补 `interval` / `n_paired`，新增 `m2_verdicts.csv`；⑦ §3.1 平滑带宽改 Scott 规则逐类（原 0.143 严重过平滑）、§3.2 power 求根区间订正为 `[1,100]`；⑧ §8.2 补四个新日志。全量 `pytest -q` **191 passed**；`run_m2` 重跑后 `table_main.csv` / `preds_B6r.csv` 仅末位浮点差（≤1e-13，无实质变化）。 |
| v1.5 | 2026-11-24 | **订正（阈值与四个分支名不变）**：§7.6 的等价带拆成两格——区间**跨 0** 标「实际等价」，区间**不含 0** 标「差异可分但实际等价」。起因是判定表与报告正文长期不一致：`decisions.controlled_verdict` 只输出「实际等价」，而 §5.1/§5.4/图单一直按两者不同来写，`sens_b5_grid._branch` 也早就是五分支。阈值 ±0.02 与「跨边界 / 分辨率不足」两条判定一字未改。同步：`src/eval/decisions.py`、`results/logs/m2_verdicts.csv`（C1 标签变为「差异可分但实际等价」）、`products/report/section_5_1_ablation.md` / `section_5_4_h2.md`、`docs/plans/roles/README.md` 索引。 |

---

*本文件属方案类文档，改动请同步 `docs/plans/CHANGELOG_structure.md`；实现代码落地后，函数签名以本文件为准并回填「已实现」标记。*
