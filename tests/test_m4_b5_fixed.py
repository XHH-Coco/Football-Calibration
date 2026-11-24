"""M4 复核落地的 B5 固定超参口径必须与产物自洽（不重跑模型，只读已落盘产物）。

守四件容易悄悄坏掉的事：
  1. 现行口径是常量：`FIXED_HP == (3, 0.01)`，且 `b5_params.csv` 48 行全同一组、
     全 `selection="fixed"`。这条一旦松掉，"B5 没有自由超参"这句话就不成立。
  2. **缓存与预测文件必须对得上**：`sens_b5_grid_test.csv` 是敏感性分析的唯一证据，
     若它与 `preds_B5a/B5b.csv` 的逐块损失不一致，说明两个脚本跑的不是同一条路径，
     报告 §5.1.4 的整张表就失去依据。
  3. 被退休规则的选中分布不能漂：交付 9 格网格里 leaf=7 占 46/48、lr=0.03 占 37/48
     ﹣报告 §4.3.6 与 M4 卡 §6.1 的"贴边"论据直接是这两个数。
  4. 刷新额度表的符号：冻结结果类特征后三臂都应更差（正数 = 冻结更差）。
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
PREDS = ROOT / "results" / "preds"
DIAG = LOGS / "selection_diagnostic"


def _need(*paths: Path) -> None:
    for p in paths:
        if not p.exists():
            pytest.skip(f"{p.name} 未生成（先跑对应的 sens_* / run_b5 脚本）")


def test_fixed_hyperparameters_are_constants() -> None:
    from src.models.b5_gbm import FIXED_HP, FIXED_PARAMS

    assert FIXED_HP == (3, 0.01)
    assert FIXED_PARAMS["max_leaf_nodes"] == 3
    assert FIXED_PARAMS["learning_rate"] == 0.01


def test_params_table_is_one_config_across_all_folds() -> None:
    _need(LOGS / "b5_params.csv")
    d = pd.read_csv(LOGS / "b5_params.csv")
    assert len(d) == 48
    assert set(d["selection"]) == {"fixed"}
    assert d["max_leaf_nodes"].nunique() == 1 and d["max_leaf_nodes"].iloc[0] == 3
    assert d["learning_rate"].nunique() == 1 and d["learning_rate"].iloc[0] == 0.01
    # 主口径不选参，所以没有验证损失可言
    assert d["val_logloss"].isna().all()


def test_grid_cache_agrees_with_reported_predictions() -> None:
    """缓存里 (3, 0.01) 那一格的逐块损失 = 主预测文件的逐块损失。"""
    _need(LOGS / "sens_b5_grid_test.csv", PREDS / "preds_B5a.csv",
          PREDS / "preds_B5b.csv")
    cache = pd.read_csv(LOGS / "sens_b5_grid_test.csv").set_index("block_id")
    from src.models._common import log_loss

    for arm in ("B5a", "B5b"):
        df = pd.read_csv(PREDS / f"preds_{arm}.csv")
        df["block_id"] = df["league"] + "|" + df["season"]
        got = df.groupby("block_id").apply(
            lambda g: log_loss(g["y"].to_numpy(),
                               g[["p_home", "p_draw", "p_away"]].to_numpy()),
            include_groups=False)
        want = cache[f"{arm}_3_0.01"].reindex(got.index).to_numpy()
        assert np.abs(got.to_numpy() - want).max() < 1e-10, arm


def test_retired_grid_selection_distribution_is_stable() -> None:
    """报告 §4.3.6 的「贴边」论据：46/48 折选 leaf=7、37/48 折选 lr=0.03。"""
    _need(DIAG / "b5_params_argmin.csv")
    d = pd.read_csv(DIAG / "b5_params_argmin.csv")
    assert len(d) == 48
    assert set(d["selection"]) == {"argmin"}
    assert int((d["max_leaf_nodes"] == 7).sum()) == 46
    assert int(np.isclose(d["learning_rate"], 0.03).sum()) == 37
    # 网格里更大的两档几乎从不被选中
    assert int((d["max_leaf_nodes"] == 31).sum()) == 0


def test_refresh_penalty_has_expected_sign() -> None:
    _need(LOGS / "sens_refresh_parity.csv")
    d = pd.read_csv(LOGS / "sens_refresh_parity.csv")
    assert len(d) == 48
    from src.models.sens_refresh_parity import _block_ll

    n = d["n"].to_numpy(float)
    for arm in ("B2", "B5a", "B5b"):
        roll = _block_ll(arm, d["block_id"])
        delta = float(np.sum((d[f"{arm}_frozen"].to_numpy() - roll) * n) / n.sum())
        # 冻结结果类特征后必然更差：正负号写死在报告 §5.1.6 的结论里
        assert delta > 0.005, f"{arm} 冻结后没有明显变差：{delta:+.5f}"
