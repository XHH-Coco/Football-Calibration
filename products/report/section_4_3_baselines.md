# §4.3 Baselines and boosted arms: B0, B1, B2, B5a, B5b

**One-sentence conclusion.** Five arms span the range from "count the past" to "boost trees on 39 features", and pooled log loss falls from **1.0743** (B0, league frequencies) to **0.9855** (B2, ordinal logit on five state features) and **0.9942** (B5b, boosted trees on everything) — but the ordering is **not monotone in model class**: both boosted arms land above the ordinal logit, and B5a is 0.0055 nats worse than the time-decayed Dixon–Coles of §4.2. The ladder is only interpretable because of two locks that are enforced in code rather than promised in prose — **the same weight formula** for B4 → B5a and **the same weights *and* hyper-parameters** for B5a → B5b — and because neither lock carries a hyper-parameter that was selected per fold.

### 4.3.1 What this section answers

This section specifies the four arms between the floor and the boosted models — B0, B1, B2, B5a — plus B5b, and states precisely what is allowed to differ at each rung. It is a model-construction section: the attribution questions (C1, C2) are answered in §5.1 with paired intervals; here we only fix what each arm is, what it sees, and what holds the comparison still.

Three things are worth stating up front because they are easy to get wrong and expensive to discover late.

1. **Half of this ladder rests on one 58-line file.** `src/elo.py` is the only Elo implementation in the repository: B1's entire input is it, three of B2's five features are it, and B5a's whitelist contains it. When the boosted arms look good, a large part of the credit belongs to the rating engine, not to the trees.
2. **"Same information set" is an idealisation.** B4 and B5a see the same *source* of information weighted by the same formula, but B4 compresses the training window into two numbers per team while B5a keeps a 5–10 match window per feature. §4.3.5 states what the comparison can and cannot claim.
3. **No arm in this section tunes a hyper-parameter on the evaluation window.** B5a/B5b use one fixed configuration for all 48 folds; §4.3.6 records the evidence that made per-fold selection untenable.

### 4.3.2 The five arms

| arm | model | what it sees | pooled log loss | 90% interval |
|---|---|---|---|---|
| **B0** | empirical class frequencies, expanding window | same league, strictly earlier matches | **1.0743** | [1.0703, 1.0782] |
| **B1** | multinomial logistic on rating difference | one number: Elo(home) − Elo(away) | **0.9926** | [0.9856, 0.9999] |
| **B2** | proportional-odds ordinal logit | five state features (Elo ×3, points ×1, rest ×1) | **0.9855** | [0.9781, 0.9930] |
| **B5a** | histogram gradient boosting | nine whitelist features | **0.9957** | [0.9888, 1.0027] |
| **B5b** | histogram gradient boosting | all 39 features | **0.9942** | [0.9872, 1.0014] |
| *(ref.)* B3 | independent Poisson | goals by team, attack/defence | 0.9986 | [0.9912, 1.0063] |
| *(ref.)* B4 | time-decayed Dixon–Coles | as B3, exponentially weighted | 0.9903 | [0.9819, 0.9988] |

Two readings of this table matter for the rest of the report.

**The floor is a real floor.** B0 is the league's own historical home/draw/away split, recomputed expanding as seasons accumulate. It scores 1.0743 against 1.0986 for the uniform 1/3 forecast, so roughly two thirds of the total distance from ignorance to the market (1.0986 → 0.9585) is covered by knowing nothing but the base rate of the league. In 2 of the 48 blocks B0 is *worse* than 1/3 — the leagues whose home-win rate drifted away from their own history — which is expected behaviour for a frequency model, not a defect, and `check_m4.py` encodes it as a tolerance band rather than an equality.

**The ladder is not monotone, and that is a result.** B2, a five-parameter ordinal logit, beats both boosted arms and the two Poisson models. The boosted arms are not under-powered — they are under-*informed* relative to what B2 can squeeze out of the same Elo engine, and their extra capacity buys variance rather than signal (§5.1.5). This is the same pattern reported in §5.4 as the "best transparent arm" robustness check, and it is why H2 is stated against the *best* transparent arm rather than against B4 alone.

### 4.3.3 One rating engine under half the ladder

`src/elo.py` follows the simplified Hvattum & Arntzen (2010) scheme: every team starts at 1500, K = 20, home advantage 75 rating points, ratings regress one third of the way to the mean between seasons, and each team carries **separate home and away ratings** because home and away form are not the same quantity. Two design choices in that file are load-bearing:

- **Updates are strictly match-by-match in date order.** A weekly batch update would let a Saturday result inform a Saturday forecast in the same round; the sequential update is the reason B1's predictions at match *t* contain nothing from match *t*. The M4 review flagged this as the single most common way this feature set leaks, and `tests/test_leakage.py` walks the feature builder one match at a time to check it.
- **Promoted teams start at the league mean rather than at their previous division's rating.** Their first-season estimates are therefore weak, which is the honest state of knowledge and is visible in the H3 `promoted` coefficient (§5.4).

B1 uses the engine in the simplest possible way: rating difference into a multinomial logit, fitted on the training window only. That single number reproduces 0.9926, i.e. it beats the independent Poisson model B3 (0.9986) and lands within 0.002 of the time-decayed Dixon–Coles B4. **A one-dimensional summary of results is worth about as much as a goal-based generative model on 30 seasons of data.** That comparison is itself one of the report's quieter findings, and it explains why adding 38 more features to a boosted model (B5b) buys only 0.0016 nats over B5a.

### 4.3.4 The two locks

The ladder is a sequence of controlled comparisons only if exactly one thing changes per rung. Two locks implement that:

| rung | what is held fixed | how it is enforced |
|---|---|---|
| **B4 → B5a** (model class) | information source **and** the sample-weight formula | `w = exp(−ξ·Δdays)` with the *same* ξ = 0.0019; both reference dates differ (B4 uses the first day of the target season, B5 uses the last training match) but that is a constant factor — after normalising to mean 1 the largest absolute difference between the two vectors is `3.55e-15`, asserted live in `check_m4.py` item 6 |
| **B5a → B5b** (information) | sample weights **and** all hyper-parameters | one `w` array is built per fold and passed to both arms; `np.array_equal` on the two arrays is asserted at fit time, and item 6 additionally reads the two fitted estimators' `max_leaf_nodes` / `learning_rate` back out and compares them |

The weight lock deserves a note on why it needed to be *asserted* rather than *described*. The previous version of the self-check compared `_weights(train, xi)` with `_weights(train, xi)` — two calls to the same function with the same arguments — which is a tautology that can never fail. The check now compares **two different implementations of the same weighting scheme** (`b3_poisson.decay_weights` with a `test_start` reference versus `b5_gbm._weights` with a training-end reference), which is the assertion that was actually missing from the repository.

One caveat is recorded rather than hidden: the scale of `w` is not exactly irrelevant. B3/B4 normalise to mean 1; B5 passes the raw `exp(−ξ·Δdays)`. Mathematically a constant factor cancels in a weighted likelihood, but `HistGradientBoostingClassifier` stops on an *absolute* improvement threshold, so a rescaling can shift the stopping iteration. Rescaling by 10⁻³ was measured to stop two iterations earlier and move one block's log loss by 0.006. The main run does not rescale, so this is a property of the implementation, not of the reported numbers, but it is the reason the lock is asserted on the normalised vector and the normalisation is documented rather than left implicit.

### 4.3.5 "Same information set" is an idealisation

B4 and B5a are described in the proposal as using the same information set. Literally that is not true, and the difference is worth stating in numbers because it bounds what C1 can mean.

| | B4 | B5a |
|---|---|---|
| what it stores per team | two scalars (attack, defence) | 9 rolling features |
| memory of the training window | exponential, half-life 365 days | 5- and 10-match windows plus Elo |
| weighted mean sample age | **485 days** | not applicable (windows are per match) |
| effective sample size | **16.4%** of the training rows | 5–10 matches per feature |

So B4 discards about 84% of the effective sample and summarises what remains into two parameters per team, while B5a keeps a short window at full resolution. Both see the same *source* — goals scored and conceded, plus recent form — weighted by the same decay, but they compress it very differently.

The honest formulation, and the one used in §5.1, is: **C1 compares two model classes on the same information source under the same weighting scheme, not two estimators of the same sufficient statistic.** A gain for either side is therefore a statement about the *class-and-compression pair*, not about "generative versus discriminative" in the abstract. This is also why a rolling re-estimation of B4 within the season is listed as the one experiment that would tighten C1 further, and why it is not attempted here: it would require re-fitting a Poisson model at intra-season cut-offs, a design change large enough to be its own arm.

### 4.3.6 Hyper-parameters are constants, and the constant is the corner

B5a and B5b use one configuration for all 48 folds: `max_leaf_nodes = 3`, `learning_rate = 0.01`, `max_iter = 1000` with early stopping on a 10% internal split. This replaces the delivered rule, which selected `(leaf, lr)` per fold from a 9-cell grid on a one-season inner validation set. The evidence is in `src/models/sens_b5_grid.py`, which rebuilds 20 configuration cells on all 48 folds and is reproducible in one command.

**Three observations, in the order they were made.**

1. **The delivered argmin sat on the boundary of its own grid.** `max_leaf_nodes = 7` — the smallest value in `{7, 15, 31}` — was selected in **46 of 48 folds**; `learning_rate = 0.03` — also the smallest in `{0.03, 0.05, 0.1}` — in **37 of 48**. An optimum that is always at the edge is not an optimum; it is the edge.
2. **Extending the grid moved the boundary, not the behaviour.** With five leaf values and four learning rates (20 cells), the argmin moves to `leaf = 3` — again the smallest — in **37 of 48 folds**, and to `lr ≤ 0.03` in 33 of 48. Mean inner-validation loss improves by 0.0099, but the *shape* of the answer is unchanged: whatever corner the grid offers is the corner that wins.
3. **Pooled test loss falls monotonically toward that corner.** Across the 20 cells, B5b ranges from **0.9942** at `(3, 0.01)` to **1.0834** at `(31, 0.1)`, and the ordering is almost perfectly monotone in capacity — every step that adds leaves or learning rate makes held-out loss worse. That is the signature of a model that is capacity-limited by its data, not by its feature set.

So the search stops at the corner: `(3, 0.01)`. It is also the modal selection of the extended grid (`leaf = 3` in 37/48 folds, `lr = 0.01` in 22/48), so the mechanical rule and the verbal rule — "take the most conservative cell the grid contains" — point at the same configuration. **The choice within the corner region does not carry the result**: the neighbouring cell `(3, 0.03)` is 0.0003 nats worse on test, i.e. 1.5% of the equivalence margin, and a reader who prefers it would change no conclusion in this report.

**What the change is worth, and what it is worth *for*.** The decomposition matters, because two different things were wrong and they are separable:

| configuration | B5a | B5b | vs delivered |
|---|---|---|---|
| delivered: 9-cell grid, per-fold argmin | 1.0061 | 1.0033 | — |
| extended: 20-cell grid, per-fold argmin | 0.9994 | 0.9968 | **−0.0067** |
| extended: 20-cell grid, fixed at the corner | **0.9957** | **0.9942** | **−0.0104** |

Widening the grid downward is worth 0.0067 nats; replacing per-fold selection with a constant on top of that is worth a further **0.0037** (paired 90% CI 0.0016–0.0060, excluding zero). Both effects are real, and the first is the larger one — which is the honest framing: **the delivered grid was drawn too narrowly, and per-fold selection then added noise on top of a mis-specified range.** Either fix alone would have helped; doing both is what the reported numbers reflect.

Two disclosure notes. First, the four fixed configurations tested all beat the delivered per-fold argmin, but they do *not* all beat the extended-grid argmin: `(5, 0.03)` and `(7, 0.03)` are 0.002–0.005 worse than it. "Fixing" is therefore not magic — fixing *at the capacity the data wants* is what recovers the loss, and per-fold selection was costing 0.0037 precisely because it sometimes chose `(7, 0.03)`. Second, the corner happens to be the best cell on test as well as on validation. That is a happy coincidence, not the reason it was chosen: the rule above uses only inner-validation selections, and §5.1.4 reports the alternative configurations so that no reader has to take the coincidence on trust.

### 4.3.7 What the walk-forward actually enforces

Every arm is fitted on `train` and then predicts `test`, where `train` is every strictly earlier match in the same league and `test` is one full season. Four things are enforced in code rather than by convention:

- **Elo is advanced, never reset, across the boundary.** At prediction time the engine state comes from the training window and is updated match by match through the test season. Match *t* therefore sees the results of *t−1* and nothing later. This is the walk-forward behaviour the prequential protocol of §4.4 assumes.
- **The feature builder is fitted on `train` and applied to `test`**, so windows, team lists and Elo state all start from the training window. The one exception is deliberate: features that are known before kick-off (rest days) are computed in real time on both sides, because "how long since this team last played" is known to anyone reading the fixture list.
- **Missing shot data is flagged, never zero-filled.** Six shot columns are missing for one evaluation match (`2425_D1`, Union Berlin–Bochum) and for most of the early training seasons; a missing indicator is set and the value is back-filled from the team's own history, then from the league's. Filling with zero would tell the model the team took no shots, which is a strong and false signal.
- **Labels are re-ordered exactly once, at write time.** Internal label order is free (`A, D, H` for the ordinal model, ascending classes for HGB); every writer re-orders to `p_home, p_draw, p_away` and asserts the rows sum to one. A swapped column does not raise — it just quietly costs log loss — so it is asserted rather than assumed.

Two known imprecisions are documented in §5.1.5 rather than papered over: same-day fixtures are ordered arbitrarily within the date, and the boosted arms continue to update their Elo and rolling features through the test season while the Poisson arms freeze their parameters for the whole season. Neither is a leak; both affect the size of the differences reported downstream.

### 4.3.8 Limitations

1. **B1 and B2 are not tuned and are not meant to be.** Both are single-purpose baselines: B1 exists to price the rating engine, B2 to give the ladder an interpretable competitor. Their coefficients are reported for direction, not for effect size.
2. **B2's proportional-odds assumption is not tested.** The multinomial alternative is reported as a robustness line (it lands within 0.0013 nats of the ordinal fit), but no formal test of the parallel-lines restriction is claimed.
3. **The boosted arms cannot be read as "machine learning does not help".** They can be read as "these features, at this capacity, under this weighting, do not beat a five-parameter model". A different capacity, a different feature set or a different loss would be a different experiment, and nothing here rules those out.
4. **One fixed configuration is used for all six leagues.** League-specific capacity is plausible (the Bundesliga and Ligue 1 have different goal rates and different competitive balance) and was not explored, because exploring it would reintroduce per-group selection.
5. **The feature table is versioned as code, not as data.** `data/processed/features_v1.parquet` was specified but not shipped; the table is regenerated by `src/features.py` in 3 s per fold. That is acceptable for reproduction but means the exact numeric table is not byte-addressable — only its generator is.
