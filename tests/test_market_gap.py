"""M2 / T2.9 市场差距层验收。依赖已入库的 preds_B3/B4/B6 与 power/shin 日志。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from src.eval.market_gap import build_market_gap, market_gap  # noqa: E402


def _has_preds() -> bool:
    d = Path(__file__).resolve().parents[1] / "results" / "preds"
    return (d / "preds_B4.csv").exists() and (d / "preds_B6.csv").exists()


@pytest.mark.skipif(not _has_preds(), reason="预测文件未生成")
def test_market_gap_b4_three_methods():
    rows = market_gap("B4")
    assert len(rows) == 3
    assert {r["devig"] for r in rows} == {"proportional", "power", "shin"}
    for r in rows:
        assert r["n_paired"] == 16_728
    prop = next(r for r in rows if r["devig"] == "proportional")
    # B4 − B6 ≈ 0.0353（pooled）
    assert prop["delta_ll"] == pytest.approx(0.0353, abs=0.005)
    assert prop["lo90"] < prop["delta_ll"] < prop["hi90"]


@pytest.mark.skipif(not _has_preds(), reason="预测文件未生成")
def test_build_market_gap_returns_dataframe():
    df = build_market_gap(arms=["B4"])
    assert list(df.columns) == ["arm", "devig", "delta_ll", "lo90", "hi90",
                                "delta_brier", "n_paired"]
    assert len(df) == 3
    assert (df["arm"] == "B4").all()
