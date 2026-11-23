# Slides 骨架（10 页 · ≤ 8:00 · 五人全出镜）

> 状态：2026-11-20 · M5 维护 · 页序对齐 `docs/plans/08_小组分工实施方案_v1.3.md` §8 · 骨架 11/17 起、11/27 定稿
> 验收红线：每页只讲一个点（G3 #8）；录像 ≤ 8:00、五人全出镜（G3 #9）。

## ⚠ 两处需组内拍板（详见 `script.md`）

1. **时长超支**：页序各页相加 = 9:00，超出 8:00 上限，需压缩约 60 秒。
2. **M4 无主讲页**：现页序 M1/M2/M3/M5 都有页，唯独 M4 没有，违反「五人全出镜」。建议：把页 4 拆成「阶梯总览(M3) + ML 臂 B5a/B5b(M4)」，或把页 7 的 C1/C2 拆一段给 M4。

## 页序（10 页）

| 页 | 标题（英文，最终上屏） | 一句话点（每页只讲一个） | 图 | 主讲 | 时长 | 状态 |
|---|---|---|---|---|---|---|
| 1 | The market as a measuring instrument | 我们不打败市场，而是审计它哪里答得差（RQ1） | — | M5 | 1:10 | ☐ |
| 2 | What a transparent model can and cannot learn | RQ2：只用赛前信息的模型追不上市场，且差距可分解 | `fig01` | M5 | | ☐ |
| 3 | Data and coverage | 6 联赛 × 22 季 46,507 场；仅射门列缺 1 场（0.999940） | `fig_data_coverage` | M1 | 0:50 | ☐ |
| 4 | The ladder B0–B6 + B6r | 只有两次单因素变更 C1/C2 作归因，其余只报告 | `fig01` | M3（+M4?） | 1:20 | ☐ |
| 5 | Evaluation protocol | 48 块 rolling-origin + 簇 bootstrap + design effect（区间宽 15–50%，≈√deff），绝不按场重采样 | — | M2 | 1:10 | ☐ |
| 6 | H1 — the market is under-dispersed | 比例法斜率 1.086（90% CI 1.047–1.124）> 1，FLB；Shin 1.052 / power 1.030（跨 1）→ 方向一致、量级依赖口径 | `fig06` | M2 | 1:00 | ☐ |
| 7 | H2 / H3 — how far, and where | B4 落后 0.035 nats；差距非局部化（H3 仅描述） | `fig07`、`fig08`左 | M5 | 1:10 | ☐ |
| 8 | H4 — information, not calibration | B6r 重校准后 gap 几乎不变（相对 0.0017，上界 0.011 < 0.25） | `fig08`右 | M2 | 1:00 | ☐ |
| 9 | Conclusions and limitations | 负结果即设计内结论；模型 over-dispersed、平局最重 | `fig05` | M1 | 1:20 | ☐ |
| 10 | Appendix A1 & reproducibility | γ 轨迹（描述性）+ 复现包 + 贡献声明 | `fig_a1_gamma` | M1 | | ☐ |

## 上屏规范

1. 每页标题 + 一句话结论放最上，正文不超过 6 行；
2. 区间一律标注「48 块簇 bootstrap (10,000 次)」；分联赛/轮次 sweep 标「描述性」；
3. 只用 B0–B6+B6r，不用 M 系列命名；无 accuracy；
4. 图统一用 `products/figures/` 成品（300 dpi）。
