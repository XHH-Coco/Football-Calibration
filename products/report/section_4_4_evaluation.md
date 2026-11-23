# §4.4 Evaluation framework and market calibration (H1 market side)

**One-sentence summary.** Every arm is scored by the same ruler: pooled log loss on paired matches, an interval from a 48-block cluster bootstrap with a reported design effect, and a verdict produced by decision rules that were written into code before the numbers existed.

### 4.4.1 Metrics

The primary metric is multinomial **log loss**, pooled over matches (`LL = Σᵢ ℓᵢ / n`, not the average of 48 per-fold averages), with Brier and RPS reported as secondary. Calibration is diagnosed by one-versus-rest logistic recalibration `logit(y_class) ~ a + b · logit(p_class)` and by reliability curves; all of these are implemented in `src/eval/metrics.py` and cross-checked against `sklearn` to 1e-9. A uniform forecast scores ln 3 = 1.0986 and the league-frequency prior B0 scores 1.0743, which is how we verify the sign and base of the metric before trusting anything else.

### 4.4.2 Intervals: 48 blocks, not 16,733 matches

Matches within a league–season share team strength, referee style and fixture congestion, so they are not independent draws. Intervals therefore come from resampling the **48 (league, season) blocks** with replacement (B = 10,000, percentile method, no bias correction, seed 20261110), and every interval is reported next to its **design effect** `deff = Var_cluster / Var_iid`. For paired comparisons the two arms are inner-joined on `match_id` first and then differenced match by match.

The consequence is quantified rather than asserted: on this panel `deff` runs from 1.31 (B0) to 2.28 (B4−B6), so block-level intervals are **15–50% wider** than a naive per-match bootstrap (`ratio ≈ √deff`, measured 1.15–1.49). The evidence — per-arm `deff`, both widths, the ratio and its consistency with `√deff`, with a PASS/FAIL verdict per line — is written to `results/logs/bootstrap_selfcheck.txt` on every run of `python -m src.eval.run_m2`. (An earlier draft of the protocol claimed a 3–5× widening; that would require `deff` of 9–25, i.e. near-perfect homogeneity inside a block, and is corrected in spec v1.4.)

With 48 clusters the smallest difference we can resolve is about 0.02 nats per match, which is why ±0.02 is the project's single equivalence margin and why no smaller difference is ever described as an improvement.

### 4.4.3 Verdicts written before the numbers

H1–H4 and the two controlled comparisons C1/C2 have their thresholds in one place (`src/eval/decisions.py`, `EQUIV_MARGIN = 0.02`) and their four-branch logic in code, exercised by `tests/test_decisions.py` on constructed intervals. Each verdict returns the decision, a one-line reason, the interval it used and `n_paired`; `run_m2` writes them all to `results/logs/m2_verdicts.csv`, so every number in §5 can be joined back to its source row instead of being checked by eye. C1/C2 are reported as results, not hypotheses, and the fourth branch distinguishes "the interval excludes zero but crosses the practical margin" (report the estimate, make no practical claim) from "the interval spans zero" (no resolution).

### 4.4.4 The market arm: de-vigging, and what B6r is for

B6 is the closing line `PSCH/PSCD/PSCA` with the margin removed by proportional scaling (primary), plus Shin and power as robustness checks. Five matches in three blocks lack all three closing columns; they are dropped, not imputed, so B6/B6r cover **16,728** of the 16,733 evaluation matches. B6r repasses B6 through its own two-parameter temperature-and-bias logit map, fitted **only on that fold's training matches** with complete closing prices (per-fold `n_fit` is logged, minimum 1,526). B6r exists only to test H4: if repairing the market's calibration leaves the model–market gap intact, the gap is information rather than calibration.

### 4.4.5 What "out of sample" means here — declared, not implied

Features that depend on results are built by a state machine that is advanced match by match in date order. In each of the 48 folds the state machine is fitted on the training window and then **kept advancing through the test season**, so match *i* of a test season is featurised with the results of matches 1…*i*−1 of the same season. No outcome of the match being predicted ever enters its own features, and the protocol is if anything the *stronger* comparison against the market, whose prices also know those earlier results.

But it does mean our "48-fold out-of-sample" evaluation is a **rolling-origin / prequential** evaluation, not "fit once, freeze the parameters, predict an entire season blind". Stated plainly because it is the kind of detail that is hard to defend if a reader discovers it instead of being told. It applies identically to every arm that uses these features (B1, B2, B4, B5a, B5b), so comparisons *between* arms remain fair; only the absolute level would move under a frozen-season protocol.

### 4.4.6 Schema and reproducibility guardrails

Predictions are written through a single schema source of truth (`PRED_COLS`, `check_pred` in `src/eval/harness.py`) with four hard assertions before anything reaches disk: column order, row count, probabilities summing to one, and unique `match_id`. Column order is not cosmetic — several models use internal label orders (B2 orders away < draw < home), and a silent reordering would only make log loss quietly worse; the reordering is asserted in code and in `tests/test_pred_schema.py`. `appendix/run_all.*` rebuilds every artefact from the committed raw data without network access.
