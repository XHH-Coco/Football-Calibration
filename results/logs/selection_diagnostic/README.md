# 被放弃的选参规则档案（只读诊断，不是第 10 个 arm）

这里存的是 **2026-11-24 之前**两条逐折选参规则的产物，两条都已在同一天被废除、
改成常量，且都是总负责人裁定：

| 规则 | 原口径 | 现口径 | 裁定记录 |
|---|---|---|---|
| B4 的 (ξ, ρ) | 每折在内层验证集上对 30 个候选取 argmin | 常量 `ξ=0.0019, ρ=0` | `docs/plans/roles/M3_结构化统计模型.md` §6.1 |
| B5 的 (leaf, lr) | 每折在内层验证集上对 9 个候选取 argmin | 常量 `leaf=3, lr=0.01` | `docs/plans/roles/M4_机器学习与特征.md` §6.1 |

保留这些文件的原因是**它们是废除该规则的证据**，不是因为它还有用。

## B4：(ξ, ρ) argmin（M3 废除）

| 文件 | 内容 | 支撑哪个结论 |
|---|---|---|
| `preds_B4_argmin.csv` | 16,733 行逐场预测 | pooled 0.9939 vs 常量臂 0.9903（`b4_fixed_hp_contrasts.csv`） |
| `convergence_argmin.csv` | 48 折收敛诊断 | 48 折 0 失败，排除「选不好是因为没收敛」 |
| `xi_rho_by_block_argmin.csv` | 每折选出的 (ξ, ρ) | ξ 15/48 挤在最长记忆端、0 折在最短端；ρ 20/48 在 −0.15 |
| `xi_rho_paired_se_argmin.csv` | 48 折 × 30 候选的逐场配对差 | 中位 \|Δ\| 0.0014 vs 配对 SE 0.0034，信噪比 0.3 → argmin 近似抽签 |
| `xi_rho_paired_summary_argmin.csv` | 每折的 runner-up 与同 ρ 最强 ξ 对手 | 仅 5/48 折显著，5 折全指向更长记忆 |

## B5：(leaf, lr) argmin（M4 废除）

| 文件 | 内容 | 支撑哪个结论 |
|---|---|---|
| `preds_B5a_argmin.csv` | 16,733 行逐场预测 | pooled **1.0061**（现行固定口径 0.9957，差 −0.0104） |
| `preds_B5b_argmin.csv` | 16,733 行逐场预测 | pooled **1.0033**（现行 0.9942，差 −0.0091） |
| `b5_params_argmin.csv` | 48 折选出的 (leaf, lr) + 该折 `val_logloss` | leaf=7（网格最小）46/48 折、lr=0.03（网格最小）37/48 折 → **贴边** |

配套的 20 格扩展网格证据不在这里，在 `results/logs/sens_b5_grid_{val,test}.csv`
（由 `src/models/sens_b5_grid.py` 生成，48 折 × 20 格 × 2 臂）。关键是它证明
「换网格不解决问题」：扩到 20 格后 argmin 仍然 37/48 折贴在新边界 leaf=3 上，
所以真正的结论是**不该搜**，而不是网格差一格。

## 一键复现

```bash
python -m src.models.run_b4 --selection argmin   # B4：(ξ, ρ) 30 候选 × 48 折
python -m src.models.b5_gbm --selection argmin   # B5：(leaf, lr) 9 候选 × 48 折
```

两条命令的产物**只写本目录**，不碰 `results/preds/`、不碰 `results/table_main.csv`。
已实测逐字节一致：B4 因 `tune_b4.LEGACY_FIT_OPTS` 把优化器容差钉在历史值
`500 / 1e-9 / 1e-7`（与主口径收紧后的 `2000 / 1e-12 / 1e-10` 分开），重跑 `md5sum`
与入库文件相符；B5 由 `tests/test_m4_b5_fixed.py` 里的
`test_retired_grid_selection_distribution_is_stable` 守住 46/37 这个分布。

**不要把这里的东西当主结果引用**：报告里所有当前数字都来自 `results/preds/preds_*.csv`
与 `results/table_main.csv`。本目录的数字只出现在 §4.2.4–§4.2.5（B4）与
§4.3.6 / §5.1.4（B5）的对照表里，且都明确标注为「retired / delivered」。
