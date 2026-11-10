# 数据变更日志 · CHANGELOG_data

> 版本 **v1.0 · 2026-11-10**（M1 / T1.10 / S5）· 冻结标签 **`data-v1.0`**
> 权威口径：`docs/plans/data_interface.md` v1.7、README §3.6、M1 分工卡 §3.6。

**维护规则（冻结后强制）**：此后任何 `data/raw/` 快照、`panel.parquet` 生成逻辑、
`configs/splits.json` / `configs/team_alias.csv` 契约的变更，都必须在下面
「变更记录」写一行，写清 **日期 / 原因 / 影响范围 / 重跑命令 / commit**，
并说明评估窗 16,733 场与 B6 有效 16,728 场是否改变。**冻结后禁止联网重下**：
源站改版会让数字无声漂移；确需重建 / 补漏，走 PR 并同步
`configs/raw_manifest.csv` 的 SHA256（README §3.2 / §3.4）。

---

## 冻结基线（data-v1.0）

| 项 | 冻结值 |
|---|---|
| 冻结时点 | 2026-11-10（S0–S5 数据底座全部交付后） |
| 冻结 commit | `aaa227a`（S5 主提交，数据内容在此冻结）；`data-v1.0` tag 落在随后**仅回填 commit id** 的登记提交上，两者 tree 差异仅为这两个 id 字段，见 `CHANGELOG_structure.md` v2.9 行 |
| 冻结 tag | `data-v1.0` |
| 原始快照 | `data/raw/` **132 个 CSV / 14,341,191 B**（0304–2425 × 6 联赛），SHA256 逐行 0 失配；`.gitattributes` 的 `-text` 不改动 |
| 队名契约 | `configs/team_alias.csv` 243 行 → 归一后 241 队名，仅 2 组真实改名（**入库**） |
| 建模总表 | `data/processed/panel.parquet` **46,507 行 × 22 列 / 1,028,001 B**，`match_id` 唯一（**不入库**，全组各自 `--stage s3` 生成） |
| 切分契约 | `configs/splits.json` **48 块 / 14,946 B**，`schema_version=1.0`，UTF-8 / LF、无时间戳、重跑字节相同（**入库**） |
| 评估窗 | 1718–2425 × 6 联赛 = **48 块 / 16,733 场**；`n_train` min **4,284**；`n_new_team` ≤ 3（实测最大 2） |
| 市场基准 | `PSCH/PSCD/PSCA`（Pinnacle 收盘）；评估窗缺 **5 场**（`1718_SP1` 1 / `1718_N1` 3 / `1819_D1` 1），drop 不回填 → **B6 / B6r 有效 n = 16,728** |
| 覆盖率 | `results/coverage_matrix.csv`（132 行 × 18 列）+ `products/figures/fig_data_coverage.png`；`PSCH` 自 2012/13、`MaxCH` 自 2019/20、N1 射门 4 列自 2017/18 |
| 已知例外 | `2425_D1` 的 Union Berlin–Bochum（2024-12-14）缺 6 个射门/半场列，比分与收盘赔率齐全；评估窗射门覆盖率 **0.999940** |
| 自检 | S0 **7/7**、S1 **8/8**、S2 **13/13**、S3 **12/12**、S4 **12/12**、S5 **12/12**；全量 `pytest -q tests/` 全绿 |
| 一键重跑 | `bash appendix/run_all.sh`（Git Bash）／`powershell -File appendix/run_all.ps1`；从已入库 raw 起跑、**不联网** |

---

## 变更记录

| 日期 | 原因 | 影响范围 | 重跑命令 | commit |
|---|---|---|---|---|
| 2026-11-10 | **首次冻结**：S0–S5 数据底座全部交付（稳健读取器 → 字段统一 → 22 列总表 → 48 块切分 → 覆盖率 / 泄漏 / 复现 / H3 收尾） | 132 raw CSV（未改动）、`panel` 生成逻辑、`team_alias.csv`、`splits.json`、覆盖率产物；评估窗 16,733 / B6 16,728 **均不变** | `bash appendix/run_all.sh`；`pytest -q tests/` | `aaa227a` |

### 后续登记模板

| 日期 | 原因 | 影响范围 | 重跑命令 | commit |
|---|---|---|---|---|
| `YYYY-MM-DD` | 为什么改（源站改版 / 修 bug / 扩窗 / 换基准） | 哪些文件、`n_test` / `n_train` / B6 有效 n 是否变、是否需要全组重新生成 | `bash appendix/run_all.sh` 及必要的额外命令 | `<short sha>` |

> **判定规则**：只要「重跑命令」跑完后 `configs/splits.json` 的 sha256 与冻结基线不同，
> 或 `panel.parquet` 的 46,507 行 / `match_id` 集合不同，就必须在原因里写明
> **影响哪几块、哪些结论要重算**，并通知 M2 主签 + M3/M4 会签，不能只改数字不通知。
