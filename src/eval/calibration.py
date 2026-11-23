"""M2 / T2.10：H1 市场校准——one-vs-rest 重校准斜率 / 截距 + 尾箱偏差 + 三法对照。

做法（与 ``m2_harness_spec.md`` §7.2 一致）：

- 对每个结果类别 k，用 ``logit(o_k) ~ a + b·logit(p_k)`` 的单特征 logistic 回归估
  ``(a_k, b_k)``。``b_k`` 即校准斜率：``b > 1`` = under-dispersed（太保守）。
- **逐块估计**：每个 (联赛, 赛季) 块各估一次，pooled 斜率 = 按块场数加权的块斜率
  均值；区间用 48 块簇 bootstrap（重抽块、重算加权均值，不做偏差校正）。
- 尾箱偏差 = 最低 / 最高预测概率箱的 ``pred_mean − obs_freq``。
- **符号断言**（提交版写反过，必须写进代码）：``b > 1`` ⇒ 低概率区可靠性曲线在
  对角线**下方**（``freq < pred``，即低概率箱 ``bias = pred − freq > 0``）；高概率区
  在对角线**上方**（``bias < 0``）。

输入概率来自 B6 三种去抽水（proportional 主基准；power / Shin 作稳健性）。

**口径提醒（v1.4）**：主斜率是三类各自斜率的块内平均，``min_mean`` 式跨类平均会把
「只有某一类 under-dispersed」稀释掉；因此除主斜率外必须同时报**逐类斜率**
（``h1_slope_by_class``），报告的 H1 措辞据此收口为「方向一致、量级依赖去抽水口径」。
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

CLIP = 1e-6
CLASS_NAMES = ("home", "draw", "away")


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), CLIP, 1 - CLIP)
    return np.log(p / (1.0 - p))


def _fit_slope(pk: np.ndarray, ok: np.ndarray) -> tuple[float, float]:
    """单特征 logistic：``logit(o) = a + b·logit(p)``，返回 ``(b, a)``。"""
    x = _logit(pk).reshape(-1, 1)
    if ok.min() == ok.max():
        return float("nan"), float("nan")
    clf = LogisticRegression(C=1e9, max_iter=1000, fit_intercept=True)
    clf.fit(x, ok)
    return float(clf.coef_[0, 0]), float(clf.intercept_[0])


def calibration_by_block(p: np.ndarray, y: np.ndarray,
                         block_ids: np.ndarray) -> np.ndarray:
    """逐块逐类估斜率。返回 ``(G, 3)`` 的斜率矩阵。"""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y)
    o = np.eye(3)[y]
    out = np.full((len(np.unique(block_ids)), 3), np.nan)
    for gi, gid in enumerate(np.unique(block_ids)):
        m = block_ids == gid
        for k in range(3):
            out[gi, k], _ = _fit_slope(p[m, k], o[m, k])
    return out


def pooled_slope(slopes: np.ndarray, weights: np.ndarray) -> float:
    """加权 pooled 斜率：输入是**某一类**的逐块斜率 ``(G,)``（不是 ``(G,3)``），
    返回按块场数加权的均值；非有限值（某块该类全为 0/1）自动剔除。"""
    s = np.asarray(slopes, dtype=float)
    w = np.asarray(weights, dtype=float)
    m = np.isfinite(s)
    if not m.any():
        return float("nan")
    return float((s[m] * w[m]).sum() / w[m].sum())


def _weighted_ci(values: np.ndarray, weights: np.ndarray, B: int, alpha: float,
                 rng: np.random.Generator) -> dict[str, float]:
    """按块加权均值的 48 块簇 bootstrap 区间（分位法，无偏差校正）。"""
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    m = np.isfinite(v)
    if not m.any():
        return {"slope": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "se": float("nan")}
    v, w = v[m], w[m]
    point = float((v * w).sum() / w.sum())
    idx = rng.integers(0, len(v), size=(B, len(v)))
    draws = (v[idx] * w[idx]).sum(axis=1) / w[idx].sum(axis=1)
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {"slope": point, "lo": float(lo), "hi": float(hi),
            "se": float(draws.std(ddof=1))}


def tail_bin_bias(p: np.ndarray, y: np.ndarray, n_bins: int = 10):
    """最低 / 最高预测概率箱的 ``pred_mean − obs_freq``，逐类返回 ``(2, 3)``。"""
    p = np.asarray(p, dtype=float)
    o = np.eye(3)[np.asarray(y)]
    low = np.zeros(3)
    high = np.zeros(3)
    for k in range(3):
        pk = p[:, k]
        ok = o[:, k]
        q = np.quantile(pk, np.linspace(0, 1, n_bins + 1))
        edges = np.unique(q)
        if len(edges) == 1:
            continue
        bins = np.clip(np.digitize(pk, edges[1:-1], right=False), 0, n_bins - 1)
        lo = bins == 0
        hi = bins == bins.max()
        low[k] = float(pk[lo].mean() - ok[lo].mean())
        high[k] = float(pk[hi].mean() - ok[hi].mean())
    return low, high


def expected_tail_bias_sign(slope: float) -> tuple[int, int]:
    """H1 符号断言：``b > 1`` ⇒ 低概率箱 ``bias = pred − freq`` **为正**（曲线在
    对角线下方）、高概率箱为负。返回 ``(low_sign, high_sign)``，符号 ∈ {−1,0,+1}。"""
    if slope > 1.0:
        return (+1, -1)
    if slope < 1.0:
        return (-1, +1)
    return (0, 0)


def h1_pipeline(p_prop: np.ndarray, p_power: np.ndarray, p_shin: np.ndarray,
                y: np.ndarray, block_ids: np.ndarray,
                B: int = 10_000, alpha: float = 0.10,
                seed: int = 20261110) -> dict:
    """三种去抽水下的斜率 pooled 估计 + 90% 簇区间（逐类，输出按类平均的主斜率）。"""
    rng = np.random.default_rng(seed)
    uids, weights = np.unique(block_ids, return_counts=True)
    G = len(uids)
    result = {}
    for name, p in (("proportional", p_prop), ("power", p_power), ("shin", p_shin)):
        slopes = calibration_by_block(p, y, block_ids)      # (G,3)
        cls = np.nanmean(slopes, axis=1)                    # 每块 3 类平均
        m = np.isfinite(cls)
        if not m.any():
            result[name] = {"slope": float("nan"), "lo": float("nan"),
                            "hi": float("nan"), "se": float("nan")}
            continue
        point = float((cls[m] * weights[m]).sum() / weights[m].sum())
        idx = rng.integers(0, G, size=(B, G))
        c = cls
        w = weights.astype(float)
        draws = (c[idx] * w[idx]).sum(axis=1) / w[idx].sum(axis=1)
        lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
        result[name] = {"slope": point, "lo": float(lo), "hi": float(hi),
                        "se": float(draws.std(ddof=1))}
    return result


def h1_slope_by_class(p_by_method: dict[str, np.ndarray], y: np.ndarray,
                      block_ids: np.ndarray, B: int = 10_000, alpha: float = 0.10,
                      seed: int = 20261110):
    """逐类校准斜率 + 90% 簇区间，三种去抽水各一遍（H1 的正文附表 / 附录）。

    与主斜率**同一估计口径**（逐块估 ``(b_k)``、按块场数加权），因此逐类结果与
    ``h1_pipeline`` 的三类平均自洽：主斜率 ≈ 三类斜率的等权平均。
    返回长表 ``method, cls, slope, lo, hi, se``。
    """
    import pandas as pd
    rng = np.random.default_rng(seed)
    uids, weights = np.unique(block_ids, return_counts=True)
    rows = []
    for name, p in p_by_method.items():
        slopes = calibration_by_block(np.asarray(p, dtype=float), y, block_ids)  # (G,3)
        for k, cname in enumerate(CLASS_NAMES):
            r = _weighted_ci(slopes[:, k], weights, B, alpha, rng)
            rows.append({"method": name, "cls": cname, **r})
    return pd.DataFrame(rows)
