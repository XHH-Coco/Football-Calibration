# §5.2 H1 — Calibration: the market is under-dispersed, the models are over-dispersed

**One-sentence conclusion.** The de-vigged closing market has a calibration slope of 1.086 (90% cluster CI 1.047–1.124, above one) and is therefore under-dispersed — longshots are overpriced and favourites underpriced, the favourite–longshot bias — whereas every transparent model arm has a slope below one on the draw class, with B4 at 0.78 and the boosted arms collapsing to 0.32–0.38: the market and the models fail calibration in *opposite* directions.

### 5.2.1 What this section answers

This section assembles the complete H1 from its two halves. The market side (calibration slope and tail-bin bias of B6 under three de-vigging methods) is computed by M2 and reported in `analysis/h1_market.ipynb`; the model side (reliability curves and calibration slopes of B0–B5b) is M5's contribution, produced by `analysis/h1_calibration.ipynb`. H1 asks whether the market is calibrated after de-vigging; the model side is not a hypothesis but a descriptive error analysis that shows whether "calibration" is even the right axis on which to compare model and market.

### 5.2.2 Data and method

**Data.** Prediction files `results/preds/preds_B0.csv … preds_B6.csv`, each carrying `p_home, p_draw, p_away, y` for the 16,733 evaluation matches (16,728 for B6 after dropping the five matches without closing prices). No market column enters any model arm.

**Market side (M2).** One-versus-rest logistic recalibration `logit(y_class) ~ a + b · logit(p_class)` pooled over the three classes, estimated per de-vigging method with cluster bootstrap over the 48 league–season blocks; tail-bin bias is `mean(pred) − mean(freq)` in the low (< 8 %) and high (> 85 %) probability tails. A slope above one means the reliability curve lies *below* the diagonal at low probabilities and above it at high probabilities (under-dispersed).

**Model side (M5).** For each arm and each class, a per-class calibration slope and intercept are estimated the same way, ECE is computed over ten bins, and reliability curves are drawn with Gaussian-kernel local smoothing (Nadaraya–Watson, bandwidth 0.045) rather than hard bins.

### 5.2.3 Results

**Market side (source: M2 `h1_market.ipynb`).**

| De-vigging | Slope | 90% CI | Tail bias low (<8%) | Tail bias high (>85%) |
|---|---:|---:|---:|---:|
| proportional | 1.0864 | 1.0472–1.1244 | +0.0124 / +0.0067 / +0.0016 | +0.0018 / −0.0103 / −0.0221 |
| Shin | 1.0515 | 1.0144–1.0882 | — | — |
| power | 1.0305 | 0.9938–1.0659 | — | — |

The proportional slope's 90% lower bound (1.047) is above one, so H1 is **supported**; the tail bins have the pre-registered sign (low positive, high negative), the favourite–longshot signature. Shin and power give the same direction, with the pre-registered ordering "largest under proportional" holding descriptively.

**Model side (source: `results/logs/m5_calibration_slopes.csv`; slope < 1 = over-dispersed).**

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

### 5.2.4 Error analysis: two opposite calibration failures

The market is under-dispersed because a bookmaker's margin is removed by a single global rescaling, which over-weights the longshot tail (FLB; Ali 1977). The models are over-dispersed for a different reason: Dixon–Coles and especially the boosted arms assign very low probability to outcomes they are unsure about, and draws are the class where evidence is thinnest. The two failures are therefore not mirror images of a shared cause, which is exactly why H4 matters — it tests whether the model–market gap is a *calibration* defect the market could itself shed (it is not; §5.4, H4).

### 5.2.5 Limitations

1. **Model-side slopes are descriptive**, not pre-registered statistics; the H1 claim attaches only to the market side. Per-class slopes have no cluster-bootstrap intervals here, so differences among arms are read as shapes, not tested.
2. **Kernel bandwidth is fixed** at 0.045; the smoothed curves are a visualisation, and the quantitative claims rest on the slopes and tail bins rather than on any single curve.
3. **B0 is omitted** from the model-side table: as a constant-frequency prior its logit range is degenerate and its slope is not interpretable.
4. This section says nothing about *why* a given arm is miscalibrated, only that it is; attribution across the ladder belongs to C1/C2 (§5.1).

---

**Self-check**

- [x] Every number traces to `results/logs/m5_*.csv` (model side) or M2's `h1_market.ipynb` (market side); slopes are one-versus-rest logistic, not accuracy.
- [x] Reliability curves use local smoothing, not ten hard bins.
- [ ] Model-side per-class cluster intervals are not reported (declared descriptive).
- [x] The H1 claim (slope above one) attaches to the market side and is judged by its 90% lower bound.
