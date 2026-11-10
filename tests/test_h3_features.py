"""M1 / T1.9（S5）—— H3 两列（三列输出）的独立泄漏测试。

S2 已在 `tests/test_s2_clean.py::test_h3_invariant_to_post_match_shuffle`
落地核心断言；本文件按 G1 前计划补齐**独立入口**，并把「H3 只能由季前名单
与赛程构造」拆成几条可单独失败的断言。任何一条变红都说明 H3 用到了赛后
信息，H3（差距局部化）的结论随之作废。

运行：``pytest -q tests/test_h3_features.py``（项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    H3_PANEL_COLS,
    PANEL_COLUMNS,
    POST_MATCH_COLS,
    add_h3_features,
    build_panel,
    h3_invariant_to_post_match,
)

H3_IDENTITY_COLS = ("league", "season", "date", "home", "away")


@pytest.fixture(scope="module")
def panel():
    return build_panel()


def test_01_h3_columns_present_and_complete(panel):
    """panel 22 列里三列齐全、无空值、是整数。"""
    assert tuple(panel.columns) == PANEL_COLUMNS
    for col in H3_PANEL_COLS:
        assert col in panel.columns
        assert panel[col].notna().all()
        assert pd.api.types.is_integer_dtype(panel[col])
    assert set(panel["is_promoted_home"].unique()) <= {0, 1}
    assert set(panel["is_promoted_away"].unique()) <= {0, 1}
    assert panel["matchday"].between(1, 38).all()


def test_02_invariant_to_post_match_shuffle(panel):
    """把全部 9 个赛后列逐列打乱后重算，三列必须逐元素不变。"""
    rng = np.random.default_rng(20261110)
    shuffled = panel.copy()
    for col in POST_MATCH_COLS:
        values = shuffled[col].to_numpy().copy()
        rng.shuffle(values)
        shuffled[col] = values
    recomputed = add_h3_features(shuffled)
    assert panel[list(H3_PANEL_COLS)].equals(recomputed[list(H3_PANEL_COLS)])
    assert h3_invariant_to_post_match(panel)


def test_03_identity_columns_alone_reproduce_h3(panel):
    """只留 5 列身份/赛程信息，删掉所有赛后列，三列仍能逐元素复现。"""
    slim = panel[list(H3_IDENTITY_COLS)].copy()
    recomputed = add_h3_features(slim)
    assert panel[list(H3_PANEL_COLS)].equals(recomputed[list(H3_PANEL_COLS)])


def test_04_shuffled_odds_columns_do_not_change_h3(panel):
    """赔率列同样属于「不该被 H3 看到」的信息，打乱后结果不变。"""
    rng = np.random.default_rng(777)
    shuffled = panel.copy()
    for col in ("PSCH", "PSCD", "PSCA"):
        values = shuffled[col].to_numpy().copy()
        rng.shuffle(values)
        shuffled[col] = values
    recomputed = add_h3_features(shuffled)
    assert panel[list(H3_PANEL_COLS)].equals(recomputed[list(H3_PANEL_COLS)])


def test_05_first_season_has_no_promoted_teams(panel):
    """首季 0304 没有「上一季名单」，全季置 0（不是置 1）。"""
    first = panel.loc[panel["season"] == "2003/04"]
    assert len(first) > 0
    assert (first["is_promoted_home"] == 0).all()
    assert (first["is_promoted_away"] == 0).all()


def test_06_promoted_teams_le_3_in_eval_window(panel):
    """评估窗 48 块，每块被标记的升班马队数 ≤ 3（S2 的「上一季名单」口径）。"""
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]
    counts = {}
    for (lg, season), g in sub.groupby(["league", "season"]):
        home = set(g.loc[g["is_promoted_home"] == 1, "home"])
        away = set(g.loc[g["is_promoted_away"] == 1, "away"])
        counts[(lg, season)] = len(home | away)
    assert len(counts) == 48
    assert max(counts.values()) <= 3


def test_07_matchday_is_continuous_and_includes_away_appearances(panel):
    """matchday = 主队本季已完成场次 + 1，**含其客场出场**；独立复算逐元素相等。"""
    n = len(panel)
    rows = np.arange(n)
    long = pd.concat([
        pd.DataFrame({"league": panel["league"], "season": panel["season"],
                      "date": panel["date"], "team": panel["home"],
                      "row": rows, "side": "H"}),
        pd.DataFrame({"league": panel["league"], "season": panel["season"],
                      "date": panel["date"], "team": panel["away"],
                      "row": rows, "side": "A"}),
    ], ignore_index=True)
    long = long.sort_values(["league", "season", "team", "date", "row"],
                            kind="mergesort")
    long["seq"] = long.groupby(["league", "season", "team"], sort=False).cumcount() + 1
    agg = long.groupby(["league", "season", "team"])["seq"].agg(["min", "max", "count"])
    assert ((agg["min"] == 1) & (agg["max"] == agg["count"])).all()
    home_seq = (long.loc[long["side"] == "H"].set_index("row")["seq"]
                .reindex(range(n)))
    assert np.array_equal(home_seq.to_numpy(), panel["matchday"].to_numpy())
