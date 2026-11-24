# §3 Data

**One-sentence summary.** One public archive, 132 league-season files, six European leagues and 22 seasons — 46,507 matches, of which 16,733 form the evaluation set — with a de-vigged closing price available for 16,728 of those 16,733.

### 3.1 Source and scope

All data come from **football-data.co.uk**, one CSV per league-season, publicly downloadable with no registration and no API key. The project uses **six leagues × 22 seasons, 2003/04–2024/25**: 132 files, 14,341,191 bytes, 46,507 matches. Nothing is scraped, nothing is merged from a second provider, and the files are committed to the repository so that the pipeline starts from a fixed object rather than from a URL.

| League | Code | Seasons | Matches | Closing price absent (league-seasons) |
|---|---|---:|---:|---:|
| English Premier League | `E0` | 22 | 8,360 | 9 |
| Spanish La Liga | `SP1` | 22 | 8,360 | 9 |
| Italian Serie A | `I1` | 22 | 8,286 | 9 |
| German Bundesliga | `D1` | 22 | 6,732 | 9 |
| French Ligue 1 | `F1` | 22 | 8,111 | 9 |
| Dutch Eredivisie | `N1` | 22 | 6,658 | 9 |
| **Total** | | **22** | **46,507** | **54** |

The archive's coverage is not rectangular in either direction, and the coverage matrix (`results/coverage_matrix.csv`, 132 rows × 18 columns; heat map in `products/figures/fig_data_coverage.png`) is the artefact that makes this visible instead of discoverable-by-crash:

- **Closing prices start in 2012/13.** The 54 league-seasons of 2003/04–2011/12 have no `PSCH/PSCD/PSCA` columns at all — not empty values, absent columns. Six further league-seasons are partially covered (0.990–0.997).
- **Shot counts are missing for long stretches.** The Eredivisie has no shot columns before 2017/18, and Serie A, Ligue 1 and La Liga lack them in 2003/04–2004/05. Inside the evaluation window the only gap is one Bundesliga match in 2024/25 (`Union Berlin–Bochum`, six shot columns), so shot-based features cover **16,732 of 16,733** evaluation matches and are never imputed with zero.

Both facts matter downstream: the market arms simply do not exist before 2012/13, and a feature set that includes shots is defined on a slightly smaller sample than one that does not.

### 3.2 What the raw files actually look like

The archive is not a set of clean rectangular tables, and treating it as one silently destroys matches. `src/build_panel.py::read_raw()` therefore reads with the standard-library `csv` module and takes columns **by name** against a 19-column whitelist, rather than parsing with a fast path. The four defects, all measured on the full 132 files:

| Defect | Measurement | Consequence if ignored |
|---|---|---|
| Row length ≠ header | **11 files** (9 with long rows, 8 with short, 6 both); **775 long rows** and **1,331 short rows**; `0304_F1` has 365 irregular rows out of 380 | `ParserError`; `on_bad_lines='skip'` would silently drop 365 real matches |
| Duplicate column names | **14 files**, including empty-string names | `InvalidIndexError` on any `concat`/`reindex` |
| Missing market columns | **54 files** have no `PSCH/PSCD/PSCA` column | `KeyError` on `df['PSCH']` |
| All-blank rows | **7 files, 11 rows** (`1213_I1` has 3) | 11 phantom matches: 46,518 → **46,507** |

Two further details are handled explicitly. Overflow fields are permitted **only if empty**: all 2,895 overflow cells are empty strings in the real data, and `read_raw()` raises `ValueError` on any non-empty overflow — a guard against a future file where a shifted row would otherwise be read as a valid one. And the encoding is not uniform: 131 files are `utf-8-sig`, only `0405_E0.csv` needs `latin-1`.

**Team identity** is harmonised once, by hand, from 243 spellings to **241 distinct clubs**; only two are genuine renames. No fuzzy matching is used anywhere — a wrong merge would corrupt every rolling-window feature for two clubs at once, and the failure would be invisible in pooled log loss.

### 3.3 The modelling table

The cleaned panel is 46,507 rows × 22 columns, keyed by `match_id = league|season|date|home|away`, sorted by `league, season, date`, with the outcome encoded `y ∈ {H = 0, D = 1, A = 2}` (21,194 / 11,824 / 13,489). Market columns are carried alongside but **never enter a feature set**; they exist only to build B6 and B6r. The panel itself is not committed (1,028,001 bytes, reproducible in about three minutes); the raw CSVs, the column whitelist and `configs/splits.json` are.

### 3.4 The evaluation design: 48 blocks, not 16,733 matches

The split is an expanding-window rolling origin, fixed in `configs/splits.json` (schema 1.0) before any model was fitted and shared by every arm through one function, `src.splits.resolve_split(panel, block)`. For target season *s* in league *ℓ*: train on every match in league *ℓ* with `date` strictly before *s* starts, predict every match of *s*. Eight target seasons × six leagues = **48 blocks**, each evaluated exactly once, no overlap, union exactly 16,733 matches.

| Target season | Blocks | Test matches | Note |
|---|---:|---:|---|
| 2017/18 | 6 | 2,132 | two blocks with 4 matches missing closing prices |
| 2018/19 | 6 | 2,132 | |
| 2019/20 | 6 | 1,957 | Ligue 1 ends at 279 matches, Eredivisie at 232 (both curtailed) |
| 2020/21 | 6 | 2,132 | closed-door season; see Appendix A1 |
| 2021/22 | 6 | 2,132 | |
| 2022/23 | 6 | 2,132 | |
| 2023/24 | 6 | 2,058 | Ligue 1 runs with 18 teams (306 matches) |
| 2024/25 | 6 | 2,058 | as above; one match missing shot columns |
| **Total** | **48** | **16,733** | 46 complete seasons, 2 curtailed |

Per-fold training samples run from **4,284** matches (the earliest block, `D1|2017/18`, whose history starts in 2003/04) to **7,980**; test blocks run from 232 to 380 matches. No random split is used anywhere, because a random split would let the model see the future of the same league-season it is being scored on — the leakage this design exists to prevent.

### 3.5 Leakage controls

Three separate guarantees, each enforced by code rather than by prose.

- **No market column in any feature set.** Asserted in the feature builder and again in `tests/test_leakage.py`, which also checks that no future-dated match enters a training window.
- **Result-dependent features advance in date order.** The state machine that builds Elo ratings and rolling goal windows is fitted on the training window and then advanced match by match through the test season, so match *i* sees results 1…*i*−1 and never its own outcome. This is a rolling-origin (prequential) protocol rather than a frozen one; §4.4.5 states the difference and what it is worth.
- **H3's two indicators read no results.** `is_promoted_*` comes from the season's team list and `matchday` from the fixture calendar. `tests/test_h3_features.py` shuffles post-match information and asserts the columns are element-wise unchanged.

### 3.6 Version and reproduction

The data layer is frozen as **`data-v1.0`** (11 November 2026): 132 files with SHA-256 checksums in `configs/raw_manifest.csv` (132 rows, zero mismatches), `data/raw/*.csv` marked `-text` in `.gitattributes` so that no checkout rewrites line endings and invalidates the checksums, and `appendix/run_all.*` rebuilding every artefact from the committed raw files with **no network access**. Eight pinned dependencies; `appendix/requirements.txt` has exactly eight lines and a test asserts it.

*Sources: `results/coverage_matrix.csv`, `configs/splits.json`, `configs/raw_manifest.csv`, `products/figures/fig_data_coverage.png`, `src/build_panel.py` (stages S0–S5), `tests/test_leakage.py`, `tests/test_h3_features.py`, `tests/test_read_raw.py`.*
