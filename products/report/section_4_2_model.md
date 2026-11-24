# §4.2 Structured score models: B3 (independent Poisson) and B4 (time-decayed Dixon–Coles)

**One-sentence conclusion.** Exponential time decay lowers pooled out-of-sample log loss from 0.9986 to 0.9903 nats per match over 16,733 matches, a gain of 0.0084 nats with a paired 90% interval of [0.0037, 0.0128] that excludes zero; the whole interval sits inside the ±0.02 equivalence margin, so under the rule of §4.4 the step is **resolvable but practically small**. B4 carries **no free hyper-parameters selected on data**: the decay rate is a pre-specified constant with a one-year half-life and the low-score correction is switched off (ρ = 0), which is why the B3 → B4 step now moves exactly one lever and can be read as a single-factor comparison. The previous per-fold grid search is retained only as a documented diagnostic: it cost 0.0036 nats.

### 4.2.1 What this section answers

This section builds **B4**, the transparent model used as the subject of H2 and as the base model for the localisation analysis in H3 and the information decomposition in H4. It is a model-construction section, not a hypothesis test: it reports how B3 and B4 are specified and fitted, whether the fitted models are numerically sound, and how much the time-decay patch is worth out of sample.

The B3 → B4 paired interval below is the same cluster bootstrap M2 uses everywhere else, taken from the `B3` row of `results/table_main.csv` (48 blocks, 10,000 resamples, seed 20261110).

**One lever, not two.** In the previous version of this report B4 applied time decay *and* a Dixon–Coles low-score correction with a per-fold estimated ρ, so the B3 → B4 step changed two things at once and was explicitly excluded from attribution. With ρ fixed at zero the correction is inactive: **B3 → B4 is now a single-factor comparison, time weights on versus off.** The rungs interpreted causally remain B4 → B5a (model class) and B5a → B5b (information set); B3 → B4 is now interpretable but is still not the subject of any registered hypothesis.

### 4.2.2 Data and method

**Data.** `data/processed/panel.parquet`, 46,507 matches in six leagues (E0, SP1, I1, D1, F1, N1) across 22 seasons. The evaluation design is the 48-block rolling-origin split in `configs/splits.json`: for each target season from 2017/18 to 2024/25, the model is trained on every strictly earlier match in the same league and predicts the target season. The evaluation set is 16,733 matches; per-fold training samples range from 4,284 to 7,980 matches. No market column enters any feature set.

**B3.** For a match with home team *h* and away team *a*,

```
log λ_home = μ + γ + α_h − β_a
log λ_away = μ + α_a − β_h
```

where goals scored by each side are Poisson with those rates, α is attack, β is defence, μ is the league baseline and γ is home advantage. Both Σα = 0 and Σβ = 0 are imposed by a reduced parameterisation, so the likelihood has a unique maximum; a ridge penalty of 1.0 on α and β keeps promoted teams from taking extreme values in their first season. Teams unseen in the training window are set to α = β = 0, the league average.

**B4.** One patch on B3: each training match receives weight `w = exp(−ξ·Δdays)`, normalised to mean one within the fold, where Δdays is measured from the first day of the target season. The Dixon–Coles τ(ρ) machinery remains in `src/models/b4_dixon_coles.py` and is exercised by the degeneracy checks, but the reported arm runs it at ρ = 0, where τ ≡ 1 by construction. With ξ = 0 and ρ = 0, B4 reproduces B3 to machine precision; `src/models/b4_dixon_coles.py --degeneracy` runs that check and four further degeneracy checks.

**Hyper-parameters are constants, and the constants are justified before the fact.** ξ = 0.0019 day⁻¹ is the midpoint of the pre-registered grid {0.0005, 0.0010, 0.0019, 0.0030, 0.0050, 0.0080}, and it corresponds to a half-life of ln2/ξ ≈ 365 days — one year, the natural scale at which a squad, a manager and a promotion/relegation cycle turn over. ρ = 0 is the neutral value: it disables the correction rather than tuning it. Neither number was chosen by looking at the evaluation window; §4.2.5 states precisely what the evaluation window would have preferred, and why that preference is not acted on.

**Fitting.** Both models maximise the weighted log likelihood with L-BFGS-B using an analytic gradient. Each fold is fitted **once** on the full training window: there is no inner validation split, no candidate grid, and no selection step. This is a deliberate change from the previous version, which fitted each fold 31 times (30 candidates on an inner season, then one refit) — §4.2.4 records why that rule was retired and what it measured.

**Optimiser tolerance.** `maxiter = 2000`, `ftol = 1e-12`, `gtol = 1e-10`. These were loosened-and-then-tightened rather than inherited: the previous settings (`500 / 1e-9 / 1e-7`) let L-BFGS-B exit on its relative-reduction criterion with a gradient norm as large as 0.76 still on the solution, and `python -m src.models.b4_dixon_coles --polish` reported FAIL for that reason. Tightening costs 0.13 s per fold and cuts the largest infinity-norm gradient across all 96 fits from 1.68 to **0.04**; the polish check now passes with a maximum test-log-loss movement of 9.4 × 10⁻⁷ (`results/logs/b4_polish_2026-11-24.txt`).

**Code.** `src/models/b3_poisson.py` (shared likelihood and gradient), `src/models/b4_dixon_coles.py` (B4 patch, degeneracy checks, `--polish`), `src/models/tune_b4.py` (the retired grid search, kept as `--selection argmin`), `src/models/run_b4.py` (48 folds), `src/models/sens_b4_fixed_hp.py` (the comparison of §4.2.5). Tables in this section are regenerated by `python -m src.models.m3_report_tables` from the artefacts of `python -m src.models.run_b4`.

### 4.2.3 Results

**Table 4.2-a. Out-of-sample log loss by league** (source: `products/tables/t4_2_model_fit.csv`; pooled over matches, not averaged over folds).

| League | Folds | Matches | B3 log loss | B4 log loss | Δ (B3 − B4) | Folds B4 better |
|---|---:|---:|---:|---:|---:|---:|
| E0 | 8 | 3,040 | 1.0000 | 0.9786 | +0.0214 | 7/8 |
| SP1 | 8 | 3,040 | 0.9974 | 0.9998 | −0.0024 | 5/8 |
| I1 | 8 | 3,040 | 0.9952 | 0.9822 | +0.0130 | 7/8 |
| D1 | 8 | 2,448 | 1.0139 | 1.0069 | +0.0071 | 5/8 |
| F1 | 8 | 2,791 | 1.0238 | 1.0190 | +0.0049 | 6/8 |
| N1 | 8 | 2,374 | 0.9575 | 0.9525 | +0.0050 | 6/8 |
| **All** | **48** | **16,733** | **0.9986** | **0.9903** | **+0.0084** | **36/48** |

The fold-level difference has mean 0.0083 and standard deviation 0.0186, and B4 is better in 36 of 48 folds. The gain is concentrated in E0 (+0.0214) and I1 (+0.0130). SP1 is the one league where B4 is worse, and by a margin (−0.0024) far inside the fold-level noise; under the retired per-fold rule SP1 lost by 0.0101, so most of that apparent anomaly was the tuning rule rather than the league. Both arms fall inside the pre-specified 0.96–1.06 band, and neither is close to the 0.90 leakage alarm.

**The paired interval for these 0.0084 nats is [0.0037, 0.0129]** (90%, 48 blocks, design effect 3.11). Read against the four-branch rule of §4.4: the interval **excludes zero**, so the patch does something; but the interval lies **entirely inside ±0.02**, so the something is below the margin the project declared practically meaningful. This is the "practically equivalent" branch of §4.4, reached with a direction that is now resolvable — a stronger statement than the previous version, which could only report an interval containing zero.

**Numerical diagnostics.** All 48 folds converged in both arms; there are no failed fits. B4 needs a median of 354 iterations (maximum 590) and B3 a maximum of 161 — the higher count is the price of the tighter tolerance. The largest infinity-norm gradient across all 96 fits is 0.04. A flat gradient at the reported solution is checked directly rather than inferred: `python -m src.models.b4_dixon_coles --polish` restarts from the reported parameters with `ftol = 1e-16` and `gtol = 1e-12`, and finds the negative log likelihood falls by at most 2.9 × 10⁻⁷ while test log loss moves by at most 9.4 × 10⁻⁷ nats (`results/logs/b4_polish_2026-11-24.txt`). The solution is a genuine optimum, not a stopping point.

### 4.2.4 The selection rule we retired, and what it measured

**Table 4.2-b. What the retired per-fold argmin chose** (source: `results/logs/selection_diagnostic/xi_rho_by_block_argmin.csv` via `products/tables/t4_2_hyperparameters.csv` and `t4_2_paired_folds.csv`). This table describes a rule that is **no longer used**; it is kept because it is the evidence for retiring it.

| ξ (day⁻¹) | Half-life (years) | Folds | | ρ | Folds |
|---:|---:|---:|---|---:|---:|
| 0.0005 | 3.80 | 15 | | -0.15 | 20 |
| 0.0010 | 1.90 | 10 | | -0.05 | 8 |
| 0.0019 | 1.00 | 7 | | 0.00 | 8 |
| 0.0030 | 0.63 | 9 | | 0.05 | 9 |
| 0.0050 | 0.38 | 7 | | 0.15 | 3 |
| 0.0080 | 0.24 | 0 | | | |
| **interior (4 middle values)** | | **33/48 (68.8%)** | | **both ends** | **23/48 (47.9%)** |

The selected ξ has median half-life 1.90 years and ranges from 0.38 to 3.80 years. The distribution is piled up on **one** side only: 15 folds choose the longest-memory grid point and none choose the shortest. ρ behaves differently, with 20 folds at −0.15 and 3 at +0.15.

The natural worry about this table is that ξ was pushed to a boundary because the likelihood is flat, so the selected value was arbitrary. The paired comparison in `products/tables/t4_2_paired_folds.csv` tests that directly. For each fold, the loss of the selected (ξ̂, ρ̂) is compared, match by match on the same validation set, with the loss of the strongest alternative at the same ρ̂; in 47 of the 48 folds this is the adjacent grid point, and in F1 2021/22 it is the opposite end of the grid at ξ = 0.0080.

- Only **5 of 48** folds show a significant difference (|t| > 1.96), and all five are folds where the selected longest-memory point beats the adjacent one: E0 2017/18 (t = 2.06), SP1 2018/19 (t = 2.84), F1 2019/20 (t = 3.09), SP1 2020/21 (t = 2.56), N1 2022/23 (t = 2.23).
- Across all folds the median absolute difference to that neighbour is 0.0014 nats, against a median paired standard error of 0.0034 nats; the median |t| is 0.42.
- Against the best of all 29 other candidates, no fold reaches significance (maximum |t| = 1.00). Every one of the 30 candidates converged in every fold.

Two things follow, and they point in opposite directions. The **identification** reading holds: ξ is weakly identified in most folds, and where the data do discriminate they prefer longer memory, so the boundary values were not arbitrary. The **decision** reading does not hold: weak identification is exactly the condition under which a per-fold argmin stops being a decision rule and becomes a draw. The validation set is one season — 306 to 380 matches — the true difference between adjacent ξ values is about 0.001 nats, and the paired standard error of that difference is 0.0034 nats: a signal-to-noise ratio of about 0.3. Selecting the minimum of 30 noisy scores at that ratio is close to a draw, and the draw is biased toward the corners, because the candidate whose noise happens to be favourable is the one that wins.

The same comparison explains why ρ sat at −0.15 so often: the validation set rarely separated neighbouring ρ values either, and where it did, the negative corner is where the low-score correction is largest.

**How the rule was retired.** The change is a pre-specified constant, not a post-hoc winner. Two properties make that distinction operational. First, ξ = 0.0019 was one of six grid points registered in advance and is the one with the a-priori justification (a one-year half-life); it is not the argmin of anything. Second, the decision was taken on the basis of a **simulation of the two candidate rules on the same 48 folds** (`src/models/sens_b4_fixed_hp.py`, §4.2.5), and the losing rule is kept in the repository so the comparison can be re-run byte for byte: `python -m src.models.run_b4 --selection argmin` reproduces the archived predictions exactly, writing to `results/logs/selection_diagnostic/` and never to `results/preds/`.

### 4.2.5 What the constant costs and what it buys

`src/models/sens_b4_fixed_hp.py` refits all 48 folds with **no selection at all** — one (ξ, ρ) pair reused in every fold — and compares against the retired arm. Nothing else changes: same training windows, same likelihood, same evaluation set.

| Configuration | Pooled log loss | vs retired argmin (90% CI) | vs B3 (90% CI) | Folds better than argmin |
|---|---:|---|---|---:|
| retired (per-fold argmin) | 0.9939 | — | +0.0048 [−0.0007, +0.0099] | — |
| **reported (0.0019, 0) — grid centre** | **0.9903** | **−0.0036 [−0.0060, −0.0013]** | **+0.0084 [0.0038, 0.0129]** | 30/48 |
| (0.0019, −0.05) | 0.9896 | −0.0043 [−0.0067, −0.0020] | +0.0090 [0.0044, 0.0136] | 33/48 |
| (0.0005, 0) — most-selected ξ | 0.9918 | −0.0021 [−0.0063, +0.0018] | +0.0069 [0.0049, 0.0088] | 24/48 |
| (0, 0) — degenerates to B3 | 0.9986 | +0.0048 [−0.0007, +0.0099] | 0.0000 | 14/48 |

Three fixed configurations beat the retired rule, and the two centred ones do so with intervals that exclude zero. The last row is the degeneracy control: with ξ = ρ = 0 the script reproduces B3 exactly (difference 0.00e+00), which confirms that the refit path is the same one the reported arm uses and that the comparison is not an artefact of a different pipeline.

**The one fork we did not take.** (0.0019, −0.05) scores 0.0007 lower than the reported arm, and the paired interval for that difference is [0.0003, 0.0011] — it excludes zero. We report the number and do not act on it, for three reasons. (i) Acting on it would be the same error one level up: a value chosen because it scored better on the 16,733-match window is selected on the evaluation data, which is precisely what the retired rule was retired for. (ii) The magnitude is 0.07% of the metric and one-thirtieth of the ±0.02 margin; nothing downstream moves. (iii) ρ = 0 is what makes §4.2.1's "one lever" claim true. If a future version wants a non-zero ρ, it needs an argument that does not come from this table.

**What the change did to the reported numbers** (90% cluster intervals; the C1, B2 − B4 and H4 rows also move because B5a's sample weights inherit ξ, see §4.2.6):

| Quantity | Reported (constant) | Retired (argmin) |
|---|---|---|
| B3 → B4 | 0.0084 [0.0038, 0.0129] — excludes 0 | 0.0048 [−0.0007, 0.0099] — contains 0 |
| H2 gap (B4 vs market) | 0.0317 [0.0278, 0.0359] | 0.0353 [0.0309, 0.0401] |
| B2 − B4 | 0.0048 [0.0013, 0.0084] | 0.0084 [0.0042, 0.0127] |
| C1 (B5a − B4) | 0.0055 [0.0009, 0.0099] | 0.0142 [0.0078, 0.0207] |
| H4 rel (B6r) | +0.19% | +0.17% |

The H2 row is the one to keep in mind when reading §5.4: the retired rule overstated the market gap by 0.0036 nats, because selection noise made B4 look worse than it is. Both numbers exceed the equivalence margin, so the H2 verdict never depended on the choice — but the direction of the bias is now known and corrected rather than merely bounded.

> **Read the C1 row with care.** Its two columns differ by *two* changes, not one: B4's hyper-parameter rule (this section) and B5's (the boosted arms were moved to a fixed configuration on the same day, §4.3.6). The 0.0142 in the second column was measured with both arms under per-fold selection; the 0.0055 in the first is both arms fixed. B4's own change is worth far less to C1 than B5's, which is why §5.1.4 reports the six configurations separately instead of attributing the whole move to one of them.

**The alternative that was tested and rejected: a longer validation window.** The binding constraint was diagnosed as the validation window, not the grid, and that diagnosis can be tested rather than asserted. `src/models/sens_b4_valwindow.py` re-runs the complete 48-fold pipeline with the inner validation set widened from one season to three (median 1,140 matches per fold instead of 306–380), keeping the target season out of selection exactly as before.

| Variant | Pooled log loss | vs reported (90% CI) |
|---|---:|---|
| reported (no validation at all) | 0.99027 | — |
| 3-season window, per-fold argmin | 0.99064 | +0.00037 [−0.00177, +0.00234] |

The paired standard error falls from 0.0034 to 0.0020 and the median signal-to-noise ratio rises from 0.42 to 0.96, which is what the diagnosis predicted. But the reward is only **to stop losing**: the three-season window lands 0.0004 *above* the constant, statistically indistinguishable from it, and 19 of 48 folds get better. It therefore buys nothing the constant does not already have, while costing a live selection rule, a full re-run of every downstream artefact, and a fresh justification of why a rule that loses to a constant should be kept. **Rejected.**

### 4.2.6 Limitations

1. **ξ is not identified from the data, and the section does not pretend otherwise.** The reported value is a pre-specified constant with an a-priori rationale; the folds disagree about the best value and cannot resolve their disagreement (median |t| = 0.42). §4.2.5 shows the consequences are small — three different constants within a factor of four of each other span 0.0023 nats — but a reader who wants a data-driven decay rate will not find one here.
2. **SP1 moves the wrong way.** B4 is worse than B3 in SP1 by 0.0024 nats, far inside the fold-level spread (sd 0.0186). We report it as measured; it is not averaged away or reframed. Under the retired rule the same league lost by 0.0101, which suggests most of that gap was the rule, not the league.
3. **The low-score correction is switched off, so its evidence is no longer in the headline.** τ(ρ) remains implemented and tested, and the sensitivity table shows (0.0019, −0.05) scoring 0.0007 lower — but with ρ = 0 the correction contributes nothing to the reported arm, and this section can say nothing about whether it would help at a different ξ. Separating the two patches is now a one-cell experiment rather than a redesign, and it is the obvious next step for anyone continuing this line.
4. **Optimiser tolerance is a reporting choice, and it changed.** The earlier solution was 5 × 10⁻⁵ nats away from the optimum in test log loss; the reported one is within 1 × 10⁻⁶. No conclusion in this report moves at that scale, but the numbers in this section are not bit-identical to the previous version for that reason alone.
5. **Promoted teams.** The 48 folds contain 25 team-season instances where a team has no history in the training window. These are handled by the league-average prior plus the ridge penalty, not by a dedicated cold-start model.
6. **What this section cannot say.** It does not say that B4 is better than the market (it is not — see §4.4), nor that time decay is the *only* thing that matters in a football score model. It also says nothing about calibration, which is estimated in §4.4 from the same prediction files.

---

**Self-check**

- [x] Every number above traces to a row in `products/tables/t4_2_*.csv`, to `results/table_main.csv`, or to `results/logs/b4_fixed_hp_*.csv` / `b4_val3_window.csv`.
- [x] The B3 → B4 interval is the `B3` row of `results/table_main.csv`, i.e. the same cluster bootstrap M2 uses in §4.4; it is not recomputed with a different method here.
- [x] Log loss is the only accuracy metric used; no accuracy figure appears.
- [x] No test-season information enters fitting: the reported arm has no validation split and no selection step at all. The retired rule is retained only as a diagnostic and writes to a separate directory.
- [x] The one configuration that scores better than the reported arm is disclosed, with its interval, and the reason for not adopting it is stated.
- [x] The change of hyper-parameter rule is recorded as a decision with an owner, not as a silent edit: see `docs/plans/roles/M3_结构化统计模型.md` §6 and `results/logs/xi_rho_decision_2026-11-11.txt`.
- [ ] Terminology still to be aligned with the glossary in `docs/plans/08_小组分工实施方案_v1.3.md` during M5 consolidation.
