# §4.5 The model–market gap (H2): what is estimated, and how

**One-sentence summary.** H2 is estimated as the mean of per-match log-loss differences between a transparent arm and the de-vigged market on the matches both cover, with two pre-registered claims read off two interval levels — 95% for "the model does not win", 90% for "the shortfall is not negligible".

§4.4 fixed the ruler. This section fixes the quantity the ruler is applied to, because "the model trails the market by 0.032 nats" can mean at least three different things and only one of them is what this report claims.

### 4.5.1 The quantity

For match *i* let ℓ<sub>m,i</sub> be the log loss of the model's three-way forecast and ℓ<sub>k,i</sub> the log loss of the de-vigged market's, both evaluated against the realised outcome. The estimated gap is

> Δ = (1/n) Σ<sub>i</sub> (ℓ<sub>m,i</sub> − ℓ<sub>k,i</sub>),  positive ⇒ the model is worse.

Three properties of this definition are deliberate.

- **It is paired, not marginal.** Because both forecasts are scored on the same match, Δ equals the difference of the two pooled log losses — but only because the match sets are identical. The estimator is written as a mean of differences so that the interval inherits the pairing: the variance that matters is the variance of (ℓ<sub>m</sub> − ℓ<sub>k</sub>), not the sum of two marginal variances.
- **It uses the intersection of the two arms' coverage.** The market exists for 16,728 of the 16,733 evaluation matches; the five without a closing price are dropped rather than imputed, so *n* = 16,728 and the comparison is on a slightly smaller sample than the ladder table. Imputing a benchmark price would have manufactured agreement in exactly the matches where the market is hardest to observe.
- **It is a per-match quantity, in nats.** No relative percentage is used as the primary scale. Relative gaps are unstable when the denominator is small — which is precisely the case in H4's robustness check (§4.6.4) — so percentages appear only where the denominator is protected.

### 4.5.2 Two claims, two interval levels

H2 is not one test. It is two one-sided claims about the same Δ, registered separately because they fail for different reasons:

| Claim | Question | Decision interval | Falsified when |
|---|---|---|---|
| **(a)** B4 does not beat B6 | is the sign of Δ established? | **95%** block bootstrap | the interval excludes zero *in B4's favour* |
| **(b)** the residual is practically non-zero | is the magnitude above the margin? | **90%** block bootstrap | the interval lies *entirely inside* ±0.02 |

The asymmetry is not a convenience. Claim (a) is an ordinary directional statement and gets the conventional two-sided level. Claim (b) is a *practical* statement about a margin, and it is deliberately the harder of the two to satisfy: to be falsified, the whole interval must sit inside ±0.02, so a wide interval cannot be used to argue "no meaningful difference". If the interval is wide the honest output is "we cannot tell", which is what §2 rule 3 says. Both intervals are percentiles of the same 10,000-replicate cluster bootstrap (Cameron, Gelbach & Miller 2008), so the two levels differ only in which pair of percentiles is read off — not in the resampling scheme, the seed or the block definition.

The margin itself is justified in §4.4.2 and not re-derived here: at 48 clusters the design's own resolution is of order 0.02 nats, so a tighter margin would be a claim the data cannot adjudicate rather than a stricter standard.

### 4.5.3 Which arm carries the claim

B4 was named in the proposal as the transparent model, so B4 carries the verdict. That choice has a cost which is reported rather than hidden: B4 is not the best transparent arm, so its gap overstates "what a transparent model can do". The report therefore computes the same estimator for **every** arm and for the best one in particular (B2), and §5.4.1 states both numbers — 0.0317 for the pre-registered arm, 0.0270 for the best one. The verdict is unchanged because both exceed the margin, but the sentence attached to it changes.

Reporting the alternative is a robustness check; it is not a re-registration. Substituting the best-performing arm into the primary claim after seeing the results would convert a pre-registered test into a search, and the whole point of writing the rules down first (§2) is to make that move unavailable.

### 4.5.4 Robustness families

Two, both declared before the numbers.

- **De-vigging.** Proportional, Shin and power methods are one family. The gap is computed under all three and reported in full (§5.3), because H1 shows the market's *calibration slope* depends on the method; if the gap did too, H2 would inherit that ambiguity. It does not, and the reason is arithmetic rather than empirical — see §5.3.3.
- **Metric.** Log loss is primary; Brier score is computed for the same pairs and moves with it in sign and ordering. A gap that appeared under log loss and vanished under Brier would be a property of the loss function, not of the forecasts.

### 4.5.5 What this design cannot settle

Three limits, stated here so that §5.3 does not have to hedge retrospectively.

1. **The gap is a lower bound on the information difference.** The rolling arms (B1, B2, B5a, B5b) refresh their result-dependent state inside the test season while B4's parameters are frozen before kick-off (§4.4.5, §5.1.6). Freezing that refresh costs B2 about 0.0116 nats, which means the delivered comparison gives the rolling arms an advantage the batch arms do not have. H2's verdict is unaffected in direction — the gaps get *larger*, not smaller — but the number attached to "the best transparent model" is a floor, not a ceiling.
2. **No equivalence test is run.** The four-branch rule says when a difference is below the practical margin; it is not a TOST procedure with a stated power, so the report never claims "equivalent" in the regulatory sense, only "not distinguishable at a magnitude that matters" (§5.1.7).
3. **One benchmark, one bookmaker.** B6 is Pinnacle closing. A different benchmark (market-maximum prices, or an exchange) would change the level of Δ; the report does not claim the gap is invariant to the choice of price source, only that it survives the three ways of removing the margin from this one.

*Sources: `results/logs/m2_verdicts.csv` (H2 rows), `results/market_gap.csv` (three de-vig methods, log loss and Brier), `results/table_main.csv`, `src/eval/decisions.py` (`EQUIV_MARGIN = 0.02`), `tests/test_decisions.py`.*
