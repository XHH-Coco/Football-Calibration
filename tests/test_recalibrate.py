"""M2 / T2.11 重校准层验收：log-odds 往返、恒等恢复、B6r 行数。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.eval.recalibrate import (  # noqa: E402
    _from_logodds,
    _to_logodds,
    apply_recalibration,
    fit_recalibration,
)


def test_logodds_roundtrip():
    rng = np.random.default_rng(0)
    p = rng.random((50, 3))
    p /= p.sum(axis=1, keepdims=True)
    z = _to_logodds(p)
    q = _from_logodds(z)
    assert np.allclose(p, q, atol=1e-9)
    assert np.allclose(q.sum(axis=1), 1.0, atol=1e-12)


def test_apply_recalibration_sums_to_one():
    rng = np.random.default_rng(1)
    p = rng.random((100, 3))
    p /= p.sum(axis=1, keepdims=True)
    q = apply_recalibration(p, c=1.3, d=-0.2)
    assert np.allclose(q.sum(axis=1), 1.0, atol=1e-12)
    assert np.all((q > 0) & (q < 1))


def test_fit_recovers_identity_on_calibrated_data():
    rng = np.random.default_rng(3)
    n = 5000
    p = rng.dirichlet(np.ones(3) * 3, n)          # 已校准：y 直接按 p 抽样
    y = np.array([rng.choice(3, p=row) for row in p])
    c, d = fit_recalibration(p, y)
    assert c == pytest.approx(1.0, abs=0.3)
    assert d == pytest.approx(0.0, abs=0.3)


def test_run_b6r_row_count():
    p = Path(__file__).resolve().parents[1] / "data" / "processed" / "panel.parquet"
    if not p.exists():
        pytest.skip("panel.parquet 不入库，本地未生成")
    from src.eval.recalibrate import run_b6r
    out = run_b6r(verbose=False)
    assert len(out) == 16_728
    assert out.columns.tolist() == [
        "match_id", "league", "season", "date", "home", "away",
        "model", "p_home", "p_draw", "p_away", "y"]
    assert np.allclose(out[["p_home", "p_draw", "p_away"]].sum(axis=1), 1.0, atol=1e-9)
