"""M2 / T2.10 校准层验收：符号断言、逐块斜率形状、尾箱偏差。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.eval.calibration import (  # noqa: E402
    _fit_slope,
    calibration_by_block,
    expected_tail_bias_sign,
    tail_bin_bias,
)


def test_sign_assertion_h1_direction():
    # 斜率 > 1（under-dispersed）：低概率区曲线在对角线下方 → 低箱 bias=pred−freq > 0
    assert expected_tail_bias_sign(1.2) == (+1, -1)
    # 斜率 < 1（over-dispersed）：方向相反
    assert expected_tail_bias_sign(0.8) == (-1, +1)
    assert expected_tail_bias_sign(1.0) == (0, 0)


def test_fit_slope_recovers_calibrated_probabilities():
    rng = np.random.default_rng(0)
    n = 2000
    pk = rng.uniform(0.05, 0.95, n)
    ok = (rng.uniform(size=n) < pk).astype(int)
    b, _ = _fit_slope(pk, ok)
    assert b == pytest.approx(1.0, abs=0.2)


def test_calibration_by_block_shape():
    rng = np.random.default_rng(1)
    n = 400
    p = rng.uniform(0.05, 0.95, (n, 3))
    y = rng.integers(0, 3, n)
    blocks = np.repeat(np.arange(4), 100)
    S = calibration_by_block(p, y, blocks)
    assert S.shape == (4, 3)


def test_tail_bin_bias_shape():
    rng = np.random.default_rng(2)
    n = 500
    p = rng.uniform(0.05, 0.95, (n, 3))
    y = rng.integers(0, 3, n)
    low, high = tail_bin_bias(p, y)
    assert low.shape == (3,) and high.shape == (3,)
