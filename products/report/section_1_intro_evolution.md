# §1 Introduction — research question and *Evolution of the proposal*

**One-sentence conclusion.** We do not try to beat the market; we audit how far a transparent, information-limited model can be trusted, and we decompose its shortfall into a calibration component and an information component.

We invert the usual framing: the de-vigged closing line is not a rival to beat but our most informative measuring instrument, and the questions worth asking are the ones it answers badly. **RQ1** asks whether de-vigged market probabilities are calibrated; **RQ2** asks whether a transparent model fitted only to pre-match information can match the market out of sample and, if not, where the gap concentrates and how much survives recalibrating the market itself. Football provides what risk-management, credit and clinical settings cannot: a high-frequency three-class outcome observed repeatedly, and a strong external forecaster with a known information set.

### *Evolution of the proposal*

The 30 October submission remains the record of what was handed in, unchanged; this report records the design actually implemented. After submission, internal review corrected **six** details without touching the research question. Four are corrections *to the submitted hypothesis statements*, and we now state each one explicitly instead of folding it into the methods: **(i)** the H1 sign — a slope above one places the reliability curve *below* the diagonal at low probabilities, and the submitted text had it above, contradicting its own slope claim; **(ii)** the H2 equivalence margin — ±0.01 is unresolvable at 48 clusters, so one margin of ±0.02 is used everywhere in the project; **(iii)** the H3 falsification rule — "falsified if either coefficient is at most 0" is inconsistent with joint estimation, so the rule is now *supported only if both coefficients are positive and both 90% intervals have lower bounds above zero*, and anything weaker is reported descriptively; **(iv)** the H4 decision rule — the 25% threshold acquired an interval criterion (judged on the 90% **upper** bound) and a guard for a near-zero denominator. Two are design changes: **(v)** the GBM comparison was split into two single-factor steps, B4→B5a (model class) and B5a→B5b (information set), because the submitted M4 changed the model class and the information set at once, so its attribution did not follow; **(vi)** the recalibrated market benchmark **B6r** was restored as the sole instrument for H4. RQ1/RQ2 and the H1–H4 line are unchanged; this is a design iteration, not a deviation.

### Mapping to the submitted proposal

| Submitted (30 Oct) | This report | Note |
|---|---|---|
| M0 prior | B0 | same model |
| M1 Elo → ordered logit | B1 + B2 | one merged arm split into two so the ladder is auditable |
| M2 multinomial logit, time-decayed goal features | — (absorbed into B5b features) | method change; B2 is ordered logit on Elo difference |
| M3 Dixon–Coles | B4 | same model; B3 added as the unpatched rung |
| M4 GBM on M2 features | B5a + B5b | split into two single-factor arms |
| MK de-vigged closing | B6 | same benchmark (`PSCH/PSCD/PSCA`) |
| MK* recalibrated market | B6r | restored as the sole instrument for H4 |

Throughout, model identifiers, prediction filenames (`preds_B0.csv … preds_B6r.csv`) and the `model` column use **B-names only**; M1–M5 are reserved for team members.
