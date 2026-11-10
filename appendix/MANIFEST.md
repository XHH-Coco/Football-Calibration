# 源码附录 · 复现清单 MANIFEST

> 版本 **v1.1 · 2026-11-11**（M1 / T1.7 / S5 + M2 复现）· 维护人 M1（M2 段落 M2）
> 对应 `docs/plans/08_小组分工实施方案_v1.3.md` §3.1 T1.7 / §3.2、根目录 README §5.3
> **一句话**：`data/raw/` 的 132 个 CSV 已随 Git 入库，复现包从这里起跑，全程不联网；
> v1.1 起 `run_all.sh` / `run_all.ps1` 追加 M2 一步（`python -m src.eval.run_m2`），
> 把 B6/B6r、`table_main.csv`、`market_gap.csv`、`fig07` 与 H1–H4 判定一并重建。

---

## 1. 数据来源与起点

| 项 | 口径 |
|---|---|
| 数据源 | `https://www.football-data.co.uk/mmz4281/{season}/{div}.csv` |
| 快照 | 22 季（0304–2425）× 6 联赛（E0 / SP1 / I1 / D1 / F1 / N1）= **132 个 CSV / 14,341,191 B** |
| 入库状态 | **已入库**（`.gitignore` 放开 `data/raw/`，`.gitattributes` 的 `data/raw/*.csv -text` 防止 CRLF 被转换），clone 即用 |
| 校验凭据 | `configs/raw_manifest.csv`（132 行，逐行 url / 字节数 / SHA256 / 下载时间，实测 0 失配） |
| 缺失审计 | `data/missing.csv` 仅表头（0 缺失） |
| **红线** | **复现包禁止联网重下**。源站改版会让数字无声漂移；重建 / 补漏才按 README §3.2 走 PR 并同步 manifest |

---

## 2. 冷启动复现（30 分钟内）

**Python 3.14.x**（本机 conda `DSC5001_Project` = 3.14.10）。8 个直接依赖锁死在
`appendix/requirements.txt`，与 README §5.2 逐行一致；间接依赖全量快照见
`appendix/pip_freeze_2026-11-10.txt`（仅备查，冷启动**不**用它安装）。

```bash
# Windows（Git Bash）
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r appendix/requirements.txt
bash appendix/run_all.sh                      # 或 bash appendix/run_all.sh --check 先看计划

# Windows（PowerShell）
powershell -ExecutionPolicy Bypass -File appendix/run_all.ps1

# Linux / macOS
python -m venv .venv && .venv/bin/python -m pip install -r appendix/requirements.txt
bash appendix/run_all.sh
```

**Windows 坑**：venv 解释器是 `.venv/Scripts/python.exe`，不是 `bin/python`；
两个脚本都不写死 `source .venv/bin/activate` / `Activate.ps1`，而是按
`$PYTHON` → Windows venv → POSIX venv → PATH 的顺序挑显式路径。

**跑完长这样**：`data/processed/panel.parquet`（46,507 × 22，**不入库**）重新生成；
`configs/splits.json`（48 块，入库契约）字节不变；覆盖率 CSV / PNG 重新生成；
M2 的 `preds_B6.csv` / `preds_B6r.csv`（各 16,728 行）、`table_main.csv`（9 行）、
`market_gap.csv`、`fig07_market_gap.png` 与 `m2_decisions_<date>.txt` 一并重建；
`pytest -q tests/` 全绿；S3 / S4 / S5 各自自检 12/12 PASS。
整体 stdout 在 `results/logs/repro_run.log`（`*.log` 已被忽略，不污染仓库）。

**本机实测**（2026-11-10，conda `DSC5001_Project` 解释器，
`PYTHON=D:/Miniconda3/envs/DSC5001_Project/python.exe bash appendix/run_all.sh`）：
从已入库 raw 起跑、未联网，见 `results/logs/s5_handover_2026-11-10.txt`。
干净 venv 的实测由 M2 在 G3 前按验收项 12 复核。

---

## 3. 数字 → 脚本 → 命令（验收项 14：抽 3 个数字可倒查）

| 数字 / 结论 | 出自哪个脚本 | 复现命令 |
|---|---|---|
| 132 个 CSV / 14,341,191 B | `configs/raw_manifest.csv`（T1.1） | `ls data/raw/*.csv \| wc -l`；SHA256 逐行校验见 README §3.4 |
| 46,518 − 11 空白行 = **46,507** 场 | `src/build_panel.py::read_raw()`（S1） | `python src/build_panel.py --stage s1 --log results/logs/s1_read_raw_2026-11-08.txt` |
| 775 长行 / 2,895 溢出格全空（非空即抛错） | 同上（r2 硬断言） | `pytest -q tests/test_read_raw.py` |
| **243** 原始队名 → **241** 归一后 / 仅 2 组真实改名 | `src/build_panel.py::build_team_alias()`（S2） | `python src/build_panel.py --build-alias`；判定清单见 `configs/README.md` |
| `y` 分布 21,194 / 11,824 / 13,489；ISO `2003-08-01 → 2025-05-25` | `src/build_panel.py::clean_panel()`（S2） | `python src/build_panel.py --stage s2 --log results/logs/s2_clean_2026-11-10.txt` |
| **46,507 行 × 22 列 / 1,028,001 B**，`match_id` 唯一 | `src/build_panel.py::build_panel()` / `write_panel()`（S3） | `python src/build_panel.py --stage s3 --log results/logs/s3_panel_2026-11-10.txt` |
| 132 块场次规则（满额 `n×(n−1)`）；2 个疫情腰斩例外 | `tests/test_panel_counts.py`（T1.3-a） | `pytest -q tests/test_panel_counts.py` |
| **48 块 / 16,733 场 / `n_train` min 4,284 / `n_new_team` max 2** | `src/splits.py::make_splits()`（S4） | `python src/build_panel.py --stage s4 --log results/logs/s4_splits_2026-11-10.txt` |
| train 严格早于、test 0 漏 0 重、五条泄漏断言 | `tests/test_leakage.py`（T1.6） | `pytest -q tests/test_leakage.py` |
| H3 三列打乱赛后列后逐元素不变 | `tests/test_h3_features.py`（T1.9） | `pytest -q tests/test_h3_features.py` |
| 收盘赔率自 **2012/13**；评估窗 **45/48** 块满格 | `src/coverage.py::build_coverage_matrix()`（S5 / T1.4） | `python src/coverage.py --log results/logs/s5_coverage_2026-11-10.txt` |
| **5 场**赔率缺失（`1718_SP1` 1 / `1718_N1` 3 / `1819_D1` 1）→ B6/B6r **16,728** | `results/coverage_matrix.csv` + `tests/test_leakage.py::test_05` | `pytest -q tests/test_leakage.py::test_05_odds_missing_exactly_five` |
| `MaxCH` 自 **2019/20**；N1 射门 4 列自 **2017/18** | `results/coverage_matrix.csv`、`products/figures/fig_data_coverage.png` | `python src/coverage.py`；逐格见 CSV |
| **1 场**评估窗缺射门（`2425_D1` Union Berlin–Bochum） | `src/coverage.py` / `tests/test_coverage.py::test_07` | `pytest -q tests/test_coverage.py::test_07_eval_window_shot_gap_is_exactly_one_match` |
| 自检 12/12（S3 / S4 / S5 各自）+ 全量 pytest 全绿 | `s3_selfcheck()` / `s4_selfcheck()` / `coverage_selfcheck()` | `pytest -q tests/`；逐项见 `results/logs/s*.txt` |
| **M2**：B6 有效 n = 16,728（比例法，三法互差 >0.05 的场次 = 0） | `src/eval/devig.py::build_b6()` | `python -m src.eval.run_m2`；`pytest -q tests/test_devig.py` |
| **M2**：B6r 16,728（train-only 两参数重校准，每折 `n_fit` 记日志） | `src/eval/recalibrate.py::run_b6r()` | `python -m src.eval.run_m2`；`results/logs/b6r_n_fit.csv` |
| **M2**：主推断表 9 行 + deff；B3 0.9986 / B4 0.9939 / B6 0.9585 / B6r 0.9585 | `src/eval/table_main.py::build_table_main()` | `python -m src.eval.run_m2`；`pytest -q tests/test_table_main.py` |
| **M2**：H1 比例法斜率 1.086（90% CI 1.047–1.124，under-dispersed 支持） | `src/eval/calibration.py::h1_pipeline()` | `python -m src.eval.run_m2`；`pytest -q tests/test_calibration.py` |
| **M2**：H2 B4−B6 = 0.0353 nats（95% CI 0.030–0.041，判据 a/b 均支持） | `src/eval/market_gap.py` + `src/eval/bootstrap.py` | `python -m src.eval.run_m2`；`results/market_gap.csv` |
| **M2**：H3 只作描述（early 系数 −0.0108，与假设方向相反） | `src/eval/localisation.py::h3_coefficients()` | `python -m src.eval.run_m2`；`pytest -q tests/test_localisation.py` |
| **M2**：H4 重校准相对变化 0.0017（90% 上界 < 25%，信息而非校准） | `src/eval/recalibrate.py` + `src/eval/decisions.py` | `python -m src.eval.run_m2`；`pytest -q tests/test_recalibrate.py` |
| **M2**：H1–H4/C1 判定规则在代码里（阈值 `EQUIV_MARGIN=0.02` 等） | `src/eval/decisions.py` | `pytest -q tests/test_decisions.py` |

---

## 4. 产物与入库边界

| 产物 | 入库 | 说明 |
|---|---|---|
| `data/raw/*.csv`、`configs/raw_manifest.csv` | ✅ | 原始输入 + 校验和，clone 即用 |
| `configs/team_alias.csv`、`configs/splits.json` | ✅ | KB 级纯文本契约，必须全组逐字一致 |
| `results/coverage_matrix.csv`、`products/figures/fig_data_coverage.png` | ✅ | 报告数据页引用 |
| `results/logs/s*.txt` | ✅ | 自检凭据（*.txt 未被忽略） |
| `appendix/`（本包）、`src/`、`tests/` | ✅ | 源码与复现入口 |
| `data/processed/panel.parquet` | ❌ | **46,507 × 22 / 1,028,001 B，可再生**；契约是「同一脚本 → 同一张表」，不是「传同一个二进制」 |
| `results/logs/repro_run.log` | ❌ | `*.log` 已被忽略 |

---

## 5. 已知例外与红线（照抄进报告数据页）

1. **B6 / B6r 有效 n = 16,728**，不是 16,733：评估窗 5 场缺 `PSCH/PSCD/PSCA`，
   按交集 drop、不回填。所有 Δ 用 `match_id` 内连接后逐场相减。
2. **评估窗射门列有 1 场缺**（`2425_D1`，2024-12-14，Union Berlin–Bochum，
   缺 `HTHG/HTAG/HS/AS/HST/AST` 六列；比分与收盘赔率齐全）。
   覆盖率 = 16,732/16,733 = 0.999940。**任何以射门列为特征的 arm 须显式处理 NaN**。
3. `PSH/PSD/PSA`（开盘）与 `B365*`（别家非收盘）**不是市场基准**，基准恒为
   `PSCH/PSCD/PSCA`；`Max*` 只用于覆盖率矩阵，不进 panel、不入模。
4. **簇 bootstrap 的重采样单位是 48 块，不是 16,733 场**；每个区间附 `deff`。
5. `panel` 的 `date` 是 ISO **字符串**（不是 `datetime64`）；`match_id` 是
   `league|season|date|home|away`，各 `preds_*.csv` 与之逐字符一致。
   落盘概率列顺序恒为 `p_home, p_draw, p_away`（标签重排，见 `data_interface.md` §1.1）。
6. **seed 只提供默认值**：`appendix/seed.py::DEFAULT_SEED = 20261110`，
   bootstrap / HGB 仍须在各自调用点显式传 `random_state`。
7. 数据冻结后（`data-v1.0` tag，T1.10）任何 raw / panel / splits 变更都写
   `docs/plans/CHANGELOG_data.md`，含日期、原因、影响范围、重跑命令。

---

## 6. 依赖

`appendix/requirements.txt` **恒 8 行**（pandas 3.1.1 / numpy 2.5.4 /
pyarrow 26.0.1 / pytest 9.2.0 / matplotlib 3.11.2 / scipy 1.18.1 /
scikit-learn 1.9.1 / statsmodels 0.15.0），与 README §5.2 第三方包行逐行一致。
**B5a / B5b 用 sklearn 内置 `HistGradientBoostingClassifier`，零新增依赖。**
`appendix/pip_freeze_2026-11-10.txt` 是本机 Windows / conda 环境的 30 行间接依赖
快照，仅供备查；冷启动安装一律以 `requirements.txt` 为准。
