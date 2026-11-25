# Presentation script — 5 speakers · 7:50 (hard limit 8:00)

> 状态：2026-11-25 v2 · 与 `Market-Audit.pptx` / `Market-Audit-CN.pptx`（同页序）同版本
> 用途：Canvas `Project Presentation (MP4)` 的口播稿；五人按时间顺序各讲一段，一人一段不打断。
> 语速口径：英文 119–130 wpm（口语化改写的实测值）。下表"词数"是实测值，超 10% 就删句，不加速。
> 与 `script.md` 的关系：`script.md` 是逐页中文底稿（10 段），本文件是按人重切的英文成稿；两者页内内容一致，主讲人分配以本文件为准。
>
> **v2 改了什么**：措辞从"演示稿朗读"改成"课堂讲授"。具体是三件事——① 结论前先给推理过程（"0.0055，这算大吗？"）；② 加教学动作（预告易错点、自问自答、指认屏幕）；③ 去掉电报式短句与排比，允许口语冗余。数字与判定口径一字未改。

## 1. 分段与计时

| 段 | 主讲 | 成员 | 页 | 起止 | 时长 | 英文词数 | 折算语速 |
|---|---|---|---|---|---|---|---|
| S1 | M1 | WAN Yihui | P1–P2 | 0:00–1:25 | 1:25 | 184 | 130 wpm |
| S2 | M4 | SUN Peng | P3–P4 | 1:25–3:10 | 1:45 | 212 | 121 wpm |
| S3 | M2 | WANG Xingshuai | P5–P6 | 3:10–4:50 | 1:40 | 202 | 121 wpm |
| S4 | M3 | ZHOU Yixuan | P7–P8 | 4:50–6:25 | 1:35 | 189 | 119 wpm |
| S5 | M5 | SHU Peixuan | P9–P10 | 6:25–7:50 | 1:25 | 173 | 122 wpm |

**合计 960 词 / 7:50，余量 10 秒。** 四个剪辑切点：**1:25 / 3:10 / 4:50 / 6:25**。

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

**EN** Let me start with what this project is not. It's not a betting model — if we could beat the closing line, we'd be selling it, not presenting it. What we study is the closing price itself: the best public three-way forecast there is, used as a measuring instrument. So the question isn't can we beat it, it's where does it read badly. Does the market calibrate itself? And can a transparent model, pre-match information only, one command, get close? If it falls short, we either lack information or there's a defect to repair. Nine arms, four hypotheses.

**中** 先说清楚这项目不是什么。它不是赌博模型——真能稳定赢过收盘线，我们早去卖了，不会站在这儿讲。我们研究的是收盘价本身：目前最好的公开三分类预测器，把它当量尺用。所以问题不是能不能赢它，而是它哪儿读得不准。市场自己校准吗？一个只用赛前信息、一条命令就能复现的透明模型，追得上吗？追不上，差的要么是信息，要么是我们本可以修掉的偏差。九个臂、四个假设。

**[P2 · 0:45–1:25] 46,507 matches, one of them incomplete**

**EN** The data: six European leagues, twenty-two seasons, 46,507 matches. But here is what people miss. Pinnacle closing odds only start in 2012/13 — thirteen seasons out of twenty-two. So the evaluation window is the last eight, because that is where the market exists to compare against. Forty-eight league-season blocks, forty-six full size. The two short ones are both 2019/20: Ligue 1 stopped at 279, the Eredivisie at 232. One match in the window is missing six shot columns. Coverage 0.999940. We keep it missing. Never imputed.

**中** 数据是六个欧洲联赛、二十二个赛季、46,507 场。但这里有个坑：Pinnacle 收盘赔率 2012/13 才有，二十二季里只有十三季。所以评估窗取最后八季，不是因为我喜欢这个数，而是只有那儿才有市场可比。四十八个联赛-赛季块，四十六块满格；腰斩的两块都在 2019/20——法甲止于 279 场，荷甲止于 232 场。窗内还有一场缺六个射门列，覆盖率 0.999940。我们让它缺着，绝不补零。

### S2 · M4 SUN Peng · P3–P4 · 1:25–3:10

**[P3 · 1:25–2:20] The ladder B0–B6 + B6r**

**EN** I'll take the ladder. Nine arms, each rung adding one thing to the one below it: a frequency prior, Elo, an ordinal logit, independent Poisson, Dixon–Coles with time decay, two boosted-tree arms, and at the top the market and a recalibrated market. Now you might read that as a causal chain. It isn't. There are exactly two steps I'm willing to defend. B4 to B5a changes the model class and nothing else. B5a to B5b adds thirty features and nothing else. Those are the only two rungs in the whole ladder where one factor moves. Everywhere else several things change at once, so those arms get reported side by side and I attribute nothing to them.

**中** 阶梯由我来讲。九个臂，每一级在下一级基础上加一件事：频率先验、Elo、有序 logit、独立泊松、带时间衰减的 Dixon–Coles，然后两个提升树臂，顶上还有市场和再校准的市场。你可能会把它读成因果链。它不是。我只敢为两步背书：B4 到 B5a 只换模型类，别的都不动；B5a 到 B5b 只多三十个特征，别的都不动。整条阶梯只有这两级是一次只动一个因素。其余每一级都是几件事一起变，所以那些臂只并列摆着，我不给它们归因。

**[P4 · 2:20–3:10] C1 and C2 — the only two attributions we own**

**EN** C1 is the clean one. Same inputs, same weights, same training data — only the functional form changes, Poisson against Dixon–Coles. And it costs 0.0055 nats, interval 0.0009 to 0.0099. The interval excludes zero, so the difference is real; I can't wave that away. But is 0.0055 large? Our equivalence margin is 0.02, and the whole interval sits inside a quarter of it. So what I write down is: separable, practically equivalent. C2 adds thirty features and buys back 0.0015, and that interval crosses zero. At the top of the ladder, more capacity bought nothing measurable.

**中** C1 是最干净的一步。同样的输入、同样的权重、同样的训练数据——只换函数形式，泊松对 Dixon–Coles。代价 0.0055 nats，区间 0.0009 到 0.0099。区间不含零，所以差异是真的，这点我没法糊过去。但 0.0055 算大吗？我们的等价边际是 0.02，整段区间落在它的四分之一里。所以我写下来的是：可分辨，但实际等价。C2 加了三十个特征，换回 0.0015，区间跨零。阶梯顶上，加容量没换来任何可测的东西。

### S3 · M2 WANG Xingshuai · P5–P6 · 3:10–4:50

**[P5 · 3:10–4:00] 48 blocks, not 16,733 matches**

**EN** One methodological point, and it matters more than it sounds. The unit of evaluation here is not the match, it's the block. Before each season I refit once, on that league's earlier matches only, then score that season once. Forty-eight blocks, forty-eight evaluations. That's rolling origin. The intervals come from a cluster bootstrap: I resample whole blocks ten thousand times, not matches one at a time, because matches in a block share teams and fixtures and are not independent. Measured design effect 1.32 to 1.89, so intervals run 1.15 to 1.37 times the naive width. Ignore that and every interval here is too short.

**中** 一个方法上的点，它比听起来重要。评估单位不是比赛，是块。每季开赛前我重训一次，只用该联赛此前的比赛，然后把这季评一次。四十八块，四十八次评估——这叫滚动原点。区间用簇 bootstrap：整块重抽一万次，不是按比赛逐场抽，因为同一块里的比赛共享球队和赛程，不独立。实测设计效应 1.32 到 1.89，所以我的区间是朴素宽度的一点一五到一点三七倍。不认这一条，这几页上每个区间都会偏窄。

**[P6 · 4:00–4:50] The market is under-dispersed**

**EN** Now the first substantive result. Strip the vig proportionally, fit a calibration slope, and you get 1.086 — ninety percent interval 1.047 to 1.124, lower bound above one, so it isn't noise. What does a slope above one mean? Probabilities pulled toward the middle. Longshots priced too high, favourites too low. That's the favourite-longshot bias, and it has been in the literature for decades. Change the de-vig method and you get Shin at 1.052, power at 1.030 with an interval that crosses one. So: direction consistent, magnitude depends on how you de-vig. I won't quote a single number.

**中** 第一个实质结果。按比例抽掉水钱，拟合校准斜率，得到 1.086——九成区间 1.047 到 1.124，下界高于一，不是噪声。斜率大于一意味着什么？概率被压向中间：冷门标贵了，热门标便宜了。这就是冷门—热门偏差，文献里几十年了。换个去水方法，Shin 法 1.052，幂法 1.030 且区间跨一。所以：方向一致，量级取决于你怎么去水。我不挑一个数字报给你。

### S4 · M3 ZHOU Yixuan · P7–P8 · 4:50–6:25

**[P7 · 4:50–5:40] How far behind — and where the gap is not**

**EN** Second hypothesis, and this is where I have to correct my own plan. I pre-registered B4 as our best transparent arm. It isn't. B2, the ordinal logit, is better: it trails the market by 0.0270 nats, interval 0.0241 to 0.0298. B4 trails by 0.0317, interval 0.0278 to 0.0359. Both intervals sit entirely above 0.02, so it isn't the intervals being too wide. The gap is real. H3 I only describe: early rounds come out at minus 0.0108, the wrong sign; promotion widens the gap by 0.0113, the right one. Two mechanisms, one works. I claim neither.

**中** 第二个假设，也是我得改自己方案的地方。我预注册的是 B4 为最好的透明臂。它不是。B2，有序 logit，更好：落后市场 0.0270 nats，区间 0.0241 到 0.0298。B4 落后 0.0317，区间 0.0278 到 0.0359。两个区间都整体高于 0.02，所以不是区间太宽测不出。差距是真的。H3 我只描述：赛季初轮次是负 0.0108，符号反了；升班马把差距拉大 0.0113，符号对。两个机制，中一个。所以两个我都不宣称。

**[P8 · 5:40–6:25] Information, not calibration**

**EN** H4 asks whether the gap is only calibration. If it were, I could take the market's own probabilities and recalibrate them against themselves, and most of the gap should go away. So I did that: two parameters, temperature and bias, fitted on the market's probabilities. The relative gap moves 0.0019, upper bound 0.0127, and the decision line is 0.25. Nowhere near. Then the open-book version — fit both parameters on the test labels, which is cheating — and you still only recover 8.7 percent. So the gap is information the models don't have.

**中** H4 问的是：差距是否只是校准问题。如果是，我把市场自己的概率拿来对自己重校准一遍，差距该消掉一大部分。我做了：两个参数，温度和偏置，用市场自己的概率拟合。相对差距只动了 0.0019，九成上界 0.0127，判据线是 0.25。差得远。再给一个开卷版：两个参数都用测试标签拟合，这就是作弊，也只补回 8.7%。所以差距是模型没有的信息。

### S5 · M5 SHU Peixuan · P9–P10 · 6:25–7:50

**[P9 · 6:25–7:20] What the models get wrong instead**

**EN** We expected one global story: models are overconfident. That's not what the data say. Class by class, draws really are over-dispersed — B4 sits at 0.944, the two boosted arms collapse to 0.528 and 0.566. But look at home and away: 1.08 to 1.11, under-dispersed, the opposite direction. The market sits at 1.06 to 1.09 on all three. So capacity isn't making the model uniformly confident; it's twisting the classes in opposite directions. And one correction I owe you: after we fixed the smoothing, all three ECEs went up while all three slopes moved toward one. Two summaries, opposite signals. I trust the slope.

**中** 我们本以为有一个统一的故事：模型过度自信。数据不这么说。逐类看，平局确实过度离散——B4 是 0.944，两个提升臂掉到 0.528 和 0.566。但看胜负两类：1.08 到 1.11，分散不足，方向正好相反。市场三类都在 1.06 到 1.09。所以容量不是让模型整体更自信，而是把三类往相反方向扭。再补一句自我更正：改完平滑口径，三个 ECE 全部上升，三个斜率全部向一靠。两个摘要，相反信号。我信斜率。

**[P10 · 7:20–7:50] A negative result, by design**

**EN** So: a negative result — but negative in a narrow sense. We did not beat the market. We did learn why not. The gap is information, not a defect we could have repaired. Three limits: one sport, closing prices only, and forty-eight blocks can't resolve anything finer than 0.02 nats. One command rebuilds every number on these slides. Contributions and the home-advantage appendix are in the report. Thank you.

**中** 一个负结果——但"负"只说了一半。我们没赢过市场，但弄清楚了为什么赢不了。差距是信息，不是我们本可以修好的缺陷。三条硬限制：单一项目、只有收盘价、四十八块分辨不出比 0.02 nats 更细的差。一条命令重建这几页上的每个数。贡献声明和主场优势附录在报告里。谢谢。

## 4. 录制与交接

1. **分段独立录**，一人一段，段首留 1 秒静场；不要拍交接动作，剪辑按四个时间码对齐。
2. **数字最密的三处**：P4（C1/C2 四个区间端点）、P7（两组点估计加区间）、P9（六个斜率）。先把数字念准，再补语气。
3. **禁语**：`accuracy`、`M0–M4` 当模型名、"B4 是最好的透明臂"、"45 块满格"、"8 个赛季有赔率"（正确说法：13 个赛季有）。
4. **超时处置**：删 P1 末句（"Nine arms, four hypotheses."）与 P3 的臂名罗列，可省约 15 秒；不要整体加速。
5. **五人出镜**：S1–S5 各一次，缺任何一段都无法覆盖"全员出镜"。
6. **口播加粗数字时不加解释**：区间、上界这类词已写进句子，不要临场补充口径，补错比少说糟。
7. **别把稿子念成诵读**：每段开头的第一句允许看着镜头说完再低头看稿；"Now / So / But" 这类词是换气点，不是要念的标点。
