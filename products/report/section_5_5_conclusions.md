# §5.5 Conclusions and the negative result

**One-sentence conclusion.** The de-vigged closing line is mildly under-dispersed in a direction we can name and cannot fully separate from the de-vigging method (slope 1.086, 90% CI 1.047–1.124), a transparent model built only from pre-match information does not close the gap (best arm 0.0270 nats per match, pre-registered arm 0.0317), and repairing the market's own calibration moves that gap by 0.2% — so the shortfall is information, not arithmetic.

### 5.5.1 The two research questions, answered

**RQ1 — is the de-vigged market calibrated?** In direction, no: the proportional-de-vigged calibration slope is **1.086** (90% CI 1.047–1.124), above one, which is the favourite–longshot signature — the price compresses probability towards the middle, so longshots occur less often than priced. The magnitude, however, is not a property of the market alone. Shin de-vigging gives 1.052 (1.014–1.088) and power gives 1.030 (0.994–1.066), the last with an interval that covers one; and the proportional method is itself the *most* deviant of the three by 0.0198 nats. So the defensible sentence is "the market is under-dispersed in direction, with a magnitude that depends on how the margin is removed", not "the market is significantly conservative". Per class, only the away class survives all three methods.

**RQ2 — can a transparent model close the gap, and where does it live?** It cannot, and the gap is not a measurement artefact. All seven model arms trail the market; the best of them, a five-feature ordinal logit (B2), trails by **0.0270** nats per match (90% CI 0.0241–0.0298) and the pre-registered Dixon–Coles arm by **0.0317** (0.0278–0.0359), with 35 of 48 blocks individually above the ±0.02 margin. Repairing the market's calibration — two parameters fitted on training data only — changes the gap by a relative **0.0019** (90% upper bound 0.013), and even an oracle recalibration fitted on each block's *test* labels closes only **8.7%** of it. Calibration, allowed to cheat, explains less than a tenth of the shortfall.

### 5.5.2 The verdicts

| Item | Verdict | Key number | One-line reading |
|---|---|---|---|
| **H1** market under-dispersed | supported (direction) | slope 1.086 (1.047–1.124); Shin 1.052, power 1.030 | favourite–longshot bias survives de-vigging in direction, not uniformly in magnitude |
| **H2** model does not close the gap | supported, both criteria | B4 +0.0317, B2 +0.0270; every 90% lower bound > 0.02 | not a tie, not noise, and not arm-dependent |
| **H3** gap localised | **not supported as stated** | promoted +0.0113 (+0.0020 to +0.0208); early **−0.0108** (−0.0175 to −0.0040) | right about promoted sides, wrong about early season |
| **H4** gap is information | supported | relative change 0.0019, 90% upper 0.013 < 0.25; oracle 8.7% | repairing the price does not close the shortfall |
| **C1** model class, B4→B5a | difference resolvable, practically equivalent | +0.0055 (0.0009–0.0099) | boosted trees measurably worse, by a quantity that does not matter |
| **C2** information set, B5a→B5b | practically equivalent | −0.0015 (−0.0032 to 0.0001) | thirty extra columns are worth 0.0015 nats |

### 5.5.3 What a negative result buys

Three things, none of which a positive result would have produced.

**A calibration map of a price, with its dependence on method declared.** The report does not pick a de-vigging method and quietly report one slope; it reports all three, states which is most deviant, and treats the ordering as a pre-registered secondary claim that held (proportional deviates most, by 0.0198 nats, lower bound above zero). A reader who de-vigs differently can recompute the conclusion rather than having to trust ours.

**A localised answer, including the part that failed.** The gap is larger where the model's information is genuinely oldest — newly promoted sides, +0.0113 nats — and *smaller* in the first six matchdays (−0.0108), which is the opposite of what we predicted and is reported as such. The pair is more informative than either alone: it says the shortfall tracks squad-identity information, not calendar position, which is a sharper statement than "the model is worse somewhere".

**A decomposition the two literatures usually keep apart.** Work on market calibration and work on forecasting models are typically separate; here the same 16,728 matches, the same metric and the same bootstrap produce both numbers, and the decomposition is the reason the calibration result matters at all. Without H4, a slope of 1.086 would be an isolated curiosity.

**And a statement about our own models that is not flattering.** The models are miscalibrated in the *opposite* direction from the market — under-dispersed on draws rather than over — and the defect worsens with capacity: B4 sits at 0.944 on draws, the boosted arms at 0.53–0.57. In the 20–35% band where draws are most likely, B4 under-predicts by 1.4–2.0 percentage points, and the market shows the same sign in five of six leagues. The models are not too keen to predict draws; they say too little exactly where draws are most likely.

### 5.5.4 What would change the answer

Four things, in order of how much they would move it.

1. **More clusters.** 48 blocks set the resolution at about 0.02 nats. Twice as many league-seasons would let a 0.01 gap be adjudicated, and H1's per-class claims would stop depending on which de-vigging method is used.
2. **A benchmark that is not one bookmaker.** Pinnacle closing is the sharpest single price in the archive, which is the right choice for an upper bound on the market's information — and also the reason the gap is, if anything, understated for other books.
3. **Information we deliberately excluded.** The gap is defined against pre-match scoreline information only. A model with line-ups, injuries or transfer spend is a different study, and H3's promoted coefficient says that is where the missing information is.
4. **A stronger recalibrator than two parameters.** H4 rules out temperature-and-bias repairs; the oracle bound rules out block-specific two-parameter repairs. A richer recalibration (per-class, per-league, monotone splines) is the natural next test, and the oracle bound is the number it would have to beat to matter.

### 5.5.5 Limitations we would put on a slide

- **No equivalence test.** The four-branch rule says when a difference is below the practical margin; it is not a TOST with stated power, so "practically equivalent" means "not distinguishable at a magnitude that matters", never "proven equal" (§5.1.7).
- **The gap is a floor.** The rolling arms refresh their state inside the test season while B4's parameters are frozen; removing that advantage costs B2 0.0116 nats, which moves the best-arm gap *away* from the margin (§5.3.6).
- **One benchmark, one metric family, one protocol.** Log loss primary with Brier as a check; Pinnacle closing as the price; rolling-origin rather than frozen-season evaluation. Each choice is defensible and each would shift the level of the numbers, which is why the verdicts are stated as inequalities against a margin rather than as point estimates to be quoted.
- **H3's mechanism is not identified.** The coefficients locate the gap; they do not establish that stale information is why it is there.

The result is negative by design, and it is reported as one: a transparent model does not know what the closing line knows, the difference is not a repairable calibration defect, and the part of it we can localise points at squad information rather than at model class or feature count.
