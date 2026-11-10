"""附录 A1（T3.5 / T3.6）验收：γ 趋势、逆方差合并、按日期切窗。

对应 M3 分工卡 §6 验收项 7 / 8 / 9：
  7. γ 逐季序列 22 点齐全、无缺口；
  8. 趋势斜率带区间，六联赛分看同向；
  9. 空场窗按日期切，不是按赛季切（用 ``select_window`` 的边界行为固定下来）。

前四条是纯逻辑测试（不碰数据，毫秒级）；最后两条读 ``results/logs/*.csv``，
产物不在时 skip —— 与 ``test_splits.py`` 对 ``configs/splits.json`` 的处理一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.models.a1_empty import WINDOWS, compare, pooled, select_window  # noqa: E402
from src.models.a1_gamma import LEAGUES, ROOT, trend  # noqa: E402

LOGS = ROOT / "results" / "logs"


def _wide(slope: float, intercept: float = 0.30, se: float = 0.02, n: int = 22) -> pd.DataFrame:
    d = pd.DataFrame({"season": [f"{2003 + i}/{4 + i:02d}" for i in range(n)],
                      "gamma_pooled": intercept + slope * np.arange(n),
                      "se_pooled": np.full(n, se)})
    return d


def test_trend_recovers_known_slope():
    tr = trend(_wide(-0.01))
    assert tr["slope_per_year"] == pytest.approx(-0.01, abs=1e-12)
    assert tr["slope_per_decade"] == pytest.approx(-0.10, abs=1e-12)
    assert tr["lo95"] < tr["slope_per_year"] < tr["hi95"]   # 区间包住点估计
    assert tr["hi95"] < 0                                   # 无噪声合成数据 → 排除 0


def test_trend_interval_widens_with_se():
    a = trend(_wide(-0.01, se=0.02))
    b = trend(_wide(-0.01, se=0.06))
    assert (b["hi95"] - b["lo95"]) > 2.5 * (a["hi95"] - a["lo95"])


def test_pooled_is_inverse_variance_and_tighter():
    d = pd.DataFrame({"gamma": [0.20, 0.20, 0.20], "se": [0.01, 0.02, 0.04],
                      "n_matches": [100, 100, 100], "converged": [True] * 3})
    p = pooled(d)
    assert p["gamma"] == pytest.approx(0.20, abs=1e-12)
    assert p["se"] < 0.01                              # 合并比任何一个都紧
    assert p["se"] == pytest.approx(1 / np.sqrt(1e4 + 0.25e4 + 0.0625e4), rel=1e-12)
    assert p["n_matches"] == 300


def test_compare_se_is_quadrature_and_windows_disjoint():
    win = {"pre": {"gamma": 0.26, "se": 0.02},
           "empty": {"gamma": 0.12, "se": 0.024},
           "post": {"gamma": 0.23, "se": 0.018}}
    out = {c["contrast"]: c for c in compare(win)}
    e = out["empty − pre"]
    assert e["diff"] == pytest.approx(-0.14, abs=1e-12)
    assert e["se"] == pytest.approx(np.hypot(0.02, 0.024), rel=1e-12)
    assert e["hi95"] < 0                               # 明显下探
    assert out["empty − post"]["diff"] == pytest.approx(-0.11, abs=1e-12)


def test_windows_cut_on_dates_not_seasons():
    """同一天的两侧边界：窗口是半开区间，且不读 season 列。"""
    panel = pd.DataFrame({
        "date": ["2020-05-31", "2020-06-01", "2021-07-31", "2021-08-01"],
        "season": ["2019/20", "2019/20", "2020/21", "2021/22"],
        "league": ["E0"] * 4,
    })
    assert list(select_window(panel, *WINDOWS[0][1:])["date"]) == ["2020-05-31"]
    assert list(select_window(panel, *WINDOWS[1][1:])["date"]) == ["2020-06-01", "2021-07-31"]
    assert list(select_window(panel, *WINDOWS[2][1:])["date"]) == ["2021-08-01"]
    # 2019/20 被劈成两半：这场比赛同属一个 season、却分属两个窗
    assert panel.loc[1, "season"] == panel.loc[0, "season"]


def test_windows_are_contiguous():
    starts = [w[1] for w in WINDOWS]
    ends = [w[2] for w in WINDOWS]
    assert ends[:-1] == starts[1:]
    assert starts == sorted(starts)


@pytest.mark.parametrize("fname,rows", [("gamma_by_season.csv", 22),
                                        ("gamma_empty_window.csv", 18)])
def test_artifacts_have_expected_shape(fname, rows):
    p = LOGS / fname
    if not p.exists():
        pytest.skip(f"{fname} 未生成（先跑 python -m src.models.a1_*）")
    d = pd.read_csv(p, encoding="utf-8")
    assert len(d) == rows


def test_gamma_series_complete_and_all_leagues_declining():
    p = LOGS / "gamma_by_season.csv"
    if not p.exists():
        pytest.skip("gamma_by_season.csv 未生成")
    d = pd.read_csv(p, encoding="utf-8")
    assert d["season"].tolist() == sorted(d["season"].tolist())
    assert d["season"].nunique() == 22
    assert not d[[f"gamma_{lg}" for lg in LEAGUES]].isna().any().any()
    for lg in LEAGUES:
        assert d[f"se_{lg}"].gt(0).all()
        tr = trend(d, f"gamma_{lg}", f"se_{lg}")
        assert tr["hi95"] < 0, f"{lg} 斜率区间不排除 0：{tr}"
    tr = trend(d)
    assert tr["slope_per_decade"] == pytest.approx(-0.090, abs=0.02)


def test_empty_window_dips_in_every_league():
    p = LOGS / "gamma_empty_window.csv"
    if not p.exists():
        pytest.skip("gamma_empty_window.csv 未生成")
    d = pd.read_csv(p, encoding="utf-8")
    piv = d.pivot_table(index="league", columns="window", values="gamma")
    assert (piv["empty"] < piv["pre"]).all()
    assert (piv["empty"] < piv["post"]).all()
    assert d.loc[d["window"] == "empty", "start"].unique().tolist() == ["2020-06-01"]
