"""M2 / T2.9：H2 市场差距——``ΔLL = LL(arm) − LL(B6)``、``ΔBrier``，三法 × 8 臂。

- 主判定臂是 **B4**（H2 的主体）；B0–B5b + B6r 是稳健性（B6 作分母不单列）。
- 三种去抽水（proportional / power / Shin）下各算一遍，必须同号同量级。
- 区间：48 块簇 bootstrap；``n_paired`` 写进表注（B6 相关一律 16,728）。

产物：``results/market_gap.csv``、``products/figures/fig07_market_gap.png``。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.bootstrap import block_deltas, cluster_bootstrap  # noqa: E402

ARMS = ["B0", "B1", "B2", "B3", "B4", "B5a", "B5b", "B6r"]
DEVIG_METHODS = ["proportional", "power", "shin"]
PRED_DIR = ROOT / "results" / "preds"
LOG_DIR = ROOT / "results" / "logs"


def _load_pred(arm: str) -> pd.DataFrame:
    p = PRED_DIR / f"preds_{arm}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype={"match_id": str, "season": str, "date": str})


def _load_b6(method: str) -> pd.DataFrame:
    if method == "proportional":
        p = PRED_DIR / "preds_B6.csv"
    else:
        p = LOG_DIR / f"b6_devig_{method}.csv"
    return pd.read_csv(p, dtype={"match_id": str, "season": str, "date": str})


def _brier(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    o = np.eye(3)[np.asarray(y, dtype=int)]
    return ((np.asarray(p) - o) ** 2).sum(axis=1)


def market_gap(arm: str, B: int = 10_000, alpha: float = 0.10,
               seed: int = 20261110) -> list[dict]:
    """一个 arm × 三法。返回行列表。"""
    a = _load_pred(arm)
    if a.empty:
        return []
    rows = []
    for method in DEVIG_METHODS:
        b = _load_b6(method)
        if b.empty:
            continue
        blk = block_deltas(a, b)
        ci = cluster_bootstrap(blk, B=B, alpha=alpha, seed=seed)
        # ΔBrier（逐场配对差，仅点估计）
        m = a[["match_id", "p_home", "p_draw", "p_away", "y"]].merge(
            b[["match_id", "p_home", "p_draw", "p_away"]],
            on="match_id", suffixes=("_a", "_b"))
        ya = m["y"].to_numpy()
        pa = m[["p_home_a", "p_draw_a", "p_away_a"]].to_numpy()
        pb = m[["p_home_b", "p_draw_b", "p_away_b"]].to_numpy()
        db = float((_brier(pa, ya) - _brier(pb, ya)).mean())
        rows.append({"arm": arm, "devig": method,
                     "delta_ll": ci["point"], "lo90": ci["lo"], "hi90": ci["hi"],
                     "delta_brier": db, "n_paired": blk.n_paired})
    return rows


def build_market_gap(arms: list[str] | None = None, out_path=None,
                     B: int = 10_000, alpha: float = 0.10,
                     seed: int = 20261110) -> pd.DataFrame:
    todo = ARMS if arms is None else arms
    rows = []
    for arm in todo:
        rows.extend(market_gap(arm, B=B, alpha=alpha, seed=seed))
    df = pd.DataFrame(rows)
    if out_path is not None and len(df):
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False, encoding="utf-8")
    return df


def plot_market_gap(df: pd.DataFrame, out_path=None):
    """fig07：三法 × 各 arm 的 ΔLL 森林图（正 = arm 比 B6 差）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if df.empty:
        return None
    methods = ["proportional", "power", "shin"]
    colors = {"proportional": "#1f77b4", "power": "#ff7f0e", "shin": "#2ca02c"}
    arms = [a for a in ARMS if a in set(df["arm"])]
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(arms) + 1.4))
    ypos = range(len(arms))
    for i, arm in enumerate(arms):
        for method in methods:
            r = df[(df["arm"] == arm) & (df["devig"] == method)]
            if r.empty:
                continue
            r = r.iloc[0]
            jitter = {"proportional": 0.0, "power": 0.12, "shin": -0.12}[method]
            ax.errorbar(r["delta_ll"], i + jitter,
                        xerr=[[r["delta_ll"] - r["lo90"]], [r["hi90"] - r["delta_ll"]]],
                        fmt="o", color=colors[method], capsize=2.5, ms=5,
                        label=method if i == 0 else None)
    ax.axvline(0, color="0.4", lw=0.8, ls="--")
    ax.axvspan(-0.02, 0.02, color="0.85", alpha=0.35)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(arms)
    ax.set_xlabel("Δ log loss vs B6 (nats, positive = worse than market)")
    ax.set_title("Market gap (H2): model − market, three de-vigging methods")
    ax.legend(loc="best", frameon=False)
    ax.grid(axis="x", ls=":", alpha=0.5)
    fig.tight_layout()
    if out_path is not None:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=130)
    return fig
