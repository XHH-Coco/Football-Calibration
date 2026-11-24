# 被放弃的选参规则档案（只读诊断，不是第 10 个 arm）

这里存的是 **2026-11-24 之前** B4 用的那条规则：每折在内层验证集（该折 train 的最后
一个赛季，306–380 场）上对 30 个 (ξ, ρ) 候选做 argmin。规则已被废除，主口径改为常量
`(ξ=0.0019, ρ=0)`，见 `docs/plans/roles/M3_结构化统计模型.md` §6.1。

保留这些文件的原因是**它们是废除该规则的证据**，不是因为它还有用：

| 文件 | 内容 | 支撑哪个结论 |
|---|---|---|
| `preds_B4_argmin.csv` | 16,733 行逐场预测 | pooled 0.9939 vs 常量臂 0.9903（`b4_fixed_hp_contrasts.csv`） |
| `convergence_argmin.csv` | 48 折收敛诊断 | 48 折 0 失败，排除「选不好是因为没收敛」 |
| `xi_rho_by_block_argmin.csv` | 每折选出的 (ξ, ρ) | ξ 15/48 挤在最长记忆端、0 折在最短端；ρ 20/48 在 −0.15 |
| `xi_rho_paired_se_argmin.csv` | 48 折 × 30 候选的逐场配对差 | 中位 \|Δ\| 0.0014 vs 配对 SE 0.0034，信噪比 0.3 → argmin 近似抽签 |
| `xi_rho_paired_summary_argmin.csv` | 每折的 runner-up 与同 ρ 最强 ξ 对手 | 仅 5/48 折显著，5 折全指向更长记忆 |

## 一键复现

```bash
python -m src.models.run_b4 --selection argmin
```

产物**只写本目录**，不碰 `results/preds/`。已实测：重跑结果与入库文件逐字节一致
（`md5sum` 相符）——因为 `tune_b4.LEGACY_FIT_OPTS` 把优化器容差钉在了历史值
`500 / 1e-9 / 1e-7`，与主口径收紧后的 `2000 / 1e-12 / 1e-10` 分开。

**不要把这里的东西当主结果引用**：报告里所有当前数字都来自 `results/preds/preds_B4.csv`
与 `results/table_main.csv`。本目录的数字只出现在 §4.2.4–§4.2.5 的对照表里，且都明确
标注为「retired」。
