# §5.3 H2 — how far the model trails

**One-sentence conclusion.** Every one of the seven model arms trails the de-vigged market by more than the equivalence margin, with a 90% lower bound above +0.02 in all seven cases; the pre-registered arm B4 trails by **0.0317** nats per match (90% CI 0.0278–0.0359; 95% CI 0.0271–0.0366) and the best transparent arm B2 by **0.0270** (0.0241–0.0298).

### 5.3.1 The gap for every arm under every de-vigging method

**Table 5.3-a. Paired log-loss gap against the market** (Δ = arm − market; positive = the arm is worse; 16,728 matches; 90% intervals from the 48-block cluster bootstrap).

| Arm | Δ log loss, proportional | 90% CI | Δ under Shin | Δ under power | Δ Brier, proportional | Lower bound clears +0.02? |
|---|---:|---|---:|---:|---:|---|
| B0 | 0.1158 | 0.1090 – 0.1226 | 0.1159 | 0.1159 | 0.0813 | yes |
| B1 | 0.0341 | 0.0311 – 0.0370 | 0.0342 | 0.0342 | 0.0232 | yes |
| **B2** | **0.0270** | **0.0241 – 0.0298** | 0.0271 | 0.0271 | 0.0183 | yes |
| B3 | 0.0401 | 0.0360 – 0.0446 | 0.0403 | 0.0403 | 0.0273 | yes |
| **B4** | **0.0317** | **0.0278 – 0.0359** | 0.0319 | 0.0319 | 0.0214 | yes |
| B5a | 0.0372 | 0.0343 – 0.0402 | 0.0374 | 0.0374 | 0.0241 | yes |
| B5b | 0.0357 | 0.0326 – 0.0388 | 0.0359 | 0.0359 | 0.0232 | yes |
| *B6r* | *−0.0001* | *−0.0004 – 0.0003* | *0.0001* | *0.0001* | *−0.0000* | *no* |

Two features of the table carry most of what H2 can claim.

**The margin is cleared by the weakest arm, not just by the best.** The tightest lower bound in the table belongs to B2 at 0.0241 — still 20% above the +0.02 margin. This is a stronger statement than "B4's interval excludes zero": it means the verdict does not depend on which arm is chosen, so the arm-substitution issue of §5.4.1 affects the *headline number* but not the *decision*.

**The ordering is not the claim.** The gaps range from 0.0270 to 0.1158 — a factor of 4.3 — and the ordering does not track model complexity: B2 (five features) sits closest to the market, B3 (a full Poisson model) sits furthest among the structured arms, and the two boosted arms sit between. §5.4.1 explains why; §5.3 records it so the explanation is not mistaken for a new result.

**B6r is in the table as a control, not as an arm.** Its gap is −0.00006 nats, i.e. recalibration moves the benchmark by 6 × 10⁻⁵ nats (90% CI −0.0004 to +0.0003). If that number were large the rest of the column would be unreadable.

### 5.3.2 The verdict, read against the pre-registered rules

| Claim | Rule (§2) | Estimate | Interval | Verdict |
|---|---|---|---|---|
| H2 (a) B4 does not beat B6 | 95% interval excludes zero in B4's favour | +0.0317 | 95%: 0.0271 – 0.0366 | **supported** — the interval is entirely on the "model is worse" side |
| H2 (b) the residual is practically non-zero | 90% interval *not* entirely inside ±0.02 | +0.0317 | 90%: 0.0278 – 0.0359 | **supported** — the whole interval lies above +0.02 |
| H2 robustness, best arm | same rule, B2 in place of B4 | +0.0270 | 90%: 0.0241 – 0.0298; 95%: 0.0236 – 0.0303 | **supported** — the verdict survives the substitution |

The 95% interval in the first row is not redundant with the 90% one: claim (a) is a two-sided statement about sign and is judged at 95%, claim (b) a one-sided statement about magnitude judged at 90%. Both are reported because both were registered, and neither is presented as the "real" one.

### 5.3.3 Why the three de-vigging methods cannot disagree

The three columns differ by **1.5 × 10⁻⁴ nats for every arm**, and this is arithmetic rather than an empirical coincidence. Write the gap under method *k* as

> Δ<sub>k</sub> = mean(ℓ<sub>arm</sub>) − mean(ℓ<sub>market,k</sub>) = Δ<sub>prop</sub> + [mean(ℓ<sub>market,prop</sub>) − mean(ℓ<sub>market,k</sub>)],

so the difference between two methods is a property of the *benchmark* and enters every arm identically. What the table therefore shows is not "the gap is robust to de-vigging" in the sense of a lucky coincidence, but something more useful: **the three de-vigging methods produce market forecasts whose own log loss differs by only 0.00015 nats**, even though their calibration *slopes* differ by up to 0.056 (1.086 proportional versus 1.030 power, §5.2). The market's loss is nearly invariant to how the margin is removed; its calibration shape is not. This is why H2 does not inherit H1's de-vigging ambiguity, and why H1's magnitude caveat does not propagate into the gap.

### 5.3.4 The block-level distribution

The pooled number is an average over 48 league-seasons, and the dispersion around it is large enough to be worth reporting rather than leaving in the file.

| Statistic | Value |
|---|---|
| Blocks with a positive mean gap | **47 of 48** |
| Blocks whose mean gap exceeds +0.02 | **35 of 48** |
| Median block mean | 0.0304 |
| 5th – 95th percentile of block means | 0.0101 – 0.0644 |
| Standard deviation across blocks | 0.0169 |
| Lowest block | `D1|2022/23`, −0.0072 |
| Highest block | `D1|2023/24`, +0.0691 |

Two observations, both descriptive. First, the single block where the model *beats* the market is a Bundesliga season, and the block where it loses most is the following Bundesliga season — the extremes are adjacent league-seasons of the same league, which is what a genuine year-to-year swing in squad strength looks like rather than a stable league property. Second, 13 of 48 blocks fall below the margin, so "the model trails by more than 0.02" is a statement about the pooled estimate backed by 35 blocks, not a statement that holds in every league-season. That distinction matters if anyone wants to use the result to decide *where* to trust a model; it does not affect the H2 verdict, which is a pooled claim.

### 5.3.5 How many margins

Expressed in the project's own unit, the pre-registered gap is **1.59 margins** (0.0317 / 0.02) and the best-arm gap is **1.35 margins**. Neither is so far above the margin that the margin is irrelevant, and neither is close enough that a different but defensible choice of interval level would flip the verdict — at 95% the lower bounds are 0.0271 and 0.0236, still above 0.02 in both cases.

### 5.3.6 The worst case after the refresh correction

The delivered comparison gives the rolling arms an advantage the batch arms do not have, because their result-dependent state updates inside the test season (§4.4.5). The correction is quantified in §5.1.6: freezing that state costs B2 **+0.0116** nats. Applying it, B2's gap becomes **0.0385** rather than 0.0270 — the robustness check moves *further* from the margin, not closer to it. This is the sense in which the reported gaps are a floor: the delivered protocol is the one most favourable to the model, and even there no arm clears the margin.

*Sources: `results/market_gap.csv` (all arms × three de-vig methods, log loss and Brier), `results/table_main.csv` (`delta_vs_B6`, `delta_vs_B6_lo90`, `delta_vs_B6_hi90`), `results/logs/m2_verdicts.csv` (H2 rows and the B2 robustness row), `results/logs/sens_refresh_parity.csv` (via §5.1.6). The block-level statistics are computed from `results/preds/preds_B4.csv` and `preds_B6.csv` joined on `match_id`.*
