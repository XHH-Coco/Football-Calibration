# 目录结构变更记录

> 根目录 README §2.4 规定：**谁改目录，谁在同一个 PR 里改 README，并在此追加一行。**

| 日期 | README 版本 | 变更内容 | 是否影响 .gitignore | 操作人 | PR |
|---|---|---|---|---|---|
| 2026-11-07 | v1.0 | 首版：建立 `data/` `configs/` `src/` `tests/` `results/` `analysis/` `docs/` `products/` `appendix/` 九类目录；归档 Proposal 与分工方案；新增 docs 模板与字段参考 | 是（新增根目录 `.gitignore` v1.0） | — | 初始提交 |
| 2026-11-07 | v1.1 | 新增文件（未新增目录）：`configs/raw_manifest.csv`（数据冻结凭据）、`docs/data_profile_v1.0.html`（数据集剖析报告）；同步 README §2.1 / §2.2 / §3.5 / §7。分析脚本置于已忽略的 `scripts/`，不改变忽略规则 | 否 | — | 689b7fe |
| 2026-11-07 | v1.2 | 新增文件（未新增目录）：`docs/data_profile_v1.1.html`（扩展口径 132 文件全量剖析）；`configs/raw_manifest.csv` 由 54 行扩为 132 行；`data/raw/` 按 T1.1 补齐至 132 个 CSV（数据不入库）。同步 README §2.1 / §3.1 / §3.2 / §3.3 / §3.5 / §7；`data_profile_v1.0.html` 加版本提示条。新增 `scripts/build_report_full.py`，仍置于已忽略的 `scripts/`，不改变忽略规则 | 否 | — | 689b7fe |
| 2026-11-07 | v1.3 | **新增目录** `docs/plans/roles/`（方案类子目录，与 `docs/templates`、`docs/references` 同级）。新增文件：`docs/plans/08_小组分工实施方案_v1.2.md`（当前权威；v1.1 降为历史版本）、`docs/plans/09_分工方案评审_v1.0.md`、`docs/plans/roles/README.md` 及 M1–M5 五份分工卡。同步 README §2.1 / §2.2 / §7 与顶部版本号。目录职责不变（`docs/` 仍只放过程性文字，图/表/报告/幻灯/录像仍在 `products/`） | 否 | — | 689b7fe |
| 2026-11-07 | v1.4 | **移出文件（未删除）**：`docs/plans/08_小组分工实施方案_v1.1.md` → 项目根 `old_docs/`（仓库外，不入库，保留原文件名）。`docs/plans/` 自此只保留每份文档的最新版本，被取代的版本一律归档至 `old_docs/`。同步 README §2.1 / §2.2 说明与 §3.5 | 否（`old_docs/` 位于仓库之外，无需忽略规则） | — | 689b7fe |
| 2026-11-07 | v1.5 | **移出文件（未删除）**：`docs/data_profile_v1.0.html`（主口径 54 文件剖析）→ 项目根 `old_docs/`；`docs/` 剖析报告只剩 `data_profile_v1.1.html`。版本归档规则由 `docs/plans/` 扩展到整个 `docs/`（含 HTML 类成品）。同步 README §2.1 / §2.2 / §3.5 / §7 | 否（`old_docs/` 位于仓库之外） | — | 689b7fe |
| 2026-11-07 | v1.6 | **忽略策略变更（非目录变更）**：`data/raw/` 的 132 个原始 CSV（14,341,191 字节）由「不入库」改为「入库」，组员 clone 即用、无需各自下载；删除 `data/raw/.gitkeep`；新增根目录 `.gitattributes`（`data/raw/*.csv -text`，防止 CRLF 被转换导致 132 行 SHA256 失配）。同步 README §0 / §2.1 / §2.2 / §2.3 / §3 全节 / §4.1 / §7，以及 `configs/README.md`、M1 分工卡、本方案 §5.2、字段速查 | 是（`.gitignore` 升 v1.1） | — | 689b7fe |
| 2026-11-07 | v1.7 | **运行时与依赖口径变更（非目录变更）**：Python 由固定 `3.14.7` 放宽为 `3.14.x`（3.14.7 / 3.14.10 均可），登记本机 conda 环境 `DSC5001_Project`；§5.2 登记 8 个直接依赖精确版本并同步 `appendix/requirements.txt`；明确 **T1.1 已完成、无需 `src/download.py`**，复现包从已入库 `data/raw/` 起跑、不联网重下（重建入口 §3.2）；同步 M1 分工卡与分工方案 v1.2 §3.1 的 T1.1 行 | 否 | M1 | 689b7fe |
| 2026-11-07 | v1.8 | **口径统一（非目录变更）**：`configs/README.md` 与 README §2.2 的 `feature_whitelist.csv` 统一为 **`feature_whitelist_b5a.csv`**（与 README §2.1 结构树、分工方案 v1.2 T4.5 / §5.2、M4 分工卡一致），并写明 `feature / source / allowed / sample_weight_rule` 四列与「M4 产出、M3 逐条会签」；`splits.json` 冻结时点由 11/10 `data-v1.0` 改为 **11/09 接口冻结**（11/10 标签仅作复核），与 `roles/README.md`、M1 分工卡一致。同步 README 顶部版本与 §7 | 否 | M1 | 689b7fe |
| 2026-11-07 | v1.9 | **忽略策略 + 交付口径（影响 .gitignore）**：新建 `data/missing.csv`（仅表头，T1.1 的 0 缺失留痕），`.gitignore` 升 **v1.2** 用 `!/data/missing.csv` 放行；README 新增 **§3.6 可再生派生物的交付约定**（`panel.parquet` 明确不入库、11/08 靠 `src/build_panel.py` 一键重跑；`y` 编码 `H/D/A→0/1/2` 与 `p_home` 列序预置为断言），同步 §3.2 / §4.1 / §7 / §2.2 说明；`configs/README.md` 规则 1、M1–M4 分工卡、`data_interface.md` §1.1 同步交付与标签口径；`09_评审 §6` 把已闭环的市场基准列改为已定；`08_分工方案_v1.2` 新增 **§4.2-a 未决事项登记表**（U1/U2 搁置、U3 命名另案）并同步 `roles/README.md`、M5 分工卡 | 是（`.gitignore` 升 v1.2） | M1 | 689b7fe |

## 追加模板

```
| YYYY-MM-DD | vX.Y | 新增/删除/重命名了哪个目录、为什么 | 是/否 | M? | #PR |
```
