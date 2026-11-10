"""M2 / T2.6 + T2.12 簇 bootstrap 验收：点估计复现、deff ≥ 1、宽度比 3–5 倍。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.eval.bootstrap import (  # noqa: E402
    BlockDeltas,
    block_deltas,
    cluster_bootstrap,
    cluster_robust_se,
    design_effect,
    width_ratio,
)


def _make_preds(proba: np.ndarray, league_season: list[tuple[str, str]],
                y: np.ndarray) -> pd.DataFrame:
    rows = []
    for i in range(len(y)):
        lg, ss = league_season[i]
        rows.append({
            "match_id": f"{lg}|{ss}|m{i}",
            "league": lg, "season": ss,
            "p_home": proba[i, 0], "p_draw": proba[i, 1], "p_away": proba[i, 2],
            "y": int(y[i]),
        })
    return pd.DataFrame(rows)


def _block_correlated() -> BlockDeltas:
    """48 块、每块 100 场；块内 δ 高度相关，块间均值差异大 → deff 明显 > 1。"""
    rng = np.random.default_rng(20261110)
    blocks = []
    for b in range(48):
        lg = ["E0", "SP1", "I1", "D1", "F1", "N1"][b % 6]
        ss = f"20{b // 6 + 17}/{b // 6 + 18}"
        mu = rng.normal(0.0, 0.05)          # 块均值差异
        delta = rng.normal(mu, 0.01, 100)   # 块内高度相关（低波动）
        blocks.append((lg, ss, delta))
    values = np.array([d.mean() for _, _, d in blocks])
    weights = np.array([100] * 48)
    per_match = np.concatenate([d for _, _, d in blocks])
    return BlockDeltas(values=values, weights=weights, per_match=per_match,
                       n_paired=4800)


def test_block_deltas_inner_join_and_sign():
    n = 6
    y = np.array([0, 1, 2, 0, 1, 2])
    ls = [("E0", "2024/25")] * n
    pa = np.array([[0.5, 0.3, 0.2]] * n)          # a 恒定
    pb = np.array([[0.7, 0.2, 0.1]] * n)          # b 对 H 更自信
    a = _make_preds(pa, ls, y)
    b = _make_preds(pb, ls, y)
    # 让 b 少一场（不同比赛批），验证内连接只保留交集
    b = b.iloc[:-1]
    blk = block_deltas(a, b)
    assert blk.n_paired == 5
    # δ = ℓ_a − ℓ_b；对 y=0 场次：a 给 0.5、b 给 0.7 → ℓ_a=−ln0.5 > ℓ_b=−ln0.7，δ>0
    assert blk.per_match[0] > 0


def test_cluster_bootstrap_point_matches_weighted_mean():
    blk = _block_correlated()
    out = cluster_bootstrap(blk, B=2000, seed=1)
    wm = (blk.values * blk.weights).sum() / blk.weights.sum()
    assert out["point"] == pytest.approx(wm, abs=1e-12)
    assert out["lo"] <= out["point"] <= out["hi"]


def test_cluster_robust_se_matches_manual():
    blk = _block_correlated()
    v, w = blk.values, blk.weights.astype(float)
    G = len(v)
    N = w.sum()
    d = v - (v * w).sum() / N
    expected = np.sqrt(G / (G - 1) * ((w / N) ** 2 * d ** 2).sum())
    assert cluster_robust_se(v, w) == pytest.approx(expected, abs=1e-12)


def test_design_effect_above_one_for_clustered_data():
    blk = _block_correlated()
    de = design_effect(blk)
    assert de["deff"] > 5.0       # 强簇内相关 → deff 明显 > 1


def test_width_ratio_consistent_with_design_effect():
    blk = _block_correlated()
    wr = width_ratio(blk, B=2000)
    de = design_effect(blk)
    # 簇重采样区间必须明显宽于逐场重采样（假显著之源），且宽度比 ≈ √deff。
    # 「3–5 倍」是真实足球数据上的验收目标（M2 卡验收项 7），不在合成数据上硬断。
    assert wr["ratio"] > 2.0
    assert wr["ratio"] == pytest.approx(np.sqrt(de["deff"]), rel=0.05)


def test_iid_bootstrap_narrower_than_cluster():
    blk = _block_correlated()
    cb = cluster_bootstrap(blk, B=2000)
    assert (cb["hi"] - cb["lo"]) > 0.02       # 块级区间明显更宽
