"""M2 / T2.6 + T2.12：48 块簇 bootstrap + cluster-robust SE + design effect。

重采样单位是**块**（``configs/splits.json`` 里的 48 个 (联赛, 赛季) 块），不是比赛。
算法（与 ``docs/plans/m2_harness_spec.md`` §3.4 逐字一致，冻结口径）：

- 配对差：先按 ``match_id`` 内连接，再逐场 ``δ_i = ℓ_a,i − ℓ_b,i``（ℓ = −log p_true）；
  块均值 ``δ_b``、块场数 ``n_b``，``N = Σ n_b``。
- 点估计：``Δ̂ = Σ_b n_b δ_b / Σ_b n_b``（按场加权 pooled，**不是** 48 块均值的简单平均）。
- 重抽样：有放回抽 48 个块，重算加权 pooled；重复 ``B`` 次；分位法取区间，**不做
  偏差校正**；种子固定 ``20261110``。
- cluster-robust SE：``Var = G/(G−1) · Σ_b (n_b/N)² (δ_b − Δ̂)²``，``G=48``。
- design effect：``deff = Var_cluster / Var_iid``，其中 ``Var_iid = s²/N``（逐场 δ 的
  样本方差）。
- 自检：块级 vs 逐场重采样的 90% 区间宽度比应 ∈ [3, 5]。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CLIP = 1e-15
G_BLOCKS = 48
DEFAULT_SEED = 20261110


@dataclass
class BlockDeltas:
    values: np.ndarray     # (G,) 块均值 δ_b
    weights: np.ndarray    # (G,) 块场数 n_b
    per_match: np.ndarray  # (N,) 逐场 δ_i
    n_paired: int

    @property
    def n_blocks(self) -> int:
        return len(self.values)


def block_deltas(df_a, df_b, key: str = "match_id") -> BlockDeltas:
    """两 arm 预测 → 逐场配对差 → 48 块聚合。

    ``df_a`` / ``df_b`` 必须含 ``p_home/p_draw/p_away``、``y``、``league``、``season``、
    ``match_id`` 列。返回 ``BlockDeltas``（``δ = ℓ_a − ℓ_b``，正 = a 更差）。
    """
    a = df_a[["match_id", "league", "season", "p_home", "p_draw", "p_away", "y"]]
    b = df_b[["match_id", "league", "season", "p_home", "p_draw", "p_away", "y"]]
    m = a.merge(b, on=key, suffixes=("_a", "_b"), how="inner")
    if len(m) == 0:
        raise ValueError("两 arm 无共同 match_id，无法配对")
    ya = m["y_a"].to_numpy()
    yb = m["y_b"].to_numpy()
    if not np.array_equal(ya, yb):
        raise ValueError("两 arm 在同一 match_id 上 y 不一致")

    def ell(df_side: str) -> np.ndarray:
        p = m[[f"p_home_{df_side}", f"p_draw_{df_side}", f"p_away_{df_side}"]].to_numpy()
        return -np.log(np.clip(p[np.arange(len(ya)), ya], CLIP, None))

    delta = ell("a") - ell("b")
    league = m["league_a"].to_numpy()
    season = m["season_a"].to_numpy()
    blocks = [f"{lg}|{ss}" for lg, ss in zip(league, season)]

    import pandas as pd
    g = pd.DataFrame({"block": blocks, "delta": delta}).groupby("block", sort=False)
    values = g["delta"].mean().to_numpy()
    weights = g["delta"].size().to_numpy()
    return BlockDeltas(values=values, weights=weights, per_match=delta,
                       n_paired=int(len(delta)))


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float((np.asarray(values) * np.asarray(weights)).sum()
                 / np.asarray(weights).sum())


def block_logloss(df, key: str = "match_id") -> BlockDeltas:
    """单个 arm 的逐块 log loss（非配对）。``values`` = 块均值，``weights`` = 块场数，
    ``per_match`` = 逐场 log loss。可直接喂给 ``cluster_bootstrap`` / ``design_effect``。
    """
    d = df[["match_id", "league", "season", "p_home", "p_draw", "p_away", "y"]]
    p = d[["p_home", "p_draw", "p_away"]].to_numpy()
    y = d["y"].to_numpy()
    per = -np.log(np.clip(p[np.arange(len(y)), y], CLIP, None))
    blocks = [f"{lg}|{ss}" for lg, ss in zip(d["league"], d["season"])]
    import pandas as pd
    g = pd.DataFrame({"block": blocks, "loss": per}).groupby("block", sort=False)
    return BlockDeltas(values=g["loss"].mean().to_numpy(),
                       weights=g["loss"].size().to_numpy(),
                       per_match=per, n_paired=int(len(per)))


def cluster_bootstrap(block: BlockDeltas, B: int = 10_000,
                      alpha: float = 0.10,
                      seed: int = DEFAULT_SEED) -> dict[str, float]:
    """簇 bootstrap：有放回抽 48 块重算加权 pooled 差，分位法取区间。"""
    G = block.n_blocks
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, G, size=(B, G))
    v = block.values
    w = block.weights.astype(float)
    draws = (w[idx] * v[idx]).sum(axis=1) / w[idx].sum(axis=1)
    point = weighted_mean(v, w)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {"point": point, "lo": float(lo), "hi": float(hi),
            "se_boot": float(draws.std(ddof=1)), "n_blocks": G,
            "n_paired": block.n_paired}


def cluster_robust_se(values: np.ndarray, weights: np.ndarray) -> float:
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    G = len(v)
    N = w.sum()
    d = v - weighted_mean(v, w)
    var = (G / (G - 1)) * float(((w / N) ** 2 * d ** 2).sum())
    return float(np.sqrt(var))


def design_effect(block: BlockDeltas) -> dict[str, float]:
    """``deff = Var_cluster / Var_iid``。Var_iid 用逐场 δ 的样本方差除以 N。"""
    N = block.n_paired
    var_cluster = cluster_robust_se(block.values, block.weights) ** 2
    var_iid = float(np.var(block.per_match, ddof=1)) / N if N > 1 else float("nan")
    return {"var_cluster": var_cluster, "var_iid": var_iid,
            "deff": var_cluster / var_iid if var_iid > 0 else float("nan")}


def iid_bootstrap(block: BlockDeltas, B: int = 10_000,
                  alpha: float = 0.10,
                  seed: int = DEFAULT_SEED) -> dict[str, float]:
    """**仅作对照**：按「比赛」重抽样（错误做法），用来跑宽度比自检。"""
    rng = np.random.default_rng(seed)
    d = block.per_match
    n = len(d)
    draws = d[rng.integers(0, n, size=(B, n))].mean(axis=1)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {"point": float(d.mean()), "lo": float(lo), "hi": float(hi)}


def width_ratio(block: BlockDeltas, B: int = 10_000, alpha: float = 0.10,
                seed: int = DEFAULT_SEED) -> dict[str, float]:
    """块级 vs 逐场 90% 区间宽度比；验收要求 ∈ [3, 5]。"""
    cb = cluster_bootstrap(block, B=B, alpha=alpha, seed=seed)
    ib = iid_bootstrap(block, B=B, alpha=alpha, seed=seed)
    wc = cb["hi"] - cb["lo"]
    wi = ib["hi"] - ib["lo"]
    return {"cluster_width": wc, "iid_width": wi,
            "ratio": wc / wi if wi > 0 else float("nan")}
