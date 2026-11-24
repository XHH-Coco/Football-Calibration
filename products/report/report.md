<!-- ============ 统稿工作台（M5 内部状态，定稿前删除本块）============
更新：2026-11-20

【已完成 · 可并入】
  §1  Intro + evolution + B↔M      → section_1_intro_evolution.md   (M5)
  §5.2 H1 校准诊断                  → section_5_2_h1_calibration.md  (M5)
  §5.4 H2 解读                      → section_5_4_h2.md              (M5)
【成员已交】
  §4.2 B3/B4（结构化模型）          → section_4_2_model.md           (M3)
  附录 A1 主场优势 γ                → appendix_A.md                 (M3)
【待供稿 · 11/24 硬截止】
  §2  假设 H1–H4                    → 按蓝本 §2 起草，M5 兜底
  §3  数据                          → M1
  §4.3 B0/B1/B2/B5a/B5b             → M4
  §4.4 评估框架 + H1 市场侧斜率      → section_4_4_evaluation.md (M2) ✅
  §4.5 H2 与市场差距                → M2
  §4.6 H3/H4                        → M2
  §5.1 消融 / C1–C2                 → M4
  §5.3 H2 结果数字                  → M2
  §5.5 结论与负结果                  → M5
【统稿三原则 T5.6】统一口径 / 删重复 / 不重写别人的技术段落。
============================================================ -->

# Do football betting markets know more than a model can learn?
# Auditing the closing line for calibration and information

**Team 32 · DSC5001C63 Statistical Machine Learning I · Final report**
Semester A 2026/27 · Instructor: Kangning Cui · Date: 2026-11-28

**Members.** *(G3 #10 requires name and student ID on the first page — fill the two `〔〕` cells per row; nothing else in this table needs editing.)*

| # | Name | Student ID | Role | Planned hours |
|---|---|---|---|---:|
| M1 | 〔姓名〕 | 〔UID〕 | Data pipeline, coverage, reproducibility package | 36 |
| M2 | 〔姓名〕 | 〔UID〕 | Evaluation harness, cluster bootstrap, market-side H1, H2–H4 verdicts | 52 |
| M3 | 〔姓名〕 | 〔UID〕 | Structured score models B3/B4, appendix A1 | 30 |
| M4 | 〔姓名〕 | 〔UID〕 | Baseline and boosted arms B0–B2/B5a/B5b, ablations C1/C2 | 36 |
| M5 | 〔姓名〕 | 〔UID〕 | Model-side calibration, report and deck, glossary, figure list | 52 |

Total 206 person-hours. The role codes M1–M5 refer to **people**, never to models: every model in this report is named `B0`–`B6` or `B6r`.

## Abstract

We treat the de-vigged closing line of the football betting market as a measuring instrument to be audited rather than an opponent to be beaten. On 46,507 matches across six European leagues (2003/04–2024/25) we evaluate nine arms — a transparent ladder from an outcome-frequency prior (B0) to a time-decayed Dixon–Coles model (B4) and gradient-boosted machines (B5a/B5b), against the de-vigged market (B6) and a recalibrated market (B6r) — under a 48-block expanding-window rolling-origin protocol with cluster bootstrap. The market is under-dispersed in direction: the proportional de-vigging slope is 1.086 (90% CI 1.047–1.124), the favourite–longshot signature, although the magnitude depends on how the margin is removed (Shin 1.052, power 1.030 with an interval covering one). The best transparent model (B2) trails the market by 0.027 nats per match (90% CI 0.024–0.030) and the pre-registered arm by 0.032 (0.028–0.036); the shortfall is not a calibration error — recalibrating the market (B6r) leaves the gap almost unchanged (relative 0.0019, 90% upper 0.013 < 0.25). Two controlled comparisons locate the reason: swapping the model class from Dixon–Coles to boosted trees costs 0.0055 nats (90% CI 0.0009–0.0099), and widening the information set from 9 to 39 features buys back 0.0015 with an interval that includes zero — both steps sit inside the ±0.02 equivalence margin. The market's edge is information the model lacks; the models, conversely, are miscalibrated in the opposite direction, and the defect is concentrated on draws and worsens as capacity rises. A negative result by design, reported as such.

---

## 1 Introduction

*(并入 `section_1_intro_evolution.md` — M5 ✅)*

Research question, the *Evolution of the proposal* paragraph, and the B↔M mapping table.

## 2 Hypotheses

*(PENDING — 按蓝本 `Team-32-Proposal_v3.0.md` §2 起草，M5 统稿兜底)*

H1 market under-dispersion · H2 transparent model does not close the gap · H3 localisation · H4 information, not calibration; each with its pre-registered falsification rule.

## 3 Data

*(PENDING — M1)*

Six leagues × 22 seasons, 46,507 matches; closing prices `PSCH/PSCD/PSCA` from 2012/13; 48-block rolling-origin split (`configs/splits.json`); coverage matrix.

## 4 Methods and models

### 4.1 The ladder *(PENDING — M5/M3)*
### 4.2 Structured score models: B3 / B4 *(并入 `section_4_2_model.md` — M3 ✅)*
### 4.3 Baselines and boosted arms: B0/B1/B2/B5a/B5b *(并入 `section_4_3_baselines.md` — M4 ✅)*
### 4.4 Evaluation framework and market calibration (H1 market side) *(并入 `section_4_4_evaluation.md` — M2 ✅)*
### 4.5 The model–market gap (H2) *(PENDING — M2)*
### 4.6 Localisation and recalibration (H3/H4) *(PENDING — M2)*

## 5 Results

### 5.1 Ablation and controlled comparisons C1/C2 *(并入 `section_5_1_ablation.md` — M4 ✅)*
### 5.2 H1 — calibration *(并入 `section_5_2_h1_calibration.md` — M5 ✅)*
### 5.3 H2 — how far the model trails *(PENDING — M2 数字)*
### 5.4 H2 — reading the gap *(并入 `section_5_4_h2.md` — M5 ✅)*
### 5.5 Conclusions and the negative result *(PENDING — M5)*

## Appendix A — Home advantage (A1)

*(并入 `appendix_A.md` — M3 ✅)*

## Author contributions

All five members designed the study, read and approved the final manuscript, and are accountable for the work. Contributions are listed at the level of the artefacts a reader can check in the repository; the per-task allocation is in `docs/plans/08_小组分工实施方案_v1.3.md`.

| Member | Conception and design | Data and code | Analysis and writing |
|---|---|---|---|
| M1 | Data scope, evaluation window, coverage criteria | S0–S5 pipeline (`src/build_panel.py`, `configs/raw_manifest.csv`, `configs/splits.json`), clean-venv reproduction package | §3, figure `fig_data_coverage`, deck pages 2/9/10 |
| M2 | Pre-registration of the four hypotheses, decision rules, equivalence margin | Evaluation harness `src/eval/` (48-block rolling origin, cluster bootstrap with design effect), `run_m2` | §4.4, §4.5–4.6, §5.3, market-side H1 in §5.2, H2–H4 verdicts, deck pages 5/6/8 |
| M3 | Model ladder design B3/B4, time-decay weighting | `src/models/b3_poisson.py`, `b4_dixon_coles.py`, hyper-parameter adjudication (§4.2) | §4.2, Appendix A, deck page 3 |
| M4 | Baseline and boosted arms, the two controlled comparisons C1/C2 | `src/models/b0…b2`, `b5_gbm.py`, feature whitelist, sensitivity scripts `sens_*` | §4.3, §5.1, deck page 4 |
| M5 | Positioning of model-side calibration as descriptive rather than a second hypothesis | `analysis/h1_calibration.ipynb` and the `m5_*` tables, glossary, figure list | §1, §2, §5.2 (model side), §5.4, §5.5, deck pages 1/7 |

**Verification.** Every number in this report is regenerated by the commands in `appendix/run_all.*`, and the committed prediction files are reproduced bit-for-bit by `src/models/check_m4.py` (14/14 checks, including five arms fitted live and compared row-by-row against `results/preds/`). Where a number in an earlier draft disagreed with the artifacts, we changed the number and recorded the change rather than the reverse; those cases are flagged in §4.2, §4.3.6, §5.1.6 and §5.2.

## References
*(PENDING)*
