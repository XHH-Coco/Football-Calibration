"""M2 / T2.13 差距局部化层验收。依赖 panel + preds_B4/B6。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from src.eval.localisation import build_h3_frame, h3_coefficients, h3_sweep  # noqa: E402


def _has_inputs() -> bool:
    r = Path(__file__).resolve().parents[1]
    return ((r / "data" / "processed" / "panel.parquet").exists()
            and (r / "results" / "preds" / "preds_B4.csv").exists()
            and (r / "results" / "preds" / "preds_B6.csv").exists())


@pytest.mark.skipif(not _has_inputs(), reason="panel / preds 未生成")
def test_build_h3_frame():
    df = build_h3_frame()
    assert len(df) == 16_728
    assert set(df.columns) == {"gap", "promoted", "matchday", "block"}
    assert df["promoted"].isin([0.0, 1.0]).all()
    assert (df["matchday"] >= 1).all()


@pytest.mark.skipif(not _has_inputs(), reason="panel / preds 未生成")
def test_h3_coefficients_smoke():
    df = build_h3_frame()
    r = h3_coefficients(df, w=6, B=200, seed=1)
    for k in ("promoted", "early"):
        assert r[k]["lo"] <= r[k]["coef"] <= r[k]["hi"]


@pytest.mark.skipif(not _has_inputs(), reason="panel / preds 未生成")
def test_h3_sweep_windows():
    df = build_h3_frame()
    sw = h3_sweep(df)
    assert sw["window"].tolist() == [3, 6, 10]
    assert len(sw) == 3
