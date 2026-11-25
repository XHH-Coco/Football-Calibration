# Presentation script — 5 speakers · 7:50 (hard limit 8:00)

> 状态：2026-11-25 · 与 `Market-Audit.pptx` / `Market-Audit-CN.pptx`（同页序）同版本
> 用途：Canvas `Project Presentation (MP4)` 的口播稿；五人按时间顺序各讲一段，一人一段不打断。
> 语速口径：英文 110–120 wpm（数字密集段落按 105 wpm 估）。下表"词数"是实测值，超 10% 就删句，不加速。
> 与 `script.md` 的关系：`script.md` 是逐页中文底稿（10 段），本文件是按人重切的英文成稿；两者页内内容一致，主讲人分配以本文件为准。

## 1. 分段与计时

| 段 | 主讲 | 成员 | 页 | 起止 | 时长 | 英文词数 | 折算语速 |
|---|---|---|---|---|---|---|---|
| S1 | M1 | WAN Yihui | P1–P2 | 0:00–1:25 | 1:25 | 162 | 114 wpm |
| S2 | M4 | SUN Peng | P3–P4 | 1:25–3:10 | 1:45 | 176 | 101 wpm |
| S3 | M2 | WANG Xingshuai | P5–P6 | 3:10–4:50 | 1:40 | 174 | 104 wpm |
| S4 | M3 | ZHOU Yixuan | P7–P8 | 4:50–6:25 | 1:35 | 182 | 115 wpm |
| S5 | M5 | SHU Peixuan | P9–P10 | 6:25–7:50 | 1:25 | 157 | 111 wpm |

**合计 7:50，余量 10 秒。** 四个剪辑切点：**1:25 / 3:10 / 4:50 / 6:25**。

## 2. 分工变动（相对 `script.md` 旧出镜表）

旧表是"谁做的谁讲"，五人交叉出场九次。本版改为**连续两页一段**，一人只讲一次，切点从 9 个降到 4 个。

| 页 | 旧主讲 | 新主讲 | 理由 |
|---|---|---|---|
| P1 | M5 | **M1** | P1 的 RQ 需要与 P2 的数据口径连着说；M1 是数据负责人 |
| P3 | M3 | **M4** | P3 的后半段（B4 / B5a / B5b）与 P4 的 C1/C2 是同一条论证 |
| P7 | M5 | **M3** | P7 的头条是 B2，有序 logit 是 M3 建的 |
| P8 | M2 | **M3** | 与 P7 的 H2/H3 连讲，避免在一段假设论证里换人 |
| P9–P10 | M1 | **M5** | 收尾是统稿的活；M1 已在 S1 出场，五人各一次 |

P2、P4、P5、P6 主讲不变。**结果：每人一段、每段至少一页是自己建的。**

## 3. 逐段讲稿（EN / 中文对照）

### S1 · M1 WAN Yihui · P1–P2 · 0:00–1:25

**[P1 · 0:00–0:45] The market as a measuring instrument**

**EN** We are not here to beat the market. The closing price is the strongest public three-way forecaster there is, so we treat it as a measuring instrument and ask where it reads badly. Two questions. Does the market calibrate itself? And can a transparent model — pre-match information only, reproducible from one command — reach it? If it falls short, the shortfall is either information or a calibration defect we could have repaired. Nine arms and four hypotheses answer those two questions.

**中** 我们不是来打败市场的。收盘价是目前最强的公开三分类预测器，所以我们把它当成一台测量仪器，问它哪里读得不准。两个问题：市场自己校准吗？一个只用赛前信息、一条命令就能复现的透明模型，能追到它吗？如果追不上，差的那部分要么是信息，要么是我们本可以修掉的校准缺陷。九个臂、四个假设，答的就是这两问。

**[P2 · 0:45–1:25] 46,507 matches, one of them incomplete**

**EN** The data are six European leagues, twenty-two seasons, forty-six thousand five hundred and seven matches. Pinnacle closing odds start in 2012/13, so thirteen seasons have them. The evaluation window is the last eight — forty-eight league-season blocks, forty-six of them at full size; the two short ones are both 2019/20, Ligue 1 at 279 matches and the Eredivisie at 232. And one match inside the window is missing six shots columns: coverage 0.999940, kept as missing, never imputed as zero.

**中** 数据是六个欧洲联赛、二十二个赛季、四万六千五百零七场。Pinnacle 收盘赔率从 2012/13 才有，二十二个赛季里十三个有。评估窗取最后八个赛季——四十八个「联赛 × 赛季」块，四十六块满格；腰斩的两块都在 2019/20，法甲止于 279 场，荷甲止于 232 场。窗内还有一场缺六个射门列，覆盖率 0.999940，我们保留为缺失，绝不插补成零。

### S2 · M4 SUN Peng · P3–P4 · 1:25–3:10

**[P3 · 1:25–2:20] The ladder B0–B6 + B6r**

**EN** Nine arms, one ladder. Each rung adds one thing: a frequency prior, then Elo, then an ordinal logit, then independent Poisson, then a time-decayed Dixon–Coles, then two boosted-tree arms, and finally the market and a recalibrated market. But look at only two steps. B4 to B5a changes the model class and nothing else. B5a to B5b adds thirty features and nothing else. Those are the only two rungs in the project where one factor moves. Every other step bundles several changes, so those arms are reported side by side, never attributed to a single cause.

**中** 九个臂，一条阶梯。每一级加一件事：频率先验、Elo、有序 logit、独立泊松、时间衰减的 Dixon–Coles，然后两个提升树臂，最后是市场和再校准的市场。但只看两步：B4 到 B5a 只换模型类，别的都不动；B5a 到 B5b 只多三十个特征，别的都不动。全项目只有这两级是一次只动一个因素。其余每一步都同时改了几件事，所以那些臂只并列报告，绝不归因到单一原因。

**[P4 · 2:20–3:10] C1 and C2 — the only two attributions we own**

**EN** C1 is B5a minus B4 — same information, same weights, only the model class changes. It costs 0.0055 nats, interval 0.0009 to 0.0099. That interval excludes zero, so the difference is real. But the whole interval sits inside the plus-or-minus 0.02 equivalence margin, so the honest reading is: separable, practically equivalent. C2 is B5b minus B5a — thirty more features buy back 0.0015, and that interval crosses zero. At the top of the ladder, more capacity did not buy better predictions.

**中** C1 是 B5a 减 B4——同样的信息、同样的权重，只换模型类。代价是 0.0055 nats，区间 0.0009 到 0.0099。区间不含零，所以差异是真的。但整段落在正负 0.02 的等价边际之内，所以诚实的读法是：可分辨，但实际等价。C2 是 B5b 减 B5a——多三十个特征，换回 0.0015，区间跨零。阶梯的顶端，加容量并没有换来更好的预测。

### S3 · M2 WANG Xingshuai · P5–P6 · 3:10–4:50

**[P5 · 3:10–4:00] 48 blocks, not 16,733 matches**

**EN** The unit of evaluation is not the match, it is the block. Before each season we refit once, on everything earlier for that league, and then score that season once — forty-eight blocks, forty-eight evaluations. That is rolling origin. Intervals come from a cluster bootstrap: we redraw whole blocks ten thousand times, never the sixteen thousand matches one at a time, because matches inside a block share teams and fixtures. We report the measured design effect, 1.32 to 1.89 — intervals are one point one five to one point three seven times the naive width.

**中** 评估单位不是比赛，是块。每个赛季开赛前重训一次，只用该联赛此前所有比赛，然后把这个赛季评一次——四十八块，四十八次评估。这叫滚动原点。区间用簇 bootstrap：整块重抽一万次，绝不按一万六千场逐场重抽，因为同一块里的比赛共享球队与赛程。我们报实测设计效应，1.32 到 1.89——区间宽度是朴素宽度的一点一五到一点三七倍。

**[P6 · 4:00–4:50] The market is under-dispersed**

**EN** H1 is supported. Strip the vig proportionally and the calibration slope is 1.086, ninety percent interval 1.047 to 1.124 — the lower bound is above one. A slope above one means probabilities are pulled toward the middle: longshots over-priced, favourites under-priced. That is the favourite-longshot bias. On robustness, Shin gives 1.052, the power method 1.030 with an interval that crosses one. So the claim is: same direction, magnitude depends on how you de-vig. We do not pick a number.

**中** H1 支持。按比例去掉抽水后，校准斜率 1.086，九成区间 1.047 到 1.124，下界高于一。斜率大于一意味着概率被压向中间：冷门被高估、热门被低估，这就是经典的冷门—热门偏差。稳健性上，Shin 法 1.052，幂法 1.030 且区间跨一。所以我们的说法是：方向一致，量级取决于怎么去水。我们不挑一个数字。

### S4 · M3 ZHOU Yixuan · P7–P8 · 4:50–6:25

**[P7 · 4:50–5:40] How far behind — and where the gap is not**

**EN** H2 is supported, but the headline arm has to change. The best transparent arm is B2, the ordinal logit — not B4, which we pre-registered. B2 trails the market by 0.0270 nats, interval 0.0241 to 0.0298; B4 trails by 0.0317, interval 0.0278 to 0.0359. Both intervals sit entirely above plus 0.02, so the gap is not a resolution problem. H3 we report as description only: early rounds come out at minus 0.0108, opposite to the hypothesised sign, while promotion widens the gap by 0.0113, as expected. One of two, so we claim neither.

**中** H2 支持，但头条臂要换。最好的透明臂是 B2，有序 logit——不是我们预注册的 B4。B2 落后市场 0.0270 nats，区间 0.0241 到 0.0298；B4 落后 0.0317，区间 0.0278 到 0.0359。两个区间都整体高于 0.02，所以差距不是分辨率问题。H3 只作描述：赛季初轮次是负 0.0108，与假设方向相反；升班马扩大差距 0.0113，符合机制。两个里只对一个，所以我们两个都不宣称。

**[P8 · 5:40–6:25] Information, not calibration**

**EN** H4 is supported. If the gap were only a calibration defect, recalibrating the market against itself would close a large part of it. We did exactly that: two parameters, temperature and bias, fitted on the market's own probabilities. The gap moves 0.0019 in relative terms, ninety percent upper bound 0.0127 — far below the 0.25 decision line. Then the extreme control: fit both parameters on the test labels, which is open-book cheating, and you still recover only 8.7 percent. So the gap is information the models do not have.

**中** H4 支持。如果差距只是校准缺陷，把市场对着自己重新校准一遍就该补上一大部分。我们真的这么做了：两个参数，温度和偏置，用市场自己的概率拟合。差距相对只动 0.0019，九成上界 0.0127——远在 0.25 的判据线之下。再做一个极端对照：两个参数都用测试标签拟合，等于开卷作弊，也只补回 8.7%。所以差距是模型没有的信息。

### S5 · M5 SHU Peixuan · P9–P10 · 6:25–7:50

**[P9 · 6:25–7:20] What the models get wrong instead**

**EN** The models are not uniformly overconfident. Class by class: draw really is over-dispersed — B4 sits at 0.944, the two boosted arms fall to 0.528 and 0.566 — while their home and away slopes are 1.08 to 1.11, under-dispersed, the other way. The market sits at 1.06 to 1.09 on all three classes. So capacity distorts the classes in opposite directions; it is not one global miscalibration. One correction we owe you: after we fixed the smoothing, all three ECEs went up while all three slopes moved toward one — two summaries, opposite signals, so the slope is our only verdict statistic.

**中** 模型不是「普遍过度自信」。逐类看：平局确实过度离散——B4 是 0.944，两个提升树臂掉到 0.528 和 0.566；但它们的胜负两类斜率是 1.08 到 1.11，反而分散不足，方向正好相反。市场三类都在 1.06 到 1.09。所以是容量在把各个类别往相反方向扭，不是一次全局性的失准。还要补一句自我更正：改平滑口径后，三个 ECE 全部上升，三个斜率全部向一靠近——两个摘要给出相反信号，所以斜率是我们唯一的判定统计量。

**[P10 · 7:20–7:50] A negative result, by design**

**EN** A negative result, by design. The gap is information, not a calibration defect we could have repaired. Three hard limits: one sport, closing prices only, and forty-eight blocks resolve nothing finer than 0.02 nats. One command rebuilds every number on these slides. The contribution statement and the home-advantage analysis are in the report. Thank you.

**中** 一个设计出来的负结果。差距是信息，不是我们本可修复的校准缺陷。三条硬限制：单一项目、只有收盘价、四十八块只够分辨 0.02 nats 以上的差。一条命令重建这套幻灯上的每个数字。贡献声明与主场优势分析都在报告里。谢谢。

## 4. 录制与交接

1. **分段独立录**，一人一段，段首留 1 秒静场；不要拍交接动作，剪辑按四个时间码对齐。
2. **数字最密的三处**：P4（C1/C2 四个区间端点）、P7（两组点估计加区间）、P9（六个斜率）。先把数字念准，再补语气。
3. **禁语**：`accuracy`、`M0–M4` 当模型名、"B4 是最好的透明臂"、"45 块满格"、"8 个赛季有赔率"（正确说法：13 个赛季有）。
4. **超时处置**：删 P1 末句（"Nine arms and four hypotheses…"）与 P3 的臂名罗列，可省约 15 秒；不要整体加速。
5. **五人出镜**：S1–S5 各一次，缺任何一段都无法覆盖"全员出镜"。
6. **口播加粗数字时不加解释**：区间、上界这类词已写进句子，不要临场补充口径，补错比少说糟。
