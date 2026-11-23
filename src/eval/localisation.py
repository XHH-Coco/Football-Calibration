"""M2 / T2.13：H3 差距局部化——升班马 / 早轮次的固定效应回归 + 描述性 sweep。

模型：逐场 ``gap_i = ℓ_B4,i − ℓ_B6,i``（正 = 模型更差）对
``β1·promoted + β2·early_w + 联赛×赛季固定效应`` 做 OLS。

- ``promoted_i = is_promoted_home ∨ is_promoted_away``；
- ``early_w_i = 1{matchday_i ≤ w}``，主版 ``w = 6``；
- **``matchday_i = min(matchday_home, matchday_away)``（预注册主版，v1.4 修正）**：
  两队本季此前出场数 + 1，均由 panel 自身算出（同联赛同赛季同队按日期 cumcount），
  0 缺失。旧交付版只用主队 matchday 并标成「已声明局限」——没有必要，
  因为客队 matchday 完全可由 panel 推出；两口径 early 标记不同的场次 1,025 场，
  系数 −0.0114（min）vs −0.0108（仅主队），结论不变但主版必须回到预注册口径。
  ``matchday_max`` 与「仅主队」两版由 ``h3_sensitivity`` 作描述性对照；
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


def team_matchday(panel: pd.DataFrame) -> pd.DataFrame:
    """每支球队每季的轮次：同联赛同赛季同队按日期累计出场数 + 1。

    返回 ``league, season, date, team, matchday_team``（键唯一，重复即报错）。
    主队和客队都走这一张表——只按 home 分组会漏掉客队（旧实现的局限）。
    """
    long = pd.concat([
        panel[["league", "season", "date", "home"]].rename(columns={"home": "team"}),
        panel[["league", "season", "date", "away"]].rename(columns={"away": "team"}),
    ], ignore_index=True)
    long = long.sort_values(["league", "season", "team", "date"], kind="stable")
    long["matchday_team"] = long.groupby(["league", "season", "team"], sort=False).cumcount() + 1
    key = ["league", "season", "date", "team"]
    dup = long.duplicated(key)
    if dup.any():
        raise ValueError(f"同一球队同日出场 {int(dup.sum())} 次，无法唯一映射轮次")
    return long[key + ["matchday_team"]]


def build_h3_frame() -> pd.DataFrame:
    """返回逐场表（B4 ∩ B6 = 16,728 场）：``gap / promoted / matchday_home /
    matchday_away / matchday(=min) / matchday_max / block``。"""
    panel = load_panel()
    b4 = _load_pred("B4")
    b6 = _load_pred("B6")
    m = b4[["match_id", "league", "season", "date", "home", "away",
            "p_home", "p_draw", "p_away", "y"]].merge(
        b6[["match_id", "p_home", "p_draw", "p_away"]],
        on="match_id", suffixes=("_b4", "_b6"))
    p4 = m[["p_home_b4", "p_draw_b4", "p_away_b4"]].to_numpy()
    p6 = m[["p_home_b6", "p_draw_b6", "p_away_b6"]].to_numpy()
    y = m["y"].to_numpy()
    l4 = -np.log(np.clip(p4[np.arange(len(y)), y], 1e-15, None))
    l6 = -np.log(np.clip(p6[np.arange(len(y)), y], 1e-15, None))
    gap = l4 - l6

    meta = panel.set_index("match_id")[["is_promoted_home", "is_promoted_away"]]
    meta = meta.loc[m["match_id"]].reset_index()
    promoted = ((meta["is_promoted_home"].astype(bool))
                | (meta["is_promoted_away"].astype(bool))).to_numpy().astype(float)

    look = team_matchday(panel)
    md_home = m[["league", "season", "date", "home"]].merge(
        look, left_on=["league", "season", "date", "home"],
        right_on=["league", "season", "date", "team"], how="left")["matchday_team"].to_numpy()
    md_away = m[["league", "season", "date", "away"]].merge(
        look, left_on=["league", "season", "date", "away"],
        right_on=["league", "season", "date", "team"], how="left")["matchday_team"].to_numpy()
    if np.isnan(md_home).any() or np.isnan(md_away).any():
        raise ValueError(f"轮次缺失：home {int(np.isnan(md_home).sum())} / "
                         f"away {int(np.isnan(md_away).sum())} 场")

    return pd.DataFrame({
        "gap": gap,
        "promoted": promoted,
        "matchday_home": md_home.astype(float),
        "matchday_away": md_away.astype(float),
        "matchday": np.minimum(md_home, md_away).astype(float),   # 预注册主版
        "matchday_max": np.maximum(md_home, md_away).astype(float),
        "block": (m["league"] + "|" + m["season"]).to_numpy(),
    })


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
        "n": int(len(df)),
    }


def h3_sweep(df: pd.DataFrame, windows: tuple[int, ...] = (3, 6, 10)) -> pd.DataFrame:
    """描述性 sweep：各早轮次窗下的 early 系数 + 90% 簇区间。"""
    rows = []
    for w in windows:
        res = h3_coefficients(df, w)
        rows.append({"window": w, "coef": res["early"]["coef"],
                     "lo": res["early"]["lo"], "hi": res["early"]["hi"]})
    return pd.DataFrame(rows)


# 预注册主版在前；其余两版只作描述性敏感性（回归结果不得据此升格为主推断）
H3_DEFINITIONS = (
    ("min(home,away)（主版）", "matchday"),
    ("max(home,away)", "matchday_max"),
    ("仅主队（旧交付版）", "matchday_home"),
)


def h3_sensitivity(df: pd.DataFrame, w: int = 6, B: int = 10_000,
                   seed: int = 20261110) -> pd.DataFrame:
    """三种 early 定义下的系数对照（``min`` 为主版，另两版描述性）。"""
    rows = []
    for label, col in H3_DEFINITIONS:
        res = h3_coefficients(df.assign(matchday=df[col].to_numpy()), w=w, B=B, seed=seed)
        rows.append({
            "definition": label,
            "early_coef": res["early"]["coef"], "early_lo": res["early"]["lo"],
            "early_hi": res["early"]["hi"],
            "promoted_coef": res["promoted"]["coef"],
            "promoted_lo": res["promoted"]["lo"], "promoted_hi": res["promoted"]["hi"],
            "n": res["n"],
        })
    return pd.DataFrame(rows)
