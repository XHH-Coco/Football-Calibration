"""M2 / T2.13：H3 差距局部化——升班马 / 早轮次的固定效应回归 + 描述性 sweep。

模型：逐场 ``gap_i = ℓ_B4,i − ℓ_B6,i``（正 = 模型更差）对
``β1·promoted + β2·early_w + 联赛×赛季固定效应`` 做 OLS。

- ``promoted_i = is_promoted_home ∨ is_promoted_away``；
- ``early_w_i = 1{matchday ≤ w}``，主版 ``w = 6``；``matchday`` 是 panel 里**主队**本季
  已完成场次 +1（客队 matchday 不在 panel 中，作已声明局限）；
- 系数区间：48 块簇 bootstrap（重抽块 → 重拟合 → 分位法）；
- sweep ``1–3 / 1–6 / 1–10`` 为跑数前声明的描述性稳健曲线，不进主推断。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.b3_poisson import load_panel  # noqa: E402


def _load_pred(arm: str) -> pd.DataFrame:
    p = ROOT / "results" / "preds" / f"preds_{arm}.csv"
    return pd.read_csv(p, dtype={"match_id": str, "season": str, "date": str})


def build_h3_frame() -> pd.DataFrame:
    """返回 ``gap / promoted / matchday / block`` 的逐场表（B4 ∩ B6 = 16,728 场）。"""
    panel = load_panel()
    b4 = _load_pred("B4")
    b6 = _load_pred("B6")
    m = b4[["match_id", "p_home", "p_draw", "p_away", "y"]].merge(
        b6[["match_id", "p_home", "p_draw", "p_away"]],
        on="match_id", suffixes=("_b4", "_b6"))
    p4 = m[["p_home_b4", "p_draw_b4", "p_away_b4"]].to_numpy()
    p6 = m[["p_home_b6", "p_draw_b6", "p_away_b6"]].to_numpy()
    y = m["y"].to_numpy()
    l4 = -np.log(np.clip(p4[np.arange(len(y)), y], 1e-15, None))
    l6 = -np.log(np.clip(p6[np.arange(len(y)), y], 1e-15, None))
    gap = l4 - l6
    meta = panel.set_index("match_id")[["league", "season", "is_promoted_home",
                                        "is_promoted_away", "matchday"]]
    meta = meta.loc[m["match_id"]].reset_index()
    promoted = ((meta["is_promoted_home"].astype(bool))
                | (meta["is_promoted_away"].astype(bool))).to_numpy().astype(float)
    block = (meta["league"] + "|" + meta["season"]).to_numpy()
    return pd.DataFrame({"gap": gap, "promoted": promoted,
                         "matchday": meta["matchday"].to_numpy(), "block": block})


def _block_suffstat(df: pd.DataFrame, w: int):
    """把设计矩阵拆成每块 ``(S_b, t_b)``，供快速重抽样：``β = (Σ m_b S_b + λI)⁻¹ Σ m_b t_b``。"""
    n = len(df)
    early = (df["matchday"].to_numpy() <= w).astype(float)
    dummies = pd.get_dummies(df["block"], drop_first=True).to_numpy(dtype=float)
    X = np.column_stack([np.ones(n), df["promoted"].to_numpy().astype(float),
                         early, dummies])
    y = df["gap"].to_numpy()
    blocks = df["block"].to_numpy()
    uids = np.unique(blocks)
    G = len(uids)
    p = X.shape[1]
    S_blocks = np.empty((G, p, p))
    t_blocks = np.empty((G, p))
    for i, uid in enumerate(uids):
        Xb = X[blocks == uid]
        yb = y[blocks == uid]
        S_blocks[i] = Xb.T @ Xb
        t_blocks[i] = Xb.T @ yb
    return X, y, S_blocks, t_blocks


def h3_coefficients(df: pd.DataFrame, w: int = 6, B: int = 10_000,
                    alpha: float = 0.10, seed: int = 20261110) -> dict:
    """固定效应回归 + 簇 bootstrap（块充分统计量，向量化重抽样）。"""
    X, y, S_blocks, t_blocks = _block_suffstat(df, w)
    p = X.shape[1]
    ridge = 1e-8 * np.eye(p)
    beta = np.linalg.solve(X.T @ X + ridge, X.T @ y)
    G = S_blocks.shape[0]
    rng = np.random.default_rng(seed)
    b_prom, b_early = [], []
    for _ in range(B):
        m = np.bincount(rng.integers(0, G, size=G), minlength=G)
        S = np.einsum("b,bij->ij", m, S_blocks)
        t = np.einsum("b,bi->i", m, t_blocks)
        bb = np.linalg.solve(S + ridge, t)
        b_prom.append(bb[1])
        b_early.append(bb[2])
    b_prom = np.asarray(b_prom)
    b_early = np.asarray(b_early)
    return {
        "promoted": {"coef": float(beta[1]),
                     "lo": float(np.quantile(b_prom, alpha / 2)),
                     "hi": float(np.quantile(b_prom, 1 - alpha / 2))},
        "early": {"coef": float(beta[2]),
                  "lo": float(np.quantile(b_early, alpha / 2)),
                  "hi": float(np.quantile(b_early, 1 - alpha / 2))},
    }


def h3_sweep(df: pd.DataFrame, windows: tuple[int, ...] = (3, 6, 10)) -> pd.DataFrame:
    """描述性 sweep：各早轮次窗下的 early 系数 + 90% 簇区间。"""
    rows = []
    for w in windows:
        res = h3_coefficients(df, w)
        rows.append({"window": w, "coef": res["early"]["coef"],
                     "lo": res["early"]["lo"], "hi": res["early"]["hi"]})
    return pd.DataFrame(rows)
