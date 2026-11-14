# M2 评估框架规格与预注册判定规则（`src/eval/` 接口契约）

> **版本 v1.3 · 2026-11-11 · 状态：实现已落地（H1/H2/H4 支持、H3 描述性、C1/C2 已判）；待签字（M2 主签 + M4/M5 会签，11/13 `harness-v1.0` 冻结前；M3 已于 2026-11-11 会签）**
> 主责 M2 · 备份人 M1 · 依据 `08_小组分工实施方案_v1.3.md` §3.2 / §5.1 / §5.3 / §5.5、`Team-32-Proposal_v3.0.md` §2 / §5、`docs/plans/data_interface.md` v1.7
> **本文件是「尺子」的唯一书面说明。** 冻结之后只修 bug，不改口径；改口径须 M2 主签 + M5 会签并在 `CHANGELOG_structure.md` 记一笔。
> **本文件不含任何代码**：§3 是模块与函数签名契约，§7 是跑数前必须落进代码分支的判定规则。

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
| B3 / B4（M3 已交） | **0.9986 / 0.9939** | 与 M3 §4.2 逐位一致 | 预测文件可直接进入评估 |

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
| `murphy_decomposition(p, y, bins=10)` | 同上 | `(reliability, resolution, uncertainty)` | 三者之和 ≈ `mean(brier)` |
| `ece(p, y, bins=10)` | 同上 | 标量 | 单元用 **实测频率**加权，不是等权 |
| `reliability_curve(p, y, smooth="w7")` | 同上 | 分箱中心 + 实测频率 + 箱内 n | 硬分箱 + **W7 局部平滑**两版都要（H1 主图用平滑版） |
| `bias_vs_pred(p, y, ...)` | 同上 | `pred − freq` 对 `pred` 的曲线 | H1「低概率区在对角线下方」的落点（§7.2） |

**聚合口径（全项目统一，最容易分歧的一条）**

- 主指标是 **pooled over matches**：`LL = Σ_i ℓ_i / n`，**不是**先算 48 个折各自的 LL 再取平均。
- 折/块级数值只用于配对差与 bootstrap（§5），以及报告里明确标注「描述性」的分联赛 / 分赛季表。
- 概率 clip 下限 `1e-15`（只防 `log 0`，不改排序）；`y` 与三列必须同源同序（`data_interface.md` §1.1）。

### 3.2 `devig.py` — B6 唯一入口

| 函数 | 算法 | 备注 |
|---|---|---|
| `proportional(o)` | `p_i = (1/o_i) / Σ_j (1/o_j)` | **B6 主基准** |
| `power(o)` | 解 `k` 使 `Σ_i (1/o_i)^k = 1`（`brentq`，k ∈ [1e-3, 10]） | 抽水视为乘性 |
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
| `iid_resample_ci(...)` | **仅作对照**，用来跑「块级 vs 逐场」宽度比的自检 |

**精确算法（冻结，避免各人写出不同区间）**

- 点估计（配对差）：`Δ̂ = Σ_b n_b δ_b / Σ_b n_b`（按场加权 pooled，**不是 48 块均值的简单平均**）。
- 重抽样后的统计量：`Δ̂* = Σ_b n_b* δ_b* / Σ_b n_b*`，其中重复抽中的块按重复次数累加 `n_b*`。
- 区间：分位法 `[q(α/2), q(1−α/2)]`，**不做偏差校正**（写明这一点，避免与他人复算不一致）。
- 主区间 `α = 0.10`（90%）；H2 判据 (a) 另用 `α = 0.05`（95%）。
- 块稳健 SE：`Var_cluster(Δ̂) = G/(G−1) · Σ_b (n_b/N)² (δ_b − Δ̂)²`，`N = Σ_b n_b`，`G = 48`。
- 对照 iid SE：`Var_iid(Δ̂) = s²/N`，`s²` 为逐场 δ 的样本方差。
- **自检断言**：块级与逐场重采样的 90% 区间宽度比 ∈ **[3, 5]**；`deff` 与宽度比一致（`deff ≈ 宽度比²`）。
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
| 区间跨边界，或宽度 > 0.04 | 「**分辨率不足，不做判定**；点估计为 x」 | 「没有差异」「不显著」 |
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

### 7.6 C1 / C2 — 受控比较（不是假设）

- `Δ_C1 = LL(B5a) − LL(B4)`（正 = B4 更好）；`Δ_C2 = LL(B5b) − LL(B5a)`。
- 四分支**必须同时存在于代码里**（不是只写在文档）：

| 90% 区间位置 | 判定 |
|---|---|
| 完全落在 (−0.02, +0.02) | 实际等价（模型类/信息集的变化在等价边际内） |
| 完全在 +0.02 以上 | 前一级更好 |
| 完全在 −0.02 以下 | 后一级更好 |
| 跨边界，或宽度 > 0.04 | 只报估计，不下结论 |

- 报告里**不写「H1 成立」**这类措辞（C1/C2 是结果不是假设）。**已判（2026-11-11，M4 的 B5a/B5b 到位后）**：C1 分辨率不足（Δ=+0.0142，90% CI 0.0078–0.0207）、C2 实际等价（Δ=−0.0053，90% CI −0.0093~−0.0015）。

### 7.7 判定层实现要求

- 每个 `*_verdict(...)` 返回 `(判定字符串, 一句话理由, 用到的区间与 n_paired)`，报告 §5 可逐条倒查。
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
| `results/logs/bootstrap_selfcheck.txt` | 块级 vs 逐场区间宽度比、deff、种子与 B |

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
| 7 块级 vs 逐场区间宽度差 3–5 倍 | §3.4 | 自动 + `bootstrap_selfcheck.txt` |
| 8 C1 四分支在代码里 | §7.6 | code review（M5） |
| 9 `table_main.csv` 每行有区间与 deff | §8.1 | 检查 9 行 |
| 10 H2 表 3 法 × 8 臂同号同量级 | §7.3 | 人眼 + 备注 |
| 11 报告 §5 数字可在 `table_main.csv` 找到 | §7.7 倒查 | 抽 5 个（M5） |
| 12 「显著/不显著」措辞与区间一致 | §6 措辞模板 | 全文搜（M5） |

---

## 10. 已知风险与本文件的对策

| 风险 | 触发信号 | 对策（本文件已写死） |
|---|---|---|
| 按场重采样 → 假显著 | 区间窄得可疑 | §3.4 断言宽度比 3–5 倍；`deff` 随行落盘 |
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

---

## 12. 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-11-11 | 首版：模块与函数签名契约（§3）、推断协议（§5）、预注册判定规则（§7）、`table_main.csv` 列定义（§8.1）、验收映射（§9）、签字区（§11）；附施工前基线实测（§1）。**不含代码**；冻结时点 11/13 与新 `harness-v1.0` 同步。 |
| v1.1 | 2026-11-11 | 落地登记（契约不变）：§2 交付物 4 明确 design effect 并入 `bootstrap.py`；§3.3 `inner_split(train)` 签名与 M3 `tune_b4.py` 一致。实现已完成：`src/eval/` 十模块、`preds_B6.csv` / `preds_B6r.csv`、`table_main.csv`、`market_gap.csv`、`fig07`、四个执行过的 notebook、9 个测试文件。H1/H2/H4 支持、H3 只作描述、C1 待 M4 的 B5a。 |
| v1.2 | 2026-11-11 | **M3 会签（契约不变）**：§11 M3 两行由 ☐ 改为 ✅，依据是在 `939e3da` 上的实测——全量 **183 passed**；用 `harness.inner_split()` 重跑 48 折后 `preds_B3.csv` / `preds_B4.csv` 与入库版逐字节相同（两个 log 仅 `elapsed_s` 变化），即 `PRED_COLS` / `check_pred` 上提与内层切分切换均为行为中性。**M2 主签与 M4/M5 会签仍待签。** |
| v1.3 | 2026-11-11 | **C1/C2 判定落地（契约不变）**：§7.6 补实测结论——C1 分辨率不足（Δ=+0.0142，90% CI 0.0078–0.0207）、C2 实际等价（Δ=−0.0053，90% CI −0.0093~−0.0015）；`decisions.py` 把 `c1_verdict` 重构为通用 `controlled_verdict(before, after, …)` 并新增 `c2_verdict`（修掉 C2 复用 C1 标签的隐患）；`table_main.csv` 补齐 9 行、`market_gap.csv` 扩到 8 arm × 3 法、`c1_model_class.ipynb` 写入真实结果。 |

---

*本文件属方案类文档，改动请同步 `docs/plans/CHANGELOG_structure.md`；实现代码落地后，函数签名以本文件为准并回填「已实现」标记。*
