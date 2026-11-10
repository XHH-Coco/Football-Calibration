"""M2 / T2.11：B6r——B6 的两参数 temperature-and-bias 重校准（H4 的唯一工具）。

参数化（``m2_harness_spec.md`` §3.5 / §7.5，写死）：

- 以客胜 A 为参考类，取两个独立 log-odds ``u = log(p_H/p_A)``、``v = log(p_D/p_A)``；
- 映射 ``u' = c·u + d``、``v' = c·v + d``（**c = 温度，d = 偏置**，恰两个参数），
  再 softmax 回 ``(p_H, p_D, p_A)``；
- **参数只在该折 train 段拟合**（最小化负对数似然），应用到 test 段；
  拟合样本只用 train 中 ``PSCH/PSCD/PSCA`` 三列齐全的比赛（收盘价自 2012/13 才有），
  每折 ``n_fit`` 落盘；断言 train ∩ test = ∅。

产物：``results/preds/preds_B6r.csv``（16,728 行，与 B6 同一批比赛）、
``results/logs/b6r_n_fit.csv``（48 行）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.devig import ODDS_COLS, build_b6, check_odds, proportional  # noqa: E402
from src.eval.harness import PRED_COLS, check_pred, pred_frame  # noqa: E402
from src.models.b3_poisson import load_panel  # noqa: E402
from src.splits import load_splits, resolve_split  # noqa: E402

B6R_N = 16_728
CLIP = 1e-9


def _to_logodds(p: np.ndarray) -> np.ndarray:
    """``(n,3)`` → ``(n,2)`` 独立 log-odds，以 A（第 2 类）为参考。"""
    p = np.clip(np.asarray(p, dtype=float), CLIP, 1 - CLIP)
    pa = p[:, 2]
    return np.column_stack([np.log(p[:, 0] / pa), np.log(p[:, 1] / pa)])


def _from_logodds(z: np.ndarray) -> np.ndarray:
    e = np.exp(np.asarray(z, dtype=float))
    denom = 1.0 + e.sum(axis=1)
    return np.column_stack([e[:, 0] / denom, e[:, 1] / denom, 1.0 / denom])


def _nll(theta: np.ndarray, z: np.ndarray, y: np.ndarray) -> float:
    c, d = theta
    p = _from_logodds(c * z + d)
    return float(-np.log(np.clip(p[np.arange(len(y)), y], CLIP, None)).sum())


def fit_recalibration(p: np.ndarray, y: np.ndarray,
                      init: tuple[float, float] = (1.0, 0.0)) -> tuple[float, float]:
    """在 train 上用 L-BFGS-B 拟合 ``(c, d)``，最小化 log loss。"""
    z = _to_logodds(p)
    res = minimize(_nll, x0=np.array(init, dtype=float), args=(z, y),
                   method="L-BFGS-B", bounds=[(1e-3, 5.0), (-5.0, 5.0)])
    return float(res.x[0]), float(res.x[1])


def apply_recalibration(p: np.ndarray, c: float, d: float) -> np.ndarray:
    z = _to_logodds(p)
    return _from_logodds(c * z + d)


def run_b6r(out_path: str | Path | None = None,
            n_fit_log: str | Path | None = None,
            verbose: bool = True) -> pd.DataFrame:
    """48 折 train-only 重校准 → ``preds_B6r.csv``（16,728 行）。"""
    panel = load_panel()
    b6 = build_b6(panel=panel, write_aux=False)          # 16,728 行，比例法
    b6_map = b6.set_index("match_id")
    blocks = load_splits()["blocks"]

    preds, fit_rows = [], []
    for i, block in enumerate(blocks, 1):
        train, test = resolve_split(panel, block)
        fit_df = train.loc[check_odds(train[ODDS_COLS].to_numpy(dtype=float))]
        if len(fit_df) == 0:
            raise RuntimeError(f"{block['block_id']}: train 无三列齐全赔率，无法拟合 B6r")
        p_train = proportional(fit_df[ODDS_COLS].to_numpy(dtype=float))
        c, d = fit_recalibration(p_train, fit_df["y"].to_numpy())

        # test 段：与 B6 同一批比赛（该块内三列齐全的 test 场次）
        test_ids = set(test["match_id"])
        t = b6.loc[b6["match_id"].isin(test_ids)].copy()
        if len(t) == 0:
            continue                                     # 该块无 B6 覆盖（评估窗内不存在）
        p_test = t[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
        p_new = apply_recalibration(p_test, c, d)
        frame = pred_frame(t, p_new, "B6r")
        check_pred(frame, len(t))
        preds.append(frame)
        fit_rows.append({"block_id": block["block_id"], "league": block["league"],
                         "season": block["season"], "n_fit": int(len(fit_df)),
                         "c": c, "d": d})
        if verbose:
            print(f"[{i:>2}/48] {block['block_id']:<12} n_fit {len(fit_df):>5,}  "
                  f"c={c:.3f} d={d:+.3f}", flush=True)

    out = pd.concat(preds, ignore_index=True)
    if out_path is not None:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(p, index=False, encoding="utf-8")
    if n_fit_log is not None:
        nf = Path(n_fit_log)
        nf.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(fit_rows).to_csv(nf, index=False, encoding="utf-8")
    return out
