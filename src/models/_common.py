"""M4 · 共用件：panel / splits 读取、48 块 runner、preds CSV 落盘校验。

preds schema（data_interface.md §1）：
  match_id, league, season, date, home, away, model, p_home, p_draw, p_away, y
四条硬校验：三概率和=1（1e-9）；y∈{0,1,2}；match_id 非空且唯一；行数=16,733。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.splits import load_splits, resolve_split  # noqa: E402

PANEL_PATH = ROOT / "data" / "processed" / "panel.parquet"
PREDS_DIR = ROOT / "results" / "preds"
SPLITS_PATH = ROOT / "configs" / "splits.json"
XI_RHO_PATH = ROOT / "results" / "logs" / "xi_rho_by_block.csv"

SCHEMA_COLS = ["match_id", "league", "season", "date", "home", "away",
               "model", "p_home", "p_draw", "p_away", "y"]
N_TEST_TOTAL = 16_733
DEFAULT_XI = 0.0019   # M3 交付 xi_rho_by_block.csv 前的兜底（半衰期约 1 年）

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def load_panel() -> pd.DataFrame:
    frame = pd.read_parquet(PANEL_PATH)
    assert len(frame) == 46_507, f"panel 行数异常: {len(frame)}"
    return frame


def load_blocks() -> list[dict]:
    data = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    return sorted(data["blocks"], key=lambda b: b["block_id"])


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    """多分类 log loss；p 为 (n,3)，列序 H/D/A，y 为 0/1/2。"""
    p = np.clip(np.asarray(p, dtype=float), 1e-15, 1.0)
    p = p / p.sum(axis=1, keepdims=True)
    return float(-np.log(p[np.arange(len(y)), np.asarray(y)]).mean())


def load_xi_map() -> dict[str, float]:
    """读 M3 的 ξ 逐块表（尚未交付时返回空表，走 DEFAULT_XI 兜底）。"""
    if not XI_RHO_PATH.exists():
        return {}
    table = pd.read_csv(XI_RHO_PATH)
    key = next((c for c in ("block_id", "block") if c in table.columns), None)
    val = next((c for c in ("xi", "Xi", "ξ") if c in table.columns), None)
    if key is None or val is None:
        return {}
    return {str(r[key]): float(r[val]) for _, r in table.iterrows()
            if pd.notna(r[val])}


def make_preds_df(test: pd.DataFrame, p: np.ndarray, model: str) -> pd.DataFrame:
    p = np.asarray(p, dtype=float)
    assert p.shape == (len(test), 3), f"{model}: 概率形状 {p.shape}"
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-9), f"{model}: 概率和≠1"
    out = test[["match_id", "league", "season", "date", "home", "away", "y"]].copy()
    out["model"] = model
    out["p_home"] = p[:, 0]
    out["p_draw"] = p[:, 1]
    out["p_away"] = p[:, 2]
    out = out[SCHEMA_COLS]
    assert out["match_id"].notna().all() and out["match_id"].is_unique
    assert set(out["y"].unique()) <= {0, 1, 2}
    return out


def run_blocks(model: str, fit, predict, out_path: str | Path,
               panel: pd.DataFrame | None = None,
               log_path: str | Path | None = None) -> dict:
    """48 块 rolling-origin 主循环（M4 自用 runner；M2 harness 之后统一接管）。

    fit(train_df) → 任意状态；predict(test_df) → (n,3) 概率（H/D/A）。
    predict 内部自行保证"测试行只用严格更早信息"（如 B1 的逐场推进）。
    """
    frame = load_panel() if panel is None else panel
    blocks = load_blocks()
    lines: list[str] = []
    parts: list[pd.DataFrame] = []
    block_losses: dict[str, float] = {}

    for i, b in enumerate(blocks, 1):
        train, test = resolve_split(frame, b)
        state = fit(train)
        p = predict(test, state)
        p = np.asarray(p, dtype=float)
        if p.shape != (len(test), 3):
            raise ValueError(f"{model} {b['block_id']}: 概率形状 {p.shape}")
        parts.append(make_preds_df(test, p, model))
        ll = log_loss(test["y"].to_numpy(), p)
        block_losses[b["block_id"]] = ll
        msg = f"[{i:02d}/48] {b['block_id']:<11} n_train={len(train):>6,} " \
              f"n_test={len(test):>4} logloss={ll:.5f}"
        print(msg)
        lines.append(msg)

    full = pd.concat(parts, ignore_index=True)
    assert len(full) == N_TEST_TOTAL, f"{model}: 总行数 {len(full)} ≠ 16,733"
    assert full["match_id"].is_unique and full["match_id"].notna().all()
    test_ids = frame.loc[frame["season"].isin(
        tuple({b["season"] for b in blocks})), "match_id"]
    assert set(full["match_id"]) == set(test_ids), f"{model}: match_id 集合与评估窗不符"

    overall = log_loss(full["y"].to_numpy(),
                       full[["p_home", "p_draw", "p_away"]].to_numpy())
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(out, index=False, encoding="utf-8")
    summary = f"[{model}] 48 块跑完，整体 logloss={overall:.5f}，行数={len(full)}，" \
              f"逐块范围 {min(block_losses.values()):.4f}–{max(block_losses.values()):.4f}，" \
              f"已写入 {out.relative_to(ROOT).as_posix()}"
    print(summary)
    lines.append(summary)
    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"logloss": overall, "n_rows": len(full), "path": str(out)}
