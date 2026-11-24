# §4.1 The ladder

**One-sentence summary.** Nine arms, of which seven are forecasts built from pre-match information only and two are the market itself; the ladder exists so that every step can be described as *one* change, and only two of its steps — B4→B5a and B5a→B5b — are single-factor enough to be interpreted causally.

### 4.1.1 Why a ladder rather than a leaderboard

The question in RQ2 is not "which model wins" but "how much of the shortfall is a property of the model class and how much is a property of the information". A single strong model cannot answer that, because a difference between two models confounds three things at once: the functional form, the features, and the estimation rule. So the design fixes a rung order in which each successive arm is meant to differ from the one below it by a single factor, and then reports the size of each step with an interval.

Two consequences follow, and both are visible in the results. First, the ladder's *ordering* is not the claim — §5.4.1 shows the ordering is not even monotone in model complexity, and that this is itself informative. Second, an arm can be a useful rung without being a good model: B0 is a poor forecaster (1.0743 nats) and an indispensable rung, because it establishes how much of the total distance from ignorance to the market is covered by the base rate alone.

### 4.1.2 The nine arms

| Rung | Model | Information it uses | Change vs previous rung | Free constants | Pooled log loss (90% CI) | Role |
|---|---|---|---|---|---:|---|
| **B0** | empirical class frequencies, expanding | same league, strictly earlier matches | — (floor) | none | **1.0743** (1.0703–1.0782) | reference floor |
| **B1** | multinomial logistic | one number: Elo(home) − Elo(away) | model **and** information | none | **0.9926** (0.9856–0.9999) | first rating arm |
| **B2** | proportional-odds ordinal logit | five state features (Elo ×3, points, rest) | +4 features **and** ordinal link | none | **0.9855** (0.9781–0.9930) | best transparent arm; H2 robustness |
| **B3** | independent Poisson | goals by team, attack/defence | model **and** information | none | **0.9986** (0.9912–1.0063) | unpatched structured rung |
| **B4** | time-decayed Dixon–Coles | as B3, exponentially weighted | **time weights only** | ξ = 0.0019, ρ = 0 | **0.9903** (0.9819–0.9988) | pre-registered H2 arm; C1 base |
| **B5a** | histogram gradient boosting | 9-feature whitelist | **model class only** | (3, 0.01) | **0.9957** (0.9888–1.0027) | C1; C2 base |
| **B5b** | histogram gradient boosting | all 39 features | **information set only** | (3, 0.01) | **0.9942** (0.9872–1.0014) | C2 upper rung |
| *B6* | de-vigged Pinnacle closing | the market's own information | — (instrument) | — | **0.95854** (0.9511–0.9661) | benchmark for H1–H4 |
| *B6r* | B6, recalibrated | as B6 | two-parameter logit map | c, d per fold | **0.95848** (0.9509–0.9661) | instrument for H4 only |

Pooled log loss over 16,733 matches for the seven model arms and over 16,728 for B6/B6r (five matches in three blocks have no closing price and are dropped, not imputed). Intervals are the 48-block cluster bootstrap of §4.4.2. Arm names are `B`-names throughout; `M1`–`M5` are reserved for team members (§1). B6r is printed to five decimals because at four it is indistinguishable from B6 — the two differ by 6 × 10⁻⁵ nats, which is the entire content of H4 (§5.4).

Two of the seven model arms are named after their published form. B3 is the independent-Poisson score model of **Maher (1982)**; B4 adds the exponential time-decay weighting of **Dixon & Coles (1997)** and, in the original specification, their low-score dependence correction τ(ρ) — which this report runs at ρ = 0, i.e. switched off, so that the B3→B4 step moves only the decay rate (§4.2). B1 and B2 use the Elo rating of **Hvattum & Arntzen (2010)** mapped to three-way probabilities.

### 4.1.3 Which steps can be read as causal

| Step | What changes | Interpretable? |
|---|---|---|
| B0 → B1 | frequency model → rating model, base rate → Elo | **no** — model and information change together |
| B1 → B2 | four more features *and* a proportional-odds link | **no** — two levers |
| B2 → B3 | logit → Poisson, rating → goals | **no** — two levers |
| **B3 → B4** | time weights on/off, nothing else | **yes, but not registered** — the low-score correction is switched off (ρ = 0), so this is a clean single-factor step; it is not the subject of any hypothesis |
| **B4 → B5a** | generative → discriminative, same 9-column information source, same weight formula | **yes — C1** |
| **B5a → B5b** | 9 → 39 features, same learner, same weights and constants | **yes — C2** |
| B5b ⇄ B6 | a forecast vs a price | not a rung — see §4.1.4 |

The two labelled steps are held in place by two locks that are enforced in code rather than promised in prose: **the same weight formula** for B4→B5a (the time-decay weights are carried into the boosted arm) and **the same weights and hyper-parameters** for B5a→B5b (the feature set is the only difference). Without the first lock, C1 would compare a time-weighted model to an unweighted one; without the second, C2 would compare two differently-regularised learners and the feature count would not be identified. §4.3.4 records how each lock is asserted.

B3→B4 is worth naming separately because it is the one unregistered step that *became* interpretable during the project: the previous version let B4 apply time decay **and** a per-fold estimated low-score correction ρ, so the step moved two levers. With ρ fixed at zero the correction is inactive and the step is time weights on versus off — a gain of 0.0084 nats (90% CI 0.0037–0.0129, inside the equivalence margin). It is reported as a structural result, not as a hypothesis, and no verdict depends on it (§4.2).

### 4.1.4 The two market arms are instruments, not rungs

B6 and B6r are not forecasts we built; they are the measuring device. B6 is the closing line with the margin removed by proportional scaling (Shin and power as robustness), and B6r is B6 passed through a two-parameter recalibration fitted only on training data. They appear in the same table because they are scored by the same ruler on the same matches — that comparability is the point — but they are never described as "a rung above B5b". A ladder step means "we changed one thing in our own forecast"; B5b → B6 means "we compared our forecast to someone else's price".

### 4.1.5 What the ladder deliberately excludes

- **No market column in any feature set.** Not a modelling preference but the definition of the exercise: an arm that sees the closing price is not a transparent model, it is the market with extra steps. Asserted in `tests/test_leakage.py`.
- **No per-fold hyper-parameter selection anywhere.** Every constant in the table is fixed for all 48 folds, and each is justified before the fact — ξ by a one-year half-life, ρ = 0 as the neutral value, the boosting pair as the minimum-capacity corner. The per-fold search rules that were tried first are retained as diagnostics under `results/logs/selection_diagnostic/`, so the comparison can be re-run byte for byte (§4.2.4, §4.3.6).
- **No ensembling, stacking or blending.** An ensemble would blur exactly the attribution the ladder exists to provide.
- **No accuracy anywhere.** Football's irreducible noise caps top-1 accuracy near 50%, so accuracy would reward a model for being confident rather than for being right; all evaluation uses strictly proper scoring rules (Gneiting & Raftery 2007), with log loss primary and the Brier score and ranked probability score (Murphy 1973) as secondary.
- **One software stack, pinned.** All seven arms are implemented in Python with scikit-learn (Pedregosa et al. 2011) on eight pinned dependencies, so a result cannot be a version artefact.

*Sources: `results/table_main.csv` (all nine rows, pooled log loss and 90% intervals), `src/models/` (`b0_prior.py` … `b5_gbm.py`), `configs/feature_whitelist_b5a.csv` (9 features), `src/features.py` (39 features), `tests/test_leakage.py`.*
