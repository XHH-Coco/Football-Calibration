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

## Abstract

We treat the de-vigged closing line of the football betting market as a measuring instrument to be audited rather than an opponent to be beaten. On 46,507 matches across six European leagues (2003/04–2024/25) we evaluate nine arms — a transparent ladder from an outcome-frequency prior (B0) to a time-decayed Dixon–Coles model (B4) and gradient-boosted machines (B5a/B5b), against the de-vigged market (B6) and a recalibrated market (B6r) — under a 48-block expanding-window rolling-origin protocol with cluster bootstrap. The market is under-dispersed in direction: the proportional de-vigging slope is 1.086 (90% CI 1.047–1.124), the favourite–longshot signature, although the magnitude depends on how the margin is removed (Shin 1.052, power 1.030 with an interval covering one). The best transparent model (B2) trails the market by 0.027 nats per match (90% CI 0.024–0.030) and the pre-registered arm by 0.032 (0.028–0.036); the shortfall is not a calibration error — recalibrating the market (B6r) leaves the gap almost unchanged (relative 0.0019, 90% upper 0.013 < 0.25). Two controlled comparisons locate the reason: swapping the model class from Dixon–Coles to boosted trees costs 0.006 nats, and widening the information set from 9 to 39 features buys back 0.002 — both steps sit inside the ±0.02 equivalence margin. The market's edge is information the model lacks; the models, conversely, are over-dispersed, most severely on draws once model capacity rises. A negative result by design, reported as such.

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

## References
*(PENDING)*
