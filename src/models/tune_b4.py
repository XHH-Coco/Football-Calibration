"""B4 的 ξ/ρ 网格搜索（M3 / T3.3）：48 折 × 6 ξ × 5 ρ，**只在内层验证集上选**。

内层切分优先用 M2 的 ``src.eval.harness.inner_split()``；该函数 11/13 才交付，所以本文件
在它还不存在时用完全同构的本地兜底（把该块 train 里最后一个赛季整段留作验证集），
M2 落地后自动切换，调用点不变。

红线：目标赛季（外层 test）**一次都不进这里**。选参只看 train 内部的最后一段历史。
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

from src.models.b3_poisson import load_panel, predict_proba  # noqa: E402
from src.models.b4_dixon_coles import (  # noqa: E402
    RHO_GRID,
    XI_GRID,
    fit,
    half_life_years,
    log_loss,
)
from src.splits import load_splits, resolve_split  # noqa: E402

try:                                    # M2 交付后自动启用，本地兜底随即失效
    from src.eval.harness import inner_split as _m2_inner_split
except (ImportError, AttributeError, ModuleNotFoundError):
    _m2_inner_split = None


def inner_split(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(拟合段, 验证段)。验证段 = train 里最后一个赛季；外层 test 仍严格更晚。"""
    if _m2_inner_split is not None:
        return _m2_inner_split(train)

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


def tune_block(panel: pd.DataFrame, block: dict,
               xi_grid: tuple[float, ...] = XI_GRID,
               rho_grid: tuple[float, ...] = RHO_GRID,
               warm: bool = True,
               paired_out: list | None = None) -> tuple[dict, object]:
    """返回 (该折的选参记录, 用选中的 (ξ,ρ) 在**完整 train** 上重拟合的模型)。

    ``paired_out`` 非空时，把 30 个候选中每个与"选中组合"的**逐场配对差**统计追加进去
    （Δlogloss、配对 SE、t）。验收项 6 的边境堆积就是靠这张表说明"分不出来"。
    """
    t0 = time.perf_counter()
    train, _test = resolve_split(panel, block)       # test 只取出来校验契约，不参与选参
    inner, val = inner_split(train)
    y_val = val["y"].to_numpy()
    ref_inner = str(val["date"].min())

    best: dict | None = None
    n_ok = 0
    prev = None
    loss_vec: dict[tuple[float, float], np.ndarray] = {}
    ll_of: dict[tuple[float, float], float] = {}
    for xi in xi_grid:
        for rho in rho_grid:
            m = fit(inner, xi=xi, rho=rho, ref_date=ref_inner,
                    init=prev.warm if (warm and prev is not None) else None)
            prev = m
            if not m.converged:
                continue
            n_ok += 1
            p_val = predict_proba(m, val)
            ll = log_loss(p_val, y_val)
            if paired_out is not None:
                loss_vec[(xi, rho)] = -np.log(
                    np.clip(p_val[np.arange(len(y_val)), y_val], 1e-15, None))
                ll_of[(xi, rho)] = ll
            if best is None or ll < best["val_logloss"] - 1e-12:
                best = {"xi": xi, "rho": rho, "val_logloss": ll,
                        "val_ll": float(m.nll), "val_iter": m.n_iter,
                        "val_grad": m.grad_norm}
    if best is None:
        raise RuntimeError(f"{block['block_id']}: 30 个候选组合全部未收敛")

    if paired_out is not None:
        ref = loss_vec[(best["xi"], best["rho"])]
        n = len(ref)
        for (xi, rho), l in loss_vec.items():
            diff = l - ref
            se = float(np.std(diff, ddof=1) / np.sqrt(n))
            paired_out.append({
                "block_id": block["block_id"], "league": block["league"],
                "season": block["season"], "xi": xi, "rho": rho,
                "val_logloss": ll_of[(xi, rho)],
                "dll_vs_selected": float(diff.mean()), "paired_se": se,
                "t": float(diff.mean() / se) if se > 0 else 0.0,
                "is_selected": (xi, rho) == (best["xi"], best["rho"]),
            })

    final = fit(train, xi=best["xi"], rho=best["rho"],
                ref_date=block["test_start"], init=prev.warm if warm else None)

    rec = {
        "block_id": block["block_id"],
        "league": block["league"],
        "season": block["season"],
        "n_train": int(len(train)),
        "n_inner": int(len(inner)),
        "n_val": int(len(val)),
        "val_season": str(sorted(val["season"].unique())[-1]),
        "xi": best["xi"],
        "rho": best["rho"],
        "xi_half_life_years": half_life_years(best["xi"]),
        "val_logloss": best["val_logloss"],
        "n_candidates_converged": n_ok,
        "n_new_team": int(block["n_new_team"]),
        "train_logloss_insample": log_loss(predict_proba(final, train), train["y"].to_numpy()),
        "converged": bool(final.converged),
        "n_iter": int(final.n_iter),
        "grad_norm": float(final.grad_norm),
        "train_nll": float(final.nll),
        "elapsed_s": time.perf_counter() - t0,
    }
    return rec, final


def _grid_table(panel: pd.DataFrame, block: dict,
                xi_grid=XI_GRID, rho_grid=RHO_GRID) -> pd.DataFrame:
    """单折的完整网格，调试用（看 ξ 是不是单调地把验证 loss 推到一个内部最优）。"""
    train, _ = resolve_split(panel, block)
    inner, val = inner_split(train)
    y_val = val["y"].to_numpy()
    rows = []
    for xi in xi_grid:
        for rho in rho_grid:
            m = fit(inner, xi=xi, rho=rho, ref_date=str(val["date"].min()))
            rows.append({"xi": xi, "rho": rho, "val_logloss": log_loss(predict_proba(m, val), y_val),
                         "converged": m.converged})
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B4 ξ/ρ 网格搜索（单折调试）")
    ap.add_argument("--block", default="E0|2024/25", help="block_id，如 E0|2024/25")
    ap.add_argument("--all", action="store_true", help="跑满 48 折（等价于 run_b4.py）")
    a = ap.parse_args(argv)

    panel = load_panel()
    data = load_splits()
    if not a.all:
        block = next(b for b in data["blocks"] if b["block_id"] == a.block)
        t0 = time.perf_counter()
        rec, model = tune_block(panel, block)
        print("=" * 78)
        print(f"{rec['block_id']} · train {rec['n_train']:,} · "
              f"inner {rec['n_inner']:,} / val {rec['n_val']:,} ({rec['val_season']})")
        print(f"选中 ξ={rec['xi']} (半衰期 {rec['xi_half_life_years']:.2f} 年)  "
              f"ρ={rec['rho']}  val logloss={rec['val_logloss']:.4f}")
        print(f"最终拟合 收敛 {rec['converged']} · {rec['n_iter']} 次迭代 · "
              f"|grad|∞ {rec['grad_norm']:.2e} · {time.perf_counter() - t0:.1f}s")
        return 0

    rows = []
    for i, block in enumerate(data["blocks"], 1):
        rec, _ = tune_block(panel, block)
        rows.append(rec)
        print(f"[{i:>2}/48] {rec['block_id']:<12} ξ={rec['xi']:<7} ρ={rec['rho']:<7.2f} "
              f"val_ll={rec['val_logloss']:.4f} {rec['elapsed_s']:.1f}s", flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / "results" / "logs" / "xi_rho_by_block.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"\n已写入 {out.relative_to(ROOT)}（{len(df)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
