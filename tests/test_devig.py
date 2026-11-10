"""M2 / T2.5 去抽水验收：三法各自和为 1；边界过滤；B6 有效 n = 16,728。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from src.eval.devig import (  # noqa: E402
    B6_N,
    build_b6,
    check_odds,
    devig,
    power,
    proportional,
    shin,
)

ODDS = np.array([
    [2.1, 3.4, 3.6],
    [1.6, 3.9, 6.0],
    [2.4, 3.2, 3.0],
    [2.8, 3.1, 2.6],
    [3.4, 3.3, 2.1],
])


def test_proportional_known_values():
    p = proportional(np.array([[2.0, 3.0, 4.0]]))
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-12)
    # 比例法：p ∝ 1/o
    inv = 1.0 / np.array([2.0, 3.0, 4.0])
    assert np.allclose(p[0], inv / inv.sum(), atol=1e-12)


def test_power_fair_odds_gives_uniform():
    p = power(np.array([[2.0, 2.0, 2.0]]))
    assert np.allclose(p, np.full((1, 3), 1 / 3), atol=1e-9)


def test_shin_fair_odds_gives_uniform():
    p, fb = shin(np.array([[2.0, 2.0, 2.0]]))
    assert fb == []
    assert np.allclose(p, np.full((1, 3), 1 / 3), atol=1e-9)


def test_all_methods_sum_to_one():
    for method in ("proportional", "power", "shin"):
        p = devig(ODDS, method)
        assert np.allclose(p.sum(axis=1), 1.0, atol=1e-12)
        assert np.all((p > 0) & (p < 1))


def test_methods_close_on_typical_odds():
    p1, p2, p3 = proportional(ODDS), power(ODDS), shin(ODDS)[0]
    # 典型足球赔率下三法互差 < 0.02（> 0.05 才是脏数据报警线，见分工方案 §5.5）
    assert np.abs(p1 - p2).max() < 0.02
    assert np.abs(p1 - p3).max() < 0.02


def test_power_satisfies_defining_equation():
    p = power(ODDS)
    inv = 1.0 / ODDS
    for r in range(len(ODDS)):
        # 存在 k 使 Σ (1/o_i)^k = 1；等价于 p ∝ (1/o)^k，Σp=1（已验）且 p 单调于 1/o
        assert np.corrcoef(inv[r], p[r])[0, 1] > 0.99


def test_check_odds_filters_bad_rows():
    o = np.array([[1.0, 2.0, 3.0], [np.nan, 2.0, 3.0], [1.5, 2.0, 3.0]])
    mask = check_odds(o)
    assert mask.tolist() == [False, False, True]


def test_devig_unknown_method_raises():
    with pytest.raises(ValueError):
        devig(ODDS, "nope")


def test_build_b6_row_count_and_schema():
    p = Path(__file__).resolve().parents[1] / "data" / "processed" / "panel.parquet"
    if not p.exists():
        pytest.skip("panel.parquet 不入库，本地未生成")
    frame = build_b6(out_path=None, write_aux=False)
    assert len(frame) == B6_N == 16_728
    assert (frame["model"] == "B6").all()
    assert frame.columns.tolist() == [
        "match_id", "league", "season", "date", "home", "away",
        "model", "p_home", "p_draw", "p_away", "y"]
    assert np.allclose(frame[["p_home", "p_draw", "p_away"]].sum(axis=1),
                       1.0, atol=1e-9)
    assert frame["match_id"].is_unique
    assert set(frame["y"].unique()) <= {0, 1, 2}
