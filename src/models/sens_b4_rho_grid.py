"""M3 复核 · ρ 网格外扩敏感性（P1-1，**不改主结果**）。

复盘问：ρ 有 23/48 折顶在网格边界 ±0.15，是不是网格截断——真实最优在 −0.15 之外？
答案取决于物理可行性，而不只是似然面：

    τ(0,1) = 1 + λρ ≥ 0   ⇒   ρ ≥ −1/λ
    τ(1,0) = 1 + νρ ≥ 0   ⇒   ρ ≥ −1/ν

λ、ν 是逐场的进球率，最大可达 5 量级，所以 **ρ 有一个由数据本身决定的硬下界**
（本项目 48 折最严的一折约 −0.18）。再往外扩，τ 会变负，`score_matrix` 里的
`clip(p, 0)` 会把它截成 0 再归一化——结果"合法"但语义是错的。

所以本脚本做三件事：
  1. 把 ρ 网格往负向外扩到 −0.35；
  2. 每折逐候选检查 τ 可行性（在 inner 训练段上算 max λ、max ν），不可行的候选直接
     排除出选参池，并记录被排除了几个；
  3. 在**验证集**上重新选参（目标赛季仍不参与），在 test 上评估，与交付版逐折配对。

产物：`results/logs/b4_rho_extension.csv`（48 行 + 汇总）。
运行：python -m src.models.sens_b4_rho_grid      （≈ 2.5 min）
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.b3_poisson import _team_params, load_panel, predict_proba  # noqa: E402
from src.models.b4_dixon_coles import XI_GRID, fit, log_loss  # noqa: E402
from src.models.tune_b4 import inner_split  # noqa: E402
from src.splits import load_splits, resolve_split  # noqa: E402

RHO_BASE = (-0.15, -0.05, 0.0, 0.05, 0.15)
RHO_EXT = (-0.35, -0.25, -0.18, -0.15, -0.05, 0.0, 0.05, 0.15)
LOGS = ROOT / "results" / "logs"


def rho_floor(model, df: pd.DataFrame) -> float:
    """该模型在该批比赛上允许的最负 ρ（再小就有 τ < 0）。"""
    a_h, b_h = _team_params(model, df["home"])
    a_a, b_a = _team_params(model, df["away"])
    lam = np.exp(model.mu + model.gamma + a_h - b_a)
    nu = np.exp(model.mu + a_a - b_h)
    return float(-1.0 / max(lam.max(), nu.max()))


def tune_fold(train: pd.DataFrame, test: pd.DataFrame, block: dict,
              rho_grid: tuple[float, ...]) -> dict:
    """一次折叠：逐候选检查 τ 可行性 → 验证集选参 → 全量重拟合 → test 评估。"""
    inner, val = inner_split(train)
    y_val = val["y"].to_numpy()
    ref_inner = str(val["date"].min())
    best, n_ok, n_inadmissible, floor = None, 0, 0, -np.inf
    prev = None
    for xi in XI_GRID:
        for rho in rho_grid:
            m = fit(inner, xi=xi, rho=rho, ref_date=ref_inner,
                    init=prev.warm if prev is not None else None)
            prev = m
            if not m.converged:
                continue
            f = rho_floor(m, inner)
            if rho < f:                       # τ 会变负 → 该候选不可行
                n_inadmissible += 1
                continue
            floor = max(floor, f) if np.isfinite(floor) else f
            n_ok += 1
            ll = log_loss(predict_proba(m, val), y_val)
            if best is None or ll < best["val_logloss"] - 1e-12:
                best = {"xi": xi, "rho": rho, "val_logloss": ll}
    if best is None:
        raise RuntimeError(f"{block['block_id']}: 无可行候选")
    final = fit(train, xi=best["xi"], rho=best["rho"], ref_date=block["test_start"])
    return {"block_id": block["block_id"], "league": block["league"],
            "season": block["season"], "n_test": int(len(test)),
            "xi_ext": best["xi"], "rho_ext": best["rho"],
            "val_logloss_ext": best["val_logloss"],
            "n_candidates_ok": n_ok, "n_candidates_infeasible": n_inadmissible,
            "rho_floor_inner": floor,
            "test_logloss_ext": log_loss(predict_proba(final, test),
                                         test["y"].to_numpy())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B4 ρ 网格外扩敏感性")
    ap.add_argument("--out", default=str(LOGS / "b4_rho_extension.csv"))
    a = ap.parse_args(argv)

    panel = load_panel()
    blocks = load_splits()["blocks"]
    base = pd.read_csv(LOGS / "convergence.csv").set_index("block_id")
    rows = []
    t0 = time.perf_counter()
    for i, b in enumerate(blocks, 1):
        train, test = resolve_split(panel, b)
        r = tune_fold(train, test, b, RHO_EXT)
        r["rho_base"] = float(base.loc[b["block_id"], "rho"])
        r["test_logloss_base"] = float(base.loc[b["block_id"], "test_logloss_b4"])
        rows.append(r)
        print(f"[{i:>2}/48] {r['block_id']:<12} ρ {r['rho_base']:+.2f} → {r['rho_ext']:+.2f}"
              f"  ll {r['test_logloss_base']:.5f} → {r['test_logloss_ext']:.5f}"
              f"  不可行候选 {r['n_candidates_infeasible']:>2}  "
              f"下界 {r['rho_floor_inner']:+.3f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(a.out, index=False, encoding="utf-8")

    n = df["n_candidates_ok"] + 0
    print("\n" + "=" * 78)
    print(f"ρ 扩展网格 {RHO_EXT}")
    print(f"被排除的不可行候选（τ 会变负）：共 {int(df['n_candidates_infeasible'].sum())} 个"
          f"（每折中位 {int(df['n_candidates_infeasible'].median())}）")
    print(f"各折最严物理下界：最紧 {df['rho_floor_inner'].max():+.3f}，"
          f"最松 {df['rho_floor_inner'].min():+.3f}")
    moved = df["rho_ext"] != df["rho_base"]
    print(f"选出的 ρ 发生变化：{int(moved.sum())}/48 折")
    print(f"  其中更负：{int((df['rho_ext'] < df['rho_base']).sum())} 折，"
          f"更不负：{int((df['rho_ext'] > df['rho_base']).sum())} 折")
    ll_b = float(np.average(df["test_logloss_base"], weights=df["n_test"]))
    ll_e = float(np.average(df["test_logloss_ext"], weights=df["n_test"]))
    d = df["test_logloss_ext"] - df["test_logloss_base"]
    print(f"池化 test log loss：交付 {ll_b:.5f} → 扩展 {ll_e:.5f}（差 {ll_e - ll_b:+.5f}）")
    print(f"扩展更好：{int((d < 0).sum())}/48 折；逐折差均值 {d.mean():+.5f}")
    print(f"用时 {time.perf_counter() - t0:.0f}s → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
