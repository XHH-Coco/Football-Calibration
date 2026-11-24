# §4.6 Localisation and recalibration (H3, H4): what is estimated, and how

**One-sentence summary.** H3 is one fixed-effects regression of the per-match gap on two pre-season indicators, bootstrapped over blocks; H4 is one ratio — the gap against a self-recalibrated market divided by the gap against the market itself — bootstrapped over the *same* blocks, with an oracle variant that lets the recalibrator cheat in order to bound how much calibration could possibly explain.

§4.4 fixed the ruler and §4.5 fixed the gap. This section fixes the two things done with that gap: it is regressed on where the match sits in the season (H3), and it is recomputed against a repaired benchmark (H4).

### 4.6.1 H3 — a fixed-effects regression on the per-match gap

**The estimating equation.** On the 16,728 matches where B4 and B6 both exist,

> gap<sub>i</sub> = α + β<sub>promoted</sub> · promoted<sub>i</sub> + β<sub>early</sub> · 1{matchday<sub>i</sub> ≤ w} + δ<sub>block(i)</sub> + ε<sub>i</sub>,

estimated by least squares with a league–season fixed effect δ for each of the 48 blocks, at w = 6. The fixed effects are not decoration: without them the promoted coefficient would be identified off cross-league differences in how hard the market is to beat, which has nothing to do with promotion.

**The two indicators.**

- `promoted` = 1 if *either* side is newly promoted into the division that season, taken from the season's team list and the previous season's, never from a result.
- `early` = 1 if `matchday ≤ 6`, where **matchday = min(matchday_home, matchday_away)**, each computed as the team's cumulative fixture count within its league-season in date order.

The `min` is a measurement choice worth naming, because the alternative — the home team's matchday, used in an earlier delivery — is not equivalent: the two definitions flag **1,025 matches differently**. `min` is the pre-registered version because the gap concerns a *match*, and a match is early if either participant is early; using the home side alone makes the indicator depend on which team happened to host. The home-only definition and a `max` variant are reported as a sensitivity table (§5.1 does the same for C1/C2), and the sign and magnitude barely move — which is the point of reporting them.

**Intervals.** The regression is bootstrapped over the 48 blocks (10,000 replicates, 90% percentile). The implementation carries each block's `(XᵗX, Xᵗy)` sufficient statistics and re-solves the normal equations on the resampled counts, so a replicate costs a 50×50 solve rather than a refit on 16,728 rows; a `1e-8` ridge keeps the solve stable in replicates that omit a block. The interval is therefore a *cluster* interval, consistent with every other interval in the report.

**The sweep.** `early` is re-estimated at w ∈ {3, 6, 10} and reported as a curve, so that "six matchdays" is a visible choice rather than a hidden one. The sweep is descriptive by declaration and enters no verdict. Its role is narrow and it is worth being precise about it: it shows whether the estimate depends on where the cut is placed, not whether the mechanism is real. A coefficient that changed sign between w = 3 and w = 10 would mean the finding was an artefact of the threshold; one that keeps its sign and order of magnitude across all three means the threshold is not doing the work.

**Why the verdict is allowed to be "descriptive only".** H3 requires *both* coefficients positive with both lower bounds above zero. That rule is strictly harder than a joint F-test, and it is the rule that was registered. When one coefficient comes out with the wrong sign, the honest output is "the mechanism is not supported in the direction claimed", not a search for a subsample where it is.

### 4.6.2 H4 — a ratio, with the pairing preserved

**The instrument.** B6r is B6 passed through a two-parameter logit map, `logit(p*) = c · logit(p) + d`, with (c, d) fitted by maximum likelihood **on that fold's training matches only** — the matches with complete closing prices inside the pre-season window — and then applied unchanged to the fold's test season. Per-fold `n_fit` is logged (minimum 1,526), and the fit asserts that the training and test match sets are disjoint. Nothing about the test season's outcomes touches (c, d); that is what makes B6r a *forecast* rather than a fitted correction.

**The statistic.**

> rel = (Δ<sub>B6r</sub> − Δ<sub>B6</sub>) / Δ<sub>B6</sub>,

where Δ<sub>B6r</sub> is the B4-versus-B6r gap and Δ<sub>B6</sub> the B4-versus-B6 gap. A positive value means repairing the market *widens* the gap, i.e. the model falls further behind a better-calibrated benchmark; a large negative value would mean the market's miscalibration was propping up part of the gap.

**Intervals.** 10,000 block-bootstrap replicates, and the same resampled block draw is used for the numerator and the denominator. This matters: taking the ratio of two independently-resampled gaps would inflate the interval, because the two gaps share almost all of their variance. The reported interval is the 5th–95th percentile of the replicate ratios.

**The decision rule, and its guard.** Supported only if the **upper** bound of the 90% interval is below 0.25; falsified only if the lower bound exceeds 0.25. If Δ<sub>B6</sub> < 0.01 nats the ratio is numerically unstable, so the absolute change is reported and no relative claim is made. That guard never fires here (Δ<sub>B6</sub> ≈ 0.032), but it is written down because a rule that only works when the denominator is large is not a rule.

### 4.6.3 The oracle bound — a reference case, deliberately not a test

The weakest point in H4 is that it asks a two-parameter map to repair a miscalibration that may need more than two parameters. A null result from a weak instrument is uninformative, so the report also computes an **oracle bound**: within each of the 48 blocks, (c, d) is fitted on **that block's own test outcomes** and the recalibrated market is re-scored on the same matches. That is 96 free parameters fitted on the very matches being scored — hindsight, not forecasting.

It is reported for one purpose only: to answer "how much of the gap *could* calibration explain, even if we cheated". It is not part of the H4 decision rule, it does not enter the verdict, and a reader who treats +8.7% as an estimate of anything other than an upper bound has misread it. If the oracle had closed most of the gap, H4 would have been in trouble and the two-parameter result would have been worthless; it does not.

### 4.6.4 What neither analysis establishes

- **H3 does not identify the mechanism.** The coefficients say *where* the gap is, not *why*. A second, correlated mechanism — fixture congestion, referee composition, the market's own early-season uncertainty — would produce the same coefficients. The report therefore treats promotion and early season as *descriptors of where the information is stale*, not as proof that staleness is the cause.
- **H4 does not generalise beyond the two-parameter family.** It shows that a temperature-and-bias repair does not close the gap, and the oracle shows that even a block-specific repair closes less than a tenth of it. It does not show that no conceivable recalibration could; it shows that the defect is not of a kind that recalibration addresses.
- **Neither analysis is causal about the market.** "The market knows something the model does not" is supported by exclusion — the gap survives calibration repair and does not concentrate where a fixable defect would put it — not by direct measurement of what the market knows.

*Sources: `src/eval/localisation.py` (`build_h3_frame`, `h3_coefficients`, `h3_sweep`), `results/logs/h3_sensitivity.csv`, `src/eval/recalibrate.py` (`run_b6r`, `oracle_bound`), `results/logs/b6r_n_fit.csv` (per-fold `c`, `d`, `n_fit`), `results/logs/h4_oracle_bound.csv`, `src/eval/run_m2.py` steps [7]–[8].*
