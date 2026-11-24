# §2 Hypotheses

**One-sentence summary.** Four hypotheses, each with the observation that would falsify it written down before any model was fitted, all of them phrased as paired per-match differences with intervals resampled over the 48 league–season blocks, and all of them judged against one margin — ±0.02 nats per match — that is used everywhere in this report.

The hypotheses were registered in the 30 October proposal and are reproduced here in the form the *code* implements, not in the form the proposal printed. Six statements about the hypotheses and the design were corrected between submission and fitting — two of them because the submitted text was internally inconsistent, two because the submitted decision rule could not have been applied at 48 clusters. §1 records each of the six, plus a seventh change that is not a hypothesis statement at all (the panel's training history reaches back to 2003/04; the evaluation set is unchanged). This section states the rules that actually decide the verdicts, so that §5 can be read against them rather than against the proposal.

Four conventions apply to all four hypotheses and are stated once here.

1. **Everything is a paired difference.** Every claim compares two forecasts on the *same* matches, joined on `match_id`, so the interval is on the difference rather than on two marginal scores. The consequence is that the market and the model are never compared through their separate averages.
2. **Intervals are block-level.** Resampling units are the 48 (league, season) blocks, 10,000 replicates, percentile method, seed 20261110; each interval is reported next to its design effect (§4.4.2).
3. **A wide interval concludes nothing.** If an interval is wider than the margin, the estimate is reported descriptively and supports neither superiority nor equivalence. This is a rule about what we are allowed to *say*, not a statement about the world.
4. **Robustness families are not extra hypothesis tests.** The three de-vigging methods are declared one family in advance, as are the per-league and per-season breakdowns; no multiplicity correction is claimed because no member of either family is allowed to generate a headline on its own.

### H1 — The market is under-dispersed, not unbiased

**Statement.** De-vigged closing probabilities have a calibration intercept near zero but a **slope greater than one**. A slope above one means the price compresses probability towards the middle of the simplex, so the reliability curve lies **below** the diagonal at low predicted probabilities and **above** it at high ones: longshots are given too much probability and favourites too little. This is the favourite–longshot bias (Ali 1977; Cain, Law & Peel 2000) and we make no claim to novelty.

**Why it is worth asking anyway.** Štrumbelj (2014) shows that some margin-removal methods eliminate the bias while proportional normalisation does not. The open question is therefore not "is there a favourite–longshot bias" but "does it survive de-vigging, and does the answer depend on how the margin is removed". We report the slope and the tail-bin bias under proportional, Shin (1993) and power de-vigging.

**Falsification.** (a) *Primary:* falsified if the proportional-de-vigged calibration slope is at most one. (b) *Secondary, for the pre-registered ordering only:* the claim "largest under proportional" is made only if the 90% block-bootstrap interval for `|slope−1|_proportional − |slope−1|_Shin` has a lower bound above zero; otherwise the three slopes are reported descriptively and no ordering is claimed.

**What is explicitly not claimed.** That the market is biased in a way a bettor could exploit. A slope above one is a statement about the *shape* of the forecast, not about its profitability after commission, stake limits and line movement.

### H2 — A transparent model does not close the gap, and the residual is not negligible

**Statement.** Two one-sided claims, both pre-specified, with **B4** (time-decayed Dixon–Coles) as the transparent model and **B6** (de-vigged Pinnacle closing) as the benchmark.

- **(a) B4 does not beat B6.** Falsified if the **95%** block-bootstrap interval on the paired per-match log-loss difference excludes zero *in B4's favour*.
- **(b) The residual gap is practically non-zero.** Falsified if the **90%** interval lies *entirely inside* ±0.02 nats per match.

The two claims use two interval levels because they are two different questions — one about the sign of a difference, one about its practical size — and both levels were fixed before the data were seen. The margin is not a round number chosen for convenience: at 48 clusters the smallest difference the design can resolve is itself of order 0.02 nats (§4.4.2), so a smaller margin would be unresolvable by construction rather than demanding.

**Which arm carries the claim.** B4, because it was named in the proposal as the transparent model. The report additionally shows what happens if the claim is attached to the *best* transparent arm instead (B2) — that substitution is a reporting robustness check, not a re-registration, and it is reported with its own numbers rather than folded silently into the verdict (§5.4.1).

### H3 — The gap is localised, not diffuse

**Statement.** The per-match gap (market minus model; positive means the model is worse) is larger for matches involving a newly promoted side, and for the first six matchdays of a season. Both indicators enter one regression estimated jointly, together with league–season fixed effects.

**Mechanism.** Each indicator signals *stale strength information*. The market observes transfers, pre-season news and spending; a model fitted to earlier scorelines does not. If the mechanism is right, the shortfall should be concentrated exactly where the model's information is oldest.

**No leakage by construction.** The two indicators are built only from pre-season team lists and the fixture calendar — `is_promoted_*` from the set of teams in the division that season, `matchday` from the cumulative count of each team's fixtures in date order. Neither reads a result. `tests/test_h3_features.py` asserts this by shuffling post-match information and checking the three columns are element-wise unchanged.

**Falsification and reporting rule.** H3 is supported only if **both** coefficients are positive **and** each 90% block-bootstrap interval has a lower bound above zero. If either interval crosses zero, both estimates are reported descriptively and the hypothesis is neither confirmed nor refuted as a whole. We also report a matchday-window sweep (1–3, 1–6, 1–10) as a **declared descriptive robustness curve**, so that "six" is a reported curve rather than an arbitrary threshold; the sweep carries no significance claim and enters no primary inference.

**What the design cannot establish.** That the mechanism is the one proposed. The coefficients measure *where* the gap is, not *why*; a second mechanism correlated with promotion and early-season fixtures would produce the same pattern.

### H4 — The gap is information, not miscalibration

**Statement.** Replacing the benchmark B6 with a recalibrated market **B6r** — a two-parameter temperature-and-bias logit map, `logit(p*) = c · logit(p) + d` — changes the estimated model–market gap by less than 25%. Both parameters are fitted strictly inside each fold's training window and applied to that fold's test season, so no outer-block outcome is used to fit them.

**Why this is the question that decides how to read the rest.** If the market's residual defect were a repairable miscalibration, then part of the model's shortfall would be an artefact of comparing a calibrated model to an uncalibrated benchmark. If repairing the benchmark leaves the gap intact, the gap is information and the whole report should be read as a statement about information rather than about arithmetic.

**Falsification.** Supported only if the **upper bound** of the 90% block-bootstrap interval on the relative change is below 25%; falsified if that interval's lower bound exceeds 25%. If the denominator gap is smaller than 0.01 nats the ratio is unstable, so the absolute change is reported instead and no relative claim is made.

**A reference case, not a second test.** Because a two-parameter map could simply be too weak to repair anything, §4.6 also computes an **oracle bound**: the market recalibrated *within each block using that block's own test outcomes*. It is deliberately cheating, it is not part of the decision rule, and it exists only to answer the objection "your recalibrator was too small".

### What is deliberately not a hypothesis

Three analyses in this report are reported without being dressed up as findings, because doing so would inflate the count of things we tested.

- **The two single-factor comparisons are results, not hypotheses.** B4→B5a (model class) and B5a→B5b (information set) are reported as **C1** and **C2** under the same ±0.02 margin and the same four-branch decision rule, which is frozen in code (`src/eval/decisions.py`) and exercised by `tests/test_decisions.py` on constructed intervals. The proposal never registered them, and we do not retro-fit a registration to them.
- **Model-side calibration is descriptive.** Reliability curves by outcome class, ECE and bias-versus-probability for *our* models are error analysis supporting H1, not a second claim. §5.2 treats them that way, and says so.
- **Appendix A1 is a robustness analysis.** The decline of the home-advantage parameter γ and the closed-door 2020/21 season are reported in Appendix A. That period coincides with two curtailed seasons, congested fixtures and rule changes, and there is exactly one such season, so no causal "natural experiment" claim is defensible from it.
