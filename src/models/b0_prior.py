"""M4 · T4.1 B0 先验基线。

只用同联赛 **严格更早** 比赛（date < test_start）的主/平/客经验频率，
expanding 随块累积。验收锚点（M4 卡 §3）：整体 log loss = 1.0743，
逐块 1.027–1.115；低于 1.00 一定是泄漏。全押 1/3 对照 = ln3 = 1.0986。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models._common import load_panel, run_blocks  # noqa: E402


def fit(train_df: pd.DataFrame, sample_weight=None) -> np.ndarray:
    """返回 (f_H, f_D, f_A)。B0 是计数频率，不接受加权。"""
    y = train_df["y"].to_numpy()
    freq = np.bincount(y, minlength=3).astype(float)
    freq /= freq.sum()
    return freq


def predict_proba(test_df: pd.DataFrame, state) -> np.ndarray:
    return np.tile(state, (len(test_df), 1))


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / T4.1 B0 先验基线")
    ap.add_argument("--out", default=str(ROOT / "results" / "preds" / "preds_B0.csv"))
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    panel = load_panel()
    summary = run_blocks("B0", fit, predict_proba, args.out,
                         panel=panel, log_path=args.log)
    print(f"B0 对照：全押 1/3 = {-np.log(1/3):.5f}；验收期望整体 ≈ 1.0743")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
