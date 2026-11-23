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
- 自检：块级 vs 逐场重采样的 90% 区间宽度比满足 ``ratio ≈ √deff > 1``。**不是**
  「3–5 倍」——那个早期口径在这里是错的（v1.4 订正，见 ``docs/plans/m2_harness_spec.md``
  §3.4）：宽度比由 deff 唯一决定，本项目实测 deff 1.32–2.28 ⇒ ratio 1.17–1.50；
  要 3–5 倍须 deff 9–25，等于假设同一块内 16,733/48 ≈ 349 场比赛几乎完全同质。
  自检文本由 ``selfcheck_text()`` 生成并落盘 ``results/logs/bootstrap_selfcheck.txt``。
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
    """块级 vs 逐场 90% 区间宽度比；``ratio ≈ √deff``（恒 > 1，本项目实测 1.17–1.50）。"""
    cb = cluster_bootstrap(block, B=B, alpha=alpha, seed=seed)
    ib = iid_bootstrap(block, B=B, alpha=alpha, seed=seed)
    wc = cb["hi"] - cb["lo"]
    wi = ib["hi"] - ib["lo"]
    return {"cluster_width": wc, "iid_width": wi,
            "ratio": wc / wi if wi > 0 else float("nan")}


# 自检里展示的 arm（覆盖先验、透明、GBM、市场四档）与配对（覆盖单臂与配对差两种用法）
SELFCHECK_ARMS = ("B0", "B2", "B4", "B5a", "B6")
SELFCHECK_PAIRS = (("B4", "B6"), ("B2", "B4"), ("B4", "B6r"))


def selfcheck_text(frames: dict, pairs=SELFCHECK_PAIRS, B: int = 10_000,
                   alpha: float = 0.10, seed: int = DEFAULT_SEED,
                   deff_tol: float = 0.25) -> str:
    """生成 ``results/logs/bootstrap_selfcheck.txt`` 的正文（验收项 7 的证据）。

    ``frames``：``{arm: 该 arm 的 preds DataFrame}``，需含 ``match_id / league / season /
    p_home / p_draw / p_away / y``。单臂走 ``block_logloss``（逐场 log loss 的块聚合），
    配对走 ``block_deltas``（``δ = ℓ_a − ℓ_b``）。

    每行报：``n``（场数）、``deff``、块级宽度、逐场宽度、``ratio``、``ratio²`` 与
    ``√deff`` 的偏差。断言 ``ratio > 1`` 且 ``ratio² ≈ deff``（相对误差 < ``deff_tol``）；
    任一不满足即在正文里标 ``FAIL``，由调用方决定是否让流水线失败。
    """
    stats: list[tuple[float, float]] = []

    def row(tag: str, block: BlockDeltas) -> tuple[str, bool]:
        de = design_effect(block)
        wr = width_ratio(block, B=B, alpha=alpha, seed=seed)
        ratio = wr["ratio"]
        deff = de["deff"]
        gap = (ratio ** 2 - deff) / deff if deff > 0 else float("nan")
        ok = bool(ratio > 1.0 and abs(gap) < deff_tol)
        stats.append((deff, ratio))
        line = (f"{tag:<10} {block.n_paired:>7,} {deff:>6.3f} "
                f"{wr['cluster_width']:>12.5f} {wr['iid_width']:>11.5f} "
                f"{ratio:>6.3f} {ratio ** 2:>8.3f} {np.sqrt(deff):>9.3f} "
                f"{gap:>+8.1%}   {'PASS' if ok else 'FAIL'}")
        return line, ok

    body: list[str] = []
    all_ok = True
    for arm in SELFCHECK_ARMS:
        if arm not in frames:
            continue
        line, ok = row(arm, block_logloss(frames[arm]))
        body.append(line)
        all_ok &= ok
    body.append("")
    for a, b in pairs:
        if a not in frames or b not in frames:
            continue
        line, ok = row(f"{a}-{b}", block_deltas(frames[a], frames[b]))
        body.append(line)
        all_ok &= ok

    deff_lo = min(s[0] for s in stats) if stats else float("nan")
    deff_hi = max(s[0] for s in stats) if stats else float("nan")
    r_lo = min(s[1] for s in stats) if stats else float("nan")
    r_hi = max(s[1] for s in stats) if stats else float("nan")
    out = [
        "bootstrap self-check（验收项 7 · 块级 vs 逐场重采样）",
        "生成命令：python -m src.eval.run_m2（src.eval.bootstrap.selfcheck_text）",
        f"重采样单位：{G_BLOCKS} 个 (league, season) 块；B = {B:,}；区间 = {1 - alpha:.0%}；"
        f"seed = {seed}；分位法，无偏差校正",
        "",
        "口径（v1.4 订正）：ratio ≈ √deff。deff 只由「块间方差 / 逐场方差」决定，",
        "      因此宽度比不是自由参数；要 3–5 倍须 deff 9–25（等于假设同一块内",
        "      ≈349 场比赛几乎完全同质），与本数据的簇结构不符。",
        f"      本次实测：deff ∈ [{deff_lo:.2f}, {deff_hi:.2f}]，ratio ∈ [{r_lo:.2f}, {r_hi:.2f}]。",
        "",
        f"{'arm/paired':<10} {'n':>7} {'deff':>6} {'width_block':>12} {'width_iid':>11} "
        f"{'ratio':>6} {'ratio^2':>8} {'sqrt(deff)':>9} {'rel.err':>8}   verdict",
    ]
    out += body
    out += [
        "",
        f"总判定：{'PASS' if all_ok else 'FAIL'}（逐行 ratio > 1 且 ratio² 与 deff 相对误差 < "
        f"{deff_tol:.0%}）",
        "说明：ratio 与 deff 都随 arm 变化（不同 arm 的块间异质性不同），故逐行报而不报一个总数。",
    ]
    return "\n".join(out) + "\n"
