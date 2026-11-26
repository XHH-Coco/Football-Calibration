# DESIGN.md — Market-Audit deck（10 页 · 16:9 · 学术风）

> 用途：DSC5001 期末汇报（Canvas 提交 `Project Slides (PDF)` 的 pptx 母版）。
> 唯一事实源：文案数字取自 `results/table_main.csv` / `results/logs/m2_verdicts.csv`，
> 页序与主讲人取自 `../slides.md`（同版本）。改任何数字前先跑
> `python -m src.report.m5_report_tables --check`。

## 1. 全局视觉约定

### ① 画布与安全区

| 项 | 值 |
|---|---|
| 画布 | 1280 × 720（16:9） |
| padding | 上下 60 / 左右 60 → 内容区 **1160 × 600**（y 60–660） |
| 页眉 | 内容页统一 A3 变体：kicker 行（13px）+ 主标（34px）+ 主标题下 1px 细线 |
| 页尾 | y 640–660 一行（14px），左＝课程与学校，右＝`Team 32 · n/10` |
| 豁免 | 封面 P1 与结束页 P10 不设页眉/页尾（Hero 页） |

### ② 配色

| 槽位 | hex | 用途 |
|---|---|---|
| 主色 | `#1E4FA8` | kicker、编号、强调、深蓝块 |
| 深主色 | `#0E3F8C` | 主标题、封面大标题 |
| 辅色 | `#E8EFF8` / `#F0F5FC` | 卡片底、结论条底 |
| 中蓝 | `#3D7BD9` | 第二强调、图注标签 |
| 强调红 | `#D9534F` | 仅 P4 / P7 用于「跨 0 / 不下结论」标记，单页 ≤3% |
| 文本 | `#1A2230` / `#4A5568` / `#8B97A8` | 主 / 副 / 辅助 |
| 线框 | `#D6DCE5` | 分区线、卡片描边 |
| 底色 | `#FFFFFF` / `#F7F9FC` | 页面 / 交替底 |

金色 0；无渐变卡底；红黄合计 <5%。

### ③ 字体

| 层级 | 字号 / 字重 | 家族 |
|---|---|---|
| 封面英文主标题 | 46 / bold | Georgia, serif |
| 页主标 | 34 / bold | Arial, Microsoft YaHei |
| 卡内标题 | 24 / bold | 同上 |
| 正文 | 22 / regular | 同上 |
| KPI 数字 | 44 / bold | 同上 |
| 注解 / 页脚 | 15 / 14 | 同上 |

### ④ 视觉母题

全篇一个：**主标题下方 1px 贯通细线（`#D6DCE5`，宽 1160）**，只出现在标题区，不下放到卡片。

### ⑤ 配图清单（跨页全局）

| 文件 | 用途 | 来源 | 真实内容 | 页 |
|---|---|---|---|---|
| `assets/fig04.png` | evidence | 材料图（`products/figures/fig04_c_equivalence.png` 裁去图内总标题） | C1 / C2 等价区间两块 | P4 |
| `assets/fig06.png` | anchor | 同上 `fig06_market_calibration.png` | 三法校准斜率 + 分位数偏差 | P7 |
| `assets/fig07.png` | anchor | 同上 `fig07_market_gap.png` | 八臂与市场的配对 ΔLL | P8 |
| `assets/fig08_right.png` | evidence | 同上 `fig08_localisation_recal.png` 右面板 | H4：重校准与 oracle 的相对变化 | P9 |

`fig05_model_reliability.png` **v4 起不上屏**（资产仍留在 `assets/`）：它要占满整幅宽度才读得出三条曲线的斜率，
而 P9 的论点是「误差不是一个可以减掉的偏移」，逐类斜率用一行读数（0.528 / 0.566 对 1.08–1.11）比三幅
曲线更快到位。`fig08_left.png`（H3 系数）仍不上屏——H3 只作描述，占版面会抢 P8 的 H2 头条。

P2 / P3 / P5 / P6 不贴位图，用原生矢量绘制，理由：P2 的覆盖率热图是 6×22 网格，缩到 16:9 不可读；
P3 的阶梯图 `fig01` 黑底块上文字对比度不足，改为矢量重绘（信息与 `fig01` 一致）；P6 的四行假设表
直接用文本排（表格图会失去可复制性）。

## 2. 逐页字段表

| 页 | title | type | role | layout | visual | density | anti_pattern |
|---|---|---|---|---|---|---|---|
| 1 | The market as a measuring instrument | cover | hero | 标题 + 双 RQ 卡 + 成员条 | 无图，矢量 | 约 120 字 / 0 图 / 留白 35% | 禁止等宽四卡横排；禁止抽象粒子背景 |
| 2 | 46,507 matches, three traps | content | supporting | 顶部三格 KPI 条 + 左 22 季时间轴 + 右「三个决定」卡 | 矢量时间轴（9 无赔率 / 5 有赔率未入选 / 8 评估窗） | 约 150 字 / 1 图 / 留白 8% | 禁止贴覆盖率热图；禁止把 48 与 16,733 并列成同权 KPI |
| 3 | A ladder, not a leaderboard | content | supporting | 九块阶梯 + 两次单因素标注 + 双 C 卡 | 矢量阶梯 | 约 150 字 / 1 图 / 留白 12% | 禁止九块等距不留标注；禁止给所有块同一强调色；**禁止在此页写 C1/C2 的数值**（数值属于 P4） |
| 4 | Scoring: log loss, and a margin of 0.02 nats | content | hero | 上双卡（分数 / 边际）+ 图注定性行 + 全宽区间图 + 判定条 | `fig04.png` | 约 160 字 / 1 图 / 留白 4% | 禁止把 C1 写成「B5a 更好」；禁止只报点估计不报区间；禁止用 accuracy；**禁止删掉图上方那行定性**（`this is the ruler's first use, not a finding`）或把措辞换成 finding / result / we find——删掉之后本页会被读成结果页，页序就退回「结论 → 方法 → 假设 → 结论」 |
| 5 | 48 blocks, not 16,733 matches | content | supporting | 左 rolling-origin 示意 + 右三行口径 | 矢量流程 | 约 140 字 / 1 图 / 留白 12% | 禁止把比赛数当独立样本；禁止只写 deff 不写换算 |
| 6 | Four hypotheses, falsified in advance | content | supporting | 四行表（ID / 猜测 / 证伪条件）+ 脚注 | 无图，表格 | 约 130 字 / 0 图 / 留白 18% | 禁止只写假设不写证伪条件；禁止把 H2 的两个区间水平合成一个 |
| 7 | The market is mildly under-dispersed | content | hero | 图 + 判定条 | `fig06.png` | 约 110 字 / 1 图 / 留白 8% | 禁止只报比例法斜率；禁止把三法画成同一结论 |
| 8 | How far behind — and where the gap is not | content | hero | 左双数字 + H3 注 + 右图 | `fig07.png` | 约 140 字 / 1 图 / 留白 8% | 禁止头条挂 B4；禁止把 H3 写成「支持」 |
| 9 | It is not an offset you can subtract | content | supporting | 左 H4 数字 + oracle 框 + 右图 + 逐类读数条 | `fig08_right.png` | 约 140 字 / 1 图 / 留白 10% | 禁止把 oracle 当模型成绩；禁止漏 25% 判据线；禁止把「draw 过散」说成整体过度自信 |
| 10 | A negative result, and what it buys | ending | hero | 三张「买到」卡 + 限制行 + 复现命令 | 无图 | 约 110 字 / 0 图 / 留白 30% | 禁止「未来展望」空话；禁止感谢页装饰；禁止只列限制不列买到什么 |

## 3. 上屏口径（与 `../slides.md` 锁定）

1. 标题与要点英文，口头讲解中文；每页一个点，正文 ≤6 行。
2. 每条 kicker 带步号（`STEP 3 / 7 · HOW WE COMPARE`），让听众随时知道在第几步——这是 v4 唯一的
   全局导航装置，改稿时不要换成主题词（`DESIGN · NINE ARMS` 之类）。
3. 区间一律标 `48-block cluster bootstrap, 10,000 resamples`；分联赛 / 轮次 sweep 标 `descriptive only`。
4. 只用 `B0`–`B6` + `B6r`，不出现 accuracy。
5. 关键数字只出现在 P4（C1/C2）、P7（H1 斜率）、P8（H2 gap / H3 系数）、P9（H4 / 逐类斜率）；P2 只有数据规模与缺陷计数。
6. 出镜：**M1 P1–P2 / M4 P3–P4 / M2 P5–P6 / M3 P7–P8 / M5 P9–P10**；时长合计 7:50，四个切点
   1:43 / 3:25 / 5:01 / 6:32。英文讲稿 `../script_en.md`。

## 4. 中文版（`Market-Audit-CN.pptx`）

同一份设计的译版，**版式零改动**：10 页、页序、页脚编号、图位与图尺寸全部与英文版一致，只替换文字。源文件在 `slides_cn/01–10.slide`，与 `slides/` 一对一。

### ① 译法约定

| 类别 | 处理 |
|---|---|
| 统计术语 | 保留英文：log loss、nats、bootstrap、cluster、deff、ESS、ECE、oracle、de-vig |
| 臂名 | `B0`–`B6` + `B6r` 原样；`arm` 译「臂」 |
| 专有名词 | Elo、Dixon–Coles、Shin / power / proportional、Pinnacle 原样 |
| 队名 / 联赛 | 法甲、荷甲（口径与报告 `section_3_data.md` 一致） |
| 图内文字 | **仍为英文**（图由 `src/eval/` 生成，改字体需改生成器，风险大于收益）；图注全中文 |
| 主标题字体 | Georgia → **Microsoft YaHei**（Georgia 无中文字形），P1 54px、P10 44px |

### ② 三条改稿纪律

1. **数字一个都不改**。`python -m src.report.m5_report_tables` 第 49 条对两版做测量型数字集合比对（含小数 / 千分位 / ≥3 位），中文版出现英文版没有的数即 FAIL。负向注入 `0.0113 → 0.0131` 已验证会红。
2. **中文段落写在一行内**。JSX 把行尾换行折叠为一个空格，中文句中断行会在渲染里留下「主胜 与客胜」这种空隙——本轮改了 13 处。全角标点（。；，）自带的字距不算问题，别去动。
3. **改稿走 `--page-index` 覆盖，不要重建 deck**。`slidep create` 产出的是 0 页文件，首次追加用不带 `--page-index` 的 `upsert-dsl`，之后按 0..9 覆盖。

### ③ 校验

`slidep lint` 10/10 无诊断；`slidep inspect` 逐页文字块坐标 max_x=1220、max_y=660，重叠 0；`slidep screenshot` 10 页逐页目视核对（含 2× 放大裁剪复检标点间距）。

## 5. 页 2 时间轴的订正（2026-11-25）

原图例把「赔率可得性」与「评估窗」画成同一刀：22 季里前 14 季标「无收盘赔率」。实测 `data/raw/` 逐季统计：

| 区间 | 季数 | 收盘赔率 |
|---|---|---|
| 2003/04 – 2011/12 | 9 | 完全没有 `PSCH/PSCD/PSCA` 三列 |
| 2012/13 – 2016/17 | 5 | 有，但不在评估窗内（6 个联赛-赛季部分缺失，覆盖 0.990–0.997） |
| 2017/18 – 2024/25 | 8 | 有，且是预注册评估窗（48 块） |

所以时间轴改成 **9 灰 / 5 中蓝 / 8 深蓝**三段，标题从「最近 8 季有赔率」改为「赔率自 2012/13 才有——13 季有」。两版 deck 同改，`script.md` 段 2 与 `script_en.md` 的 P2 台词同步。

## 6. v4 重排（2026-11-26）

页序从「按假设编号」改成「按读者要依次接受的四个判断」，与 `../../plain_zh.md` §1–§7 对应：

| 页 | v3 | v4 |
|---|---|---|
| 1 | 封面 + 双 RQ | **未改** |
| 2 | 46,507 / 16,733 / 时间轴 / 缺陷卡（左 KPI 三行） | 标题改 `46,507 matches, three traps`；KPI 改为顶部三格条，腾出的竖向空间给右侧「三个决定」卡（三个坑各配一个决定，含 243→241 队名） |
| 3 | The ladder B0–B6 + B6r | 改 `A ladder, not a leaderboard`；**移走 C1/C2 的数值**，只留两个定义 |
| 4 | C1 and C2 — the only two attributions we own | 改 `Scoring: log loss, and a margin of 0.02 nats`；上半页讲 log loss 与 0.02 两种读法，下半页用 `fig04` 当场量 C1/C2 |
| 5 | 48 blocks, not 16,733 matches | **未改**（kicker 改 `STEP 4 / 7`） |
| 6 | The market is under-dispersed | 换成 **Four hypotheses, falsified in advance**（新页，四行表） |
| 7 | How far behind | 换成 H1 读数（原 P6 内容前移一页） |
| 8 | Information, not calibration | 换成差距与 H3（原 P7 内容后移一页） |
| 9 | What the models get wrong instead | 换成 `It is not an offset you can subtract`：H4 + 逐类斜率一行读数 |
| 10 | A negative result, by design | 改 `A negative result, and what it buys`：三张「买到」卡 + 限制行 + 复现命令 |

三条纪律（改稿时保持）：

1. **kicker 的步号不许改**。`STEP n / 7` 是 v4 唯一的全局导航：听众在第 4 步知道自己在「怎么判」，
   在结果页知道还有两页。换成主题词就退回 v3 那种「十页并排」的观感。
2. **P3 不写数值**。C1 / C2 的 0.0055 与 0.0015 只出现在 P4——这是「先给尺子再给读数」的物理保证；
   一旦 P3 也写上，口播就会提前用掉 P4 的边际。
3. **P9 的一行读数与 `m5_calibration_slopes.csv` 对齐**：B5a/B5b 的 draw 0.528 / 0.566、home 1.103 /
   1.109、away 1.082 / 1.091；B4 三类 0.940 / 0.944 / 0.964；B6 三类 1.061 / 1.092 / 1.076。
   写成区间（1.08–1.11、0.94–0.96、1.06–1.09）是为了不念六个小数，但区间端点必须落在上面这些值上。
