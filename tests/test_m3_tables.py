"""§4.2 / 附录 A 成品表的一致性：表 ← 日志 ← 预测文件，三层必须对得上。

对应 M3 分工卡 §6：
  3. 48 折全部跑完、失败折 ≤ 2；
  4. 预测文件 16,733 行；
  5. B4 的 log loss 在 0.96–1.06；
  7/8. γ 22 点、斜率带区间且六联赛同向。
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.models.a1_empty import pooled as pool_windows  # noqa: E402
from src.models.a1_gamma import LEAGUES, ROOT, trend  # noqa: E402
from src.models.b4_dixon_coles import RHO_GRID, XI_GRID  # noqa: E402
from src.models.m3_report_tables import BUILDERS, build_all  # noqa: E402

LOGS = ROOT / "results" / "logs"
TABLES = ROOT / "products" / "tables"
PREDS = ROOT / "results" / "preds"


def _log(name: str) -> pd.DataFrame:
    p = LOGS / f"{name}.csv"
    if not p.exists():
        pytest.skip(f"{name}.csv 未生成")
    return pd.read_csv(p, encoding="utf-8")


def _table(name: str) -> pd.DataFrame:
    p = TABLES / f"{name}.csv"
    if not p.exists():
        pytest.skip(f"{name}.csv 未生成（先跑 python -m src.models.m3_report_tables）")
    return pd.read_csv(p, encoding="utf-8")


def _match_loss(d: pd.DataFrame) -> np.ndarray:
    p = d[["p_home", "p_draw", "p_away"]].to_numpy(float)
    return -np.log(np.clip(p[np.arange(len(d)), d["y"].to_numpy()], 1e-15, None))


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_shipped_table_matches_a_fresh_build(name):
    disk = _table(name)
    fresh = pd.read_csv(io.StringIO(build_all()[name].to_csv(index=False)))
    pd.testing.assert_frame_equal(disk, fresh, check_dtype=False,
                                  check_exact=False, rtol=1e-9, atol=1e-9)


def test_model_fit_row_totals_and_acceptance_band():
    t = _table("t4_2_model_fit").set_index("league")
    assert t.loc["ALL", "n_folds"] == 48
    assert t.loc["ALL", "n_matches"] == 16733
    assert t.loc["ALL", "n_failed_fits"] == 0
    assert t.loc[list(LEAGUES), "n_folds"].sum() == 48
    assert t.loc[list(LEAGUES), "n_matches"].sum() == t.loc["ALL", "n_matches"]
    assert 0.96 <= t.loc["ALL", "logloss_b4"] <= 1.06
    assert t.loc["ALL", "logloss_b4"] < t.loc["ALL", "logloss_b3"]
    assert t.loc["ALL", "dll"] > 0
    assert t.loc["ALL", "n_b4_better"] >= 24


def test_preds_reproduce_every_block_logloss():
    b3 = pd.read_csv(PREDS / "preds_B3.csv")
    b4 = pd.read_csv(PREDS / "preds_B4.csv")
    conv = _log("convergence").set_index("block_id")
    assert len(b3) == len(b4) == int(conv["n_test"].sum())
    for d, col in ((b3, "test_logloss_b3"), (b4, "test_logloss_b4")):
        d = d.assign(block_id=d["league"] + "|" + d["season"])
        rec = d.groupby("block_id").apply(
            lambda g: _match_loss(g).mean(), include_groups=False)
        assert len(rec) == 48
        assert np.allclose(rec.sort_index(), conv.loc[rec.index, col].sort_index(),
                           atol=1e-12)
    sizes = b4.assign(block_id=b4["league"] + "|" + b4["season"]) \
             .groupby("block_id").size()
    assert (sizes.sort_index() == conv["n_test"].sort_index()).all()


def test_hyperparameter_counts_cover_the_grid():
    t = _table("t4_2_hyperparameters")
    for p, grid in (("xi", XI_GRID), ("rho", RHO_GRID)):
        g = t.loc[t["parameter"] == p]
        points = g.loc[g["kind"] == "grid"]
        assert len(points) == len(grid)
        assert points["n_folds"].sum() == 48
        assert sorted(points["value"].round(6)) == sorted(np.round(grid, 6))
    xi = t.loc[(t["parameter"] == "xi") & (t["kind"] == "interior_4_mid")]
    assert int(xi["n_folds"].iloc[0]) == int(
        (~_log("convergence")["xi"].isin([XI_GRID[0], XI_GRID[-1]])).sum())
    # 堆积是单侧的：没有折选到网格最大端
    assert t.loc[(t["parameter"] == "xi") & (t["value"] == XI_GRID[-1]), "n_folds"].iloc[0] == 0


def test_paired_summary_matches_fold_rows_and_selection():
    folds = _table("t4_2_paired_folds")
    summ = _table("t4_2_paired_summary").iloc[0]
    sel = _log("xi_rho_by_block").set_index("block_id")
    assert len(folds) == 48
    assert np.allclose(folds.set_index("block_id")["xi"].sort_index(),
                       sel["xi"].sort_index())
    assert int(summ["n_sig_vs_neighbour"]) == int(folds["xi_neighbour_significant"].sum())
    assert int(summ["n_sig_vs_best_other"]) == int(folds["runner_up_significant"].sum())
    nb = folds.dropna(subset=["dll_vs_neighbour"])
    assert summ["median_abs_dll_vs_neighbour"] == pytest.approx(
        nb["dll_vs_neighbour"].abs().median(), abs=1e-6)
    assert summ["median_se_vs_neighbour"] == pytest.approx(
        nb["se_vs_neighbour"].median(), abs=1e-6)
    # 「差比噪声小」：中位 |t| 远低于 1.96
    assert summ["median_abs_t_vs_neighbour"] < 1.0


def test_trend_table_reproduces_weighted_least_squares():
    g = _log("gamma_by_season")
    t = _table("tA1_gamma_trend").set_index("scope")
    assert len(t) == 7 and t.loc["pooled", "n_points"] == 22
    for scope, col, se_col in ([("pooled", "gamma_pooled", "se_pooled")] +
                               [(lg, f"gamma_{lg}", f"se_{lg}") for lg in LEAGUES]):
        tr = trend(g, col, se_col)
        for k in ("slope_per_year", "lo95", "hi95", "first", "last"):
            assert t.loc[scope, k] == pytest.approx(tr[k], abs=1e-6)
        assert t.loc[scope, "hi95"] < 0, f"{scope} 的斜率区间不排除 0"
    assert t.loc["pooled", "slope_per_decade"] == pytest.approx(-0.090, abs=0.02)


def test_empty_window_contrasts_are_negative_and_use_pooled_se():
    w = _log("gamma_empty_window")
    t = _table("tA1_empty_window")
    win = {name: pool_windows(w.loc[w["window"] == name])
           for name in ("pre", "empty", "post")}
    for name, p in win.items():
        row = t.loc[(t["scope"] == "pooled") & (t["window"] == name)].iloc[0]
        assert row["gamma"] == pytest.approx(p["gamma"], abs=1e-6)
        assert row["n_matches"] == p["n_matches"]
    for other in ("pre", "post"):
        row = t.loc[t["window"] == f"empty-{other}"].iloc[0]
        diff = win["empty"]["gamma"] - win[other]["gamma"]
        se = np.hypot(win["empty"]["se"], win[other]["se"])
        assert row["diff"] == pytest.approx(diff, abs=1e-6)
        assert row["se"] == pytest.approx(se, abs=1e-6)
        assert row["hi95"] < 0 and row["diff"] < 0
    assert (t.loc[t["scope"] == "contrast", "yoy_sd"] > 0).all()


def test_extrapolation_pooled_row_is_match_weighted():
    e = _log("a1_extrapolation")
    t = _table("tA1_extrapolation").set_index("league")
    assert t.loc["ALL", "scope"] == "pooled"
    assert t.loc["ALL", "n_test"] == e["n_test"].sum() == 2058
    for col in ("ll_stale", "ll_oracle"):
        assert t.loc["ALL", col] == pytest.approx(
            (e[col] * e["n_test"]).sum() / e["n_test"].sum(), abs=1e-6)
    assert t.loc["ALL", "dll"] == pytest.approx(
        t.loc["ALL", "ll_stale"] - t.loc["ALL", "ll_oracle"], abs=1e-9)
    assert t.loc[list(LEAGUES), "n_test"].sum() == t.loc["ALL", "n_test"]
    assert t.loc["ALL", "dll"] > 0             # 用真实 γ 总体更好
