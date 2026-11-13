"""M4 · T4.2 B1 Elo 基线（Hvattum & Arntzen 2010 简化）。

Elo 引擎见 src/elo.py（初始 1500 / K=20 / 主场加成 75 / 赛季间回归 1/3 /
主客各存一分、严格按日期逐场更新）。B1 本体只做一件事：在训练窗内用
multinomial logistic 把「分差」映射成三概率，应用到 test 行（test 行的
分差同样逐场推进——每场比赛只用其之前的信息，见防泄漏红线）。
验收预估 log loss 1.00–1.03。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.elo import EloLeague  # noqa: E402
from src.models._common import load_panel, run_blocks  # noqa: E402


def _diffs(frame: pd.DataFrame, elo: EloLeague | None = None,
           update: bool = True) -> tuple[np.ndarray, EloLeague]:
    """逐场算 Elo 分差（主客各用其主/客分）。update=True 时把本场结果写回。"""
    eng = elo if elo is not None else EloLeague()
    srt = frame.sort_values("date")
    vals: list[float] = []
    for row in srt.itertuples():
        eng.maybe_regress(row.season)
        vals.append(eng.home_rating(row.home) - eng.away_rating(row.away))
        if update:
            eng.update(row.home, row.away, int(row.y))
    out = pd.Series(vals, index=srt.index).reindex(frame.index).to_numpy()
    return out, eng


def fit(train_df: pd.DataFrame, sample_weight=None) -> tuple[LogisticRegression, EloLeague]:
    """训练窗内：逐场算分差 → multinomial logistic 拟合（只用 train）。"""
    diffs, eng = _diffs(train_df)
    clf = LogisticRegression(multi_class="multinomial", max_iter=2000)
    clf.fit(diffs.reshape(-1, 1), train_df["y"].to_numpy())
    return clf, eng


def predict_proba(test_df: pd.DataFrame, state) -> np.ndarray:
    clf, eng = state
    diffs, _ = _diffs(test_df, elo=eng)
    p = clf.predict_proba(diffs.reshape(-1, 1))          # classes_ = [0,1,2] = H/D/A
    internal = list(clf.classes_)
    order = [internal.index(k) for k in [0, 1, 2]]
    p = p[:, order]
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-9)
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / T4.2 B1 Elo 基线")
    ap.add_argument("--out", default=str(ROOT / "results" / "preds" / "preds_B1.csv"))
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    panel = load_panel()
    summary = run_blocks("B1", fit, predict_proba, args.out,
                         panel=panel, log_path=args.log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
