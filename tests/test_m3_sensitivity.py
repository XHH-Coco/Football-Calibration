"""M3 复核的三张敏感性表必须自洽（不重跑模型，只读已落盘产物）。

守三条容易悄悄坏掉的东西：
  1. `flat` 配置（ξ=ρ=0）必须逐折等于 B3——这是整条比较管线的退化对照，
     它一旦不成立，说明敏感性脚本走的不是交付版的同一条拟合路径；
  2. 固定超参的四档排序（centre/centre_neg/min_xi/flat）不能翻；
  3. ρ 外扩表里记录的最严物理下界必须与「−0.15 已在边界上」这个结论一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOGS = ROOT / "results" / "logs"
SENS = LOGS / "sensitivity"


def _need(*paths: Path) -> None:
    for p in paths:
        if not p.exists():
            pytest.skip(f"{p.name} 未生成（先跑对应的 sens_* 脚本）")


def test_fixed_hp_table_shape_and_convergence():
    p = LOGS / "b4_fixed_hp_by_fold.csv"
    _need(p)
    d = pd.read_csv(p)
    assert len(d) == 4 * 48
    assert set(d["config"]) == {"centre", "centre_neg", "min_xi", "flat"}
    assert d.groupby("config").size().eq(48).all()
    assert d["converged"].all()
    assert np.allclose(d.groupby("config")["n_test"].sum() / 48, d["n_test"].mean(),
                       rtol=0.5)


def test_flat_config_reproduces_b3():
    """退化对照：ξ=ρ=0 的逐折 test log loss 必须等于 convergence.csv 的 B3 列。

    容差 1e-5 而不是 0：两条路径都收敛到同一个最优点，但 L-BFGS 的迭代路径不同
    （B3 由 `run_b3` 直接调，`flat` 经 `b4.fit` 再调同一函数），末位可差 5e-7。
    真正的错误——权重没归一、参考日不同、ρ 没真正置 0——会产生 1e-3 以上的差，
    所以 1e-5 仍然能抓住它们。
    """
    p = LOGS / "b4_fixed_hp_by_fold.csv"
    _need(p)
    d = pd.read_csv(p)
    flat = d.loc[d["config"] == "flat"].set_index("block_id")["test_logloss"]
    b3 = pd.read_csv(LOGS / "convergence.csv").set_index("block_id")["test_logloss_b3"]
    assert np.max(np.abs(flat - b3.loc[flat.index])) < 1e-5


def test_fixed_hp_ranking_is_stable():
    p = LOGS / "b4_fixed_hp_by_fold.csv"
    _need(p)
    d = pd.read_csv(p)
    pooled = (d.assign(w=d["n_test"]).groupby("config")
              .apply(lambda g: np.average(g["test_logloss"], weights=g["w"]),
                     include_groups=False))
    # centre_neg 最优、centre 次之、flat（=B3）最差：与报告 §4.2.5 的表一致
    assert pooled["centre_neg"] < pooled["centre"] < pooled["min_xi"] < pooled["flat"]
    assert pooled["flat"] == pytest.approx(0.9986, abs=5e-4)


def test_contrast_table_has_degenerate_zero():
    p = LOGS / "b4_fixed_hp_contrasts.csv"
    _need(p)
    d = pd.read_csv(p)
    row = d.loc[(d["config"] == "flat") & (d["vs"] == "B3")].iloc[0]
    assert row["point"] == pytest.approx(0.0, abs=1e-12)
    # 固定中心 vs 已放弃的 argmin 必须为负（更好），且区间不含 0
    c = d.loc[(d["config"] == "centre") & (d["vs"] == "argmin_abandoned")].iloc[0]
    assert c["point"] < 0 and c["hi90"] < 0


def test_rho_extension_floor_blocks_the_deep_corner():
    p = LOGS / "b4_rho_extension.csv"
    _need(p)
    d = pd.read_csv(p)
    assert len(d) == 48
    # 每折都排除掉了一些候选（−0.25 / −0.35 会撞上 τ>0 的物理下界）
    assert (d["n_candidates_infeasible"] > 0).all()
    assert d["rho_floor_inner"].max() < -0.15 + 0.02      # 最紧的折贴着 −0.15
    assert d["rho_ext"].min() >= -0.35


def test_val3_window_uses_three_seasons():
    p = LOGS / "b4_val3_window.csv"
    _need(p)
    d = pd.read_csv(p)
    assert len(d) == 48
    assert d["n_val"].median() > 900                     # 1 季约 306–380 场
    assert d["n_candidates_converged"].min() == 30


def test_sensitivity_preds_are_schema_clean():
    files = sorted(SENS.glob("preds_B4_*.csv")) if SENS.exists() else []
    if not files:
        pytest.skip("sensitivity/ 下无预测文件")
    for f in files:
        d = pd.read_csv(f)
        assert d.columns.tolist() == ["match_id", "league", "season", "date", "home",
                                      "away", "y", "p_home", "p_draw", "p_away",
                                      "model"] or {"p_home", "p_draw", "p_away"} <= set(d.columns)
        s = d[["p_home", "p_draw", "p_away"]].to_numpy().sum(axis=1)
        assert np.allclose(s, 1.0, atol=1e-9), f.name
        assert (d[["p_home", "p_draw", "p_away"]].to_numpy() >= 0).all(), f.name


def test_main_pipeline_runs_on_the_fixed_rule():
    """主口径守门：48 折的 (ξ, ρ) 必须是同一个常量，且记录里标明 fixed。

    这条之所以必要：逐折 argmin 的代码路径还在（`--selection argmin`），一旦谁把
    `run_b4` 的默认值改回去，`convergence.csv` 会出现多个 ξ 值——主表数字会变，
    但所有阈值检查仍然通过，属于不会自己报警的静默回归。
    """
    p = LOGS / "convergence.csv"
    _need(p)
    c = pd.read_csv(p)
    assert len(c) == 48
    if "selection" in c.columns:
        assert set(c["selection"]) == {"fixed"}
    assert c["xi"].nunique() == 1 and float(c["xi"].iloc[0]) == pytest.approx(0.0019)
    assert c["rho"].nunique() == 1 and float(c["rho"].iloc[0]) == pytest.approx(0.0)
    # 主 B4 的池化 loss 必须等于该常量配置在敏感性表里的那一档（同一条拟合路径）
    by = pd.read_csv(LOGS / "b4_fixed_hp_by_fold.csv")
    centre = by.loc[by["config"] == "centre"].set_index("block_id")["test_logloss"]
    assert np.max(np.abs(c.set_index("block_id")["test_logloss_b4"]
                         - centre.loc[c["block_id"]].values)) < 1e-5
