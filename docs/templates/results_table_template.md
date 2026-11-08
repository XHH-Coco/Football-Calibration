# 结果表模板（表头与主推断表完全对齐）

> 填写前先复制本文件到 `products/tables/`。表头**不许改结构**，否则报告取数要重做。
> 所有数字必须来自 `results/` 的机器产出（主推断表 `results/table_main.csv`，**9 行 + `deff` 列**），禁止手工敲入。
> 模型标识一律 `B0`–`B6` + `B6r`；`M1`–`M5` 只指成员，提交版 Proposal 的 `M0`–`M4` / `MK` / `MK*` 映射见 `Team-32-Proposal_v3.0.md` §4 末。

## 主推断表：模型 × 指标

| model | log_loss | LL_90CI_low | LL_90CI_high | deff | Brier | ECE | ΔLL_vs_B4 | ΔLL_vs_B6 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| B0 | | | | | | | | | 先验基线（expanding 频率，实测 ≈ 1.0743） |
| B1 | | | | | | | | | Elo |
| B2 | | | | | | | | | 有序 logit（Elo 差 + 近期状态，门槛由数据估） |
| B3 | | | | | | | | | 独立 Poisson |
| B4 | | | | | | | 留空 | | Dixon–Coles，主炮；C1/C2 与 H2 的参照模型 |
| B5a | | | | | | | | | 同信息 sklearn HGB（锁特征 + `sample_weight`，零新增依赖） |
| B5b | | | | | | | | | 全特征 sklearn HGB（只换信息，权重与超参锁死） |
| B6 | | | | | | | | 留空 | 去抽水收盘市场（`PSCH/PSCD/PSCA`），天花板 |
| B6r | | | | | | | | | 重校准市场（两参数只在 train 段拟合），H4 唯一工具 |

> `deff = Var_cluster / Var_iid`，随每个区间落盘；B6 与 B6r 有效 n = 16,728（3 块共 5 场缺三列收盘赔率：`1718_SP1` 1 / `1718_N1` 3 / `1819_D1` 1，drop 不回填），其余臂 16,733。

## 去抽水稳健性表（H1 校准斜率 / H2 差距）

| de-vig 方法 | 校准斜率 | 低端尾部偏差 | 高端尾部偏差 | B4 与 B6 的配对 ΔLL | 结论 |
|---|---|---|---|---|---|
| proportional | | | | | 主口径 |
| Shin | | | | | 稳健性 |
| power | | | | | 稳健性 |

## 填写规则

1. 每个区间写清是 90% 还是 95% 簇 bootstrap（重采样单位＝48 个「联赛-赛季」块，10,000 次），并在 `deff` 列给出 design effect；**绝不按「比赛」重采样**。
2. 配对差必须与 `B4` / `B6` 在**同一批比赛**上计算，按 `match_id` 内连接（`match_id = league|season|date|home|away`，`date` 为 ISO，见 `data_interface.md` §1.0）：`ΔLL_vs_B4` 以 B4 为参照、`ΔLL_vs_B6` 以 B6 为参照；B4 行与 B6 行自身的参照格**留空**。
3. 分联赛 / 分赛季、轮次 sweep 的表单独放，并在标题标注「描述性」，不得由子集结果反推主结论。
4. 判定规则在跑数前写死：**全项目唯一等价边际 ±0.02 nats**（C1/C2 四分支、H2 判据②），H4 用 90% 区间上界 < 25%；表内数字不得为了好看而调整，负结果如实写。
5. `B6r` 的两参数（temperature and bias）只在每折 train 段**且 `PSCH/PSCD/PSCA` 三列齐全**的比赛上拟合，再应用到 test 段；在 test 段拟合即为泄漏，H4 结论作废。每折拟合样本数 `n_fit` 写进日志（`PSCH` 自 2012/13 才有，训练史前 9 季无收盘赔率）。
6. 落盘前把各模型内部标签（B2 有序 logit 的 客胜=0 / 平=1 / 主胜=2、HGB 的 `classes_` 顺序）**重排成 `p_home,p_draw,p_away` 并写断言**；`y` 恒为 `H=0 / D=1 / A=2`。见 `data_interface.md` §1.1。
