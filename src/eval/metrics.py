"""M2 / T2.4：指标层（proper scoring rules + 校准诊断）。

纯 numpy 实现，零新增依赖；与 ``sklearn.metrics`` 交叉核对（见 ``tests/test_metrics.py``）。
约定：

- 每个主指标同时提供**逐场向量**与**pooled 均值**两版：``log_loss`` / ``mean_log_loss``
  等。判定用 pooled over matches（先求和再除 n），不是先按折平均。
- 概率 clip 下限 ``CLIP = 1e-15``（只防 ``log 0``，不改排序）。
- ``p`` 恒为 ``(n, 3)`` 且列序 ``p_home, p_draw, p_away``；``y ∈ {0,1,2}``。
- Murphy 分解与 ECE 采用**逐类别分箱**（对每一类的预测概率分别分箱），这是
  多分类 Brier 分解 / 校准的标准形式；恒等式 ``Brier = REL − RES + U`` 写成断言。
"""

from __future__ import annotations

import numpy as np

CLIP = 1e-15
CLASSES = (0, 1, 2)


def _check(p: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(p, dtype=float)
    y = np.asarray(y)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError(f"p 必须是 (n,3)，实际 {p.shape}")
    if y.ndim != 1 or p.shape[0] != len(y):
        raise ValueError(f"y 必须是 (n,)，实际 {y.shape}（p 行数 {p.shape[0]}）")
    if not np.issubdtype(y.dtype, np.integer):
        y = y.astype(int)
    if not set(np.unique(y)) <= {0, 1, 2}:
        raise ValueError("y 必须 ∈ {0,1,2}")
    return p, y


def _onehot(y: np.ndarray) -> np.ndarray:
    n = len(y)
    o = np.zeros((n, 3))
    o[np.arange(n), y] = 1.0
    return o


def log_loss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """逐场 log loss：``−log(p[y])``，返回 ``(n,)`` 向量。"""
    p, y = _check(p, y)
    return -np.log(np.clip(p[np.arange(len(y)), y], CLIP, None))


def mean_log_loss(p: np.ndarray, y: np.ndarray) -> float:
    return float(log_loss(p, y).mean())


def brier(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """逐场 Brier：``Σ_k (p_k − 1{y=k})²``，返回 ``(n,)`` 向量。"""
    p, y = _check(p, y)
    return ((p - _onehot(y)) ** 2).sum(axis=1)


def mean_brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(brier(p, y).mean())


def rps(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """逐场排名概率分（3 类，H<D<A 有序）。

    ``RPS = 1/2 · Σ_{j=0}^{1} (P_j − Y_j)²``，其中 ``P_j`` / ``Y_j`` 是到第 j 类为止的
    累积预测概率 / 累积观测指示。
    """
    p, y = _check(p, y)
    o = _onehot(y)
    P = np.cumsum(p, axis=1)      # P_j = Σ_{k≤j} p_k，j∈{0,1,2}
    Y = np.cumsum(o, axis=1)
    return 0.5 * ((P[:, :2] - Y[:, :2]) ** 2).sum(axis=1)


def mean_rps(p: np.ndarray, y: np.ndarray) -> float:
    return float(rps(p, y).mean())


def murphy_decomposition(p: np.ndarray, y: np.ndarray,
                         n_bins: int = 10) -> dict[str, float]:
    """多分类 Brier 的 Murphy 分解（分箱版）。

    逐类别按该类的预测概率分 ``n_bins`` 个分位箱。恒等式
    ``brier = reliability − resolution + uncertainty + within_bin_var`` 精确成立，
    其中 ``within_bin_var`` 是**箱内预测方差**（连续预测分箱后的残留项，≥ 0）；
    教科书里「``Brier = REL − RES + UNC``」只在预测为离散类别（箱内恒定）时严格成立。
    """
    p, y = _check(p, y)
    o = _onehot(y)
    n = len(y)
    rel = res = unc = wbv = 0.0
    for k in CLASSES:
        pk = p[:, k]
        ok = o[:, k]
        o_bar = float(ok.mean())
        unc += o_bar * (1.0 - o_bar)
        bins = _qcut(pk, n_bins)
        for b in range(bins.max() + 1):
            m = bins == b
            n_b = int(m.sum())
            if n_b == 0:
                continue
            p_bar = float(pk[m].mean())
            o_hat = float(ok[m].mean())
            rel += (n_b / n) * (p_bar - o_hat) ** 2
            res += (n_b / n) * (o_hat - o_bar) ** 2
            wbv += (n_b / n) * float(np.var(pk[m], ddof=1)) if n_b > 1 else 0.0
    return {"reliability": rel, "resolution": res, "uncertainty": unc,
            "within_bin_var": wbv, "brier": mean_brier(p, y)}


def ece(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    """期望校准误差（逐类别分箱版）：三类 ``Σ_b (n_b/n)|p̄−ō|`` 的简单平均。"""
    p, y = _check(p, y)
    o = _onehot(y)
    n = len(y)
    vals = []
    for k in CLASSES:
        pk = p[:, k]
        ok = o[:, k]
        bins = _qcut(pk, n_bins)
        e = 0.0
        for b in range(bins.max() + 1):
            m = bins == b
            if not m.any():
                continue
            e += (m.sum() / n) * abs(float(pk[m].mean()) - float(ok[m].mean()))
        vals.append(e)
    return float(np.mean(vals))


def reliability_curve(p: np.ndarray, y: np.ndarray, n_bins: int = 10):
    """逐类别可靠性曲线（硬分箱）。返回 ``DataFrame(class, pred_mean, obs_freq, count)``。

    延迟导入 pandas，保持本模块纯 numpy 可独立使用。
    """
    import pandas as pd
    p, y = _check(p, y)
    o = _onehot(y)
    rows = []
    for k in CLASSES:
        pk = p[:, k]
        ok = o[:, k]
        bins = _qcut(pk, n_bins)
        for b in range(bins.max() + 1):
            m = bins == b
            if not m.any():
                continue
            rows.append({"class": k, "pred_mean": float(pk[m].mean()),
                         "obs_freq": float(ok[m].mean()), "count": int(m.sum())})
    return pd.DataFrame(rows)


def reliability_curve_smooth(p: np.ndarray, y: np.ndarray,
                             grid: int = 64, bandwidth: float | None = None):
    """逐类别**局部平滑**可靠性曲线（Nadaraya–Watson 高斯核，W7 局部平滑落点）。

    对每一类，在预测概率的支撑上取 ``grid`` 个点，用核加权局部均值估计
    ``E[1{y=k} | p_k]``。``bandwidth=None`` 时用 Scott 规则 ``n^{-1/5}`` 的启发式。
    """
    import pandas as pd
    p, y = _check(p, y)
    o = _onehot(y)
    n = len(y)
    h = bandwidth if bandwidth is not None else max(n ** (-1.0 / 5.0), 0.02)
    rows = []
    for k in CLASSES:
        x = p[:, k]
        ok = o[:, k]
        xs = np.linspace(x.min(), x.max(), grid)
        for xq in xs:
            w = np.exp(-0.5 * ((x - xq) / h) ** 2)
            sw = w.sum()
            if sw < 1e-12:
                continue
            rows.append({"class": k, "pred": float(xq),
                         "smoothed_freq": float((w * ok).sum() / sw)})
    return pd.DataFrame(rows)


def bias_vs_pred(p: np.ndarray, y: np.ndarray, n_bins: int = 10):
    """偏差−预测概率表：``bias = pred_mean − obs_freq``，逐类别分箱。

    H1「低概率区在对角线下方」的区域主张就落在 ``bias`` 的符号上（见
    ``src/eval/decisions.py`` 的符号断言说明）。
    """
    import pandas as pd
    curve = reliability_curve(p, y, n_bins=n_bins)
    curve = curve.copy()
    curve["bias"] = curve["pred_mean"] - curve["obs_freq"]
    return curve


def _qcut(x: np.ndarray, n_bins: int) -> np.ndarray:
    """把一维数组按分位数分成 ``n_bins`` 箱，返回每点的箱号 ``(n,)``。

    用 ``np.unique`` 去重边界的 ``digitize``，避免重复分位点导致空箱报错；
    全是常数时退化为全 0 箱。
    """
    x = np.asarray(x, dtype=float)
    q = np.quantile(x, np.linspace(0.0, 1.0, n_bins + 1))
    edges = np.unique(q)
    if len(edges) == 1:
        return np.zeros(len(x), dtype=int)
    # digitize 用 (edges[1:-1]) 作内边界；右闭左开，保证点数最多的箱不越界
    inner = edges[1:-1]
    if inner.size == 0:
        return np.zeros(len(x), dtype=int)
    return np.clip(np.digitize(x, inner, right=False), 0, n_bins - 1)
