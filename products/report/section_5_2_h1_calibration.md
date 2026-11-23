# §5.2 H1 — Calibration: the market is under-dispersed, the models are over-dispersed

**One-sentence conclusion.** De-vigged closing prices are under-dispersed **in direction**: the pre-registered proportional de-vigging gives a calibration slope of 1.086 (90% cluster CI 1.047–1.124, lower bound above one) with the favourite–longshot signature in both tails — but the **magnitude depends on how the margin is removed** (Shin 1.052, 1.014–1.088; power 1.030, 0.994–1.066, crossing one), and only the away class is above one under all three methods. Every transparent model arm, by contrast, has a slope below one on the draw class (B4 at 0.78, the boosted arms at 0.32–0.38): the market and the models fail calibration in *opposite* directions.

### 5.2.1 What this section answers

This section assembles the complete H1 from its two halves. The market side (calibration slope, per-class slopes and tail-bin bias of B6 under three de-vigging methods) is computed by M2 and reported in `analysis/h1_market.ipynb`; the model side (reliability curves and calibration slopes of B0–B5b) is M5's contribution, produced by `analysis/h1_calibration.ipynb`. H1 asks whether the market is calibrated after de-vigging; the model side is not a hypothesis but a descriptive error analysis showing whether "calibration" is even the right axis on which to compare model and market.

### 5.2.2 Data and method

**Data.** Prediction files `results/preds/preds_B0.csv … preds_B6.csv`, each carrying `p_home, p_draw, p_away, y` for the 16,733 evaluation matches (16,728 for B6 after dropping the five matches without closing prices). No market column enters any model arm.

**Market side (M2).** One-versus-rest logistic recalibration `logit(y_class) ~ a + b · logit(p_class)`: the slope is estimated **within each of the 48 league–season blocks** and pooled with block-size weights (so the point estimate and its interval share one estimator); intervals come from the same 48-block cluster bootstrap. A slope above one means the reliability curve lies *below* the diagonal at low probabilities and above it at high probabilities (under-dispersed). Tail-bin bias is `mean(pred) − mean(freq)` in the lowest and highest deciles.

**Model side (M5).** For each arm and each class, a per-class calibration slope and intercept are estimated the same way at the single-equation level, ECE is computed over ten bins, and reliability curves are drawn with Gaussian-kernel local smoothing (Nadaraya–Watson; fixed bandwidth 0.045 on the model side, per-class Scott bandwidth on the market side).

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
| B2 (ordinal logit) | 0.976 | 0.795 | 1.006 |
| B3 (Poisson) | 1.018 | 0.952 | 1.057 |
| **B4 (Dixon–Coles)** | **0.918** | **0.775** | **0.943** |
| B5a (HGB, B4 info) | 0.892 | 0.323 | 0.884 |
| B5b (HGB, +shots/rest) | 0.896 | 0.378 | 0.887 |
| B6 (market) | 1.061 | 1.092 | 1.076 |

Two features stand out. First, the market's slopes are all above one while almost every model slope is below one — the market compresses probabilities toward the middle, the models spread them too wide. Second, the defect concentrates in the **draw** class and worsens as the model gets "stronger": Elo is well calibrated on draws (1.097), B4 is over-dispersed (0.775), and the two boosted arms collapse to 0.32–0.38 with draw ECE of ≈ 0.04 — the worst of the whole ladder. The reliability curves are shown in `products/figures/fig05_model_reliability.png` (models, three classes separated) and the market slope and tail bias in `fig06_market_calibration.png`.

> **A note on two estimators of the same quantity.** The market's per-class slopes in the model-side table above (1.061 / 1.092 / 1.076) are single-equation estimates on the pooled 16.7k matches, whereas the per-class table earlier in §5.2.3 is block-pooled (1.068 / 1.104 / 1.087). The two differ by up to 0.012 because averaging block-level logit slopes is not the same functional as one pooled logit fit (non-collapsibility). The pre-registered H1 statistic is the block-pooled one; the model-side table is kept for shape comparison across arms and is not used in any verdict.


### 5.2.4 Error analysis: two opposite calibration failures, and one confound we own

The market is under-dispersed because a bookmaker's margin is removed by a single global rescaling, which over-weights the longshot tail (FLB; Ali 1977). The models are over-dispersed for a different reason: Dixon–Coles and especially the boosted arms assign very low probability to outcomes they are unsure about, and draws are the class where evidence is thinnest. The two failures are therefore not mirror images of a shared cause, which is exactly why H4 matters — it tests whether the model–market gap is a *calibration* defect the market could itself shed (it is not; §5.4, H4).

**The confound we cannot separate.** Proportional de-vigging is itself known to leave a residual favourite–longshot bias, and our own pre-registered secondary criterion identifies proportional as the *most* deviant of the three methods (by 0.020 nats, interval excluding zero). Those two facts point the same way: part of the 1.086 is a property of the *method*, not of the market. This is why we state H1 as **direction-consistent with a de-vigging-dependent magnitude** rather than as "the market is significantly conservative", and why the per-class table matters — the away class survives all three methods, the home class does not.

This does **not** propagate to H2 or H4: the model–market gap is 0.0353 / 0.0355 / 0.0355 nats under proportional / Shin / power (spread < 2 × 10⁻⁴), so no conclusion about the gap depends on which de-vigging is chosen.

### 5.2.5 Limitations

1. **Model-side slopes are descriptive**, not pre-registered statistics; the H1 claim attaches only to the market side. Per-class slopes on the model side have no cluster-bootstrap intervals here, so differences among arms are read as shapes, not tested.
2. **The smoothing bandwidth is a visualisation choice, not a result.** Market-side curves use per-class Scott bandwidth (`h ≈ 0.010–0.029`); the model-side curves in `fig05` use a fixed 0.045. Both are drawn for shape only; every quantitative claim rests on the slopes and tail bins. (Superseded: an earlier market-side curve used a single bandwidth of `n^(-1/5) = 0.143` on the probability scale, which flattened the draw curve to a near-horizontal line — a visualisation artefact, corrected in `metrics.reliability_curve_smooth`.)
3. **B0 is omitted** from the model-side table: as a constant-frequency prior its logit range is degenerate and its slope is not interpretable.
4. This section says nothing about *why* a given arm is miscalibrated, only that it is; attribution across the ladder belongs to C1/C2 (§5.1).

---

**Self-check**

- [x] Every number traces to `results/logs/m2_verdicts.csv` / `h1_slope_by_class.csv` (market side) or `results/logs/m5_*.csv` (model side); slopes are one-versus-rest logistic, not accuracy.
- [x] Reliability curves use local smoothing, not ten hard bins; the bandwidth is per-class Scott on the market side and the choice is declared.
- [ ] Model-side per-class cluster intervals are not reported (declared descriptive).
- [x] The H1 claim attaches to the market side, is judged by its 90% lower bound, and is stated as direction-consistent rather than as an unqualified "market is conservative".
- [x] The proportional-method confound is stated explicitly, together with the reason it cannot affect H2/H4.
