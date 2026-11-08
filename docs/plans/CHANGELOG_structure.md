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
| 2026-11-08 | **v2.0** | **假设体系与执行蓝本统一（文件重命名 + 新增，非目录变更）**：新增 `docs/plans/Team-32-Proposal_v3.0.md`（唯一执行蓝本，英文正本 + 中文 Revision notes + B↔M 映射）；`docs/plans/08_小组分工实施方案_v1.2.md` → **`v1.3.md`**，旧版按归档规则移出仓库至项目根 `old_docs/`；五份 M 分工卡升 v1.1、`data_interface.md` 升 v1.2、`configs/README.md` 与 `roles/README.md` 同步；`09_评审 §6` 决策项全部标记闭环；`docs/templates/figure_list_template.md` / `results_table_template.md` / `report_section_template.md` 与 `docs/references/football_data_fields.md` 同步到 B0–B6 + B6r / H1–H4 口径（9 arm 表头 + deff 列、8 张图清单）。同步 README §1 / §2.1 / §2.2 / §3.5 / §5.2 / §6 / §7 与顶部版本号。**忽略规则不变**，`.gitignore` 仍为 v1.2 | 否 | M1 | 979be61 |
| 2026-11-08 | **v2.1** | **D1 定案 + 两处契约补丁（非目录变更，`requirements.txt` 与 `.gitignore` 均不变）**：B5a/B5b 改用 scikit-learn 1.9.1 内置 `HistGradientBoostingClassifier`，全仓清除 LightGBM 口径；`data_interface.md` 升 **v1.3**（内部标签重排断言、B6r 拟合样本边界）；分工方案 `v1.3-r2`（同日修订，不重命名文件）、M2/M4 卡升 v1.2、Proposal v3.0 补实现注记、`results_table_template.md` / `roles/README.md` 同步；README 升 **v2.1** 并同步 §0 / §1 / §2.1 / §3.5 / §5.2 / §7 | 否 | M1 | feff4be |
| 2026-11-08 | **v2.2** | **M1 开工前全量复核（非目录变更，`requirements.txt` 与 `.gitignore` 均不变）**：① 数据事实订正——评估窗三列收盘赔率缺 5 场（3 块），B6 / B6r 有效 n = **16,728**；② `data_interface.md` 升 **v1.4**（新增 §1.0 `match_id` / ISO 日期 / `season` 契约，preds schema 增 `match_id` 列）；③ M1 分工卡升 **v1.2**（T1.2-a 稳健读取器 + 参考实现、T1.10 数据冻结、`n_train ≥ 4,284`、Windows 复现包）；④ 分工方案 `v1.3-r3`、README 升 **v2.2**（§2.1 结构树新增 `docs/plans/CHANGELOG_data.md`、§3.3 补 4 个读取实测坑）、`football_data_fields.md` v1.3、`configs/README.md`、`roles/README.md` v1.3、结果表模板、M2 卡、`09_评审` 加数值订正警示 | 否 | M1 | 668d954 |
| 2026-11-08 | **v2.3** | **S0 交付状态登记（非目录变更，`requirements.txt` / `.gitignore` 均不变）**：新增入库产物 `results/logs/s0_selfcheck_2026-11-08.txt`（M1 环境与快照自检 7 项 PASS 明细 + 依赖版本快照）；README 升 **v2.3**（§0 自检提示、§2.1 `results/logs/` 注释、§3.4 S0 实测结论、§5.1 默认解释器提醒、§7 修订记录）；M1 分工卡升 **v1.3**（新增 §3.1 S0 交付记录、§5 产物表补自检记录、§6 验收项 1 标注已通过、§7 补坑 8）；`roles/README.md` 升 **v1.4**（§1 交付状态速览） | 否 | M1 | 待回填 |


## 追加模板

```
| YYYY-MM-DD | vX.Y | 新增/删除/重命名了哪个目录、为什么 | 是/否 | M? | #PR |
```
