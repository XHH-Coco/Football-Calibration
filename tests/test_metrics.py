"""M2 / T2.4 指标层验收：与 sklearn 差 < 1e-9；全 1/3 → ln3；Murphy 恒等式。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from sklearn.metrics import brier_score_loss, log_loss as sk_log_loss  # noqa: E402

from src.eval.metrics import (  # noqa: E402
    brier,
    ece,
    log_loss,
    mean_brier,
    mean_log_loss,
    mean_rps,
    murphy_decomposition,
    reliability_curve,
    rps,
)


def _rng(n: int = 500, seed: int = 20261110) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    p = rng.random((n, 3))
    p /= p.sum(axis=1, keepdims=True)
    y = rng.integers(0, 3, size=n)
    return p, y


def test_uniform_is_ln3():
    n = 100
    p = np.full((n, 3), 1 / 3)
    y = np.zeros(n, dtype=int)
    assert mean_log_loss(p, y) == pytest.approx(np.log(3), abs=1e-12)


def test_log_loss_matches_sklearn():
    for seed in (0, 1, 2):
        p, y = _rng(300, seed=seed)
        assert mean_log_loss(p, y) == pytest.approx(sk_log_loss(y, p), abs=1e-9)


def test_brier_matches_sklearn():
    for seed in (3, 4, 5):
        p, y = _rng(300, seed=seed)
        assert mean_brier(p, y) == pytest.approx(brier_score_loss(y, p), abs=1e-9)


def test_log_loss_returns_per_match_vector():
    p, y = _rng(50)
    v = log_loss(p, y)
    assert v.shape == (50,)
    assert np.isfinite(v).all()
    assert v.mean() == pytest.approx(mean_log_loss(p, y))


def test_brier_range_and_rps_range():
    p, y = _rng(200)
    b = brier(p, y)
    assert np.all((b >= 0) & (b <= 2))
    r = rps(p, y)
    assert np.all((r >= 0) & (r <= 1))


def test_rps_perfect_and_antiperfect():
    p_perfect = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    y = np.array([0, 1, 2])
    assert mean_rps(p_perfect, y) == pytest.approx(0.0, abs=1e-12)
    p_wrong = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])
    assert mean_rps(p_wrong, y) > 0.5


def test_murphy_decomposition_invariants():
    p, y = _rng(1000, seed=7)
    m = murphy_decomposition(p, y, n_bins=10)
    # 各分量非负
    for k in ("reliability", "resolution", "uncertainty", "within_bin_var"):
        assert m[k] >= -1e-12
    # UNC = 基准率熵 ō̄(1−ō̄)，可直接由 y 复算
    o_bar = (np.eye(3)[y]).mean(axis=0)
    assert m["uncertainty"] == pytest.approx(float((o_bar * (1 - o_bar)).sum()),
                                             abs=1e-12)
    # resolution ≤ uncertainty（Brier 分解的已知界）
    assert m["resolution"] <= m["uncertainty"] + 1e-9
    # binned 分解接近 Brier（连续预测分箱后的残留 = within_bin_var）
    assert m["brier"] == pytest.approx(
        m["reliability"] - m["resolution"] + m["uncertainty"] + m["within_bin_var"],
        abs=0.01)


def test_ece_in_unit_interval():
    p, y = _rng(800, seed=11)
    e = ece(p, y, n_bins=10)
    assert 0.0 <= e <= 1.0


def test_reliability_curve_columns():
    p, y = _rng(500, seed=13)
    c = reliability_curve(p, y, n_bins=10)
    assert set(c.columns) == {"class", "pred_mean", "obs_freq", "count"}
    assert set(c["class"]) <= {0, 1, 2}
    assert np.all((c["obs_freq"] >= 0) & (c["obs_freq"] <= 1))
