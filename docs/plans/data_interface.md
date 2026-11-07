# 数据接口约定（统一预测文件 schema 与防泄漏红线）

> 版本 **v1.3** · 2026-11-08 · 摘录自 `08_小组分工实施方案_v1.3.md`（r2 修订）§5.1 / §5.3 / §5.5，蓝本 `Team-32-Proposal_v3.0.md`，供全员实现前对齐。
> **v1.2 → v1.3**：① §1.1 补「内部有序标签 → 落盘 `p_home,p_draw,p_away` 重排」硬规则与断言示例；② §2 补 B6r 的 train 段拟合样本边界（`PSCH` 自 2012/13 才有）；③ §2 对照一致性行补 sklearn HGB 的 `classes_` 重排；④ §5 H4 判定备注同步。D1 决策落地为零新增依赖。
> ✅ **命名已定稿（U3 闭环）**：模型标识、文件名与 `model` 列一律用 **`B0`–`B6` + `B6r`** 共 9 个 arm；`M1`–`M5` 只指成员。对外假设编号用 Proposal 的 **H1–H4**；原「结构 vs 灵活」降为受控比较 **C1/C2**，主场优势降为**附录 A1**。B↔M 映射表见 `Team-32-Proposal_v3.0.md` §4 末。
> **市场基准列已定：只读收盘价 `PSCH/PSCD/PSCA`**（见 v1.3 §5.5）；`PSH/PSD/PSA` 为开盘价、`B365*` 为别家非收盘价，均不作基准。

## 1. 统一预测文件 schema

任何模型只要按这张表产出 CSV，就能直接进入评估框架，**不需要各自写评估代码**。这是全项目最重要的接口约定。

| 列 | 类型 | 说明 |
|---|---|---|
| `league` | str | 联赛代码，如 `E0` / `SP1` |
| `season` | str | 赛季，如 `2024/25` |
| `date` | str | 比赛日期（原始字段） |
| `home` / `away` | str | 队名（已按 `configs/team_alias.csv` 统一） |
| `model` | str | 模型标识 |
| `p_home` / `p_draw` / `p_away` | float | 三概率，和为 1（误差 < 1e-9），顺序 H / D / A |
| `y` | int | 0 / 1 / 2 = H / D / A |

三条硬性校验：三概率和为 1；`y ∈ {0,1,2}`；行数等于该块 test 场次。**落盘路径统一为 `results/preds/preds_{B0..B6,B6r}.csv`（9 个文件），每个 arm 1 个文件含全部 48 块（合计 16,733 行；B6 / B6r 有效 16,730 行）**，不要一块一个文件；按 `match_id` 对齐，**不同模型在同一块上必须预测同一批比赛**，否则配对差算不出来。

### 1.1 `y` 编码与类别顺序（M1 在 `build_panel.py` 里定死）

| 项 | 约定 |
|---|---|
| 标签 | `FTR` 的字符串 `H / D / A` → `y = 0 / 1 / 2`，直接写进 `panel.parquet` 的 `y` 列 |
| 概率列顺序 | 恒为 `p_home, p_draw, p_away`，与 `y` 的 0/1/2 一一对应；**`p_home` 必须是三列中的第一列** |
| 判定 | `build_panel.py` 内加断言：`set(df.y.unique()) <= {0,1,2}` 且 `df.FTR.map({"H":0,"D":1,"A":2}).equals(df.y)`；`preds_*.csv` 落盘前再验一次三列顺序与三概率和为 1 |
| **内部标签（v1.3 新增）** | 各模型内部三分类编码**自由**：B2 有序 logit 可用「客胜=0 / 平=1 / 主胜=2」（否则系数符号全反），B5a/B5b 的 sklearn HGB 按 `classes_` 排序。**但写 `preds_*.csv` 之前必须按内部标签顺序重排成 `p_home, p_draw, p_away`**，并在落盘断言里核对；禁止把内部标签顺序直接当列序。**实测 API（2026-11-08，statsmodels 0.15.0 / scikit-learn 1.9.1）**：`OrderedModel.predict(exog=...)` 返回**列名为 `[0,1,2]` 的 DataFrame**，列序 = 建模时 `pd.Categorical(..., categories=[...], ordered=True)` 的 `categories` 顺序；`HistGradientBoostingClassifier.predict_proba` 的列序 = `model.classes_`（数值标签时恒为升序 `[0,1,2]`）。**两者都不会替你对齐 H/D/A** |
| 签字 | 口径已按分工方案 v1.3 §3.2 #3 与本表预置，**M1 不必等 11/09**；M2 在 11/09 接口冻结时确认即可，不作为 11/08 交 panel 的前置条件 |

> 顺序反了**不会报错**，只会让 log loss 悄悄变差（见 M2 分工卡 §7 坑 3），所以必须写成断言，不能只靠口头约定。
>
> **落盘断言示例**（`y` 与三列必须同源同序；每个模型先声明「我的第 j 列是哪个结果」）：
>
> ```python
> # 每个模型自己声明内部列序，长度必须为 3
> #   B2  OrderedModel : internal = list(建模型时的 categories)   如 ["A", "D", "H"]
> #   B5a/B5b HGB      : internal = list(clf.classes_)            如 [0, 1, 2]（y=H/D/A→0/1/2）
> internal = ["A", "D", "H"]                       # 示例：B2
> order = [internal.index(k) for k in ["H", "D", "A"]]   # → [2, 1, 0]
> p = np.asarray(proba)[:, order]                  # proba: B2 的 predict() 或 HGB 的 predict_proba()
> assert np.allclose(p.sum(axis=1), 1, atol=1e-9)
> out = pd.DataFrame(p, columns=["p_home", "p_draw", "p_away"])
> assert out.columns.tolist() == ["p_home", "p_draw", "p_away"]
> ```
>
> **反例（务必避免）**：B2 按「客胜=0 / 平=1 / 主胜=2」拟合后，直接把预测结果三列命名为 `p_home,p_draw,p_away` —— 不报错，但 `p_home` 装的其实是客胜概率，log loss 会显著变差且很难查。
>
> **B2 建模提示（同日实测）**：`OrderedModel` 的 `endog` 必须是 `pd.Categorical(..., categories=["A","D","H"], ordered=True)` 的 Series；直接传字符串 dtype 会抛 `ValueError: Pandas data cast to numpy dtype of object`。`predict` 时 `exog` **只传特征列**，不要连 `y` 一起传。

## 2. 防泄漏红线（违反即结论作废）

| 红线 | 具体要求 |
|---|---|
| 切分 | 目标赛季为 test，只用**严格更早**的比赛训练 |
| 特征 | 滚动特征只能用 t 之前的比赛（至少 shift 一场）；Elo 只能逐场顺序更新；禁止全样本标准化 |
| 调参 | ξ、ρ、树深、学习率只在训练窗内的 expanding 子窗选 |
| 先验基线 | 只用严格更早比赛的历史频率，禁止当季信息 |
| 市场列 | 任何模型 arm 的特征里都不允许出现赔率列；赔率只用于构造 `B6` / `B6r` 基准，且**只读 `PSCH/PSCD/PSCA`** |
| **B6r 时点** | B6r 的两个重校准参数（temperature and bias）**只在该折 train 段拟合、应用到 test 段**，与 ξ/ρ/树深同受调参红线约束；在 test 段拟合即为泄漏，H4 结论作废。**拟合样本边界（v1.3 新增）**：`PSCH/PSCD/PSCA` 自 2012/13 季才有，训练史前 9 季无收盘赔率；因此两参数**只用 train 段中这三列齐全的比赛拟合**（缺一即 drop、不回填，与 B6 同规则），每折拟合样本数 `n_fit` 写进日志；test 段仍按 B6 的 16,730 场评估。不设此边界，各折分子分母口径会分歧，H4 作废 |
| **H3 指示变量** | `is_promoted_*` 与 `matchday` 只能由季前名单 / 赛程构造，禁止使用比分、射门或任何赛后信息（M1 的 T1.9 打乱测试） |
| **对照一致性** | `B4` 与 `B5a` 必须在**特征**与**样本权重**两处都一致（`B5a` 传 `sample_weight = exp(−ξ̂·Δ天)`，ξ̂ 取该折 B4 的估计值）；`B5a` 与 `B5b` 必须在**权重**与**其余超参**两处都一致。只锁特征不锁权重，单因素归因失效。**B5a/B5b 统一用 `sklearn.ensemble.HistGradientBoostingClassifier`（scikit-learn 1.9.1 内置，零新增依赖，D1）；其 `predict_proba` 列序按 `classes_`，落盘前同样按 §1.1 重排** |
| test 次数 | 每个块的目标赛季只预测一次；重跑须在日志记原因 |
| 子集结论 | 合并配对差是唯一主推断；分联赛 / 分赛季只作描述性报告 |

## 3. 评估协议摘要

- Expanding-window rolling origin：8 个目标赛季 × 6 联赛 = **48 块**，每块只评估一次。
- 主指标 **log loss**；辅指标 Brier score / RPS；校准用可靠性曲线、校准斜率与截距、ECE、偏差-预测概率图。**不用 accuracy**。全项目**唯一等价边际 ±0.02 nats**；H4 用 90% 区间上界 < 25% 判定。
- 不确定度：以 **(联赛, 赛季) 块**为重采样单位做簇 bootstrap（10,000 次），cluster-robust SE 交叉核对；**绝不按「比赛」重采样**；每个区间附 **design effect**。
- 负结果即成功；等价性阈值等判定规则必须在跑数之前写死，不得事后修改。

### 基线自检数（实测，实现指标层后先对这三个数）

| 基线 | log loss | 用途 |
|---|---|---|
| 全押 1/3 | **1.0986**（= ln 3） | 验算指标实现（十有八九是取了 log10 或漏了负号） |
| `B0` 先验（同联赛、严格更早赛季 expanding） | **1.0743**，逐块 1.027–1.115 | "地板"；**低于 1.00 一定是泄漏**；有 8/48 块低于 ln3 属正常 |
| `B6` 市场基准 | 远低于以上（约 0.96–0.98，预估） | 天花板；若任何模型显著低于它，先查泄漏 |

## 4. 课程方法挂靠

| 课次工具 | 本项目落点 |
|---|---|
| W3 Bootstrap | 48 块簇重采样，给每个 Δ 配区间而非点估计 |
| W5 样条 / GAM | **主推断**：H1 可靠性曲线、H3 轮次 sweep；附录 A1 的 γ 趋势作描述性补充 |
| W7 局部平滑 / 高斯过程 | H1 校准曲线平滑，避免硬分箱锯齿 |

## 5. 假设编号与判定规则速查

| 编号 | 内容 | 判定 | 主责 |
|---|---|---|---|
| **H1** | 市场 under-dispersed（斜率 > 1） | 比例法斜率 ≤ 1 证伪；**斜率 > 1 时低概率区曲线在对角线下方** | M2 + M5 |
| **H2** | B4 追不上 B6，残差非零 | 95% 配对区间 / 90% 区间是否整体落在 ±0.02 内 | M2 |
| **H3** | 差距局部化（升班马、前 6 轮） | 两系数均正且各自区间下界 > 0；sweep 描述性 | M2 + M1 |
| **H4** | 差距是信息不是校准 | B6r 前后相对变化 90% 区间上界 < 25%（B6r 参数只在 train 段且 PSCH 齐全样本上拟合；见 §2） | M2 |
| **C1/C2** | 受控比较（原 H1） | ±0.02 四分支 | M2 / M3 / M4 |
| **A1** | γ 轨迹（原 H3 主场优势） | 附录描述性，不做因果主张 | M3 |

---

*本文件属方案类文档；若接口变更，请同步更新根目录 README §2.1 结构说明与 `CHANGELOG_structure.md`。*
