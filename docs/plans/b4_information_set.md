# B4 信息集清单（M3 → M4 接口冻结件）

> 版本 v1.0 · 2026-11-11 · 对应 `08_小组分工实施方案_v1.3.md` §5（11/09 接口冻结：**B4 信息集清单**，M2 主签 / M3 会签）。
> 用途：`B4 → B5a` 是**唯一两级可归因**的受控比较之一（另一级是 `B5a → B5b`）。
> **只锁特征不锁权重，C1 的归因就混进"权重不同"这个第三因素**，所以本清单同时给权重口径。

## 1. B4 实际摄入的东西

| 项 | 内容 |
|---|---|
| 样本 | 每折 train = **同联赛、`date < test_start`** 的全部比赛（`src.splits.resolve_split`） |
| 观测字段 | `home`, `away`, `FTHG`, `FTAG`, `date`（`match_id` 只用于对齐，不入模） |
| 参数 | 每队进攻力 α、防守力 β；全局基线 μ；主场加成 γ。约束 **Σα = 0 且 Σβ = 0**，α/β 带 L2=1.0 |
| 进球率 | `λ_home = exp(μ + γ + α_home − β_away)`，`λ_away = exp(μ + α_away − β_home)` |
| 低比分修正 | `τ(ρ)` 只改 0-0 / 1-0 / 0-1 / 1-1 四格（Dixon–Coles） |
| 升班马 | train 内场次少的队由 L2=1.0 收缩向 0；test 里 train 完全没出现过的队直接取 α = β = 0（联赛平均）。`n_new_team` 记入日志 |

**一句话**：B4 只吃"谁在什么时候、主场还是客场，进了几个球"。它不读射门、角球、牌、半场比分、赔率、伤停、旅行。

## 2. 样本权重（B5a 必须逐折照抄）

```
w_t = exp(−ξ̂ · Δdays_t)        Δdays_t = date(test_start) − date(t)   （单位：天）
w_t = w_t / mean(w_t)           归一化到均值 1（否则 ξ 会与 L2 收缩混在一起）
```

- **ξ 的取值（2026-11-24 起）**：**常量 0.0019**，48 折相同。见
  `results/logs/xi_rho_by_block.csv` 的 `xi` 列——该列在常量口径下 48 行同值，
  `selection` 列为 `fixed`。B5a 照抄该列即可，不要自己指定。
- **为什么不再逐折估计**：原口径在每折的内层验证集（该折 train 的最后一个赛季）
  上 argmin 选 ξ̂，但该验证集只有 306–380 场、相邻 ξ 的真实差异约 0.001 nats、
  配对 SE 0.0034（信噪比 0.3），选出来的值近似抽签，且成本可测（pooled 0.9939 vs
  常量 0.9903）。裁定记录见 `docs/plans/roles/M3_结构化统计模型.md` §6.1 与
  `results/logs/xi_rho_decision_2026-11-11.txt` §7。**B4 与 B5a 现在共用同一个常量，
  锁定关系比原来更强**（原来只是"同一折同一个 ξ̂"，现在是"全项目同一个 ξ"）。
- 旧的逐折 argmin 证据仍可复现：`python -m src.models.run_b4 --selection argmin`
  写入 `results/logs/selection_diagnostic/`，不覆盖主产物。
- B5a 调用：

```python
day = (pd.to_datetime(block["test_start"]) - pd.to_datetime(train["date"])).dt.days
w = np.exp(-xi_hat * day)
w = w / w.mean()
clf.fit(X_train, y_train, sample_weight=w)
```

## 3. B5a 白名单的边界（M4 产出、M3 逐条会签）

**允许**——只用第 1 节的信息在赛前可算的量：

| 特征 | 来源 |
|---|---|
| 双方滚动进球率 / 失球率（近 N 场，含主客场拆分或合并） | 该队 `date` 之前的 `FTHG/FTAG` |
| Elo 差 / 双方 Elo | 逐场顺序更新的历史比分 |
| 主客身份 | `home` / `away` |
| 滚动比赛场次 / 滚动窗口长度（若用作特征） | `date` 之前的赛程 |

**禁止**（任何一条出现，B4↔B5a 的差值就不再是"模型类别"一个因素）：

- 射门、射正、角球、犯规、牌、半场比分 —— 赛后信息；
- 赔率（`PSCH/PSCD/PSCA` 及其他任何博彩列）—— B6 专用；
- 休息天数、旅行距离、伤停名单 —— B4 没有这些信息；
- 目标赛季的任何统计量、全样本标准化、用未来比赛算的滚动量（必须 `shift(1)`）。

**权重列**：`configs/feature_whitelist_b5a.csv` 要有 `feature / source / allowed / sample_weight_rule` 四列；`sample_weight_rule` 写明"ξ 取自 `xi_rho_by_block.csv` 的 `xi` 列（常量 0.0019）"。

## 4. 会签

| 角色 | 事项 | 状态 |
|---|---|---|
| M3 | 本清单（信息集 + 权重口径） | ✅ 2026-11-11 出具 |
| M2 | 主签（与 `splits.json`、9 arm schema、H3 两列四项一并） | 待签 |
| M4 | 会签 `configs/feature_whitelist_b5a.csv`（文件由 M4 产出） | 待文件到位 |
| M3 | 逐条核对白名单 + 权重规则 | 待文件到位 |

> 冻结后任何口径改动走 PR，PR 描述里写明受影响的模型与已产出的预测文件，并在群里 @全员。
