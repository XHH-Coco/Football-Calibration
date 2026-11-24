"""M5 报告数字校验：把 §5.1 / §5.2 / §5.4、摘要与幻灯片里出现的每个关键数字钉到产物 CSV 上。

**为什么需要它**：2026-11-24 一天之内，同一类事故犯了三次——

1. 摘要与幻灯片写「B4 落后 0.035」，而 `table_main.csv` 里 B4 与 B6 的差是 0.0317，最好的
   透明臂是 B2（0.0270）而不是 B4；
2. §5.2 写「draw ECE 从 0.030 降到 0.018」，实测是 0.0107 **升到** 0.0179，0.030 在任何
   产物里都不存在；
3. 幻灯片页 8 写「H4 相对 0.0017、上界 0.011」，现行判定表是 0.0019 / 0.0127。

三次都通过了 `pytest`（205 passed）、`check_m4`（14/14）与 `m3_report_tables --check`
（9/9）——因为那三道关卡检查的是**代码与产物**，没有一道检查**正文数字是否等于产物**，
而 §5.2 连 `--check` 都没有。

**做法**：不重算任何模型，只做两件事——
① 从已落盘 CSV 取出应有的值；② 断言正文里确实写着这个值（正则捕获 + 数值比较）。
每条规则都带出处，失败信息会同时打印「正文写的」与「产物里的」。

用法：
    python -m src.report.m5_report_tables            # 校验
    python -m src.report.m5_report_tables --list     # 只列出规则与出处
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "products" / "report"
SLIDES = ROOT / "products" / "slides"
LOGS = ROOT / "results" / "logs"

MINUS = ("−", "–", "—")
NUM = r"([−–—\-]?\d+(?:\.\d+)?)"


def _f(s: str) -> float:
    """把正文里的数字转成 float；兼容 Unicode 减号与短破折号。"""
    t = s.strip()
    for m in MINUS:
        t = t.replace(m, "-")
    return float(t)


def _load():
    tm = pd.read_csv(ROOT / "results" / "table_main.csv").set_index("arm")
    vd = pd.read_csv(LOGS / "m2_verdicts.csv")
    sl = pd.read_csv(LOGS / "m5_calibration_slopes.csv")
    slopes = sl.pivot(index="arm", columns="cls", values="slope")
    orc = pd.read_csv(LOGS / "h4_oracle_bound.csv").iloc[0]
    ref = pd.read_csv(LOGS / "sens_refresh_parity.csv")
    h3 = pd.read_csv(LOGS / "h3_sensitivity.csv").iloc[0]
    return tm, vd, slopes, orc, ref, h3


def _vrow(vd: pd.DataFrame, prefix: str) -> pd.Series:
    hit = vd[vd.hypothesis.str.startswith(prefix)]
    if len(hit) != 1:
        raise SystemExit(f"m2_verdicts.csv 里以 {prefix!r} 开头的行数为 {len(hit)}，应为 1")
    return hit.iloc[0]


def _row_numbers(path: Path, marker: str) -> list[float | None]:
    """把 Markdown 表格里含 marker 的那一行，按列切成数字（非数字列返回 None）。"""
    for line in path.read_text(encoding="utf-8").splitlines():
        if marker in line and line.lstrip().startswith("|"):
            cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
            out: list[float | None] = []
            for c in cells:
                try:
                    out.append(_f(c))
                except ValueError:
                    out.append(None)
            return out
    return []


def build_checks():
    """返回 [(文件, 标签, 正则(单捕获组), 期望值, 容差, 出处)]。"""
    tm, vd, slopes, orc, ref, h3 = _load()
    h1, h4 = _vrow(vd, "H1 斜率"), _vrow(vd, "H4")
    c1, c2 = _vrow(vd, "C1"), _vrow(vd, "C2")

    b2_gap, b4_gap = tm.loc["B2", "delta_vs_B6"], tm.loc["B4", "delta_vs_B6"]
    b2_lo, b2_hi = tm.loc["B2", "delta_vs_B6_lo90"], tm.loc["B2", "delta_vs_B6_hi90"]
    b4_lo, b4_hi = tm.loc["B4", "delta_vs_B6_lo90"], tm.loc["B4", "delta_vs_B6_hi90"]
    t3 = 6e-4          # 正文写到 3 位小数时的最大舍入误差

    abstract = REPORT / "report.md"
    s52 = REPORT / "section_5_2_h1_calibration.md"
    s54 = REPORT / "section_5_4_h2.md"
    s51 = REPORT / "section_5_1_ablation.md"
    deck = SLIDES / "slides.md"

    checks = [
        # ---------- 摘要 ----------
        (abstract, "摘要 · B2 的 H2 差距",
         r"trails the market by " + NUM + r" nats per match \(90% CI", b2_gap, t3,
         "table_main.csv · B2.delta_vs_B6"),
        (abstract, "摘要 · B2 差距区间下界",
         r"nats per match \(90% CI " + NUM + r"–", b2_lo, t3,
         "table_main.csv · B2.delta_vs_B6_lo90"),
        (abstract, "摘要 · 预注册臂 B4 的差距",
         r"and the pre-registered arm by " + NUM + r" \(", b4_gap, t3,
         "table_main.csv · B4.delta_vs_B6"),
        (abstract, "摘要 · H1 主斜率",
         r"proportional de-vigging slope is " + NUM + r" \(90% CI", h1.point, t3,
         "m2_verdicts.csv · H1 斜率>1（比例法）"),
        (abstract, "摘要 · H4 相对变化",
         r"relative " + NUM + r", 90% upper", h4.point, t3,
         "m2_verdicts.csv · H4 重校准相对变化"),
        (abstract, "摘要 · H4 上界",
         r"90% upper " + NUM + r" < 0\.25", h4.hi, t3,
         "m2_verdicts.csv · H4 · hi"),
        (abstract, "摘要 · C1 代价",
         r"to boosted trees costs " + NUM + r" nats", c1.point, 1.5e-3,
         "m2_verdicts.csv · C1"),
        (abstract, "摘要 · C2 买回",
         r"buys back " + NUM, abs(c2.point), 1.5e-3,
         "m2_verdicts.csv · C2（正文写绝对值）"),

        # ---------- §5.2 ----------
        (s52, "§5.2 · H1 主斜率与区间",
         r"calibration slope of " + NUM + r" \(90% cluster CI " + NUM + r"–" + NUM,
         (h1.point, h1.lo, h1.hi), t3,
         "m2_verdicts.csv · H1 主判据"),

        # ---------- §5.4 ----------
        (s54, "§5.4 · 头条臂 B2 落后",
         r"ordinal logit B2, by " + NUM + r" nats", b2_gap, t3,
         "table_main.csv · B2.delta_vs_B6"),
        (s54, "§5.4 · 预注册臂 B4 落后",
         r"designated protagonist B4 by " + NUM, b4_gap, t3,
         "table_main.csv · B4.delta_vs_B6"),
        (s54, "§5.4 · B4 差距 90% 区间",
         r"\(0\.0317, 90% CI " + NUM + r"–" + NUM, (b4_lo, b4_hi), t3,
         "table_main.csv · B4 90% 区间"),
        (s54, "§5.4 · H4 相对变化",
         r"changes the gap by a relative " + NUM, h4.point, t3,
         "m2_verdicts.csv · H4"),
        (s54, "§5.4 · oracle 相对上界",
         r"a relative change of \*\*\+" + NUM + r"%", 100 * orc["rel"], 0.05,
         "h4_oracle_bound.csv · rel ×100"),

        # ---------- §5.1 ----------
        (s51, "§5.1 · C1 点估计",
         r"\*\*\+" + NUM + r" nats\*\*, 90% CI \*\*\+", c1.point, t3,
         "m2_verdicts.csv · C1"),
        (s51, "§5.1 · C2 点估计",
         r"= \*\*" + NUM + r" nats\*\*, 90% CI \*\*[−–—\-]", c2.point, t3,
         "m2_verdicts.csv · C2"),
        (s51, "§5.1 · 六口径表里固定配置那一行的 C1",
         r"\| \*\*fixed \(3, 0\.01\) — reported\*\* \|[^|]*\|[^|]*\| \*\*\+" + NUM,
         c1.point, t3,
         "m2_verdicts.csv · C1"),

        # ---------- 幻灯片 ----------
        (deck, "幻灯页 7 · B2 差距区间",
         r"B2 落后 " + NUM + r"（" + NUM + r"–" + NUM, (b2_gap, b2_lo, b2_hi), t3,
         "table_main.csv · B2"),
        (deck, "幻灯页 7 · B4 差距",
         r"B4 落后 " + NUM, b4_gap, t3,
         "table_main.csv · B4"),
        (deck, "幻灯页 8 · H4 上界",
         r"相对变化 " + NUM + r"（90% 上界 " + NUM, (h4.point, h4.hi), t3,
         "m2_verdicts.csv · H4"),
        (deck, "幻灯页 4 · C1",
         r"换模型类多花 " + NUM, c1.point, t3,
         "m2_verdicts.csv · C1"),
        (deck, "幻灯页 4 · C2",
         r"加 30 个特征买回 " + NUM, abs(c2.point), t3,
         "m2_verdicts.csv · C2（正文写绝对值）"),
        (deck, "幻灯页 9 · 强化臂平局斜率",
         r"draw 过度离散（" + NUM + r" / " + NUM, (slopes.loc["B5a", "draw"],
                                                 slopes.loc["B5b", "draw"]), 6e-4,
         "m5_calibration_slopes.csv · B5a/B5b.draw"),
        (deck, "幻灯页 6 · H1 主斜率",
         r"比例法斜率 " + NUM + r"（90% CI " + NUM + r"–", (h1.point, h1.lo), t3,
         "m2_verdicts.csv · H1"),
    ]
    return checks, dict(tm=tm, slopes=slopes, ref=ref, h3=h3, vd=vd, orc=orc)


def table_checks(tm, slopes):
    """逐列比对：正文表格行 vs 产物。返回 [(文件, 标签, [(列名, 正文值, 期望值)])]。"""
    s52 = REPORT / "section_5_2_h1_calibration.md"
    specs = {
        "**B4 (time-decayed DC)**": "B4",
        "| B5a (HGB, B4 info) |": "B5a",
        "| B5b (HGB, +shots/rest) |": "B5b",
        "| B6 (market) |": "B6",
    }
    out = []
    for marker, arm in specs.items():
        cells = _row_numbers(s52, marker)
        vals = [c for c in cells if c is not None][-3:]     # 末三列 = home / draw / away
        want = [slopes.loc[arm, c] for c in ("home", "draw", "away")]
        out.append((arm, vals, want))
    return out


def ladder_check(tm):
    """阶梯顺序：正文点名的臂必须按 log loss 严格递增（B2 < B4 < B1 < B5b < B5a < B3）。"""
    order = ["B2", "B4", "B1", "B5b", "B5a", "B3"]
    vals = [tm.loc[a, "log_loss"] for a in order]
    return order, vals


def main(argv: list[str]) -> int:
    checks, ctx = build_checks()
    if "--list" in argv:
        for f, label, _pat, _exp, _tol, src in checks:
            print(f"{f.name:38s} {label:42s} ← {src}")
        return 0

    n_pass = n_fail = 0
    print("M5 报告数字校验（正文 vs 产物 CSV）\n")

    for path, label, pattern, expected, tol, src in checks:
        text = path.read_text(encoding="utf-8")
        hits = re.findall(pattern, text)
        if not hits:
            print(f"FAIL  {path.name} · {label}：模式未命中（正文里找不到这个数）  ← {src}")
            n_fail += 1
            continue
        bad = []
        for hit in hits:
            got_t = hit if isinstance(hit, tuple) else (hit,)
            exp_t = expected if isinstance(expected, tuple) else (expected,)
            try:
                got_f = [_f(g) for g in got_t]
            except (TypeError, ValueError):
                print(f"FAIL  {path.name} · {label}：捕获 {got_t!r} 无法解析为数字  ← {src}")
                n_fail += 1
                bad = None
                break
            bad += [(g, e) for g, e in zip(got_f, exp_t) if abs(g - e) > tol]
        if bad is None:
            continue
        if bad:
            shown = ", ".join(f"正文 {g:+.4f} vs 产物 {e:+.4f}" for g, e in bad)
            print(f"FAIL  {path.name} · {label}：{shown}  ← {src}")
            n_fail += 1
        else:
            # 同一组数字在正文里可能出现在多处（正文表格 + 版本差异表）：全部都要对
            tag = "" if len(hits) == 1 else f"（{len(hits)} 处一致）"
            print(f"PASS  {path.name} · {label} = "
                  + ", ".join(f"{x:+.4f}" for x in got_f) + tag)
            n_pass += 1

    # 表格逐列
    for arm, vals, want in table_checks(ctx["tm"], ctx["slopes"]):
        if len(vals) != 3:
            print(f"FAIL  section_5_2 · 斜率表 {arm} 行解析出 {len(vals)} 列（应为 3）")
            n_fail += 1
            continue
        bad = [(v, w) for v, w in zip(vals, want) if abs(v - w) > 1.5e-3]
        if bad:
            print(f"FAIL  section_5_2 · 斜率表 {arm}：" +
                  ", ".join(f"正文 {v:.3f} vs 产物 {w:.3f}" for v, w in bad))
            n_fail += 1
        else:
            print(f"PASS  section_5_2 · 斜率表 {arm} = "
                  + " / ".join(f"{v:.3f}" for v in vals))
            n_pass += 1

    # 阶梯顺序
    order, vals = ladder_check(ctx["tm"])
    if all(a < b for a, b in zip(vals, vals[1:])):
        print("PASS  table_main · 阶梯顺序 " + " < ".join(
            f"{a} {v:.4f}" for a, v in zip(order, vals)))
        n_pass += 1
    else:
        print("FAIL  table_main · 阶梯顺序与 §5.4 自述不符：" +
              ", ".join(f"{a} {v:.4f}" for a, v in zip(order, vals)))
        n_fail += 1

    # 刷新额度（§5.4 引用的两个数必须能从 per-block 表算出）
    ref = ctx["ref"]
    n = ref["n"].to_numpy(float)
    frozen_b2 = float((ref["B2_frozen"] * n).sum() / n.sum())
    rolled_b2 = float(ctx["tm"].loc["B2", "log_loss"])
    gap_frozen = frozen_b2 - float(ctx["tm"].loc["B6", "log_loss"])
    for label, got, want, tol, note in (
        ("§5.4 · 刷新额度 B2", round(frozen_b2 - rolled_b2, 3), 0.012, 6e-4,
         "+0.0116"),
        ("§5.4 · 拉平后的 H2 稳健性", round(gap_frozen, 3), 0.039, 6e-4, "0.0385"),
    ):
        if abs(got - want) <= tol:
            print(f"PASS  {label} = {got:+.3f}（正文 {note}）")
            n_pass += 1
        else:
            print(f"FAIL  {label}：算出 {got:+.3f}，正文写 {want:+.3f}")
            n_fail += 1

    print(f"\n{n_pass} passed, {n_fail} failed")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
