"""G1 验收项 4：``results/preds/preds_B{3,4}.csv`` 的落盘契约。

`data_interface.md` §1 / §1.0 / §1.1：
  - 11 列，顺序固定，``p_home, p_draw, p_away`` 且和为 1（atol 1e-9）；
  - ``y ∈ {0,1,2}`` 且与 FTR 同源同序（H/D/A）；
  - ``match_id = league|season|date|home|away``，ISO 日期，单文件内唯一；
  - 一个 arm 一个文件含全部 48 块，合计 16,733 行；
  - 同一块上两个 arm 必须预测同一批比赛，否则配对差算不出来。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.models.run_b4 import PRED_COLS, check_pred  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRED_DIR = ROOT / "results" / "preds"
EXPECTED_ROWS = 16_733


def _load(arm: str) -> pd.DataFrame:
    p = PRED_DIR / f"preds_{arm}.csv"
    if not p.exists():
        pytest.skip(f"{p.name} 未生成（先跑 python -m src.models.run_b4）")
    return pd.read_csv(p, dtype={"match_id": str, "season": str, "date": str})


@pytest.mark.parametrize("arm", ["B3", "B4"])
def test_columns_and_row_count(arm):
    d = _load(arm)
    assert d.columns.tolist() == PRED_COLS
    assert len(d) == EXPECTED_ROWS
    assert (d["model"] == arm).all()


@pytest.mark.parametrize("arm", ["B3", "B4"])
def test_probabilities_and_labels(arm):
    d = _load(arm)
    assert np.allclose(d[["p_home", "p_draw", "p_away"]].sum(axis=1), 1.0, atol=1e-9)
    assert (d[["p_home", "p_draw", "p_away"]].to_numpy() >= 0).all()
    assert set(d["y"].unique()) <= {0, 1, 2}
    check_pred(d, EXPECTED_ROWS)             # 跑的是落盘前那一套断言


@pytest.mark.parametrize("arm", ["B3", "B4"])
def test_match_id_contract(arm):
    d = _load(arm)
    assert d["match_id"].notna().all()
    assert d["match_id"].is_unique
    rebuilt = (d["league"] + "|" + d["season"] + "|" + d["date"] + "|"
               + d["home"] + "|" + d["away"])
    assert (rebuilt == d["match_id"]).all()
    assert d["season"].str.fullmatch(r"\d{4}/\d{2}").all()
    assert d["date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()


def test_arms_share_the_same_matches():
    a, b = _load("B3"), _load("B4")
    assert a["match_id"].tolist() == b["match_id"].tolist()
    assert (a["y"].to_numpy() == b["y"].to_numpy()).all()


def test_covers_all_48_blocks():
    d = _load("B4")
    blocks = d.groupby(["league", "season"], sort=False).size()
    assert len(blocks) == 48
    assert blocks.min() > 0
    assert blocks.sum() == EXPECTED_ROWS


def test_matches_panel_when_present():
    p = ROOT / "data" / "processed" / "panel.parquet"
    if not p.exists():
        pytest.skip("panel.parquet 不入库，本地未生成")
    panel = pd.read_parquet(p, columns=["match_id"])
    d = _load("B4")
    assert set(d["match_id"]) <= set(panel["match_id"])
