"""M5 图单里两张「主结果图」的生成器：fig03（九臂）与 fig04（C1/C2 等价性）。

这两张图原先只有 PNG、没有生成脚本，于是 2026-11-24 把 B4 口径改成常量超参后它们仍停在
旧数字上（B4 = 0.9939、C1 = 0.0142）。本模块把它们接到 ``run_m2`` 的出口，和
``market_gap.plot_market_gap``（fig07）一样的待遇：**图只从已落盘的 CSV 画，不重算任何模型**。

- fig03 ← ``results/table_main.csv``（9 行 + deff），与报告 Table 4.1 同源。
- fig04 ← ``results/logs/m2_verdicts.csv`` 的 C1 / C2 两行，与 §4.4 同源。

两张图的标题里都印着点估计与 90% 区间，所以图会自动跟着表走；这正是当初该做而没做的事。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIG_DIR = ROOT / "products" / "figures"
ARMS = ["B0", "B1", "B2", "B3", "B4", "B5a", "B5b", "B6", "B6r"]


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def plot_arms(table_main: pd.DataFrame | None = None, out_path=None):
    """fig03：九臂 pooled log loss + 90% 簇 bootstrap 区间，按从差到好自下而上排。"""
    plt = _plt()
    if table_main is None:
        table_main = pd.read_csv(ROOT / "results" / "table_main.csv")
    t = table_main.set_index("arm")
    arms = [a for a in ARMS if a in t.index]
    # 画图顺序：loss 从高到低自上而下（与原图一致：顶部 B0 最差）
    order = sorted(arms, key=lambda a: -t.loc[a, "log_loss"])

    b6 = float(t.loc["B6", "log_loss"]) if "B6" in t.index else np.nan
    fig, ax = plt.subplots(figsize=(10, 0.5 * len(order) + 1.6))
    ypos = list(range(len(order)))[::-1]
    for y, arm in zip(ypos, order):
        r = t.loc[arm]
        ax.errorbar(r["log_loss"], y,
                    xerr=[[r["log_loss"] - r["ll_lo90"]], [r["ll_hi90"] - r["log_loss"]]],
                    fmt="o", color="#1f77b4", capsize=3, ms=6)
    ax.axvline(b6, color="#d62728", lw=1.2, ls="--", label="B6 (de-vigged market)")
    ax.set_yticks(ypos)
    ax.set_yticklabels(order)
    ax.set_xlabel("log loss (nats/match)")
    ax.set_title("fig03: 9 arms, pooled log loss with 90% cluster-bootstrap CI")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", ls=":", alpha=0.5)
    fig.tight_layout()
    p = Path(out_path) if out_path is not None else FIG_DIR / "fig03_arms.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def plot_c_equivalence(verdicts: pd.DataFrame | None = None, out_path=None):
    """fig04：C1 / C2 的 Δ 与 ±0.02 等价带。标题数字取自 ``m2_verdicts.csv``。"""
    plt = _plt()
    if verdicts is None:
        verdicts = pd.read_csv(ROOT / "results" / "logs" / "m2_verdicts.csv")
    v = verdicts.set_index("hypothesis")

    specs = [
        ("C1", "C1 (B4 → B5a)", "Δ log loss (nats) · > 0 = B4 better, < 0 = B5a better"),
        ("C2", "C2 (B5a → B5b)", "Δ log loss (nats) · > 0 = B5a better, < 0 = B5b better"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.2), sharey=True)
    for ax, (key, title, xlab) in zip(axes, specs):
        r = v.loc[key]
        ax.axvspan(-0.02, 0.02, color="0.85", alpha=0.45)
        ax.axhline(0, color="0.25", lw=1.0)
        ax.axvline(0.02, color="0.45", lw=1.0, ls="--")
        ax.axvline(-0.02, color="0.45", lw=1.0, ls="--")
        ax.errorbar(r["point"], 0,
                    xerr=[[r["point"] - r["lo"]], [r["hi"] - r["point"]]],
                    fmt="o", color="#d62728", capsize=5, ms=7)
        ax.set_title(f"{title}\nΔLL = {r['point']:+.4f} (90% [{r['lo']:+.4f}, {r['hi']:+.4f}])",
                     fontsize=10)
        ax.set_xlabel(xlab, fontsize=9)
        ax.set_xlim(-0.045, 0.045)
        # 必须显式给 ylim：所有点都在 y=0 上，轴范围会退化成零高度，
        # 渲染时 `axhline` 的变换算出溢出整数，matplotlib 直接抛 TypeError。
        ax.set_ylim(-1.0, 1.0)
        ax.set_yticks([])
        ax.grid(axis="x", ls=":", alpha=0.5)
        ax.text(-0.0435, 0.62, "equivalence band ±0.02", fontsize=8.5, color="0.35")
    fig.suptitle("fig04: controlled comparisons vs the ±0.02 equivalence margin", fontsize=11)
    fig.tight_layout()
    p = Path(out_path) if out_path is not None else FIG_DIR / "fig04_c_equivalence.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def main() -> int:
    a = plot_arms()
    b = plot_c_equivalence()
    for p in (a, b):
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size:,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
