# Do football betting markets know more than a model can learn? Auditing the closing line for calibration and information

**Team 32 · DSC5001C63 Statistical Machine Learning I · Project Proposal, revised execution blueprint v3.0**
Date: 2026-11-08 · Supersedes the submitted 2026-10-30 version as the internal execution blueprint. The submitted PDF is retained unchanged as the record of what was handed in; this document records the design actually implemented, with a short *evolution of the proposal* section to appear in the final report.

| | |
|---|---|
| Team | Team 32 (5 members; names and UIDs as on the submitted PDF) |
| Submitted version | `Team-32-Proposal.pdf`, 2026-10-30 (2-point deliverable, unchanged) |
| This version | **v3.0**, 2026-11-08 — same research question, corrected hypotheses, controlled ladder |
| Companion documents | `08_小组分工实施方案_v1.3.md` (r2 execution revision), `data_interface.md` v1.3 (contracts), five role cards |
| Status | Approved as the single execution blueprint; no parallel naming or hypothesis sets remain |

---

## 1. Problem and research questions

Bookmakers publish closing decimal prices for home win, draw and away win, and the de-vigged probabilities implied by those prices are among the most accurate publicly available three-class forecasts in sport. They are usually treated as a rival to be beaten, or as a diagnostic of the bettor, rather than as an object to be audited. We invert the framing: **the market is not our opponent but our most informative measuring instrument, and the questions worth asking are the ones it answers badly.**

**RQ1.** After de-vigging, are market probabilities calibrated — does the reliability curve lie on the diagonal, and is the calibration slope equal to one?

**RQ2.** Can a transparent model fitted only to pre-match information (no market columns in any feature set) match de-vigged closing log loss out of sample; if not, precisely where does the gap concentrate, and how much of it survives recalibrating the market itself?

This is not a football prediction project. In risk management, insurance pricing, credit scoring and clinical decision support, decisions are driven by predicted probabilities rather than predicted labels, and a model that classifies well but is badly calibrated is dangerous in each of those settings. Football gives us what those domains cannot: a high-frequency three-class outcome that is repeatedly observed, and a strong external forecaster with a known information set. **A negative result here is informative only if the shortfall is localised and decomposable — which is exactly what we estimate.**

---

## 2. Hypotheses

Each hypothesis is stated with the observation that would falsify it, fixed before any model is fitted. All claims are paired per-match differences with cluster-bootstrap intervals; an interval wider than its pre-specified margin is reported descriptively and supports neither superiority nor equivalence.

**H1 — The market is under-dispersed, not unbiased.** De-vigged closing probabilities have a calibration intercept near zero but a **slope greater than one**: the forecast is too conservative, so the reliability curve lies **below** the diagonal at low predicted probabilities and **above** it at high ones. In plain terms, longshots are assigned too much probability and favourites too little (equivalently, longshot decimal odds are too short and favourite odds too long) — the favourite–longshot bias (Ali 1977; Cain, Law & Peel 2000). We do not claim this is new; the open question is whether it survives de-vigging. Štrumbelj (2014) shows that some margin-removal methods remove it while proportional normalisation does not. We therefore report the slope and the tail-bin bias under proportional, Shin and power de-vigging, and pre-register the prediction that the bias is largest under proportional de-vigging.

> **Correction to the submitted version.** The 2026-10-30 text described the reliability curve as *above* the diagonal at low probabilities while simultaneously claiming a slope above one; those two statements have opposite signs. A slope above one means the market compresses probabilities toward the middle, so low-probability events occur **less** often than priced. The direction above is the corrected one, and the implementation asserts this sign.

*Falsification.* (a) Primary: falsified if the proportional-de-vigged calibration slope is at most 1. (b) Secondary, for the pre-registered ordering: we claim "largest under proportional" only if the 90% cluster-bootstrap interval for `|slope−1|_proportional − |slope−1|_Shin` has a lower bound above 0; otherwise the three slopes are reported descriptively. The three de-vigging methods are declared **one robustness family**, not three independent hypothesis tests, so no multiplicity correction is claimed.

**H2 — A transparent model does not close the gap, and the residual is not negligible.** Two one-sided claims, both pre-specified, with **B4 (Dixon–Coles)** as the transparent model and **B6** as the de-vigged closing market.
(a) B4 does not beat B6: falsified if the 95% cluster-bootstrap interval on the paired per-match log-loss difference excludes zero in B4's favour.
(b) The residual gap is practically non-zero: falsified if the 90% interval lies entirely within **±0.02 nats per match**, our single pre-specified equivalence margin. *Correction to the submitted version:* the submitted text used ±0.01; at 48 clusters the minimum detectable difference is itself of order 0.02, so ±0.01 would be unresolvable by design. One margin, 0.02, is used everywhere in the project.
If an interval is wider than the margin we report the estimate descriptively and claim neither superiority nor equivalence.

**H3 — The gap is localised, not diffuse.** The per-match gap (market minus model; positive means the model is worse) is larger for matches involving a newly promoted side and for the first six matchdays of a season; both indicators are estimated jointly with league–season fixed effects. The mechanism is that each signals stale strength information — the market observes transfers, preselection news and spending, whereas our model observes only earlier scorelines. The two indicators (`is_promoted_*`, `matchday`) are constructed **only from pre-season team lists and the fixture calendar**, never from results, so they cannot leak outcomes.

*Falsification and reporting rule.* H3 is supported only if **both** coefficients are positive **and** each 90% cluster-bootstrap interval has a lower bound above 0. If either interval crosses 0 we report both estimates descriptively and neither confirm nor refute the hypothesis as a whole — *correction to the submitted version*, which declared H3 falsified if "either coefficient is at most 0", a rule inconsistent with joint estimation. We report a matchday-window sweep (1–3, 1–6, 1–10) as a **declared descriptive robustness curve** so that "six" is a reported curve rather than an arbitrary threshold; the sweep carries no significance claim and enters no primary inference.

**H4 — The gap is information, not miscalibration.** Replacing the market benchmark B6 with a recalibrated market **B6r** (submitted version: `MK*`) — a two-parameter temperature-and-bias logit map — changes the estimated model–market gap by less than 25%. **Both recalibration parameters are fitted strictly inside the training window of each rolling-origin fold and applied to that fold's test season**; no outer-block outcome is used to fit them. *Falsification:* H4 is supported only if the **upper bound** of the 90% cluster-bootstrap interval on the relative change is below 25%, and is falsified if that interval's lower bound exceeds 25%. If the denominator gap is smaller than 0.01 nats we report the absolute change instead and state that the ratio is unstable. *Correction to the submitted version:* the 25% rule previously had no interval criterion and no guard for a near-zero denominator.

**This question is the reason to run RQ1 at all**: it decides how the rest of the results should be read.

> **What is deliberately *not* a hypothesis.** (i) The B4↔B5a and B5a↔B5b single-factor comparisons are reported as **controlled comparisons C1 and C2**, not as hypotheses; their equivalence margin is the same ±0.02 and their four-way decision rule is frozen in code. This keeps the ladder clean without pretending a null result is a research finding. (ii) Absolute calibration diagnostics of the *models* (reliability curves by outcome class, ECE, bias-vs-probability) are descriptive error analysis supporting H1, not a separate claim. (iii) The decline of the home-advantage parameter γ and the closed-door 2020–21 period are an **appendix robustness analysis (A1)**, not a hypothesis: the period coincides with curtailed seasons, congested fixtures and rule changes, and there is only one such season, so a causal "natural experiment" claim is not defensible.

---

## 3. Data

- **Source.** football-data.co.uk — publicly downloadable, no registration and no API key. One CSV per league-season, match-level.
- **Snapshot.** All **132** files (six leagues × 22 seasons, 2003/04–2024/25) are committed to the repository with a 132-row SHA256 manifest; **46,507 matches** in total. Team members clone rather than re-download, so no source-site drift is possible. *Correction:* the submitted version described only a 9-season, 18,865-match window; the extra 14 seasons enter training history only and produce no test blocks.
- **Evaluation window.** Eight target seasons 2017/18–2024/25 × 6 leagues = **48 (league, season) blocks, 16,733 matches**, each evaluated exactly once.
- **Benchmark.** Pinnacle closing prices `PSCH/PSCD/PSCA` (de-vigged by proportional, Shin and power methods). Coverage is complete in 45 of 48 blocks; the other three blocks lack 5 matches in total (Eredivisie 2017/18: 3, La Liga 2017/18: 1, Bundesliga 2018/19: 1), which are dropped, not imputed, giving **B6 n = 16,728**. `PSH/PSD/PSA` are pre-closing, `B365*` is another bookmaker, and `MaxCH` (from 2019/20) is a robustness benchmark only.
- **Target.** Three-class outcome `FTR` H/D/A → `y = 0/1/2`; probability column order is fixed as `p_home, p_draw, p_away` and asserted in code.
- **Known challenges.** Chronological dependence (random splits leak the future); non-stationary team identities from promotion/relegation; two curtailed 2019/20 seasons; intrinsic noise bounding top-1 accuracy near 50% (accuracy is not used); heterogeneous team-name spelling, harmonised via a committed alias table.

---

## 4. Models

The ladder is built so that the two steps used for attribution change **exactly one factor**. No market column enters any model arm by construction; market columns are used only to construct B6 and B6r.

| Arm | Content | Role |
|---|---|---|
| **B0** | Expanding league-level outcome frequencies from strictly earlier matches | Trivial reference |
| **B1** | Chronologically updated Elo ratings with a home increment | Team strength |
| **B2** | Ordered logit on rating differences and recent-form covariates (multinomial logit as robustness) | Interpretable classical baseline |
| **B3** | Independent Poisson attack–defence model → score matrix → three probabilities | Score-generating mechanism |
| **B4** | B3 plus exponential time decay ξ and low-score dependence ρ (**Dixon–Coles**); primary transparent model, H2's subject | Structurally correct model |
| **B5a** | Gradient boosting **restricted to B4's information set**, with the identical `sample_weight = exp(−ξ̂·Δdays)` | C1: model class only |
| **B5b** | The same booster with additional shot, rest-day and season-stage features; identical weights and hyperparameters | C2: information only |
| **B6** | De-vigged Pinnacle closing probabilities | Market benchmark (H2, H3) |
| **B6r** | B6 passed through the two-parameter recalibration map; fitted in-fold on train only | Instrument for H4 |

**B4 → B5a** changes only the model class (both feature whitelist and sample weights are locked and signed off); **B5a → B5b** changes only the information set. These are the only two rungs that support an interpretable attribution claim: B1→B2 changes both estimation principle and covariates, and B2→B3 changes both model and information, so B0–B3 are reported without causal interpretation. *Correction to the submitted version:* its M4 arm was trained on M2's richer feature set but compared against M3, so the claimed "difference is information, not model class" did not follow; B5a/B5b fix this. The goal-based multinomial-logit features of the submitted M2 are retained inside B5b's full feature set.

**Implementation note (D1, 2026-11-08).** Both boosting arms are fitted with `sklearn.ensemble.HistGradientBoostingClassifier` from the already-locked scikit-learn 1.9.1 (`loss='log_loss'`, `early_stopping=True`, `sample_weight` passed explicitly); no third-party boosting library is added and the dependency set stays at eight packages. The controlled comparison locks the *implementation, weights and hyperparameters*, not a particular vendor, so this choice leaves C1/C2 unchanged. Because `predict_proba` follows the estimator's internal `classes_` order, every arm is re-ordered to `p_home, p_draw, p_away` before writing predictions, with an assertion (see `data_interface.md` §1.1).

### Mapping to the submitted proposal

| Submitted (2026-10-30) | This version | Note |
|---|---|---|
| M0 prior | B0 | Same model |
| M1 Elo → ordered logit | B1 + B2 | One merged arm split into two, so the ladder is auditable |
| M2 multinomial logit, time-decayed goal features | — (absorbed into B5b features) | Method change: B2 is ordered logit on Elo difference; declared in the report |
| M3 Dixon–Coles | B4 | Same model; B3 added as the unpatched rung |
| M4 GBM on M2 features | B5a + B5b | Split into two single-factor arms |
| MK de-vigged closing | B6 | Same benchmark (`PSCH/PSCD/PSCA`) |
| MK* recalibrated market | **B6r** | Restored as the sole instrument for H4 |

Model identifiers, filenames (`preds_B0.csv` … `preds_B6.csv`, `preds_B6r.csv`) and the `model` column use **B-names only**; M1–M5 are reserved for team members.

---

## 5. Evaluation

**Protocol.** Expanding-window rolling origin by season: for target season *s* and league ℓ, every model is fitted on matches in ℓ strictly before *s* and predicts every match of *s*. Hyperparameters (ξ, ρ, boosting settings) and both B6r recalibration parameters are selected by an inner expanding-window validation that sees only pre-*s* data (for B6r, only training matches with complete `PSCH/PSCD/PSCA` are usable, since closing prices begin in 2012/13); each outer block is evaluated exactly once.

**Inference.** All claims are paired per-match differences on the same matches. Intervals are cluster-bootstrap over the **48 (league, season) blocks** (10,000 resamples) with cluster-robust standard errors as a cross-check; individual matches are never the resampling unit. We report the estimated **design effect** alongside every interval, since at 48 clusters the detectable difference is governed by within-block correlation rather than by the 16,733 matches. Per-league and per-season breakdowns, the matchday-window sweep, and the appendix A1 home-advantage analysis are declared descriptive in advance so that no result is promoted after the fact on a favourable subset.

**Metrics.** Log loss primary; Brier score and ranked probability score secondary. Calibration is assessed by reliability diagrams smoothed with **local smoothing / splines (W7 / W5)** rather than hard decile bins, by one-versus-rest calibration slope and intercept per outcome class, by ECE, and by a bias-versus-predicted-probability plot carrying H1's regional claim. All are strictly proper scoring rules (Gneiting & Raftery 2007).

**Course tools.** W3 cluster bootstrap for every interval and design effect; W5 splines/GAM and W7 local smoothing for the H1 reliability curves and the H3 matchday robustness curve; appendix A1 additionally tracks the 22-point γ series with a spline fit as a descriptive robustness check.

---

## 6. Expected contribution

- A calibration audit of real closing prices that reports its own dependence on the de-vigging method instead of silently choosing one.
- A localised account of where a transparent model falls short — promoted sides and early-season fixtures — with league–season fixed effects and a pre-declared descriptive window sweep, rather than a single aggregate accuracy number.
- A decomposition of the market's advantage into a calibration component and an information component (B6r / H4), which the literature on either side does not make.
- A controlled ladder with two genuinely single-factor steps and a signed feature-and-weight whitelist, so that the model-class and information effects are separately identified.
- A reproducible appendix: committed, checksummed raw data, pinned versions, fixed seeds, one-command rebuild of the modelling panel.

**Negative results are the designed outcome.** Whether or not a model beats the market, the project still delivers a calibration map of the price and a diagnosis of where its information lives. This project is newly initiated for DSC5001C63 and does not reuse data, code or analysis from any other course.

---

## 7. Team and work packages

| Work package | Content | Owner |
|---|---|---|
| Data | Six-league ingestion, name harmonisation, checksummed snapshot, coverage matrix, promoted/matchday indicators | ZHOU Yixuan |
| Models B0/B1/B2/B5a/B5b | Baselines, feature engineering, whitelist, ablation | SHU Peixuan / SUN Peng (per role cards M3/M4) |
| Models B3/B4 | Dixon–Coles with ξ/γ/ρ, convergence diagnostics, appendix A1 | SHU Peixuan |
| Evaluation & inference | Rolling-origin harness, three de-vigging methods, B6r recalibration, cluster bootstrap, H1–H4 decisions, design effects | WANG Xingshuai |
| Outputs | Calibration diagnostics, error analysis, slides, all-member recording, appendix | WAN Yihui |

*(Names map to role cards M1–M5; see `08_小组分工实施方案_v1.3.md` §9 for the contribution statement.)*

---

## 8. Timeline

| Period | Milestone |
|---|---|
| 8–9 Nov | Contracts frozen: splits, alias table, feature whitelist, prediction schema, B-names |
| 10–17 Nov | Rolling-origin harness, B0–B5b, B6 under three de-vigging methods, G1 full-chain pass |
| 18–24 Nov | B6r, cluster bootstrap, H1–H4 analysis, calibration diagnostics, core figures, G2 numbers frozen |
| 25–29 Nov | Slides (10 pages), all-member recording, appendix, report, submission 29 Nov |

---

## Revision notes（中文，供组内与报告使用）

**v2.0（2026-10-30 提交版）→ v3.0 的实质改动**

| # | 改动 | 原因 |
|---|---|---|
| 1 | **H1 方向订正**：斜率 >1（under-dispersed）时，低概率区可靠性曲线在对角线**下方**、高概率区在**上方**；并把 "over-priced/under-priced" 改成不歧义的概率表述 | 提交版把曲线方向写反，照文字写断言会把符号设反 |
| 2 | **阶梯换成 B0–B6 + B6r**，B5a/B5b 锁特征与 `sample_weight` | 提交版 M4 用 M2 的信息集却与 M3 对照，归因不成立 |
| 3 | M1 合并臂拆成 B1（Elo）+ B2（有序 logit），B3 作为未打补丁的一级 | 阶梯可审计；报告写明 M2→B2 的方法学变更 |
| 4 | **H1 补预注册判定**：三种去抽水下 "proportional 最大" 需 90% 区间下界 > 0；三法声明为一个稳健性族 | 提交版预注册了「最大」却没给证伪规则 |
| 5 | **等价边际统一 ±0.02**（原 ±0.01） | 48 簇下最小可检测差约 0.02，±0.01 设计上不可分辨 |
| 6 | **B6r 两参数只在 train 段拟合**；H4 用 90% 区间上界 < 25% 判定，分母 < 0.01 时改报绝对差 | 提交版 in-sample 边界不明（防泄漏缺口），25% 无区间判定且分母不稳定 |
| 7 | **H3 证伪改为「两系数均正且各自区间下界 > 0」**；matchday sweep 声明描述性 | 提交版「任一 ≤0 即证伪」与联合估计不匹配，且 sweep 有多重比较问题 |
| 8 | **补 H3 的数据契约**：`is_promoted_*` 与 `matchday` 由季前名单 / 赛程构造，写进 `panel.parquet` | H3 原本在分工方案里没有对应列，做不出来 |
| 9 | 原 v1.2 的 H1（结构 vs 灵活）降为**受控比较 C1/C2**，H2a/H2b 降为描述性误差分析与稳健性，H3（主场优势）降为**附录 A1** | 一个项目只保留一条主线；空场季 n=1 且混杂严重，不做因果主张 |
| 10 | 课程工具改挂主线：样条 / 局部平滑用于 H1 可靠性曲线与 H3 matchday 曲线 | W5/W7 直接服务主推断，而非挂在一个偏题的假设上 |
| 11 | 数据事实订正：132 CSV / 46,507 场 / 48 块 16,733 场 / B6 有效 n=16,728 | 与 `configs/raw_manifest.csv` 实测一致 |
| 12 | **D1 实现口径**：B5a/B5b 用 sklearn 1.9.1 内置 HGB，零新增依赖；补两条静默错误契约（内部标签重排断言、B6r train 段拟合样本边界） | 分工方案 v1.3 曾写死 LightGBM 却未登记依赖；B2 内部标签与全局 `y` 方向相反；`PSCH` 自 2012/13 才有 |
| 13 | **数据事实再订正（11/08 全窗复测）**：三列收盘赔率缺失由「N1 1718 的 3 场」改为「3 块共 5 场」，B6 / B6r 有效 n 由 16,730 改为 **16,728**；补 `match_id` 与 ISO 日期契约 | 初测漏计 `1718_SP1` 与 `1819_D1` 各 1 场，会让 B6 行数断言与 H4 分母错 |

**报告里必须有的两段**

1. **B↔M 映射表**（本文件 §4 末）：老师按提交版检查，代码与图表一律用 B 系列，映射表消除歧义。
2. ***Evolution of the proposal***：一段 100–150 字，说明 10/30 提交后经组内评审，修正了校准斜率方向、把 GBM 对照拆成两次单因素、统一等价边际、补回重校准基准；**研究问题 RQ1/RQ2 与 H1–H4 主线未变**。这不是 deviation 声明，而是设计迭代说明。

**报备**：本修订属计划迭代，不重新提交 Proposal（2 分已计）。给 instructor 的简短说明可与「Slides / Poster / Main Report 口径确认信」合并发出，见分工方案 §4.2-a U2。

---

*Proposal v3.0 · 2026-11-08 · 唯一执行蓝本；提交版 PDF 保留为提交凭据，不覆盖。*
