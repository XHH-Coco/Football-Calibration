# configs/ — 必须入库的小型契约文件

本目录放**体积小、且全组必须完全一致的「定义 / 清单 / 映射」**，与原始数据分离，便于 review 与 diff。

> 注：`data/raw/` 的 132 个原始 CSV 自 2026-11-07 起**已入库**（约 14 MB，clone 即用），`data/` 其余子目录仍不入库。原始 CSV 只放 `data/raw/`，契约文件仍放本目录，两者不混放。

| 文件 | 内容 | 产出者 | 冻结时点 |
|---|---|---|---|
| `splits.json` | 48 个 `(联赛, 赛季)` 块的 train / test 边界、`n_train`、`n_test`、`n_new_team`；**S4 已于 2026-11-10 交付（48 块 / 14,946 B）**，判定说明见下方专节 | M1 | **11/09 接口冻结**（11/10 随 `data-v1.0` 标签复核）；✅ 已交付（实际 11/10，比冻结时点晚 1 天）；**M2 主签 + M3/M4 会签待办** |
| `team_alias.csv` | 队名归一映射（`raw_name,canonical_name,league,first_seen_season`），**S2 已于 2026-11-10 产出 243 行**；由 `python src/build_panel.py --build-alias` 从 raw 一键重生成，判定依据见下方专节 | **M1（M4 会签）** | ✅ 已交付（2026-11-10，比 §3 的 11/08 时点晚 2 天）；**M4 会签待办**；后续改动走 PR |
| `feature_whitelist_b5a.csv` | **B5a 专用**的信息集白名单，四列 `feature / source / allowed / sample_weight_rule`；是 B4↔B5a「特征与样本权重都锁死」的受控比较证据。文件名以本行为准，与 README §2.1 结构树、分工方案 v1.3 T4.5 / §5.2、M4 分工卡一致（旧稿里的 `feature_whitelist.csv` 作废） | M4 产出、M3 逐条会签 | 11/09 接口冻结（信息集清单）；11/13 M3 签字定稿 |
| `raw_manifest.csv` | 132 个原始 CSV 的 URL / 字节数 / SHA256 / 下载时间 | M1 | 下载完成即冻结 |

## `team_alias.csv` 判定说明（S2 / 2026-11-10 全库实测）

> **生成方式**：`python src/build_panel.py --build-alias`（项目环境 `DSC5001_Project`）。
> 脚本从 132 个 raw CSV 收集全部 `(league, raw_name)`，逐行写 `first_seen_season`；
> `canonical_name` 默认等于原名，只有源码里 `CANONICAL_MERGES` 的**人工判定**会改指向。
> `src/build_panel.py::s2_selfcheck()` 会断言「磁盘上的表 == 脚本重生成的表」，防止手工漂移。

| 实测项 | 结果 |
|---|---|
| 原始队名 | **243** 个（D1 38 / E0 44 / F1 41 / I1 47 / N1 32 / SP1 41）；跨联赛同名 0 |
| 归一后 | **241** 个；每联赛每季参赛队数仍为 18 或 20，与归一前一致 |
| 真实改名 | **仅 2 组**，都在荷甲 N1、且赛季完全不重叠：`Roda JC`(2003/04–2009/10) → `Roda`(2010/11–2017/18)；`Sparta`(2005/06–2009/10) → `Sparta Rotterdam`(2016/17–2024/25) |
| 归一的实际收益 | 不归一会把改名队误判成升班马：`is_promoted_home=1` 从 **6,367 → 6,350** 场（-17）；M4 的 Elo 也不再因同一队被拆成两队而从 1500 重启 |
| 覆盖断言 | M1 卡 §6 验收项 9：`unique(home) ∪ unique(away)` 与 alias 差集为 0；`load_team_alias()` 遇到未登记队名**直接抛 ValueError**，不静默留白 |

**明确不合并的相似队名**（人工判读，勿用模糊匹配自动并）：`Ajaccio` vs `Ajaccio GFCO`（同城两支不同俱乐部）、`Man City` vs `Man United`、`Bayern Munich` vs `Munich 1860`、`Den Bosch` vs `Den Haag`、`Ath Madrid` vs `Real Madrid`、`Le Mans` vs `Lens`、`Augsburg` vs `Duisburg`。原始数据里 `Man United` 这类写法**跨季是一致的**，不存在旧稿举例的 `Manchester Utd` 变体。

**新增映射的三条硬规则**：① 两个名字的赛季范围不重叠且有确切证据是同一队；② `canonical_name` 必须是同一联赛中**已经出现过**的原始名（禁止引入「幽灵队名」，脚本会断言）；③ 改 `src/build_panel.py::CANONICAL_MERGES` 后重跑 `--build-alias`、S2 自检与全量 pytest，并走 PR + M4 会签。

## `splits.json` 判定说明（S4 / 2026-11-10 全库实测）

> **生成方式**：`python src/build_panel.py --stage s4`（等价 `python src/splits.py`）。脚本从 132 个 raw 重建 22 列 panel，按规则切 48 块，写 JSON 再读回逐项比对。`tests/test_splits.py::test_on_disk_contract_matches_regenerated` 断言「磁盘契约 == 脚本重生成」，**手工改一行就红**。

| 项 | 约定 / 实测 |
|---|---|
| 顶层 | `schema_version=1.0`、`rule`（test / train / equivalence_check / cluster / n_new_team）、`n_blocks=48`、`n_test_total=16733`、`n_train_min=4284`、`blocks` |
| 每块字段 | `block_id, league, season, test_start, test_end, train_start, train_end, n_train, n_test, n_new_team`；`block_id = league\|season` |
| test | 该联赛该季全部比赛；48 块两两不重叠、并集恰 **16,733 场（0 漏 0 重）** |
| train | **同联赛 + `date < test_start`**（ISO 字符串比较、严格更早、跨季累积）；与「`season` 严格更早」逐块等价已写成断言；train 中目标季及之后 **0 场**、`train_end < test_start` 全成立 |
| `n_train` | 最小 **4,284**（`D1 2017/18` / `N1 2017/18` = 14 季 × 306 场），随季递增；逐联赛范围见 `results/logs/s4_splits_2026-11-10.txt` |
| `n_new_team` | **历史累积 train** 口径（test 里从未在 train 出现过的队数），实测最大 **2**、20 块非零；与归一后 `is_promoted_*`（上一季名单）**不是同一个数** |
| 序列化 | UTF-8 / LF、缩进 2、固定字段顺序、**无时间戳**；重跑两次 sha256 相同，Git diff 无噪音 |
| 入库 | ✅ 本文件入库、随 Git 分发；`data/processed/panel.parquet` 仍不入库（README §3.6） |

**消费方式**：M2 harness 统一调 `src.splits.resolve_split(panel, block)` 取 `(train_df, test_df)`；切分由规则决定，JSON 里的 `n_train` / `n_test` 只用于校验，手工把 `test_start` 往后挪会当场抛 `ValueError`。簇 bootstrap 的重采样单位是**这 48 个块**，绝不是 16,733 场比赛。

**改契约的三条硬规则**：① 改 `src/splits.py` 的切分规则后重跑 `--stage s4`、S4 自检与全量 pytest；② 走 PR + **M2 主签 / M3·M4 会签**，PR 描述写明受影响的模型与已产出的预测文件；③ 在 `docs/plans/CHANGELOG_data.md` 记日期、原因、影响范围与重跑命令。11/10 的 `data-v1.0` 只作复核，不替代 11/09 签字。

## 规则

1. 只放 **KB 级、纯文本、可 diff** 的文件；`panel.parquet` 等可再生的大文件放 `data/processed/`，`data/raw/` 只放 132 个原始 CSV 快照（已入库，不放契约）。
   **`data/processed/panel.parquet` 一律不入库**（`.gitignore` 全局 `*.parquet` + `/data/processed/*`，不要为此放行）：**S3 已于 2026-11-10 交付**（46,507 行 × 22 列 / 1,028,001 B，12/12 PASS），交付方式是**全组各自运行 `python src/build_panel.py --stage s3` 一键重跑生成**，契约是「同一脚本 → 同一张表」，而不是「传同一个二进制」；群里发的应急副本仅供救急，不作权威版本。T1.7 的干净环境复现同样以脚本重跑为准（见根目录 README §3.6）。
2. `raw_manifest.csv` 记录 132 个 CSV 的 URL / 字节数 / SHA256，是数据快照的**校验凭据**，**不要静默更新**；Git 本身保证 clone 到同一份字节，manifest 用于发现换行符被改写、文件被误覆盖等异常（详见 README §3.4）。变更须走 PR 并写明原因。
3. 判定规则（**全项目唯一等价边际 ±0.02 nats**、三种去抽水方法、评估窗口、H4 的 25% 门槛）若要写成配置，也放本目录，并在根目录 README §2.1 结构树里补一行。
4. 本目录新增/删除文件，按根目录 README §2.4 同步更新结构树与职责表。
5. **键与日期格式是全组契约**（`data_interface.md` §1.0）：`season` 一律 `YYYY/YY`、`date` 一律 ISO `YYYY-MM-DD`、`match_id = league|season|date|home|away`。`splits.json` 的 `test_start` / `test_end` 同用 ISO；队名以本目录 `team_alias.csv` 归一后的 `canonical_name` 为准。数据变更日志放 `docs/plans/CHANGELOG_data.md`，不放本目录。
