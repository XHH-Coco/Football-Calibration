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
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

CLIP = 1e-6


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
    """按块场数加权的 pooled 斜率（``(G,3)`` 斜率先按类内平均再跨类？——这里输入
    是**某一类**的逐块斜率 ``(G,)``，返回加权均值）。"""
    s = np.asarray(slopes, dtype=float)
    w = np.asarray(weights, dtype=float)
    m = np.isfinite(s)
    if not m.any():
        return float("nan")
    return float((s[m] * w[m]).sum() / w[m].sum())


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
