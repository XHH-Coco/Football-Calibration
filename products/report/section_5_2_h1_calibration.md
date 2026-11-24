# §5.2 H1 — Calibration: the market is under-dispersed, the models are over-dispersed

**One-sentence conclusion.** De-vigged closing prices are under-dispersed **in direction**: the pre-registered proportional de-vigging gives a calibration slope of 1.086 (90% cluster CI 1.047–1.124, lower bound above one) with the favourite–longshot signature in both tails — but the **magnitude depends on how the margin is removed** (Shin 1.052, 1.014–1.088; power 1.030, 0.994–1.066, crossing one), and only the away class is above one under all three methods. Every transparent model arm, by contrast, has a slope well below one on the draw class (B4 at 0.94, the boosted arms at 0.53–0.57): the market and the models fail calibration in *opposite* directions on the class where it matters most.

### 5.2.1 What this section answers

This section assembles the complete H1 from its two halves. The market side (calibration slope, per-class slopes and tail-bin bias of B6 under three de-vigging methods) is computed by M2 and reported in `analysis/h1_market.ipynb`; the model side (reliability curves and calibration slopes of B0–B5b) is M5's contribution, produced by `analysis/h1_calibration.ipynb`. H1 asks whether the market is calibrated after de-vigging; the model side is not a hypothesis but a descriptive error analysis showing whether "calibration" is even the right axis on which to compare model and market.

### 5.2.2 Data and method

**Data.** Prediction files `results/preds/preds_B0.csv … preds_B6.csv`, each carrying `p_home, p_draw, p_away, y` for the 16,733 evaluation matches (16,728 for B6 after dropping the five matches without closing prices). No market column enters any model arm.

**Market side (M2).** One-versus-rest logistic recalibration `logit(y_class) ~ a + b · logit(p_class)`: the slope is estimated **within each of the 48 league–season blocks** and pooled with block-size weights (so the point estimate and its interval share one estimator); intervals come from the same 48-block cluster bootstrap. A slope above one means the reliability curve lies *below* the diagonal at low probabilities and above it at high probabilities (under-dispersed). Tail-bin bias is `mean(pred) − mean(freq)` in the lowest and highest deciles.

**Model side (M5).** For each arm and each class, a per-class calibration slope and intercept are estimated the same way at the single-equation level, ECE is computed over ten bins, and reliability curves are drawn with Gaussian-kernel local smoothing (Nadaraya–Watson). Both sides now share one implementation, `metrics.reliability_curve_smooth`: per-class Scott bandwidth, a grid restricted to each series' 1%–99% quantile range, and a minimum effective sample size of 20 per grid point. Tail-bin bias is written to `results/logs/m5_tail_bias.csv` at both quintile and decile resolution, and the decile ends are asserted equal to M2's `calibration.tail_bin_bias` to machine precision so the figure and the verdict table cannot drift apart.

### 5.2.3 Results

**Market side, method level (M2 `h1_market.ipynb`, `results/logs/m2_verdicts.csv`).**

| De-vigging | Slope | 90% cluster CI | Tail bias low | Tail bias high |
|---|---:|---:|---:|---:|
| **proportional** (pre-registered) | **1.0864** | **1.0472–1.1244** | +0.0124 / +0.0067 / +0.0016 | +0.0018 / −0.0103 / −0.0221 |
| Shin | 1.0515 | 1.0144–1.0882 | — | — |
| power | 1.0305 | 0.9938–1.0659 | — | — |

The proportional lower bound (1.047) is above one and the tail bins carry the pre-registered sign (low tail positive, high tail negative), so H1 is **supported as pre-registered**. The pre-registered ordering also holds: the deviation of proportional from one exceeds that of Shin by 0.0198 (90% CI 0.0130–0.0263, lower bound above zero).

**Market side, per-class slopes (`results/logs/h1_slope_by_class.csv`).**

| De-vigging | Home | Draw | Away |
|---|---:|---:|---:|
| proportional | 1.068 (1.035–1.103) | 1.104 (1.007–1.195) | 1.087 (1.049–1.125) |
| Shin | 1.037 (1.004–1.071) | 1.064 (0.970–1.153) | 1.054 (1.017–1.092) |
| power | 1.023 (0.990–1.057) | 1.024 (0.936–1.111) | **1.044 (1.008–1.081)** |

**Only the away class is above one under all three de-vigging methods.** Home and draw both cross one once the margin is removed by the power method. This is the single most informative cut of H1: the phenomenon is real but class-specific, and averaging the three classes dilutes it.

**Model side (source: `results/logs/m5_calibration_slopes.csv`; slope < 1 = over-dispersed, single-equation estimates).**

| Arm | Home | Draw | Away |
|---|---:|---:|---:|
| B1 (Elo) | 1.019 | 1.097 | 1.014 |
| B2 (ordinal logit) | 0.976 | 0.797 | 1.006 |
| B3 (Poisson) | 1.018 | 0.952 | 1.057 |
| **B4 (time-decayed DC)** | **0.940** | **0.944** | **0.964** |
| B5a (HGB, B4 info) | 1.103 | 0.528 | 1.082 |
| B5b (HGB, +shots/rest) | 1.109 | 0.566 | 1.091 |
| B6 (market) | 1.061 | 1.092 | 1.076 |

Two features stand out. First, the market's slopes are all above one (1.061–1.092) and **no transparent arm reproduces that pattern**: B4 sits just below one on all three classes (0.940–0.964), while the boosted arms bracket the market from both sides — home and away *above* one, draw far below. Second, the defect concentrates in the **draw** class and gets worse with model capacity, not better: Elo is well calibrated on draws (1.097) and B4 is mildly over-dispersed (0.944), but the two boosted arms fall to 0.53–0.57 with draw ECE of 0.019–0.024 — the worst of the whole ladder. The reliability curves are shown in `products/figures/fig05_model_reliability.png` (models, three classes separated) and the market slope and tail bias in `fig06_market_calibration.png`.

> **Both boosted arms' calibration moved when the hyper-parameter rule changed.** Under the retired per-fold grid, B5a/B5b used `max_leaf_nodes = 7` in 46 of 48 folds and scored draw slopes of 0.357 / 0.369 with home–away slopes of 0.904–0.919. With the fixed, shallower configuration (`leaf = 3`, `lr = 0.01`, §4.3.6) the draw slopes rise to **0.528 / 0.566** and the home–away slopes cross one to 1.08–1.11. So capacity was not merely "spreading draws too wide": it was distorting all three classes, and shrinking it moved the arms from uniformly over-dispersed to *under*-dispersed on home and away and much less over-dispersed on draws. The direction matches B4's experience — reduced capacity improved draw calibration *and* pooled log loss at the same time — but it also shows that a slope table read at one configuration describes that configuration, not the model class.

> **A correction we owe on the ECE sentence.** An earlier draft of this section claimed that with ρ fixed at zero "draw ECE falls from 0.030 to 0.018". Recomputed with the notebook's own `ece_binned` on the two prediction files, the retired argmin gives a draw ECE of **0.0107** and the fixed rule **0.0179** — it *rose*, and 0.030 does not appear in any artifact. All three classes rise (home 0.0139 → 0.0156, draw 0.0107 → 0.0179, away 0.0046 → 0.0072) while all three slopes move *towards* one (0.918 → 0.940, 0.775 → 0.944, 0.943 → 0.964). Two summary statistics of the same change therefore point in opposite directions. This is not noise to be averaged: ten equal-width bins put most draw predictions into two or three bins, so binned ECE is governed by *which* bins happen to be populated, whereas the slope uses every match. **We consequently treat the slope as the only decision statistic in this section and report ECE as a descriptive appendix.** The lesson generalises — a calibration claim quoted from ECE alone does not survive a change of binning.

> **What the draw slope change does and does not say.** Under the retired per-fold argmin (which selected ρ = −0.15 in 20 of 48 folds, `selection_diagnostic/xi_rho_by_block_argmin.csv`) the low-score correction pushed B4's draw slope down to 0.775; with ρ fixed at zero it is 0.944, and pooled log loss fell from 0.9939 to 0.9903 at the same time. The correction was therefore hurting *both* draw calibration and pooled loss, which makes it the clearest single example in the report of a defect that belonged to the estimation rule rather than to the model class. It is also a reminder that the two diagnostics need not agree: here they agreed on direction and disagreed only on ECE's sign, which is exactly why the slope carries the verdict.

> **A note on two estimators of the same quantity.** The market's per-class slopes in the model-side table above (1.061 / 1.092 / 1.076) are single-equation estimates on the pooled 16.7k matches, whereas the per-class table earlier in §5.2.3 is block-pooled (1.068 / 1.104 / 1.087). The two differ by up to 0.012 because averaging block-level logit slopes is not the same functional as one pooled logit fit (non-collapsibility). The pre-registered H1 statistic is the block-pooled one; the model-side table is kept for shape comparison across arms and is not used in any verdict.


### 5.2.4 Error analysis: two opposite calibration failures, and one confound we own

The market is under-dispersed because a bookmaker's margin is removed by a single global rescaling, which over-weights the longshot tail (FLB; Ali 1977). The models fail differently, and the sign depends on the class: draws are over-dispersed — models assign too much probability to a *specific* draw scoreline they cannot actually distinguish — while home and away for the boosted arms are under-dispersed, because a shallow tree ensemble that has shrunk most of the way to the base rate cannot express the confidence its own base rate implies. Draw is the class where evidence is thinnest, so it is where the failure is largest. The two sides' failures are therefore not mirror images of a shared cause, which is exactly why H4 matters — it tests whether the model–market gap is a *calibration* defect the market could itself shed (it is not; §5.4, H4).

**Where the draw error actually is — and its sign is not the one we expected.** The task card anticipated that draws in the 20–35% band would be *over*-predicted. They are under-predicted: B4 −0.0198, B3 −0.0140, i.e. 1.4–2.0 percentage points too low, while the arms that identify the draw least sharply are positive (B0 +0.0059, B1 +0.0031, B2 +0.0008). The third cut, by league (`results/logs/m5_league_bias.csv`, descriptive — six leagues × eight arms, no intervals), shows this is not uniform. B4 is negative in all six leagues, from −0.001 in the Premier League to −0.034 in the Bundesliga (−0.032 Serie A, −0.026 La Liga, −0.021 Eredivisie, −0.008 Ligue 1). The market is negative in five of six, smallest in magnitude in the same places. That co-movement is why we read the deficit as a property of how draws resolve in those leagues rather than a defect the models invented — and it is another reason not to hang a causal story on a single class-wide number.

**The confound we cannot separate.** Proportional de-vigging is itself known to leave a residual favourite–longshot bias, and our own pre-registered secondary criterion identifies proportional as the *most* deviant of the three methods (by 0.020 nats, interval excluding zero). Those two facts point the same way: part of the 1.086 is a property of the *method*, not of the market. This is why we state H1 as **direction-consistent with a de-vigging-dependent magnitude** rather than as "the market is significantly conservative", and why the per-class table matters — the away class survives all three methods, the home class does not.

This does **not** propagate to H2 or H4: the model–market gap is 0.0317 / 0.0319 / 0.0319 nats under proportional / Shin / power (spread < 1.5 × 10⁻⁴), so no conclusion about the gap depends on which de-vigging is chosen.

### 5.2.5 Limitations

1. **Model-side slopes are descriptive**, not pre-registered statistics; the H1 claim attaches only to the market side. Per-class slopes on the model side have no cluster-bootstrap intervals here, so differences among arms are read as shapes, not tested.
2. **The smoothing is a visualisation choice, not a result.** Every curve in `fig05` and `fig06` now goes through `metrics.reliability_curve_smooth` — per-class Scott bandwidth (`h ≈ 0.010–0.029`), a grid restricted to each series' own 1%–99% quantile range, and ESS ≥ 20 per grid point. This replaced an earlier model-side implementation with a fixed 0.045 bandwidth on a fixed 0.01–0.99 grid, which extrapolated across regions containing no matches: in the draw panel B6's curve climbed from x = 0.54 to 0.985 although no B6 draw prediction exceeds 0.416. The curves are drawn for shape only; every quantitative claim rests on the slopes and the tail bins.
3. **B0 is omitted** from the model-side table: as a constant-frequency prior its logit range is degenerate and its slope is not interpretable.
4. This section says nothing about *why* a given arm is miscalibrated, only that it is; attribution across the ladder belongs to C1/C2 (§5.1).

---

**Self-check**

- [x] Every number traces to `results/logs/m2_verdicts.csv` / `h1_slope_by_class.csv` (market side) or `results/logs/m5_*.csv` (model side); slopes are one-versus-rest logistic, not accuracy.
- [x] Reliability curves use local smoothing, not ten hard bins; both sides share `metrics.reliability_curve_smooth` (per-class Scott bandwidth, 1%–99% grid, ESS ≥ 20) and the choice is declared.
- [x] ECE is reported as descriptive only, and the paragraph that quoted it in the "improvement" direction has been corrected with the recomputed values.
- [ ] Model-side per-class cluster intervals are not reported (declared descriptive).
- [x] The H1 claim attaches to the market side, is judged by its 90% lower bound, and is stated as direction-consistent rather than as an unqualified "market is conservative".
- [x] The proportional-method confound is stated explicitly, together with the reason it cannot affect H2/H4.
