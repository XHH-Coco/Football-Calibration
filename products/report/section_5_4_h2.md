# §5.4 H2 — Reading the gap: the market's edge is information, not miscalibration

**One-sentence conclusion.** Every transparent arm trails the de-vigged market on the same matches — the *best* of them, the ordinal logit B2, by 0.027 nats per match, and the designated protagonist B4 by 0.032 — and repassing the market through its own recalibration barely moves that gap, so the shortfall is information the model lacks, not a calibration error.

The shortfall is measured in three parts.

**First, it is universal.** All seven transparent arms B0–B5b trail B6 on the same 16,728 matches, from 0.027 (B2) to 0.116 (B0) nats. The pre-registered comparison uses B4 (0.0317, 90% CI 0.0278–0.0359; 95% CI 0.0271–0.0366), and both H2 criteria are met: the 95% interval excludes zero on the "model is worse" side, and the 90% interval lies entirely above the +0.02 equivalence margin.

**Second, it is not a method artefact.** The three de-vigging methods — proportional, Shin and power — give the same sign and essentially the same magnitude (0.0317, 0.0319, 0.0319 nats), so the gap survives however the margin is removed. This matters for H1 too: §5.2 shows that the *level* of the market's calibration slope depends on the de-vigging method, but the *gap* does not, so no H2 conclusion inherits that ambiguity.

**Third, it is information, not calibration.** Passing the market through its own two-parameter recalibration fitted only on each fold's training data (B6r) changes the gap by a relative 0.0019 (90% CI −0.0085–0.0127, upper bound 0.013 < 0.25). The fair objection at this point is that a two-parameter tool may simply be too weak to repair anything, so we also computed an **oracle bound**: recalibrate the market *within each of the 48 league–season blocks using that block's own test outcomes* (96 free parameters, hindsight included) and re-evaluate on the same matches. Even then the market's log loss improves only from 0.958536 to 0.955763 (+0.00277 nats) and the gap *widens* from 0.0317 to 0.0345 — a relative change of **+8.7%, still far below 25%**. Calibration, even when allowed to cheat, explains less than a tenth of the shortfall.

### 5.4.1 Why the ladder is not monotone (and why that does not rescue the model)

The model column of `table_main.csv` is not ordered by complexity: B2 = 0.9855, B4 = 0.9903, B1 = 0.9926, B5b = 0.9942, B5a = 0.9957, B3 = 0.9986. **B2 beats B4 by 0.0048 nats (90% paired CI 0.0013–0.0084, excluding zero)** — a difference the pre-registered design does not anticipate, because B4 was fixed in advance as the H2 protagonist.

Three consequences: a caveat, a correction to that caveat, and a finding.

*The caveat:* the headline gap of 0.032 is attached to B4, not to the best arm. Using B2 instead gives **0.027 (90% CI 0.0241–0.0298; 95% CI 0.0236–0.0303)**, i.e. B4's shortfall overstates "what a transparent model can do" by about 18%. The H2 verdict is unchanged — 0.027 is still entirely above the +0.02 equivalence margin, and its 95% interval still excludes zero — but the honest sentence is "the best transparent model trails the market by at least 0.027 nats", not "by 0.032".

*A correction we owe on top of that caveat:* B2's advantage over B4 is largely a **protocol artefact**. B2 updates its Elo state and rolling windows inside the target season; B4 freezes its parameters before kick-off. §5.1.6 measures the difference at **+0.0116 nats** for B2 — 2.4 times its 0.0048 lead. With the refresh removed, B2 scores 0.99706 against B4's 0.99027, i.e. **B4 is ahead by 0.0068 rather than behind by 0.0048**, and the robustness check becomes 0.0385 instead of 0.0270. Both gaps remain far above the +0.02 margin, so the H2 verdict and its robustness check survive the correction intact; what changes is the identity of the best transparent arm. Under one protocol **B4 is it**; B2 wins the delivered comparison partly because it is allowed to update inside the season.

*The finding:* more complexity buys nothing here, and the controlled comparisons say why. On 16,733 matches an Elo difference plus an ordinal logit on five features already captures most of what is predictable from pre-match information; Dixon–Coles adds time decay on top and lands between the two; and the two boosted arms add thirty-odd columns and extra capacity to the same information source and land at 0.9942–0.9957. Both controlled comparisons come out **practically equivalent** under the ±0.02 rule:

- **C2** (B5a → B5b, information widens, model class and weights fixed): **−0.0015, 90% CI −0.0032 to +0.0001**, spanning zero. Thirty extra columns are worth 0.0015 nats — inside the margin and inside the noise.
- **C1** (B4 → B5a, model class changes, information source and weights fixed): **+0.0055, 90% CI +0.0009 to +0.0099**. The interval *excludes* zero — B4 is detectably the better of the two — but it lies entirely inside ±0.02, so under the pre-registered rule the two are **practically equivalent**. Reading this correctly matters: the boosted model is not "as good as" Dixon–Coles in the sense of being indistinguishable; it is measurably worse by a quantity too small to matter for any forecasting decision in this study.

Together the two comparisons say the same thing from both ends: on this information source, at this sample size, neither the model class (generative versus discriminative) nor the width of the feature set moves the answer by more than a fifth of the equivalence margin. The extra capacity buys variance rather than signal — the same mechanism §5.1 attributes to per-fold hyper-parameter selection, and the same reason the boosted arms' draw calibration is so poor (§5.2).

*Rebuild note (v1.5).* `preds_B2.csv` was regenerated in the locked environment on 2026-11-24 after `b2_ordinal.py` was found to pass the removed `multi_class` argument to `LogisticRegression` (sklearn 1.9.1). The rebuild is byte-identical across repeated runs and moves pooled log loss from 0.985554 to 0.985497 (−5.7 × 10⁻⁵ nats); individual match probabilities move by up to 6 × 10⁻², so the *file* is not reproduced, but every downstream number in this section is recomputed from the rebuilt file. No verdict changes.

### 5.4.2 A league-level pattern that does not transfer

B6r's fitted temperature is systematically league-specific and stable across all eight seasons per league: D1 0.959–0.969, N1 0.932–0.996, E0 1.030–1.060, SP1 1.023–1.057, F1 1.051–1.093, I1 1.104–1.143 (the bias term `d` stays within ±0.07). That is not noise — it says the market's over/under-dispersion has a persistent national character (Italian prices are too flat, German prices too sharp).

But when those parameters are applied to the *next* season's matches — which is exactly what B6r does — the total effect is 6.1 × 10⁻⁵ nats (90% CI −4.0 × 10⁻⁴ to +2.8 × 10⁻⁴, covering zero). The pattern is real, league-level and slow-moving, and yet worth nothing for forecasting the next match. This is a clean illustration of why H4 comes out as it does: the market's residual calibration defect is a *style*, not a tradable error, so repairing it cannot close an information gap.

*Sources: `results/table_main.csv` (B4−B6 = 0.0317; B2−B4 = −0.0048; B2−B6 = 0.0270), `results/market_gap.csv` (three methods; B6r row), `results/logs/b6r_n_fit.csv` (per-fold `c`, `d`, `n_fit`), `analysis/h4_information.ipynb` (H4 relative change 0.0019, 90% upper 0.013), `results/logs/h4_oracle_bound.csv` (oracle +8.7%).*
