"""M2 / T2.8：主推断表 ``results/table_main.csv``（9 行 + deff）。

每个 arm 一行：主指标 log loss 的 pooled 点估计 + 90% 簇区间 + cluster-robust SE +
design effect，辅指标 Brier / RPS，以及与 B4、与 B6 的配对差（含区间）。

B0–B2 / B5a / B5b 由 M4 交付，缺失时该行留 NaN 并标 ``pending_M4``；B6 行「与 B6 差」留空。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.bootstrap import (  # noqa: E402
    block_deltas,
    block_logloss,
    cluster_bootstrap,
    cluster_robust_se,
    design_effect,
)
from src.eval.metrics import mean_brier, mean_rps  # noqa: E402

ARMS = ["B0", "B1", "B2", "B3", "B4", "B5a", "B5b", "B6", "B6r"]
PRED_DIR = ROOT / "results" / "preds"


def _load(arm: str) -> pd.DataFrame:
    p = PRED_DIR / f"preds_{arm}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, dtype={"match_id": str, "season": str, "date": str})


def _paired(delta: object) -> dict:
    if delta.n_paired == 0:
        return {"delta": np.nan, "lo": np.nan, "hi": np.nan, "n_paired": 0}
    ci = cluster_bootstrap(delta)
    return {"delta": ci["point"], "lo": ci["lo"], "hi": ci["hi"],
            "n_paired": delta.n_paired}


def build_table_main(out_path=None) -> pd.DataFrame:
    rows = []
    for arm in ARMS:
        d = _load(arm)
        if d.empty:
            rows.append({"arm": arm, "n_matches": np.nan, "log_loss": np.nan,
                         "ll_lo90": np.nan, "ll_hi90": np.nan,
                         "se_cluster": np.nan, "deff": np.nan,
                         "brier": np.nan, "rps": np.nan,
                         "delta_vs_B4": np.nan, "delta_vs_B4_lo90": np.nan,
                         "delta_vs_B4_hi90": np.nan,
                         "delta_vs_B6": np.nan, "delta_vs_B6_lo90": np.nan,
                         "delta_vs_B6_hi90": np.nan, "n_paired_vs_B6": np.nan,
                         "note": "pending_M4"})
            continue
        blk = block_logloss(d)
        ci = cluster_bootstrap(blk)
        de = design_effect(blk)
        p = d[["p_home", "p_draw", "p_away"]].to_numpy()
        y = d["y"].to_numpy()
        row = {
            "arm": arm, "n_matches": len(d), "log_loss": ci["point"],
            "ll_lo90": ci["lo"], "ll_hi90": ci["hi"],
            "se_cluster": cluster_robust_se(blk.values, blk.weights),
            "deff": de["deff"],
            "brier": mean_brier(p, y), "rps": mean_rps(p, y),
            "delta_vs_B4": np.nan, "delta_vs_B4_lo90": np.nan,
            "delta_vs_B4_hi90": np.nan,
            "delta_vs_B6": np.nan, "delta_vs_B6_lo90": np.nan,
            "delta_vs_B6_hi90": np.nan, "n_paired_vs_B6": np.nan,
            "note": "",
        }
        b4 = _load("B4")
        if not b4.empty and arm != "B4":
            pd_ = _paired(block_deltas(d, b4))
            row.update({"delta_vs_B4": pd_["delta"],
                        "delta_vs_B4_lo90": pd_["lo"], "delta_vs_B4_hi90": pd_["hi"]})
        b6 = _load("B6")
        if not b6.empty and arm != "B6":
            pd_ = _paired(block_deltas(d, b6))
            row.update({"delta_vs_B6": pd_["delta"],
                        "delta_vs_B6_lo90": pd_["lo"], "delta_vs_B6_hi90": pd_["hi"],
                        "n_paired_vs_B6": pd_["n_paired"]})
        rows.append(row)

    df = pd.DataFrame(rows, columns=[
        "arm", "n_matches", "log_loss", "ll_lo90", "ll_hi90", "se_cluster", "deff",
        "brier", "rps", "delta_vs_B4", "delta_vs_B4_lo90", "delta_vs_B4_hi90",
        "delta_vs_B6", "delta_vs_B6_lo90", "delta_vs_B6_hi90", "n_paired_vs_B6",
        "note"])
    if out_path is not None:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False, encoding="utf-8")
    return df
