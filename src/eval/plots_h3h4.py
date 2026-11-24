"""fig08 的生成器：H3（局部化，描述性）+ H4（重校准能解释多少 gap）。

这张图此前**全仓没有生成脚本**（`grep -r fig08_localisation_recal` 零命中），所以
2026-11-24 之后它一直停在旧数字上：early 系数印的是 −0.0108（应为 −0.0107）、H4 上界
印的是 0.011（应为 0.013）、点估计印的是 0.0017（应为 0.0019）。本模块按 `plots_main`
的同一条纪律写成：**只从已落盘的 CSV 画，不重算任何模型**，并接到 ``run_m2`` 的出口。

- 左面板 ← ``results/logs/h3_sensitivity.csv``（三种 early 定义 × 两个系数 + 90% 簇区间）
- 右面板 ← ``results/logs/m2_verdicts.csv``（H4 行，重校准的相对变化与区间）
           + ``results/logs/h4_oracle_bound.csv``（用 test 标签拟合两参数的 oracle 上界）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIG_DIR = ROOT / "products" / "figures"
LOGS = ROOT / "results" / "logs"

# H4 判据线：重校准后 gap 的相对变化若超过 25%，才算「差距主要是校准缺陷」。
H4_THRESHOLD = 0.25


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _h4_rows(verdicts: pd.DataFrame) -> tuple[float, float, float, float]:
    """从判定表与 oracle 表读出 H4 的四个数：(rel, lo, hi, rel_oracle)。"""
    row = verdicts[verdicts.hypothesis.str.startswith("H4")].iloc[0]
    orc = pd.read_csv(LOGS / "h4_oracle_bound.csv").iloc[0]
    return float(row.point), float(row.lo), float(row.hi), float(orc["rel"])


def _label(d: str) -> str:
    """三种 early 定义 → 上屏英文标签。图里不能出现中文（DejaVu 无 CJK 字形）。"""
    if d.startswith("min"):
        return "min(home, away)  ·  main"
    if d.startswith("max"):
        return "max(home, away)"
    return "home team only  ·  retired"


def plot_localisation_recal(verdicts: pd.DataFrame | None = None, out_path=None):
    """fig08：左＝H3 系数（三种定义），右＝H4 重校准能把 gap 解释掉多少。"""
    plt = _plt()
    if verdicts is None:
        verdicts = pd.read_csv(LOGS / "m2_verdicts.csv")
    sens = pd.read_csv(LOGS / "h3_sensitivity.csv")
    rel, rel_lo, rel_hi, rel_oracle = _h4_rows(verdicts)

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(11, 4.0),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    # ---------------- 左：H3 系数（描述性） ----------------
    # 主版 min(home, away) 用实心点，另两种定义用空心点，避免读者以为三条都是主结论。
    defs = list(sens["definition"])
    vgap = len(defs) + 1
    ypos = np.array([-(i * vgap + j) for i in range(2) for j in range(len(defs))],
                    dtype=float)
    k = 0
    for tag, color in (("early", "#b2182b"), ("promoted", "#2166ac")):
        for j in range(len(defs)):
            y = ypos[k]
            k += 1
            c = sens.iloc[j][f"{tag}_coef"]
            lo = sens.iloc[j][f"{tag}_lo"]
            hi = sens.iloc[j][f"{tag}_hi"]
            main = j == 0
            ax0.errorbar(c, y, xerr=[[c - lo], [hi - c]], fmt="o",
                         ms=7 if main else 5,
                         mfc=color if main else "white", mec=color, ecolor=color,
                         capsize=3, lw=1.4)
    ax0.axvline(0.0, color="#555", ls="--", lw=1)
    ax0.set_yticks(ypos)
    ax0.set_yticklabels([f"early · {_label(d)}" for d in defs]
                        + [f"promoted · {_label(d)}" for d in defs], fontsize=7)
    ax0.set_xlabel("Coefficient on log-loss gap  (nats, 90% cluster CI)")
    ax0.set_title("H3 — the gap is not localised (descriptive only)", fontsize=9.5)
    ax0.set_ylim(ypos[-1] - 0.6, ypos[0] + 0.6)
    ax0.set_xlim(-0.022, 0.024)

    # ---------------- 右：H4 相对变化 ----------------
    xs = [100 * rel, 100 * rel_oracle]
    names = ["B6r — two-parameter\nrecalibration", "oracle — fitted on\nthe test labels"]
    ys = [1.0, 0.0]
    ax1.axvline(100 * H4_THRESHOLD, color="#b2182b", ls="--", lw=1.2)
    ax1.text(100 * H4_THRESHOLD, 1.55, "decision line 25%", color="#b2182b",
             fontsize=7.5, ha="right", va="bottom")
    ax1.errorbar(xs[0], ys[0], xerr=[[xs[0] - 100 * rel_lo], [100 * rel_hi - xs[0]]],
                 fmt="o", color="#1f4e9c", capsize=4, ms=7, lw=1.4)
    ax1.plot(xs[1], ys[1], "o", color="#555", ms=7)
    ax1.set_yticks(ys)
    ax1.set_yticklabels(names, fontsize=7.5)
    ax1.set_ylim(-0.7, 1.7)
    ax1.set_xlim(-3, 30)
    ax1.set_xlabel("Relative change in the model–market gap  (%)")
    ax1.set_title("H4 — recalibration explains almost none of it", fontsize=9.5)
    ax1.annotate(f"{xs[0]:+.2f}%  (90% CI {100 * rel_lo:+.2f} to {100 * rel_hi:+.2f})",
                 (xs[0], ys[0]), xytext=(6, 14), textcoords="offset points",
                 fontsize=7.5, color="#1f4e9c")
    ax1.annotate(f"{xs[1]:+.1f}%  (upper bound)", (xs[1], ys[1]),
                 xytext=(6, 10), textcoords="offset points", fontsize=7.5, color="#555")

    fig.suptitle("fig08 · H3 coefficients are descriptive; H4 says the gap is information, not calibration",
                 fontsize=9.5)
    fig.tight_layout()
    out = Path(out_path) if out_path else FIG_DIR / "fig08_localisation_recal.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    p = plot_localisation_recal()
    print(f"已写入 {Path(p).relative_to(ROOT)}")
