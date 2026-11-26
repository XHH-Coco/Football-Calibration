# Presentation script — 5 speakers · 7:50 (hard limit 8:00)

> 状态：2026-11-26 **v4 重排**（页序 = `products/plain_zh.md` §1–§7）· 与 `Market-Audit.pptx` / `Market-Audit-CN.pptx` 同版本
> 用途：Canvas `Project Presentation (MP4)` 的口播稿；五人按时间顺序各讲一段，一人一段不打断。
> 语速口径：英文 127 wpm（v3 实测 122–133）。超 10% 就删句，不加速。
> 与 `script.md` 的关系：`script.md` 是逐页中文底稿（10 段，含每页的「回指 / 递出」检查表），本文件是按人重切的英文成稿；两者页内内容一致，主讲人分配以本文件为准。
>
> **v4 改了什么**：v3 的问题是句子之间没有关系——每句都对，连起来像十条并排的说明。
> ① **页序改为七步**（做什么 → 数据 → 怎么比 → 怎么判 → 四假设 → 结果 → 负结果值什么），
> 打分规则与四个假设各得独立一页，因为它们才是让后面每个数字有意义的东西。
> ② **每页首句回指上一页，末句递出下一个问题**（检查表见 `script.md` §「每页的接缝」）。
> ③ 结果从五页压到三页：市场侧 / 差距 / 差距的成分，并在口播里明说「七个结果，三页」。
> ④ 净词数 995，与 v3 的 998 持平；页数不变，所以每页的密度略降、接缝变硬。

## 1. 分段与计时

| 段 | 主讲 | 成员 | 页 | 起止 | 时长 | 英文词数 | 折算语速 |
|---|---|---|---|---|---|---|---|
| S1 | M1 | WAN Yihui | P1–P2 | 0:00–1:43 | 1:43 | 217 | 126 wpm |
| S2 | M4 | SUN Peng | P3–P4 | 1:43–3:25 | 1:42 | 218 | 128 wpm |
| S3 | M2 | WANG Xingshuai | P5–P6 | 3:25–5:01 | 1:36 | 203 | 127 wpm |
| S4 | M3 | ZHOU Yixuan | P7–P8 | 5:01–6:32 | 1:31 | 192 | 127 wpm |
| S5 | M5 | SHU Peixuan | P9–P10 | 6:32–7:50 | 1:18 | 165 | 127 wpm |

**合计 995 词 / 7:50。** 四个剪辑切点：**1:43 / 3:25 / 5:01 / 6:32**。

页内分界：P1 0:45 / P2 1:43 / P3 2:33 / P4 3:25 / P5 4:09 / P6 5:01 / P7 5:42 / P8 6:32 / P9 7:12 / P10 7:50。

> 这一版把页 9 压到 0:40（86 词，129 wpm），是全片最赶的一页：它要在一页里讲完 H4 与逐类斜率。
> 试录若超 45 秒，先删 "The price aggregates all of it; our features do not."

## 2. 分工（相对 v3 只换了页号，人没换）

| 段 | 讲什么 | 为什么是他 |
|---|---|---|
| S1 P1–P2 | 研究定位 + 数据三个坑 | M1 是数据负责人，坑与决定都是他落的 |
| S2 P3–P4 | 阶梯、C1/C2、打分规则 | B5a/B5b 与 C1/C2 是 M4 建的；打分规则必须紧跟阶梯讲，否则 C1/C2 无处落地 |
| S3 P5–P6 | 评估单位 + 四个假设 | 簇 bootstrap、判定表都在 M2 的 harness 里 |
| S4 P7–P8 | H1 读数 + 差距与 H3 | P8 的头条是 B2，有序 logit 是 M3 建的；P7 的 H1 判定与 P8 同属「报数」 |
| S5 P9–P10 | H4 与逐类误差 + 收尾 | 逐类偏差（`m5_tail_bias`）与统稿都是 M5 的活 |

**每人一段、每段至少一页是自己建的。**

## 3. 逐段讲稿（EN / 中文对照）

### S1 · M1 WAN Yihui · P1–P2 · 0:00–1:43

**[P1 · 0:00–0:45] Do football betting markets know more than a model can learn?**

**EN** That question — first, what this is not: not a betting model. If we could beat the closing line reliably, we would be selling it. What we study is the closing price itself, the best public three-way forecast there is, used as a ruler. Two questions follow. Is the ruler accurate? And how far behind it is a transparent model that only sees pre-match information? Those are one question: the same prices are what we audit and what we measure ourselves against. So before saying how far behind we are, I check the ruler.

**中** 这个问句先说清楚它不是什么：不是赌博模型。真能稳定赢过收盘线，我们早去卖这个了。我们研究收盘价本身——目前最好的公开三分类预测——把它当尺子用。两个问题：尺子准不准？一个只看赛前信息的透明模型，离它多远？这其实是一个问题：同一串价格既是被审计的对象，也是量我们的标尺。所以说差多远之前，先验尺子。

**[P2 · 0:45–1:43] 46,507 matches, three traps**

**EN** Start with what the ruler is made of: six leagues, twenty-two seasons, 46,507 matches. Three traps. One: closing odds start only in 2012/13, so the first nine seasons have no such columns, and the window can be the last eight only, fixed before we saw any result. Eight seasons, six leagues, forty-eight blocks. Two: the files are not rectangular. Long rows, short rows, duplicated names, blank trailers. Skipping what you cannot parse is the cheap fix and it throws away real matches, so we read against a nineteen-column whitelist and raise on a non-empty overflow. Three: 243 spellings of club names are 241 clubs. One match has no shots block; we leave it missing, because zero is a measurement we do not have.

**中** 这把尺子的原料：六个联赛、二十二季、46,507 场。三个坑。一：收盘赔率 2012/13 才有，前九季那三列不存在——评估窗只能取最后八季，而且在看结果之前就定下：八季乘六联赛，四十八块。二：文件不方正——行长对不上表头、重名列、整行空白。跳过读不懂的行最省事，但那会扔掉真实比赛，所以我们按十九列白名单读，多出的格子非空就报错。三：243 种队名写法其实只有 241 支队。缺射门列的那场让它缺着：零是测量值。

### S2 · M4 SUN Peng · P3–P4 · 1:43–3:25

**[P3 · 1:43–2:33] A ladder, not a leaderboard**

**EN** Next: what gets compared with what. The nine arms are on the slide, so I skip them. What matters is why this is a ladder and not a leaderboard. Handing you my best model teaches you nothing, because two models can differ in three things at once: the form, the features, how it was fitted. The ladder fixes an order so that each rung moves one of them. Most rungs fail at that. Only two steps move one factor: B4 to B5a changes the model class, B5a to B5b the features. Those two we call C1 and C2. The rest are reported side by side.

**中** 接下来是拿什么跟什么比。九个臂在屏幕上，我不念。要紧的是为什么它是阶梯不是排行榜：直接给你我最好的模型，你学不到东西——两个模型的差可能同时来自三件事：函数形式、特征、参数怎么估。阶梯把顺序固定，让每级只动一件。但多数级做不到：只有两步真的只动一个因素，B4 到 B5a 换模型类，B5a 到 B5b 换特征。这两步叫 C1 和 C2，其余的差只并列报告。

**[P4 · 2:33–3:25] Scoring: log loss, and a margin of 0.02 nats**

**EN** That settles the comparison. Now, how the ruler reads. Three probabilities per match, summing to one; afterwards you are charged on the probability you gave to what happened, on a log scale, so a confident miss is expensive. Averaged over matches, that is the log loss, and lower is better. The second number is 0.02. On one match, pricing a one-in-three event at thirty-two point six instead of thirty-three point three is about that much. More to the point, 0.02 is the resolution of forty-eight blocks. These two rungs are not findings but the ruler's first use: C1 sits on one side of zero, inside the margin; C2 crosses zero. Separable, not decisive.

**中** 比法定了。现在，这把尺子怎么读数。每场给三个概率，加起来等于一；赛后只按你给真发生那个结果的概率扣分，取负对数，敢押又押错罚最重，全场平均就是 log loss，越小越好。第二个数 0.02：单场看，把三分之一的概率标成三成二，差不多就是它；更要紧的是四十八块的分辨率就在这个量级。这两个台阶的比较我们早就有了，不是发现，是拿尺子试一下手：C1 区间整段在零一侧，全在边际内；C2 跨零。可分，但不决定什么。

### S3 · M2 WANG Xingshuai · P5–P6 · 3:25–5:01

**[P5 · 3:25–4:09] 48 blocks, not 16,733 matches**

**EN** So why forty-eight blocks and not sixteen thousand matches? Because the unit of evaluation is the block, not the match. Before each season I refit once, on that league's earlier matches only, then score the season. Forty-eight blocks, forty-eight evaluations: rolling origin, which is what stops anyone peeking. The intervals come from a cluster bootstrap, whole blocks redrawn, because matches inside a block share teams and fixtures. They are not independent, and resampling them one at a time would understate the uncertainty. The honest sample size is about half of what it looks like.

**中** 可为什么是四十八块，不是一万六千场？因为评估单位不是比赛，是块。每季开赛前重训一次，只用该联赛此前的比赛，然后评这一季；四十八块，四十八次，这叫滚动原点，保证没人偷看未来。区间也用簇 bootstrap，整块整块地重抽：同一块里的比赛共享球队和赛程，不独立，逐场抽会把不确定性说小。所以诚实的样本量差不多打对折。

**[P6 · 4:09–5:01] Four hypotheses, falsified in advance**

**EN** That is the protocol: one ruler, one margin, forty-eight blocks. Now what counts as winning. Four hypotheses, each with its falsification condition, fixed before any model ran. H1: the market is biased toward the middle, falsified if the slope is at or below one. H2: a transparent model does not reach it and the gap is not small, falsified if a 95% interval puts a model ahead, or a 90% interval sits inside ±0.02. H3: the gap concentrates on promoted clubs and the first six rounds, falsified if either coefficient is not positive. H4: the gap is information, not calibration, falsified if recalibration closes over a quarter of it.

**中** 规则说完了：一把尺、一个边际、四十八个块。现在说清什么算赢——四个假设，每个都带证伪条件，跑之前就写死。H1：市场有系统偏差，斜率小于等于一就算推翻。H2：透明模型追不上且差得不小——95% 区间有模型更好，或 90% 区间全在 ±0.02 内。H3：差距集中在升班马和赛季初六轮，两个系数有一个不为正。H4：差距是信息不是校准，重校准能补掉 25% 以上。

### S4 · M3 ZHOU Yixuan · P7–P8 · 5:01–6:32

**[P7 · 5:01–5:42] The market is mildly under-dispersed**

**EN** Seven results, three pages: the market, the gap, and what the gap is made of. Result one, H1. De-vig proportionally, fit a slope, and you get 1.086, with an interval entirely above one. A slope above one means probabilities pulled toward the middle: longshots priced too high, favourites too cheap. That is the favourite-longshot bias, in the literature since 1977, not our discovery. But change the de-vigging and the number moves: the last method does not even clear one. So we report a direction, not a size.

**中** 七个结果，三页：市场、差距、差距的成分。第一个结果，H1。按比例扣掉抽水、拟合斜率，得到 1.086，区间整段在一以上。斜率大于一的意思是概率被压向中间：冷门标贵，热门标便宜。这叫冷门—热门偏差，1977 年就有文献，不是我们的发现。但换一种扣法，数会动：最后一个连大于一都不成立。所以只能说方向，不能说大小。

**[P8 · 5:42–6:32] How far behind — and where the gap is not**

**EN** Result two, and this page is three things. The best transparent arm is not the one I pre-registered: B2 sits closer, B4 is the pre-registered one, and both intervals lie entirely above the margin, so the gap is real rather than a resolution artefact. Why put B4 in the headline? It is the default opponent in this literature, and it freezes before kick-off, the same information timing as the market. But part of B2's lead is a rule: it updates its ratings inside the season. Freeze that too and the lead disappears. Third: H3 is half wrong. Promotion widens the gap; early rounds narrow it.

**中** 第二个结果，这一页是三件事。最好的透明臂不是我预注册的那个——B2 更近，B4 才是预注册的；两个区间都整段在边际之上，差距是真的，不是测不出来。为什么挂 B4？它是这类文献的默认对手，而且开赛前就冻结参数，和市场同一个信息时点。但 B2 的领先有一部分是规则给的：它赛季内会更新评分，把这条也冻上，领先就没了。第三件：H3 猜错一半，升班马那里差距更大，赛季初反而更小。

### S5 · M5 SHU Peixuan · P9–P10 · 6:32–7:50

**[P9 · 6:32–7:12] It is not an offset you can subtract**

**EN** Result three answers a different question: is the gap an arithmetic error, or is it ignorance? If it were calibration, recalibrating the market against itself would close most of it. It barely moves. Then the cheating version, two parameters fitted on the test labels, recovers only 8.7%. So the gap is information: lineups, motivation, the ninety minutes. The price aggregates all of it; our features do not. And the models' own error has no single direction either: draws collapse, home and away go the other way.

**中** 第三个结果回答：这差距是算错了，还是不知道。如果只是校准问题，重校准市场的概率，差距该消掉大半。做了，几乎不动；再给一个作弊版，参数直接对着测试标签拟合，也只补回 8.7%。所以是信息：阵容、动机、那九十分钟。价格把这些聚合进去了，我们的特征没有。模型自己的错也没有单一方向——平局塌了，主客反过来散得不够。

**[P10 · 7:12–7:50] A negative result, and what it buys**

**EN** So this is a negative result, but negative in a narrow sense: we did not win, and we found out why we could not. Three things bought. A price map that carries its method, three de-vigging routes reported, so a reader can recompute. An answer located by kind of match, including the half we got wrong. And two literatures joined up. Limits: one sport, closing prices only, the resolution of forty-eight blocks. One command rebuilds every number. Thank you.

**中** 所以这是个负结果，但“负”很窄：我们没赢，我们弄清楚了为什么赢不了。买到三样：一张带方法的价格地图，三种扣法都报，读者能自己重算；一个定位到哪类比赛的答案，包括猜错的那半；还有把两条分开的研究线接上。限制：一种运动、只有收盘价、四十八块的分辨率。一条命令重建每个数。谢谢。

## 4. 录制与交接

1. **分段独立录**，一人两页一条过，段首留 1 秒静场；不要拍交接动作，剪辑按四个时间码对齐。
2. **不要念屏幕上的数**。v4 已把成串读数删掉：页 3 的臂名、页 4 与页 8 的区间端点、页 9 的斜率。
   说到「这页上」时用手或激光笔指一下，再讲它意味着什么——指着说比念出来可信。
3. **必须念准的三个数**：P2 的 `46,507`、P7 的 `1.086`、P9 的 `8.7`。其余数字以「大约」「四分之一」
   「差得远」这类相对说法出现，念错的风险低。
4. **页 4 的 nats / 0.02 解释是全片唯一的单位解释**，不许省。
5. **首句回指不许删**。删掉任意一页的首句，那一页就退回成 v3 那种「孤立说明」。压时长先删举例，
   不要删首句与末句（对照表见 `script.md`）。
6. **禁语**：`accuracy`、`M0–M4` 当模型名、「B4 是最好的透明臂」、「45 块满格」、「8 个赛季有赔率」
   （正确说法：13 个赛季有）、「四个假设都成立」（H3 只作描述）。
7. **超时处置**（按顺序删，每条约 4–6 秒）：P2 的 `243 spellings` 那句 → P7 的 `since 1977` →
   P9 的 `The price aggregates all of it` → P3 的三件事罗列。不要整体加速。
8. **五人出镜**：S1–S5 各一次，缺任何一段都无法覆盖「全员出镜」。
