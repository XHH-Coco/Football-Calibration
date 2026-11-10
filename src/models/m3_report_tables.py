"""§4.2 / 附录 A 的成品表：只读 ``results/logs``，不重跑任何模型。

报告里的每个数字都必须能在 ``products/tables/`` 找到；``--check`` 会把表重新生成到内存
并与磁盘上的文件逐单元格比对，不一致就退出非零（CI 与本地自检共用）。
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.a1_empty import pooled as pool_windows  # noqa: E402
from src.models.a1_gamma import LEAGUES, Z95, trend  # noqa: E402
from src.models.b4_dixon_coles import RHO_GRID, XI_GRID  # noqa: E402

LOGS = ROOT / "results" / "logs"
TABLES = ROOT / "products" / "tables"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(LOGS / f"{name}.csv")


def _match_loss(d: pd.DataFrame) -> np.ndarray:
    p = d[["p_home", "p_draw", "p_away"]].to_numpy(float)
    return -np.log(np.clip(p[np.arange(len(d)), d["y"].to_numpy()], 1e-15, None))


def model_fit() -> pd.DataFrame:
    """逐联赛（+ ALL）的样本量、B3/B4 **按场合并**的 log loss 与 B4 胜出的折数。"""
    c = _read("convergence").sort_values("block_id")
    b3 = pd.read_csv(ROOT / "results" / "preds" / "preds_B3.csv")
    b4 = pd.read_csv(ROOT / "results" / "preds" / "preds_B4.csv")
    b3["loss"], b4["loss"] = _match_loss(b3), _match_loss(b4)
    rows = []
    for lg, d in [("ALL", c)] + [(lg, c.loc[c["league"] == lg]) for lg in LEAGUES]:
        m3 = b3 if lg == "ALL" else b3.loc[b3["league"] == lg]
        m4 = b4 if lg == "ALL" else b4.loc[b4["league"] == lg]
        dll = d["test_logloss_b3"] - d["test_logloss_b4"]
        rows.append({
            "league": lg,
            "n_folds": len(d),
            "n_matches": len(m4),
            "n_train_min": int(d["n_train"].min()),
            "n_train_max": int(d["n_train"].max()),
            "n_new_team": int(d["n_new_team"].sum()),
            "n_failed_fits": int((~d["b3_converged"]).sum() + (~d["b4_converged"]).sum()),
            "logloss_b3": m3["loss"].mean(),
            "logloss_b4": m4["loss"].mean(),
            "dll_fold_mean": dll.mean(),
            "dll_fold_sd": dll.std(ddof=1) if len(d) > 1 else np.nan,
            "n_b4_better": int((dll > 0).sum()),
            "b3_iter_median": d["b3_iter"].median(),
            "b3_iter_max": int(d["b3_iter"].max()),
            "b4_iter_median": d["b4_iter"].median(),
            "b4_iter_max": int(d["b4_iter"].max()),
            "max_grad_norm": float(max(d["b3_grad_norm"].max(), d["b4_grad_norm"].max())),
        })
    out = pd.DataFrame(rows)
    out["dll"] = out["logloss_b3"] - out["logloss_b4"]
    return out.round({"logloss_b3": 6, "logloss_b4": 6, "dll": 6,
                      "dll_fold_mean": 6, "dll_fold_sd": 6, "max_grad_norm": 3})


def hyperparameters() -> pd.DataFrame:
    """ξ/ρ 的网格分布 + 中间值合计；``kind`` 区分单点与汇总行。"""
    c = _read("convergence")
    rows = []
    for p, grid, lo, hi, fmt in (("xi", XI_GRID, XI_GRID[0], XI_GRID[-1], "{:.4f}"),
                                 ("rho", RHO_GRID, RHO_GRID[0], RHO_GRID[-1], "{:.2f}")):
        for v in grid:
            n = int((c[p] == v).sum())
            rows.append({"parameter": p, "value": v, "label": fmt.format(v),
                         "n_folds": n, "share": n / len(c), "kind": "grid",
                         "at_bound": v in (lo, hi)})
        if p == "xi":
            n, kind = int((~c[p].isin([lo, hi])).sum()), "interior_4_mid"
            label = "0.0010-0.0050"
        else:
            n, kind = int(c[p].isin([lo, hi]).sum()), "both_ends"
            label = "-0.15 and +0.15"
        rows.append({"parameter": p, "value": np.nan, "label": label, "n_folds": n,
                     "share": n / len(c), "kind": kind, "at_bound": np.nan})
    return pd.DataFrame(rows).round({"share": 4})


def paired() -> tuple[pd.DataFrame, pd.DataFrame]:
    """逐折配对比较 + 汇总。t>0 表示“选中更好”（差 = 对手 loss − 选中 loss）。"""
    p = _read("xi_rho_paired_summary").sort_values("block_id")
    sel = _read("xi_rho_by_block")[["block_id", "xi_half_life_years",
                                    "val_logloss", "n_candidates_converged"]]
    p = p.merge(sel, on="block_id", how="left", validate="one_to_one")
    keep = ["block_id", "league", "season", "xi", "rho", "xi_half_life_years",
            "val_logloss", "n_candidates_converged", "xi_interior",
            "runner_up_xi", "runner_up_rho", "dll_runner_up", "se_runner_up",
            "t_runner_up", "runner_up_significant",
            "xi_neighbour", "dll_xi_neighbour", "se_xi_neighbour",
            "t_xi_neighbour", "xi_neighbour_significant"]
    folds = p[keep].rename(columns={
        "dll_runner_up": "dll_vs_best_other", "se_runner_up": "se_vs_best_other",
        "t_runner_up": "t_vs_best_other",
        "dll_xi_neighbour": "dll_vs_neighbour", "se_xi_neighbour": "se_vs_neighbour",
        "t_xi_neighbour": "t_vs_neighbour"}).round(
        {"xi_half_life_years": 3, "val_logloss": 6,
         "dll_vs_best_other": 6, "se_vs_best_other": 6, "t_vs_best_other": 3,
         "dll_vs_neighbour": 6, "se_vs_neighbour": 6, "t_vs_neighbour": 3})
    nb = p.dropna(subset=["dll_xi_neighbour"])
    summ = pd.DataFrame([{
        "n_folds": len(p),
        "n_sig_vs_neighbour": int(p["xi_neighbour_significant"].sum()),
        "n_sig_vs_best_other": int(p["runner_up_significant"].sum()),
        "median_abs_dll_vs_neighbour": float(nb["dll_xi_neighbour"].abs().median()),
        "median_se_vs_neighbour": float(nb["se_xi_neighbour"].median()),
        "median_abs_t_vs_neighbour": float(nb["t_xi_neighbour"].abs().median()),
        "max_abs_t_vs_best_other": float(p["t_runner_up"].abs().max()),
    }]).round(6)
    return folds, summ


def gamma_trend() -> pd.DataFrame:
    g = _read("gamma_by_season")
    rows = []
    for scope, col, se_col in ([("pooled", "gamma_pooled", "se_pooled")] +
                               [(lg, f"gamma_{lg}", f"se_{lg}") for lg in LEAGUES]):
        t = trend(g, col, se_col)
        rows.append({"scope": scope, "n_points": len(g), **t,
                     "n_matches_first": int(g["n_matches_cumulative"].iloc[0]),
                     "n_matches_last": int(g["n_matches_cumulative"].iloc[-1]),
                     "gamma_se_first": float(g[se_col].iloc[0]),
                     "gamma_se_last": float(g[se_col].iloc[-1]),
                     "home_boost_first_pct": float(np.exp(t["first"]) - 1),
                     "home_boost_last_pct": float(np.exp(t["last"]) - 1)})
    return pd.DataFrame(rows).round(6)


def trend_se_inflation(n_sim: int = 4000, seed: int = 0) -> pd.DataFrame:
    """相邻 γ̂ 共用大部分比赛 ⇒ 误差正相关，独立误差的 WLS 区间偏窄。

    用真实的 22 个 se 与 AR(1) 误差做小仿真，量出真实斜率 SD 与朴素 WLS SE 的比值。
    """
    g = _read("gamma_by_season")
    se = g["se_pooled"].to_numpy(float)
    t = np.arange(len(se), dtype=float)
    x = np.column_stack([np.ones_like(t), t])
    rng = np.random.default_rng(seed)
    rows = []
    for rho in (0.0, 0.5, 0.9):
        slopes, naives = [], []
        for _ in range(n_sim):
            e = np.empty(len(se))
            e[0] = rng.normal() * se[0]
            for i in range(1, len(se)):
                e[i] = rho * e[i - 1] + np.sqrt(1 - rho ** 2) * rng.normal() * se[i]
            w = 1.0 / se ** 2
            inv = np.linalg.inv(x.T @ (w[:, None] * x))
            slopes.append(float(inv[1] @ (x.T @ (w * e))))
            naives.append(float(np.sqrt(inv[1, 1])))
        rows.append({"rho": rho, "n_sim": n_sim,
                     "empirical_sd": float(np.std(slopes)),
                     "mean_naive_se": float(np.mean(naives)),
                     "inflation_ratio": float(np.std(slopes) / np.mean(naives))})
    return pd.DataFrame(rows).round(5)


def empty_window() -> pd.DataFrame:
    w = _read("gamma_empty_window")
    rows = []
    pooled: dict[str, dict] = {}
    for win in ("pre", "empty", "post"):
        d = w.loc[w["window"] == win]
        for _, r in d.iterrows():
            rows.append({"scope": "league", "window": win, "league": r["league"],
                         "gamma": r["gamma"], "se": r["se"],
                         "n_matches": int(r["n_matches"])})
        pooled[win] = pool_windows(d)
        rows.append({"scope": "pooled", "window": win, "league": "ALL", **pooled[win]})
    for other in ("pre", "post"):
        e, o = pooled["empty"], pooled[other]
        diff = e["gamma"] - o["gamma"]
        se = float(np.sqrt(e["se"] ** 2 + o["se"] ** 2))
        rows.append({"scope": "contrast", "window": f"empty-{other}", "league": "ALL",
                     "diff": diff, "se": se, "lo95": diff - Z95 * se,
                     "hi95": diff + Z95 * se, "z": diff / se,
                     "pct": float(np.exp(diff) - 1)})
    g = _read("gamma_by_season")
    jumps = g["gamma_pooled"].diff().drop(index=[17, 18]).dropna()
    for r in rows:
        r["yoy_sd"] = float(jumps.std())
    out = pd.DataFrame(rows)
    out["n_matches"] = out["n_matches"].astype("Int64")
    return out.round(6)


def extrapolation() -> pd.DataFrame:
    e = _read("a1_extrapolation")
    out = e.copy().assign(scope="league")
    out["dll"] = out["ll_stale"] - out["ll_oracle"]      # >0 = 用真实 γ 更好
    n = out["n_test"]
    pooled = {
        "scope": "pooled", "league": "ALL", "season": "2024/25",
        "n_test": int(n.sum()), "n_train": int(out["n_train"].sum()),
        "n_new_team": int(out["n_new_team"].sum()),
        "gamma_stale": float((out["gamma_stale"] * n).sum() / n.sum()),
        "gamma_oracle": float((out["gamma_oracle"] * n).sum() / n.sum()),
        "dgamma": float(out["dgamma"].mean()),
        "ll_stale": float((out["ll_stale"] * n).sum() / n.sum()),
        "ll_oracle": float((out["ll_oracle"] * n).sum() / n.sum()),
        "dll": float(((out["ll_stale"] - out["ll_oracle"]) * n).sum() / n.sum()),
        "p_home_stale": float((out["p_home_stale"] * n).sum() / n.sum()),
        "p_home_oracle": float((out["p_home_oracle"] * n).sum() / n.sum()),
        "home_share_actual": float((out["home_share_actual"] * n).sum() / n.sum()),
    }
    out = pd.concat([out, pd.DataFrame([pooled])], ignore_index=True)
    return out.round(6)


BUILDERS = {
    "t4_2_model_fit": model_fit,
    "t4_2_hyperparameters": hyperparameters,
    "t4_2_paired_summary": lambda: paired()[1],
    "t4_2_paired_folds": lambda: paired()[0],
    "tA1_gamma_trend": gamma_trend,
    "tA1_trend_se_inflation": trend_se_inflation,
    "tA1_empty_window": empty_window,
    "tA1_extrapolation": extrapolation,
}


def build_all() -> dict[str, pd.DataFrame]:
    return {name: fn() for name, fn in BUILDERS.items()}


def write_all(frames: dict[str, pd.DataFrame]) -> list[Path]:
    TABLES.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, df in frames.items():
        p = TABLES / f"{name}.csv"
        df.to_csv(p, index=False, encoding="utf-8")
        paths.append(p)
    return paths


def check_all(frames: dict[str, pd.DataFrame]) -> bool:
    ok = True
    for name, fresh in frames.items():
        p = TABLES / f"{name}.csv"
        if not p.exists():
            print(f"FAIL {name}: 文件不存在")
            ok = False
            continue
        disk = pd.read_csv(p)
        # 两边都过一遍 CSV 往返，避免 Int64 / NaN 的 dtype 表示差异
        norm = pd.read_csv(io.StringIO(fresh.to_csv(index=False)))
        try:
            pd.testing.assert_frame_equal(
                disk, norm, check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-9)
            print(f"PASS {name}  {len(fresh)} 行")
        except AssertionError as exc:
            print(f"FAIL {name}: {exc}".splitlines()[0])
            ok = False
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成 §4.2 / 附录 A 的成品表")
    ap.add_argument("--check", action="store_true", help="只比对磁盘上的表，不覆盖")
    a = ap.parse_args(argv)
    frames = build_all()
    if a.check:
        return 0 if check_all(frames) else 1
    for p in write_all(frames):
        print(f"{p.relative_to(ROOT).as_posix()}  {p.stat().st_size:,} B  "
              f"{len(frames[p.stem])} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
