"""B4 的超参口径（M3 / T3.3）：**主口径是固定超参**，逐折网格搜索降级为诊断。

## 现行主口径（2026-11-24 总负责人裁定，取代预注册的逐折 argmin）

``ξ = 0.0019``（半衰期 ln2/ξ ≈ 365 天）、``ρ = 0``，48 折共用同一组值，**不做任何在线选择**。

依据（``results/logs/b4_fixed_hp_contrasts.csv``）：在每折验证集只有 1 个赛季（约 306–380 场）
的条件下，相邻 ξ 的真实差异约 0.001 nats 而配对 SE 中位 0.0034（信噪比 0.3），argmin 近似
抽签。把规则换成常量后池化 test log loss 由 0.9939 降到 0.9903，配对差
−0.0036 [−0.0060, −0.0013]，29/48 折更好；另两个固定配置同样优于 argmin。

事前合理性（不依赖任何 test 表现）：365 天半衰期对应「球队实力约一年翻新一次」这一
足球建模的常见尺度；ρ=0 意味着不加低比分修正，于是 **B3→B4 的差异纯粹来自时间衰减**，
归因比原来更干净。

## 被放弃的规则（仍可复现，作诊断）

``tune_block()`` 保留不动：48 折 × 6 ξ × 5 ρ 在内层验证集上 argmin。它现在的用途是
产出「为什么这条规则不可信」的证据（验证集内 30 个候选两两分不出来、ξ 堆在网格边界），
由 ``run_b4.py --selection argmin`` 写入 ``results/logs/selection_diagnostic/``，
**不再写入主产物**。

红线不变：目标赛季（外层 test）**一次都不进选参**。固定口径更进一步——连验证集都不碰。
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


# ── 主口径：固定超参，不做在线选择 ────────────────────────────────────────────
# 0.0019 是预注册网格 (0.0005, 0.0010, 0.0019, 0.0035, 0.0065, 0.0120) 的正中间那个值，
# 也是复盘 §4.2.5 里四个固定配置中最优的那个；选它的理由写在模块 docstring，
# 与任何 test 表现无关。
FIXED_XI: float = 0.0019
FIXED_RHO: float = 0.0
FIXED_HP: tuple[float, float] = (FIXED_XI, FIXED_RHO)
SELECTIONS: tuple[str, ...] = ("fixed", "argmin")


# 被放弃的 argmin 规则钉在**历史容差**上（b3_poisson.fit 在 2026-11-24 收紧之前的值）。
# 理由：归档目录里的 preds_B4_argmin.csv 是用这组容差跑出来的，改了就再也复现不了；
# 而这条规则本身已经是只供诊断的死路径，没有理由跟着主口径一起"升级"。
LEGACY_FIT_OPTS = {"maxiter": 500, "tol": 1e-9, "gtol": 1e-7}


def fit_fixed(train: pd.DataFrame, block: dict,
              xi: float = FIXED_XI, rho: float = FIXED_RHO) -> tuple[dict, object]:
    """固定口径：不做选择，直接用在**完整 train** 上拟合 ``(xi, rho)``。

    ``train`` 由调用方用 ``resolve_split`` 切好（外层 test 从不进来）。返回的记录与
    ``tune_block()`` 同 schema，便于两者写同一张逐折表；只在内层验证相关的字段上置
    ``NaN`` / ``0``——本口径压根没有内层切分，填 0 会谎称"验证过"。
    """
    t0 = time.perf_counter()
    final = fit(train, xi=xi, rho=rho, ref_date=block["test_start"], init=None)
    rec = {
        "block_id": block["block_id"],
        "league": block["league"],
        "season": block["season"],
        "selection": "fixed",
        "n_train": int(len(train)),
        "n_inner": np.nan,
        "n_val": np.nan,
        "val_season": "",
        "xi": xi,
        "rho": rho,
        "xi_half_life_years": half_life_years(xi),
        "val_logloss": np.nan,
        "n_candidates_converged": 0,
        "n_new_team": int(block["n_new_team"]),
        "train_logloss_insample": log_loss(predict_proba(final, train),
                                           train["y"].to_numpy()),
        "converged": bool(final.converged),
        "n_iter": int(final.n_iter),
        "grad_norm": float(final.grad_norm),
        "train_nll": float(final.nll),
        "elapsed_s": time.perf_counter() - t0,
    }
    return rec, final


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
                    init=prev.warm if (warm and prev is not None) else None,
                    **LEGACY_FIT_OPTS)
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
                ref_date=block["test_start"], init=prev.warm if warm else None,
                **LEGACY_FIT_OPTS)

    rec = {
        "block_id": block["block_id"],
        "league": block["league"],
        "season": block["season"],
        "selection": "argmin",
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
            m = fit(inner, xi=xi, rho=rho, ref_date=str(val["date"].min()),
                    **LEGACY_FIT_OPTS)
            rows.append({"xi": xi, "rho": rho, "val_logloss": log_loss(predict_proba(m, val), y_val),
                         "converged": m.converged})
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B4 超参调试（固定口径 vs 已放弃的 argmin）")
    ap.add_argument("--block", default="E0|2024/25", help="block_id，如 E0|2024/25")
    ap.add_argument("--all", action="store_true",
                    help="48 折跑一遍 argmin 选参，只写 selection_diagnostic/（诊断用）")
    a = ap.parse_args(argv)

    panel = load_panel()
    data = load_splits()
    if not a.all:
        block = next(b for b in data["blocks"] if b["block_id"] == a.block)
        train, _ = resolve_split(panel, block)
        t0 = time.perf_counter()
        rec_f, _m = fit_fixed(train, block)
        rec_a, _ = tune_block(panel, block)
        print("=" * 78)
        print(f"{rec_f['block_id']} · train {rec_f['n_train']:,}")
        print(f"  固定口径   ξ={rec_f['xi']} (半衰期 {rec_f['xi_half_life_years']:.2f} 年)"
              f"  ρ={rec_f['rho']}  |grad|∞ {rec_f['grad_norm']:.2e}"
              f"  收敛 {rec_f['converged']}")
        print(f"  已放弃     ξ={rec_a['xi']}  ρ={rec_a['rho']}"
              f"  val logloss={rec_a['val_logloss']:.4f}"
              f"（内层 {rec_a['n_inner']:,} / val {rec_a['n_val']:,} 赛季 {rec_a['val_season']}）")
        print(f"  合计 {time.perf_counter() - t0:.1f}s")
        return 0

    rows = []
    for i, block in enumerate(data["blocks"], 1):
        rec, _ = tune_block(panel, block)
        rows.append(rec)
        print(f"[{i:>2}/48] {rec['block_id']:<12} ξ={rec['xi']:<7} ρ={rec['rho']:<7.2f} "
              f"val_ll={rec['val_logloss']:.4f} {rec['elapsed_s']:.1f}s", flush=True)
    df = pd.DataFrame(rows)
    out = ROOT / "results" / "logs" / "selection_diagnostic" / "xi_rho_by_block_argmin.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"\n已写入 {out.relative_to(ROOT)}（{len(df)} 行）——诊断用，不是主产物")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
