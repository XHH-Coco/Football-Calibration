# §5.1 Ablation and controlled comparisons: C1 (model class) and C2 (information set)

**One-sentence conclusion.** Neither lever moves the answer. Swapping the model class from time-decayed Dixon–Coles to boosted trees (C1) costs **0.0055 nats** (90% CI 0.0009–0.0099) and widening the information set from 9 to 39 features (C2) gains **0.0015** (90% CI −0.0032 to +0.0001); under the pre-registered ±0.02 rule **both are practically equivalent**, but for different reasons that matter — C1's interval *excludes* zero, so Dixon–Coles is genuinely the better model, while C2's interval *spans* zero, so the extra columns carry no resolvable signal at all. Every number here is conditional on one hyper-parameter rule, and the sensitivity is reported in §5.1.4: under the delivered per-fold grid, C1 would have been **0.0158** — three times larger and, for the first time, across the equivalence margin.

### 5.1.1 What this section answers

The proposal registers two controlled comparisons, and they are the only causal claims in the report:

- **C1** — *does the model class matter?* B4 → B5a. Same information source, same sample weights, same decay constant; only the estimator changes (generative Poisson/Dixon–Coles versus a discriminative tree ensemble).
- **C2** — *does the information set matter?* B5a → B5b. Same model, same weights, **same hyper-parameters**; only the columns change (9 whitelist features versus all 39).

Everything else in the ladder is descriptive. This section reports both comparisons with paired cluster-bootstrap intervals, then does the two things a controlled comparison has to do to be credible: it shows the answer does not depend on the arbitrary choices made along the way (§5.1.4), and it states which asymmetry between the arms it cannot remove (§5.1.6).

### 5.1.2 Design and estimator

**The locks.** §4.3.4 describes them; in one line: B4 and B5a share `w = exp(−0.0019·Δdays)` (normalised, agreeing to 3.6 × 10⁻¹⁵ after removing the constant factor), and B5a and B5b share one weight vector *and* one hyper-parameter pair, both asserted at fit time and re-read from the fitted estimators in `check_m4.py` item 6.

**The estimator.** Paired per-match log-loss differences, aggregated to the 48 (league, season) blocks, then a cluster bootstrap over blocks: 10,000 resamples, 10% quantile interval, seed 20261110. This is the same estimator M2 uses for every other interval in the report (`src/eval/bootstrap.py`), so C1 and C2 are on the same scale as the H2 gap.

The block-level design effect on these comparisons is 1.42 (B5a) and 1.42 (B5b), so the cluster interval is about √1.42 ≈ 1.19 times wider than a naive per-match interval would be. Ignoring the clustering would therefore *understate* the uncertainty by about 16% — not enough to flip either verdict, but enough to matter if the point estimate had landed near the margin.

### 5.1.3 C1 — the model class

**Result.** Δ_C1 = LL(B5a) − LL(B4) = 0.99573 − 0.99027 = **+0.0055 nats**, 90% CI **+0.0009 to +0.0099**, n = 16,733 paired matches. Positive means the boosted arm is worse.

**Verdict.** The interval excludes zero: the difference is *resolvable*, and its sign is not in doubt. But the whole interval lies inside ±0.02, so under the pre-registered four-branch rule the two arms are **practically equivalent** — "差异可分但实际等价", not "no difference". Saying this precisely matters, because the two claims license different sentences in a conclusion. What the data support is:

> a generative goal-based model with exponential time decay is a slightly better predictor than a gradient-boosted ensemble on the same information source, by about a quarter of the margin the study treats as practically meaningful.

What they do not support is either "the boosted model is as good as Dixon–Coles" (it is measurably worse) or "the boosted model is meaningfully worse" (0.0055 is 27% of the margin, and the study's own threshold says such differences are not worth acting on).

**What C1 cannot mean.** §4.3.5 sets this out: B4 compresses the training window into two parameters per team (weighted mean sample age 485 days, effective sample size 16% of the rows), while B5a keeps a 5–10 match window per feature. C1 therefore compares *model class and compression together*. A pro-generative reading ("structural models win") and a pro-parsimony reading ("fewer effective parameters wins") are both consistent with +0.0055; this design cannot separate them, and the report does not claim to. The same applies to the estimation *protocol*: B5a is allowed to update its features inside the season and B4 is not, which biases C1 in B5a's favour by about 0.010 (§5.1.6).

### 5.1.4 C2 — the information set, and the sensitivity of both

**Result.** Δ_C2 = LL(B5b) − LL(B5a) = 0.99421 − 0.99573 = **−0.0015 nats**, 90% CI **−0.0032 to +0.0001**, n = 16,733. Negative means the wider information set is (very slightly) better. The interval spans zero, so the branch is **实际等价** on the strict reading: thirty extra columns — shots, shots on target, rest days, matchday, opponent strength — move pooled log loss by a quantity indistinguishable from nothing.

This is the expected shape of the result and it is consistent with the feature-importance picture. Permutation importance on a held-out inner season (`products/figures/fig08_importance.png`, one block, five repeats) puts `elo_diff` at **0.063** — three and a half times the runner-up `h_elo` at 0.018 — and then a long tail of shot and rolling-goal columns between 0.0003 and 0.008:

| rank | feature | Δ log loss when permuted |
|---|---|---|
| 1 | `elo_diff` | 0.0631 |
| 2 | `h_elo` | 0.0181 |
| 3 | `a_shf5` (away shots, 5-match) | 0.0077 |
| 4 | `a_gf10` (away goals for, 10-match) | 0.0073 |
| 5 | `a_sha5` (away shots against, 5-match) | 0.0069 |

Two things follow. First, **the rating engine is doing most of the work** — the top two features are both Elo, and §4.3.3 showed that Elo *alone* (B1) reaches 0.9926, better than the Poisson model. Second, the tail is where B5b's thirty extra columns live: individually worth 0.0003–0.008, and collectively worth 0.0015 once their correlations are accounted for. There is no hidden signal in the shot columns that the models were failing to find; there is simply very little signal there.

**Hyper-parameter sensitivity.** Because both C1 and C2 depend on the configuration B5a/B5b run at, the whole comparison was repeated across six configurations: the two per-fold argmin rules (delivered 9-cell, extended 20-cell) and four fixed cells. All six use the same weights, the same features and the same estimator; only the reported arm's capacity changes.

| configuration | B5a | B5b | C1 (90% CI) | C1 branch | C2 (90% CI) | C2 branch |
|---|---|---|---|---|---|---|
| delivered: 9-cell argmin | 1.0061 | 1.0033 | +0.0158 (0.0109, 0.0209) | **跨边界** | −0.0028 (−0.0062, +0.0005) | 实际等价 |
| extended: 20-cell argmin | 0.9994 | 0.9968 | +0.0091 (0.0045, 0.0139) | 差异可分但实际等价 | −0.0026 (−0.0052, −0.0002) | 差异可分但实际等价 |
| **fixed (3, 0.01) — reported** | **0.9957** | **0.9942** | **+0.0055 (0.0009, 0.0099)** | 差异可分但实际等价 | **−0.0015 (−0.0032, +0.0001)** | 实际等价 |
| fixed (3, 0.03) | 0.9960 | 0.9944 | +0.0057 (0.0014, 0.0100) | 差异可分但实际等价 | −0.0017 (−0.0036, +0.0003) | 实际等价 |
| fixed (5, 0.03) | 1.0018 | 0.9986 | +0.0115 (0.0067, 0.0162) | 差异可分但实际等价 | −0.0032 (−0.0062, −0.0002) | 差异可分但实际等价 |
| fixed (7, 0.03) | 1.0043 | 1.0018 | +0.0141 (0.0094, 0.0187) | 差异可分但实际等价 | −0.0025 (−0.0057, +0.0005) | 实际等价 |

Read across the rows, three things are stable and one is not.

- **C1's sign never changes**: B4 is better than B5a in all six configurations, by 0.0055 to 0.0158. The claim "the transparent model is at least as good" survives every configuration tested.
- **C1's verdict does depend on the rule.** Under the delivered grid the interval reaches 0.0209 and the branch is 跨边界 — no practical claim allowed. Under every other configuration the interval sits inside the margin and the correct branch is "resolvable but practically equivalent". The difference is not the model; it is that the delivered grid forced the boosted arms into a capacity the data cannot support.
- **C2's verdict is 实际等价 in all six** (twice as "resolvable but equivalent", four times as "spans zero"). The extra features never buy a meaningful gain, whatever capacity they are given.
- **Capacity is monotone**: reading the four fixed rows from the corner upward, every step that adds leaves or learning rate makes both arms worse. This is the same pattern §4.3.6 documents on inner validation, now on held out data.

### 5.1.5 Why neither lever pays

Three observations explain the shape of the results, and none of them involves a modelling failure.

**The ladder is information-limited, not capacity-limited.** B1 uses one number and gets 0.9926; B2 uses five and gets 0.9855; adding thirty-four more columns and a few hundred trees (B5b) gets 0.9942. If capacity were the binding constraint, B5b would win. It does not, which is the signature of a problem where the marginal information in the extra columns is small compared with the estimation noise they bring.

**The boosted arms over-fit the season, not the training window.** With `max_leaf_nodes = 3` and `lr = 0.01` the fitted ensemble is close to an additive model of shallow interactions — roughly 50–120 boosting rounds before early stopping. At that size, what remains is not "too much flexibility" but "the wrong loss": a tree ensemble optimises a non-parametric log loss that has no notion of the draw being a low-information class. §5.2 shows the consequence: draw calibration slopes of 0.53–0.57 for the boosted arms against 0.944 for B4.

**Randomisation within the season hurts more than it helps.** Elo and rolling windows are recomputed through the test season, so the boosted arms get a within-season refresh the Poisson arms do not (§5.1.6). It is not enough to close the 0.0055 gap, which is itself informative: the free information the rolling arms receive is worth less than 0.02 nats.

### 5.1.6 The asymmetry we own: intra-season refresh

The controlled comparisons hold the weights and the features fixed, but they do **not** hold the *estimation protocol* fixed, and the report states this rather than hiding it.

- B3 and B4 are **batch** models: every parameter is frozen before the season starts. Match 300 of a season is predicted by the same α, β, ξ as match 1.
- B1, B2, B5a and B5b are **rolling** models: `transform_features(test, builder)` keeps advancing the Elo state and the rolling windows through the test season, so match 300 is predicted using the results of matches 1–299.

Neither is leakage — every prediction uses only strictly earlier matches — but the rolling arms receive a refresh budget the batch arms do not. `src/models/sens_refresh_parity.py` measures it by freezing the *outcome-derived* features (rolling goals, shots, Elo, opponent strength) at their season-start snapshot while keeping the *calendar* features (rest days, matchday, stage) live, since those are known before kick-off:

| arm | rolling (reported) | frozen at season start | frozen − rolling (90% CI) | folds where frozen wins |
|---|---|---|---|---|
| B2 | 0.98550 | 0.99706 | **+0.01156** (+0.00783, +0.01554) | 10/48 |
| B5a | 0.99573 | 1.00591 | **+0.01018** (+0.00616, +0.01440) | 11/48 |
| B5b | 0.99421 | 1.00867 | **+0.01446** (+0.01113, +0.01796) | 6/48 |

The budget is real, it is large relative to the effects being compared, and it accrues entirely to the rolling arms. Two consequences follow, and both are stated as corrections rather than footnotes.

**C1 is a lower bound on B4's advantage.** On a like-for-like protocol — both arms denied the refresh — the boosted arm would score 1.00591 instead of 0.99573, and C1 becomes **+0.0156** (point estimate; the interval shifts with it). Still inside ±0.02, so the *verdict* does not change, but the effect is now 78% of the margin rather than 27%. The honest sentence is therefore: *under the delivered protocol, Dixon–Coles is better by 0.0055 nats; with the refresh advantage removed, by about 0.016; neither crosses the equivalence threshold, but the second is close enough that the margin is doing real work.*

**B2's lead over B4 is an artefact of the same asymmetry.** The ladder in §5.4 shows B2 beating B4 by 0.0048. B2's refresh budget is 0.0116 — 2.4 times that lead. Equalising the protocol reverses the ordering: B2 frozen at 0.99706 against B4's 0.99027 means **B4 is ahead by 0.0068**, not behind by 0.0048. This does not change any H2 verdict (§5.4 keeps the robustness check and reports the frozen gap of 0.0385, still above the margin), but it does change the sentence "the best transparent arm is B2". Under a single protocol, **B4 is the best transparent arm**; B2 wins the delivered comparison partly by being allowed to update inside the season.

We keep the rolling protocol rather than switching to a batch one, for a reason that is about the research question rather than convenience: H2 asks how far a *forecastable* model trails a market that itself updates continuously, and a bookmaker does not freeze its ratings in August. Reporting both protocols would be better than reporting either; that is what this subsection is for, and it is why the adjustment is quantified rather than assumed away.

One caveat on the measurement itself: the frozen arm is **not** a re-fit-per-round batch model. It holds the model fitted on the training window fixed and freezes the feature snapshot; a true batch analogue of B4 would re-estimate its parameters at each intra-season cut-off. The two differ, and the frozen number should be read as *"the rolling arm with its refresh removed"* rather than *"the batch version of the rolling arm"*. The direction of the correction is not in doubt — B4's information is genuinely older than B5a's at every point in the season — but the magnitude ±0.003.

### 5.1.7 What this section cannot say

1. **It cannot say "machine learning does not help".** It can say that this feature set, at this capacity, under this weighting, on this sample, does not beat a five-parameter ordinal logit or a time-decayed Dixon–Coles by more than the margin.
2. **It cannot separate model class from compression** (§5.1.3), nor class from refresh budget (§5.1.6). Both would need a dedicated arm: B4 re-estimated at intra-season cut-offs, and B5a restricted to B4's two-parameters-per-team summary.
3. **It cannot certify the equivalence.** A ±0.02 margin declared in advance and two intervals inside it is evidence of practical equivalence given the margin; it is not a formal TOST with a power calculation, and no power statement is made.
4. **It is one sample of 48 blocks.** The bootstrap interval accounts for within-block dependence but conditions on the realised 48 league-seasons; it says nothing about a 49th league.
5. **Fixed hyper-parameters are a bias-variance trade, not a free lunch.** They remove a selection step that was actively harmful here; in a larger sample the per-fold rule might well win. The claim is about this sample, and §4.3.6 gives the size of what was traded away (0.0037 nats).
