# Do football betting markets know more than a model can learn?
# Auditing the closing line for calibration and information

**Team 32 · DSC5001C63 Statistical Machine Learning I · Final report**
Semester A 2026/27 · Instructor: Kangning Cui · Date: 2026-11-28

**Members.**

| # | Name | Student ID | Role | Planned hours |
|---|---|---|---|---:|
| M1 | WAN Yihui | 60918408 | Data pipeline, coverage, reproducibility package | 36 |
| M2 | WANG Xingshuai | 61044852 | Evaluation harness, cluster bootstrap, market-side H1, H2–H4 verdicts | 52 |
| M3 | ZHOU Yixuan | 60802448 | Structured score models B3/B4, appendix A1 | 30 |
| M4 | SUN Peng | 61039829 | Baseline and boosted arms B0–B2/B5a/B5b, ablations C1/C2 | 36 |
| M5 | SHU Peixuan | 57855209 | Model-side calibration, report and deck, glossary, figure list | 52 |

Total 206 person-hours. The role codes M1–M5 refer to **people**, never to models: every model in this report is named `B0`–`B6` or `B6r`.

## Abstract

We treat the de-vigged closing line of the football betting market as a measuring instrument to be audited rather than an opponent to be beaten. On 46,507 matches across six European leagues (2003/04–2024/25) we evaluate nine arms — a transparent ladder from an outcome-frequency prior (B0) to a time-decayed Dixon–Coles model (B4) and gradient-boosted machines (B5a/B5b), against the de-vigged market (B6) and a recalibrated market (B6r) — under a 48-block expanding-window rolling-origin protocol with cluster bootstrap. The market is under-dispersed in direction: the proportional de-vigging slope is 1.086 (90% CI 1.047–1.124), the favourite–longshot signature, although the magnitude depends on how the margin is removed (Shin 1.052, power 1.030 with an interval covering one). The best transparent model (B2) trails the market by 0.027 nats per match (90% CI 0.024–0.030) and the pre-registered arm by 0.032 (0.028–0.036); the shortfall is not a calibration error — recalibrating the market (B6r) leaves the gap almost unchanged (relative 0.0019, 90% upper 0.013 < 0.25), and even an oracle recalibration fitted on the test labels closes only 8.7% of it. Two controlled comparisons locate the reason: swapping the model class from Dixon–Coles to boosted trees costs 0.0055 nats (90% CI 0.0009–0.0099), and widening the information set from 9 to 39 features buys back 0.0015 with an interval that includes zero — both steps sit inside the ±0.02 equivalence margin. The shortfall is *not* uniformly localised: it is larger where a newly promoted side is involved (+0.0113) but **smaller** in the first six matchdays (−0.0108), the opposite of the pre-registered mechanism. The market's edge is information the model lacks, and it tracks squad identity rather than calendar position; the models, conversely, are miscalibrated in the opposite direction, and the defect is concentrated on draws and worsens as capacity rises. A negative result by design, reported as such.

---

## 1 Introduction

*(并入 `section_1_intro_evolution.md`)*

Research question, the *Evolution of the proposal* paragraph (seven deviations, each with what it changed), and the B↔M mapping table that reconciles the submitted model names with the nine arms reported here.

## 2 Hypotheses

*(并入 `section_2_hypotheses.md`)*

H1 market under-dispersion · H2 transparent model does not close the gap · H3 localisation · H4 information, not calibration; each with its pre-registered falsification rule, plus the three analyses deliberately reported without being dressed up as hypotheses.

## 3 Data

*(并入 `section_3_data.md`)*

Six leagues × 22 seasons, 46,507 matches; the four ways the raw archive is not a rectangular table; closing prices `PSCH/PSCD/PSCA` from 2012/13; the 48-block rolling-origin split (`configs/splits.json`) and its leakage controls; the `data-v1.0` freeze.

## 4 Methods and models

### 4.1 The ladder
*(并入 `section_4_1_ladder.md`)*

Nine arms in one table, the multi-lever steps marked as unattributable, the two single-factor steps held by enforced locks, and the two market arms described as instruments rather than rungs.

### 4.2 Structured score models: B3 / B4
*(并入 `section_4_2_model.md`)*

### 4.3 Baselines and boosted arms: B0/B1/B2/B5a/B5b
*(并入 `section_4_3_baselines.md`)*

### 4.4 Evaluation framework and market calibration (H1 market side)
*(并入 `section_4_4_evaluation.md`)*

### 4.5 The model–market gap (H2)
*(并入 `section_4_5_h2_method.md`)*

The paired estimator, the two claims read at 95% and 90%, why B4 carries the verdict while B2 is reported alongside it, the three de-vigging methods as one robustness family, and what the design cannot settle.

### 4.6 Localisation and recalibration (H3/H4)
*(并入 `section_4_6_h3h4_method.md`)*

The fixed-effects regression on the per-match gap (48 league–season intercepts, block bootstrap), the `min`-matchday measurement choice and the 1,025 matches it moves, the B6r ratio with its pairing preserved, and the oracle bound as a reference case rather than a test.

## 5 Results

### 5.1 Ablation and controlled comparisons C1/C2
*(并入 `section_5_1_ablation.md`)*

### 5.2 H1 — calibration
*(并入 `section_5_2_h1_calibration.md`)*

### 5.3 H2 — how far the model trails
*(并入 `section_5_3_h2_numbers.md`)*

The gap for all seven model arms under all three de-vigging methods, the two pre-registered criteria read off the intervals, why the methods cannot disagree by more than 1.5 × 10⁻⁴ nats, and the block-level distribution behind the pooled number.

### 5.4 H2 reading, H3 localisation
*(并入 `section_5_4_h2.md`)*

Three parts of the gap (universal, not a method artefact, not calibration), why the ladder is not monotone, the league-level temperature pattern that does not transfer, and §5.4.3: the H3 coefficients — promoted as predicted, early season in the opposite direction.

### 5.5 Conclusions and the negative result
*(并入 `section_5_5_conclusions.md`)*

## Appendix A — Home advantage (A1)

*(并入 `appendix_A.md`)*

## Author contributions

All five members designed the study, read and approved the final manuscript, and are accountable for the work. Contributions are listed at the level of the artefacts a reader can check in the repository; the per-task allocation is in `docs/plans/08_小组分工实施方案_v1.3.md`.

| Member | Conception and design | Data and code | Analysis and writing |
|---|---|---|---|
| M1 | Data scope, evaluation window, coverage criteria | S0–S5 pipeline (`src/build_panel.py`, `configs/raw_manifest.csv`, `configs/splits.json`), clean-venv reproduction package | §3, figure `fig_data_coverage`, deck pages 2/9/10 |
| M2 | Pre-registration of the four hypotheses, decision rules, equivalence margin | Evaluation harness `src/eval/` (48-block rolling origin, cluster bootstrap with design effect), `run_m2` | §4.4, §4.5–4.6, §5.3, market-side H1 in §5.2, H2–H4 verdicts, deck pages 5/6/8 |
| M3 | Model ladder design B3/B4, time-decay weighting | `src/models/b3_poisson.py`, `b4_dixon_coles.py`, hyper-parameter adjudication (§4.2) | §4.2, Appendix A, deck page 3 |
| M4 | Baseline and boosted arms, the two controlled comparisons C1/C2 | `src/models/b0…b2`, `b5_gbm.py`, feature whitelist, sensitivity scripts `sens_*` | §4.3, §5.1, deck page 4 |
| M5 | Positioning of model-side calibration as descriptive rather than a second hypothesis | `analysis/h1_calibration.ipynb` and the `m5_*` tables, glossary, figure list | §1, §2, §5.2 (model side), §5.4, §5.5, deck pages 1/7 |

**Verification.** Every number in this report is regenerated by the commands in `appendix/run_all.*`, and the committed prediction files are reproduced bit-for-bit by `src/models/check_m4.py` (14/14 checks, including five arms fitted live and compared row-by-row against `results/preds/`). Where a number in an earlier draft disagreed with the artifacts, we changed the number and recorded the change rather than the reverse; those cases are flagged in §4.2, §4.3.6, §5.1.6 and §5.2. Prose and table numbers are additionally checked against the artefacts by 48 rules in `src/report/m5_report_tables.py` — regular-expression rules for the abstract, §5.1, §5.2, §5.4 and the deck, plus row-by-row comparison of Tables 4.1-a and 5.3-a — run as part of `pytest`.

## References

*(并入 `references.md`)*
