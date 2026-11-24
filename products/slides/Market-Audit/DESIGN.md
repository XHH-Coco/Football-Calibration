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
| `assets/fig06.png` | anchor | 同上 `fig06_market_calibration.png` | 三法校准斜率 + 分位数偏差 | P6 |
| `assets/fig07.png` | anchor | 同上 `fig07_market_gap.png` | 八臂与市场的配对 ΔLL | P7 |
| `assets/fig08_right.png` | evidence | 同上 `fig08_localisation_recal.png` 右面板 | H4：重校准与 oracle 的相对变化 | P8 |
| `assets/fig05.png` | anchor | 同上 `fig05_model_reliability.png` | 三类可靠性曲线（B0/B4/B5b/B6） | P9 |

`fig08_left.png`（H3 系数）已裁出备查，本版不上屏——H3 只作描述，占版面会抢 P7 的 H2 头条。
P2 / P3 / P5 不贴位图，用原生矢量绘制，理由：P2 的覆盖率热图是 6×22 网格，缩到 16:9 不可读；
P3 的阶梯图 `fig01` 黑底块上文字对比度不足，改为矢量重绘（信息与 `fig01` 一致）。

## 2. 逐页字段表

| 页 | title | type | role | layout | visual | density | anti_pattern |
|---|---|---|---|---|---|---|---|
| 1 | The market as a measuring instrument | cover | hero | 标题 + 双 RQ 卡 + 成员条 | 无图，矢量 | 约 120 字 / 0 图 / 留白 35% | 禁止等宽四卡横排；禁止抽象粒子背景 |
| 2 | 46,507 matches, one of them incomplete | content | supporting | 左 KPI 三行 + 右 22 季时间轴 | 矢量时间轴 | 约 130 字 / 1 图 / 留白 10% | 禁止贴覆盖率热图；禁止把 48 与 16,733 并列成同权 KPI |
| 3 | The ladder B0–B6 + B6r | content | supporting | 九块阶梯 + 两次单因素标注 | 矢量阶梯 | 约 150 字 / 1 图 / 留白 12% | 禁止九块等距不留标注；禁止给所有块同一强调色 |
| 4 | C1 and C2 — the only two attributions we own | content | supporting | 全宽区间图 + 双结论卡 | `fig04.png` | 约 130 字 / 1 图 / 留白 8% | 禁止把 C1 写成「B5a 更好」；禁止只报点估计不报区间 |
| 5 | 48 blocks, not 16,733 matches | content | supporting | 左 rolling-origin 示意 + 右三行口径 | 矢量流程 | 约 140 字 / 1 图 / 留白 12% | 禁止把比赛数当独立样本；禁止只写 deff 不写换算 |
| 6 | The market is under-dispersed | content | hero | 左图右数字 | `fig06.png` | 约 120 字 / 1 图 / 留白 8% | 禁止只报比例法斜率；禁止把三法画成同一结论 |
| 7 | How far behind — and where the gap is not | content | hero | 左数字右图 | `fig07.png` | 约 140 字 / 1 图 / 留白 8% | 禁止头条挂 B4；禁止把 H3 写成「支持」 |
| 8 | Information, not calibration | content | supporting | 左结论右图 | `fig08_right.png` | 约 110 字 / 1 图 / 留白 15% | 禁止把 oracle 当模型成绩；禁止漏 25% 判据线 |
| 9 | What the models get wrong instead | content | supporting | 全宽三联曲线 + 三行读数 | `fig05.png` | 约 130 字 / 1 图 / 留白 8% | 禁止把「draw 过散」说成整体过度自信；禁止不提 ECE 反向 |
| 10 | A negative result, by design | ending | hero | 三限制 + 复现命令 | 无图 | 约 100 字 / 0 图 / 留白 35% | 禁止「未来展望」空话；禁止感谢页装饰 |

## 3. 上屏口径（与 `../slides.md` 锁定）

1. 标题与要点英文，口头讲解中文；每页一个点，正文 ≤6 行。
2. 区间一律标 `48-block cluster bootstrap, 10,000 resamples`；分联赛 / 轮次 sweep 标 `descriptive only`。
3. 只用 `B0`–`B6` + `B6r`，不出现 accuracy。
4. 关键数字只出现在 P4（C1/C2）、P6（H1 斜率）、P7（H2 gap）、P8（H4 相对变化）。
5. 出镜：M5 P1、M1 P2、M3 P3、M4 P4、M2 P5·P6·P8、M5 P7、M1 P9·P10；时长合计 7:50。
