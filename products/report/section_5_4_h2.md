# §5.4 H2 — Reading the gap: the market's edge is information, not miscalibration

**One-sentence conclusion.** Every transparent arm trails the de-vigged market on the same matches — the *best* of them, the ordinal logit B2, by 0.027 nats per match, and the designated protagonist B4 by 0.032 — and repassing the market through its own recalibration barely moves that gap, so the shortfall is information the model lacks, not a calibration error.

The shortfall is measured in three parts.

**First, it is universal.** All seven transparent arms B0–B5b trail B6 on the same 16,728 matches, from 0.027 (B2) to 0.116 (B0) nats. The pre-registered comparison uses B4 (0.0317, 90% CI 0.0278–0.0359; 95% CI 0.0271–0.0366), and both H2 criteria are met: the 95% interval excludes zero on the "model is worse" side, and the 90% interval lies entirely above the +0.02 equivalence margin.

**Second, it is not a method artefact.** The three de-vigging methods — proportional, Shin and power — give the same sign and essentially the same magnitude (0.0317, 0.0319, 0.0319 nats), so the gap survives however the margin is removed. This matters for H1 too: §5.2 shows that the *level* of the market's calibration slope depends on the de-vigging method, but the *gap* does not, so no H2 conclusion inherits that ambiguity.

**Third, it is information, not calibration.** Passing the market through its own two-parameter recalibration fitted only on each fold's training data (B6r) changes the gap by a relative 0.0019 (90% CI −0.0085–0.0127, upper bound 0.013 < 0.25). The fair objection at this point is that a two-parameter tool may simply be too weak to repair anything, so we also computed an **oracle bound**: recalibrate the market *within each of the 48 league–season blocks using that block's own test outcomes* (96 free parameters, hindsight included) and re-evaluate on the same matches. Even then the market's log loss improves only from 0.958536 to 0.955763 (+0.00277 nats) and the gap *widens* from 0.0317 to 0.0345 — a relative change of **+8.7%, still far below 25%**. Calibration, even when allowed to cheat, explains less than a tenth of the shortfall.

### 5.4.1 Why the ladder is not monotone (and why that does not rescue the model)

The model column of `table_main.csv` is not ordered by complexity: B2 = 0.9855, B4 = 0.9903, B1 = 0.9926, B3 = 0.9986, B5b = 1.0033, B5a = 1.0061. **B2 beats B4 by 0.0048 nats (90% paired CI 0.0013–0.0084, excluding zero)** — a difference the pre-registered design does not anticipate, because B4 was fixed in advance as the H2 protagonist.

Two consequences, one of which we state as a caveat and one as a finding.

*The caveat:* the headline gap of 0.032 is attached to B4, not to the best arm. Using B2 instead gives **0.027 (90% CI 0.0241–0.0298; 95% CI 0.0236–0.0303)**, i.e. B4's shortfall overstates "what a transparent model can do" by about 18%. The H2 verdict is unchanged — 0.027 is still entirely above the +0.02 equivalence margin, and its 95% interval still excludes zero — but the honest sentence is "the best transparent model trails the market by at least 0.027 nats", not "by 0.032".

*The finding:* more complexity buys nothing here, and the controlled comparisons say why. On 16,728 matches an Elo difference plus an ordinal logit on five features already captures most of what is predictable from pre-match information; Dixon–Coles adds time decay on top and lands between the two; and the two boosted arms add thirty-odd columns on the same information set and land at 1.0033–1.0061. C2 is the controlled evidence: holding the model class and hyper-parameters fixed and only widening the information set (B5a → B5b) is **practically equivalent** (−0.0028, 90% CI −0.0062 to +0.0005, entirely inside ±0.02 and spanning zero). The extra features do not carry usable signal at this sample size; they carry variance.

*Rebuild note (v1.5).* `preds_B2.csv` was regenerated in the locked environment on 2026-11-24 after `b2_ordinal.py` was found to pass the removed `multi_class` argument to `LogisticRegression` (sklearn 1.9.1). The rebuild is byte-identical across repeated runs and moves pooled log loss from 0.985554 to 0.985497 (−5.7 × 10⁻⁵ nats); individual match probabilities move by up to 6 × 10⁻², so the *file* is not reproduced, but every downstream number in this section is recomputed from the rebuilt file. No verdict changes.

### 5.4.2 A league-level pattern that does not transfer

B6r's fitted temperature is systematically league-specific and stable across all eight seasons per league: D1 0.959–0.969, N1 0.932–0.996, E0 1.030–1.060, SP1 1.023–1.057, F1 1.051–1.093, I1 1.104–1.143 (the bias term `d` stays within ±0.07). That is not noise — it says the market's over/under-dispersion has a persistent national character (Italian prices are too flat, German prices too sharp).

But when those parameters are applied to the *next* season's matches — which is exactly what B6r does — the total effect is 6.1 × 10⁻⁵ nats (90% CI −4.0 × 10⁻⁴ to +2.8 × 10⁻⁴, covering zero). The pattern is real, league-level and slow-moving, and yet worth nothing for forecasting the next match. This is a clean illustration of why H4 comes out as it does: the market's residual calibration defect is a *style*, not a tradable error, so repairing it cannot close an information gap.

*Sources: `results/table_main.csv` (B4−B6 = 0.0317; B2−B4 = −0.0048; B2−B6 = 0.0270), `results/market_gap.csv` (three methods; B6r row), `results/logs/b6r_n_fit.csv` (per-fold `c`, `d`, `n_fit`), `analysis/h4_information.ipynb` (H4 relative change 0.0019, 90% upper 0.013), `results/logs/h4_oracle_bound.csv` (oracle +8.7%).*
