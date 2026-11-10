"""M2 / T2.2 + T2.3：rolling-origin 主循环 + 内层验证 + 预测落盘契约。

这是全项目**唯一**的 schema 真相源：``PRED_COLS``、``check_pred()``、``pred_frame()``。
M3 的 ``src/models/run_b4.py`` 已改为从这里 import（不再自带一份），任何 arm 落盘前
都必须过 ``check_pred()``。

红线（``data_interface.md`` §2）：
- 取数一律 ``src.splits.resolve_split(panel, block)``，禁止另切一遍；
- 外层每块目标赛季只预测一次；
- ``inner_split()`` 只用 train 内部数据：验证段 = train 内最后一个完整赛季，
  断言 ``max(inner.date) < min(val.date)`` 且外层 test 严格更晚。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.splits import load_splits, resolve_split  # noqa: E402

PRED_COLS = ["match_id", "league", "season", "date", "home", "away",
             "model", "p_home", "p_draw", "p_away", "y"]
EXPECTED_ROWS = 16_733


def check_pred(df: pd.DataFrame, expected_rows: int) -> None:
    """落盘前四条硬校验；任何一条不满足即抛异常，不得写盘。"""
    if df.columns.tolist() != PRED_COLS:
        raise ValueError(f"列序不符：{df.columns.tolist()} ≠ {PRED_COLS}")
    if len(df) != expected_rows:
        raise ValueError(f"预测行数 {len(df)} ≠ {expected_rows}")
    s = df[["p_home", "p_draw", "p_away"]].to_numpy().sum(axis=1)
    if not np.allclose(s, 1.0, atol=1e-9):
        raise ValueError(f"三概率和偏离 1：max|Σp−1| = {np.abs(s - 1).max():.3e}")
    if not np.isfinite(df[["p_home", "p_draw", "p_away"]].to_numpy()).all():
        raise ValueError("概率含 NaN / Inf")
    if df["match_id"].isna().any() or not df["match_id"].is_unique:
        raise ValueError("match_id 必须非空且唯一")
    if not set(df["y"].unique()) <= {0, 1, 2}:
        raise ValueError("y 越界")


def pred_frame(test: pd.DataFrame, proba: np.ndarray, model: str) -> pd.DataFrame:
    """把 ``(n,3)`` 概率按 schema 组装成 ``PRED_COLS`` 顺序的 DataFrame。

    ``proba`` 列序必须是 ``[p_home, p_draw, p_away]``（模型内部标签重排由各 arm 自行
    负责，见 ``data_interface.md`` §1.1；这里再按列名对齐一次，双保险）。
    """
    proba = np.asarray(proba, dtype=float)
    if proba.ndim != 2 or proba.shape[1] != 3:
        raise ValueError(f"proba 必须是 (n,3)，实际 {proba.shape}")
    df = test[["match_id", "league", "season", "date", "home", "away", "y"]].copy()
    df["model"] = model
    df["p_home"] = proba[:, 0]
    df["p_draw"] = proba[:, 1]
    df["p_away"] = proba[:, 2]
    return df[PRED_COLS]


def inner_split(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(拟合段, 验证段)。验证段 = train 内最后一个完整赛季。

    与 M3 ``tune_b4.py`` 的本地兜底同构；``tune_b4.py`` 会在本模块存在后自动切换
    到 ``src.eval.harness.inner_split``（其签名就是 ``inner_split(train)``）。
    """
    if "season" not in train.columns or "date" not in train.columns:
        raise ValueError("train 缺 season / date 列")
    seasons = sorted(train["season"].unique())
    if len(seasons) < 3:
        raise ValueError(f"内层需要至少 3 个赛季，实际 {len(seasons)}：{seasons}")
    val_season = seasons[-1]
    inner = train.loc[train["season"] != val_season]
    val = train.loc[train["season"] == val_season]
    if inner.empty or val.empty:
        raise ValueError("内层切分为空")
    if str(inner["date"].max()) >= str(val["date"].min()):
        raise ValueError("内层拟合段未严格早于验证段")
    return inner, val


def load_panel() -> pd.DataFrame:
    """读建模总表；不存在时报错并给出重建命令（不静默重建，避免误跑）。"""
    p = ROOT / "data" / "processed" / "panel.parquet"
    if not p.exists():
        raise FileNotFoundError(
            f"{p} 不存在。请先跑：python src/build_panel.py --stage s3")
    return pd.read_parquet(p)


def run_arm(arm: str, fit, predict, blocks: list[dict] | None = None,
            panel: pd.DataFrame | None = None,
            sample_weight_fn=None,
            out_path: str | Path | None = None,
            verbose: bool = True) -> pd.DataFrame:
    """滚动原点主循环：48 块 ``fit(train) → predict(test) → 落盘一个文件``。

    - ``fit(train_df, sample_weight=None) -> model``
    - ``predict(model, test_df) -> (n,3)``（列序 ``[p_home, p_draw, p_away]``）
    - ``sample_weight_fn(block, train_df) -> np.ndarray | None``（B4→B5a 权重同步用）
    """
    import time

    panel = load_panel() if panel is None else panel
    data = load_splits()
    todo = data["blocks"] if blocks is None else blocks
    preds: list[pd.DataFrame] = []
    for i, block in enumerate(todo, 1):
        t0 = time.perf_counter()
        train, test = resolve_split(panel, block)
        sw = sample_weight_fn(block, train) if sample_weight_fn is not None else None
        model = fit(train, sample_weight=sw)
        proba = predict(model, test)
        frame = pred_frame(test, proba, arm)
        check_pred(frame, block["n_test"])
        preds.append(frame)
        if verbose:
            print(f"[{i:>2}/{len(todo)}] {block['block_id']:<12} "
                  f"n_train {len(train):,} / n_test {len(test):,} "
                  f"{time.perf_counter() - t0:.1f}s", flush=True)
    out = pd.concat(preds, ignore_index=True)
    if out_path is not None:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(p, index=False, encoding="utf-8")
    return out
