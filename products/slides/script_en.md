# Presentation script — 5 speakers · 7:50 (hard limit 8:00)

> 状态：2026-11-25 v3 · 与 `Market-Audit.pptx` / `Market-Audit-CN.pptx`（同页序）同版本
> 用途：Canvas `Project Presentation (MP4)` 的口播稿；五人按时间顺序各讲一段，一人一段不打断。
> 语速口径：英文 125–133 wpm（实测值）。超 10% 就删句，不加速。
> 与 `script.md` 的关系：`script.md` 是逐页中文底稿（10 段），本文件是按人重切的英文成稿；两者页内内容一致，主讲人分配以本文件为准。
>
> **v3 改了什么**：把「念数字」换成「讲道理」。
> ① **删掉照读**——页 3 的九臂名单、页 4 / 页 7 的区间端点、页 9 的六个斜率，屏幕上已经写着，不再逐个念，改成「这页上那个数」+ 它意味着什么。
> ② **补五处解释**：nats 是什么、0.02 为什么是这个数量级、为什么用阶梯而不是排行榜（一个模型的差异同时混了三件事）、差距落在哪类信息上（阵容 / 动机 / 场内）、为什么预注册 B4（默认对手 + 与市场同一信息时点）。
> ③ **加两处自我限制**：斜率大于一不等于可套利；B2 的领先有一部分是协议给的。
> 净词数基本持平，段切点不变。

## 1. 分段与计时

| 段 | 主讲 | 成员 | 页 | 起止 | 时长 | 英文词数 | 折算语速 |
|---|---|---|---|---|---|---|---|
| S1 | M1 | WAN Yihui | P1–P2 | 0:00–1:25 | 1:25 | 184 | 130 wpm |
| S2 | M4 | SUN Peng | P3–P4 | 1:25–3:10 | 1:45 | 228 | 130 wpm |
| S3 | M2 | WANG Xingshuai | P5–P6 | 3:10–4:50 | 1:40 | 203 | 122 wpm |
| S4 | M3 | ZHOU Yixuan | P7–P8 | 4:50–6:25 | 1:35 | 203 | 128 wpm |
| S5 | M5 | SHU Peixuan | P9–P10 | 6:25–7:50 | 1:25 | 180 | 127 wpm |

**合计 998 词 / 7:50。** 四个剪辑切点：**1:25 / 3:10 / 4:50 / 6:25**。

页内分界（v3 微调，段切点未动）：P1 0:42 / P2 1:25 / P3 2:20 / P4 3:10 / P5 4:02 / P6 4:50 / P7 5:42 / P8 6:25 / P9 7:17 / P10 7:50。

## 2. 分工变动（相对 `script.md` 旧出镜表）

旧表是"谁做的谁讲"，五人交叉出场九次。本版改为**连续两页一段**，一人只讲一次，切点从 9 个降到 4 个。

| 页 | 旧主讲 | 新主讲 | 理由 |
|---|---|---|---|
| P1 | M5 | **M1** | P1 的 RQ 需要与 P2 的数据口径连着说；M1 是数据负责人 |
| P3 | M3 | **M4** | P3 的后半段（B4 / B5a / B5b）与 P4 的 C1/C2 是同一条论证 |
| P7 | M5 | **M3** | P7 的头条是 B2，有序 logit 是 M3 建的 |
| P8 | M2 | **M3** | 与 P7 的 H2/H3 连讲，避免在一段假设论证里换人 |
| P9–P10 | M1 | **M5** | 收尾是统稿的活；M1 已在 S1 出场，五人各一次 |

**结果：每人一段、每段至少一页是自己建的。**

## 3. 逐段讲稿（EN / 中文对照）

### S1 · M1 WAN Yihui · P1–P2 · 0:00–1:25

**[P1 · 0:00–0:42] The market as a measuring instrument**

**EN** Let me start with what this is not. Not a betting model — if we could beat the closing line reliably, we'd be selling it. What we study is the closing price itself, the best public three-way forecast there is, used as a measuring instrument. So: is the instrument accurate? And how far behind it is a transparent model, pre-match information only? Those are one question. The same price is both what we audit and what we're measured against. Before I say how far behind we are, I have to check the ruler.

**中** 先说清楚这不是什么。不是赌博模型——真能稳定赢过收盘线，我们早去卖了，不会站在这儿讲。我们研究的是收盘价本身：目前最好的公开三分类预测器，把它当量尺用。所以两个问题：这把尺子准不准？一个只用赛前信息的透明模型，离它多远？这两个其实是一个问题——同一串价格，既是我们审计的对象，也是量我们自己的标尺。所以在说"差多远"之前，得先检查尺子。

**[P2 · 0:42–1:25] 46,507 matches, one of them incomplete**

**EN** The data: six leagues, twenty-two seasons, 46,507 matches. Here's the trap — Pinnacle closing odds only start in 2012/13. Thirteen seasons have them; nine don't have the columns at all. Why only the last eight? Not because it's a nice number. Because that's where the market exists, and the window was fixed before we looked at any result. Eight seasons, six leagues, forty-eight blocks. Two are short, both 2019/20. One match is missing six shot columns. We leave it missing — a zero is a measurement, and we don't have one.

**中** 数据是六个联赛、二十二个赛季、46,507 场。这里有个坑：Pinnacle 收盘赔率 2012/13 才有，二十二季里十三季有，另外九季连列都没有。为什么只用最后八季？不是数字好看，是只有那儿有市场可比——而且窗口是在看任何结果之前就定下的。八季乘六联赛，四十八个块。两块是残季，都在 2019/20。还有一场缺六个射门列。我们让它缺着：零是一个测量值，我们手上没有。

### S2 · M4 SUN Peng · P3–P4 · 1:25–3:10

**[P3 · 1:25–2:20] The ladder B0–B6 + B6r**

**EN** The nine arms are on the slide, so I won't read them out. What matters is why it's a ladder, not a leaderboard. Showing you my best model would teach you nothing — two models differ in three things at once: the form, the features, how it was fitted. The ladder fixes an order so each rung is supposed to move one of those. But most rungs don't manage it. Only two steps move exactly one factor: B4 to B5a changes the model class, B5a to B5b changes the features. The rest move several things at once, so I attribute nothing. And the order doesn't follow complexity: our simplest arm, one number, beats both boosted arms.

**中** 九个臂在幻灯片上，我不念了。要紧的是为什么它是阶梯而不是排行榜。如果我直接给你我最好的模型，你什么也学不到——两个模型之间的差，同时混了三件事：函数形式、特征、还有拟合方式。阶梯把顺序固定下来，让每一级只动其中一件。但大多数级其实做不到：整条阶梯只有两步确实只动一个因素——B4 到 B5a 换模型类，B5a 到 B5b 换特征。其余每一级都是几件事一起变，所以那些我不给归因。而且排序并不跟复杂度走：我们最简单的那个臂，只用一个数，赢过两个提升树臂。

**[P4 · 2:20–3:10] C1 and C2 — the only two attributions we own**

**EN** Take C1, the clean one. Same inputs, same weights, same data — only the functional form changes. The number is on the slide, and its interval sits entirely on one side of zero, so the difference is real. Is it large? Nats mean nothing to most people. It's the loss on the probability you gave to what happened, on a log scale — being wrong is punished fast. Our equivalence line, 0.02, is about what you lose by pricing a one-in-three event slightly under one in three — the finest tick this ruler can show. A quarter of a tick. Separable, practically equivalent. C2 adds thirty features and buys back almost nothing.

**中** 看 C1，最干净的一步：同样的输入、同样的权重、同样的数据，只换函数形式。数就在这页上，区间整段落在零的一侧，所以差异是真的。那它大吗？nats 对多数人没意义：它是你给真实结果所赋概率上的损失，在对数尺度上，给错了罚得很快。我们的等价边际 0.02，大约等于把一个三分之一的概率标成略低于三分之一所吃的亏——这就是这把尺子能显示的最小刻度。而这一步只有四分之一个刻度。所以：可分辨，但实际等价。C2 多加了三十个特征，几乎什么也没换回来。

### S3 · M2 WANG Xingshuai · P5–P6 · 3:10–4:50

**[P5 · 3:10–4:02] 48 blocks, not 16,733 matches**

**EN** One methodological point, and it matters more than it sounds. The unit of evaluation is not the match, it's the block. Before each season I refit once, on that league's earlier matches only, then score that season once. Forty-eight blocks, forty-eight evaluations. That's rolling origin. The intervals come from a cluster bootstrap — I resample whole blocks, not matches one at a time, because matches inside a block share teams and fixtures. They're not independent. So the honest sample size isn't sixteen thousand matches; it's closer to half that, and every interval on these slides is wider for it.

**中** 一个方法上的点，比听起来重要。评估单位不是比赛，是块。每季开赛前重训一次，只用该联赛此前的比赛，然后把这季评一次。四十八块，四十八次评估，这叫滚动原点。区间用簇 bootstrap：整块整块地重抽，不是一场一场抽——同一块里的比赛共享球队和赛程，它们不独立。所以诚实的样本量不是一万六千多场，差不多要打对折；这几页上的每个区间都因此更宽。

**[P6 · 4:02–4:50] The market is under-dispersed**

**EN** First substantive result. Strip the vig proportionally, fit a calibration slope, and you get 1.086 — interval well above one, so it isn't noise. What does a slope above one mean? Probabilities pulled toward the middle: longshots priced too high, favourites too low. That's the favourite-longshot bias, and it's been in the literature for decades. Two caveats. Change the de-vig method and the magnitude moves; the direction holds, the number doesn't. And a slope above one describes the shape of the forecast — it is not a claim that you could make money. Commission, stake limits, line movement: none of that is in here.

**中** 第一个实质结果。按比例抽掉水钱、拟合校准斜率，得到 1.086，区间整段在一以上，所以不是噪声。斜率大于一是什么意思？概率被压向中间：冷门标贵了，热门标便宜了。这就是冷门—热门偏差，文献里几十年了。两个限定。换一种去水方法，量级会动；方向站得住，数字站不住。还有，斜率大于一只描述预测的形状，没说你能靠它赚钱——佣金、投注上限、临场走盘，一样都不在这里面。

### S4 · M3 ZHOU Yixuan · P7–P8 · 4:50–6:25

**[P7 · 4:50–5:42] How far behind — and where the gap is not**

**EN** Second hypothesis, and this is where I have to correct my own plan. I pre-registered B4, the time-decayed Dixon–Coles, as our best transparent arm. It isn't; B2 sits closer. Both intervals are on the slide, both above the margin — the gap is real. We chose B4 because it's the default opponent in this literature, and because it freezes before kick-off — same information timing as the market, which is what makes the comparison fair. But B2's lead is partly a rule, not a model — it updates its ratings inside the season, B4 doesn't. Freeze that, and the lead reverses. H3: one sign right, one wrong. Descriptive only.

**中** 第二个假设，也是我得改自己方案的地方。我预注册的是 B4，带时间衰减的 Dixon–Coles，作为最好的透明臂。它不是，B2 更近。两个区间都在这页上，都在边际之上——差距是真的，不是测不出来。选它挂头条，是因为它是这类文献的默认对手，而且在开赛前冻结参数：和市场同一个信息时点，比较才公平。但 B2 的领先有一部分来自规则，不是来自模型——它赛季内会更新评分，B4 不动。把这一条也冻上，领先就没有了，还会反过来。H3 是：一个系数符号对，一个反了，只作描述。

**[P8 · 5:42–6:25] Information, not calibration**

**EN** H4 asks whether the gap is only calibration. If it were, recalibrating the market against itself would close most of it. I did that: two parameters, fitted on the market's probabilities, applied forward — the gap barely moves. Then the cheating version, fitting on the test labels themselves: even that recovers only 8.7 percent. So the gap is information. Team news — who was bought in July, who's injured. Motivation — a relegation fight, a cup tie on Tuesday. What happens inside the ninety minutes. The price aggregates all of it; our features don't.

**中** H4 问的是：差距是不是只是校准问题。如果是，把市场自己的概率拿来对自己重校准，差距该消掉大半。我做了：两个参数，用市场自己的概率拟合，往前应用——差距几乎不动。再给一个作弊版，两个参数直接对着测试标签拟合，即便这样也只补回 8.7%。所以差距是信息。阵容消息——夏天买了谁、谁伤了；动机——保级生死战、下周二还有杯赛；还有那九十分钟里发生的事。价格把这些都聚合进去了，我们的特征没有。

### S5 · M5 SHU Peixuan · P9–P10 · 6:25–7:50

**[P9 · 6:25–7:17] What the models get wrong instead**

**EN** We expected one global story: models are overconfident. That's not what the data say. Class by class, draws really are over-dispersed — the boosted arms collapse there. But home and away go the other way, under-dispersed. So capacity isn't making the model uniformly confident; it's twisting the three classes in opposite directions. And one correction I owe you. After we fixed the smoothing, all three error summaries went up while all three slopes moved toward one — two summaries, opposite signals. I trust the slope, and the slide says why: when they disagree, only one of them can be the decision statistic.

**中** 我们本以为有一个统一的故事：模型过度自信。数据不这么说。逐类看，平局确实过度离散——两个提升臂在那儿塌了。但主胜和客胜反过来，分散不足。所以容量不是让模型整体更自信，而是把三类往相反方向扭。还有一句自我更正：改完平滑口径，三个误差摘要全部上升，三个斜率全部向一靠——两个摘要，相反信号。我信斜率，幻灯片上写了为什么：两个摘要打架的时候，只能有一个当判定统计量。

**[P10 · 7:17–7:50] A negative result, by design**

**EN** So: a negative result, but negative in a narrow sense. We didn't beat the market. We learned why not — the gap is information, not a defect we could have repaired. Three limits. One sport. Closing prices only. And forty-eight blocks cannot resolve anything finer than our margin: that's not a demand we set, it's the resolution of the instrument we built. One command rebuilds every number here. Contributions and the appendix are in the report. Thank you.

**中** 所以这是一个负结果，但"负"是很窄的意思。我们没赢过市场，我们弄清楚了为什么赢不了——差距是信息，不是我们本可以修好的缺陷。三条限制：只有一种运动；只有收盘价；四十八块分辨不出比我们的边际更细的差——那不是我们提的要求，是我们造出来的仪器的分辨率。一条命令重建这里每个数。贡献声明和附录在报告里。谢谢。

## 4. 录制与交接

1. **分段独立录**，一人一段，段首留 1 秒静场；不要拍交接动作，剪辑按四个时间码对齐。
2. **不要念屏幕上的数**。v3 已经把成串读数删掉：页 3 的臂名、页 4 / 页 7 的区间端点、页 9 的斜率。说到"这页上那个数"时用手或激光笔指一下，再讲它意味着什么——指着说比念出来可信。
3. **必须念准的三个数**：P2 的 `46,507`、P6 的 `1.086`、P8 的 `8.7`。其余数字都以"大约""四分之一""差得远"这类相对说法出现，念错的风险低。
4. **nats 那段（P4）是全片唯一的单位解释**，不许省。省掉之后后面每个数字对听众都是无意义的符号。
5. **禁语**：`accuracy`、`M0–M4` 当模型名、"B4 是最好的透明臂"、"45 块满格"、"8 个赛季有赔率"（正确说法：13 个赛季有）。
6. **超时处置**：删 P1 末句（"Before I say how far behind... check the ruler."）与 P3 的三件事罗列，可省约 15 秒；不要整体加速。
7. **五人出镜**：S1–S5 各一次，缺任何一段都无法覆盖"全员出镜"。
8. **别把稿子念成诵读**：每段第一句允许看着镜头说完再低头；"So / But / Now"是换气点，不是要念的标点。
