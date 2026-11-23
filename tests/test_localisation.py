"""M2 / T2.13 差距局部化层验收。依赖 panel + preds_B4/B6。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.eval.localisation import (  # noqa: E402
    H3_DEFINITIONS,
    build_h3_frame,
    h3_coefficients,
    h3_sensitivity,
    h3_sweep,
)


def _has_inputs() -> bool:
    r = Path(__file__).resolve().parents[1]
    return ((r / "data" / "processed" / "panel.parquet").exists()
            and (r / "results" / "preds" / "preds_B4.csv").exists()
            and (r / "results" / "preds" / "preds_B6.csv").exists())


@pytest.mark.skipif(not _has_inputs(), reason="panel / preds 未生成")
def test_build_h3_frame():
    df = build_h3_frame()
    assert len(df) == 16_728
    # v1.4：主版 matchday = min(home, away)，并保留两版敏感性所需的原始列
    assert set(df.columns) == {"gap", "promoted", "matchday", "matchday_home",
                               "matchday_away", "matchday_max", "block"}
    assert df["promoted"].isin([0.0, 1.0]).all()
    assert (df["matchday"] >= 1).all()
    assert (df["matchday_home"] >= 1).all() and (df["matchday_away"] >= 1).all()
    assert (df["matchday"] == np.minimum(df["matchday_home"], df["matchday_away"])).all()
    assert not df[["matchday_home", "matchday_away"]].isna().any().any()


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


@pytest.mark.skipif(not _has_inputs(), reason="panel / preds 未生成")
def test_h3_sensitivity_three_definitions():
    """预注册主版是 min(home,away)；另两版只作描述性对照，必须都能跑通。"""
    df = build_h3_frame()
    se = h3_sensitivity(df, w=6, B=200, seed=1)
    assert se["definition"].tolist() == [d[0] for d in H3_DEFINITIONS]
    assert se["definition"].iloc[0].startswith("min(")
    for c in ("early_lo", "early_coef", "early_hi", "promoted_lo", "promoted_coef"):
        assert (se[c].notna()).all()
    assert ((se["early_lo"] <= se["early_coef"]) & (se["early_coef"] <= se["early_hi"])).all()
