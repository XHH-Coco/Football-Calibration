# configs/ — 必须入库的小型契约文件

本目录放**体积小、且全组必须完全一致的「定义 / 清单 / 映射」**，与原始数据分离，便于 review 与 diff。

> 注：`data/raw/` 的 132 个原始 CSV 自 2026-11-07 起**已入库**（约 14 MB，clone 即用），`data/` 其余子目录仍不入库。原始 CSV 只放 `data/raw/`，契约文件仍放本目录，两者不混放。

| 文件 | 内容 | 产出者 | 冻结时点 |
|---|---|---|---|
| `splits.json` | 48 个 `(联赛, 赛季)` 块的 train / test 边界、`n_train`、`n_test` | M1 | **11/09 接口冻结**（11/10 随 `data-v1.0` 标签复核） |
| `team_alias.csv` | 队名同义写法映射（`Man United` / `Manchester Utd` 等），人工维护 | **M1（M4 会签）** | 随用随改，改动走 PR |
| `feature_whitelist_b5a.csv` | **B5a 专用**的信息集白名单，四列 `feature / source / allowed / sample_weight_rule`；是 B4↔B5a「特征与样本权重都锁死」的受控比较证据。文件名以本行为准，与 README §2.1 结构树、分工方案 v1.3 T4.5 / §5.2、M4 分工卡一致（旧稿里的 `feature_whitelist.csv` 作废） | M4 产出、M3 逐条会签 | 11/09 接口冻结（信息集清单）；11/13 M3 签字定稿 |
| `raw_manifest.csv` | 132 个原始 CSV 的 URL / 字节数 / SHA256 / 下载时间 | M1 | 下载完成即冻结 |

## 规则

1. 只放 **KB 级、纯文本、可 diff** 的文件；`panel.parquet` 等可再生的大文件放 `data/processed/`，`data/raw/` 只放 132 个原始 CSV 快照（已入库，不放契约）。
   **`data/processed/panel.parquet` 一律不入库**（`.gitignore` 全局 `*.parquet` + `/data/processed/*`，不要为此放行）：11/08 的交付方式是**全组各自运行 `src/build_panel.py` 一键重跑生成**，契约是「同一脚本 → 同一张表」，而不是「传同一个二进制」；群里发的应急副本仅供救急，不作权威版本。T1.7 的干净环境复现同样以脚本重跑为准（见根目录 README §3.6）。
2. `raw_manifest.csv` 记录 132 个 CSV 的 URL / 字节数 / SHA256，是数据快照的**校验凭据**，**不要静默更新**；Git 本身保证 clone 到同一份字节，manifest 用于发现换行符被改写、文件被误覆盖等异常（详见 README §3.4）。变更须走 PR 并写明原因。
3. 判定规则（**全项目唯一等价边际 ±0.02 nats**、三种去抽水方法、评估窗口、H4 的 25% 门槛）若要写成配置，也放本目录，并在根目录 README §2.1 结构树里补一行。
4. 本目录新增/删除文件，按根目录 README §2.4 同步更新结构树与职责表。
5. **键与日期格式是全组契约**（`data_interface.md` §1.0）：`season` 一律 `YYYY/YY`、`date` 一律 ISO `YYYY-MM-DD`、`match_id = league|season|date|home|away`。`splits.json` 的 `test_start` / `test_end` 同用 ISO；队名以本目录 `team_alias.csv` 归一后的 `canonical_name` 为准。数据变更日志放 `docs/plans/CHANGELOG_data.md`，不放本目录。
