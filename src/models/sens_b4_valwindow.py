"""M3 复核 · 「验证集改 3 季」的干跑取证（P0-1 第 2 条，**不改主结果**）。

复盘 P0-1 的判断是：逐折选参之所以是负收益，根因不是网格、也不是代码，而是**验证集
太短**——每折只有一个赛季（约 306–380 场），相邻 ξ 的真实差异 ~0.001 nats，
配对 SE 0.0034，信噪比 0.3。

若这个诊断成立，把验证集从「最后 1 季」扩到「最后 3 季」应当能把信噪比抬到 0.5 以上，
选参才可能开始有正收益。本脚本就是把这句**预测**变成**实测**：

- 48 折完整走一遍（验证集 = 内层最后 3 个赛季）；
- 目标赛季仍不参与选参（结构上保证，与 `tune_b4.py` 同一条红线）；
- 在 test 上评估，与交付版（1 季验证集）逐折配对。

**它不写 `results/preds/`，不改 `convergence.csv`，不动 `table_main.csv`。**
按 §7 第 7 步，这个口径变更须 M2 主签 + M5 会签后才能进主结果；本脚本只提供
签字前必须看到的数字。

产物：`results/logs/b4_val3_window.csv`
运行：python -m src.models.sens_b4_valwindow      （≈ 90 s）
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

from src.eval.bootstrap import block_deltas, cluster_bootstrap, design_effect  # noqa: E402
from src.eval.harness import pred_frame  # noqa: E402
from src.models.b3_poisson import load_panel, predict_proba  # noqa: E402
from src.models.b4_dixon_coles import RHO_GRID, XI_GRID, fit, log_loss  # noqa: E402
from src.splits import load_splits, resolve_split  # noqa: E402

LOGS = ROOT / "results" / "logs"
SEED = 20261110
VAL_SEASONS = 3                 # 交付版是 1；这里是待签字的候选口径


def inner_split_3(train: pd.DataFrame, n_val: int = VAL_SEASONS
                  ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(拟合段, 验证段)；验证段 = 内层最后 ``n_val`` 个赛季。"""
    seasons = sorted(train["season"].unique())
    if len(seasons) <= n_val:
        raise ValueError(f"内层只剩 {len(seasons)} 季，不够留 {n_val} 季做验证")
    val_seasons = seasons[-n_val:]
    inner = train.loc[~train["season"].isin(val_seasons)]
    val = train.loc[train["season"].isin(val_seasons)]
    if str(inner["date"].max()) >= str(val["date"].min()):
        raise ValueError("内层拟合段未严格早于验证段")
    return inner, val


def run_fold(panel: pd.DataFrame, block: dict) -> tuple[dict, pd.DataFrame]:
    train, test = resolve_split(panel, block)
    inner, val = inner_split_3(train)
    y_val = val["y"].to_numpy()
    ref_inner = str(val["date"].min())

    best, prev, n_ok = None, None, 0
    se_neighbour = np.nan
    for xi in XI_GRID:
        for rho in RHO_GRID:
            m = fit(inner, xi=xi, rho=rho, ref_date=ref_inner,
                    init=prev.warm if prev is not None else None)
            prev = m
            if not m.converged:
                continue
            n_ok += 1
            p_val = predict_proba(m, val)
            ll = log_loss(p_val, y_val)
            if best is None or ll < best["val_logloss"] - 1e-12:
                best = {"xi": xi, "rho": rho, "val_logloss": ll, "loss": -np.log(
                    np.clip(p_val[np.arange(len(y_val)), y_val], 1e-15, None))}

    # 验证集上「选中 vs 同 ρ 的相邻 ξ」的配对 SE —— 这就是信噪比的分母
    adj = [x for x in XI_GRID if abs(XI_GRID.index(x) - XI_GRID.index(best["xi"])) == 1]
    if adj:
        xi_n = min(adj, key=lambda x: abs(x - best["xi"]))
        m = fit(inner, xi=xi_n, rho=best["rho"], ref_date=ref_inner)
        ll_n = -np.log(np.clip(
            predict_proba(m, val)[np.arange(len(y_val)), y_val], 1e-15, None))
        diff = ll_n - best["loss"]
        n = len(y_val)
        se_neighbour = float(np.std(diff, ddof=1) / np.sqrt(n))
        dll_neighbour = float(diff.mean())
    else:
        dll_neighbour = np.nan

    final = fit(train, xi=best["xi"], rho=best["rho"], ref_date=block["test_start"])
    rec = {"block_id": block["block_id"], "league": block["league"],
           "season": block["season"], "n_inner": int(len(inner)),
           "n_val": int(len(val)), "xi": best["xi"], "rho": best["rho"],
           "val_logloss": best["val_logloss"], "n_candidates_converged": n_ok,
           "dll_vs_neighbour": dll_neighbour, "se_vs_neighbour": se_neighbour,
           "test_logloss": log_loss(predict_proba(final, test), test["y"].to_numpy()),
           "converged": bool(final.converged)}
    return rec, pred_frame(test, predict_proba(final, test), "B4")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B4 三季验证集干跑（待签字口径）")
    ap.add_argument("--out", default=str(LOGS / "b4_val3_window.csv"))
    a = ap.parse_args(argv)

    panel, blocks = load_panel(), load_splits()["blocks"]
    base = pd.read_csv(LOGS / "convergence.csv").set_index("block_id")
    rows, frames = [], []
    t0 = time.perf_counter()
    for i, b in enumerate(blocks, 1):
        rec, fr = run_fold(panel, b)
        rec["xi_base"] = float(base.loc[b["block_id"], "xi"])
        rec["rho_base"] = float(base.loc[b["block_id"], "rho"])
        rec["test_logloss_base"] = float(base.loc[b["block_id"], "test_logloss_b4"])
        rows.append(rec)
        frames.append(fr)
        print(f"[{i:>2}/48] {rec['block_id']:<12} val {rec['n_val']:>4,} 场  "
              f"ξ {rec['xi_base']:<7}→{rec['xi']:<7} ρ {rec['rho_base']:+.2f}→{rec['rho']:+.2f}"
              f"  test {rec['test_logloss_base']:.5f}→{rec['test_logloss']:.5f}"
              f"  SE {rec['se_vs_neighbour']:.4f}", flush=True)
    df = pd.DataFrame(rows)
    df.round(6).to_csv(a.out, index=False, encoding="utf-8")

    cur = pd.concat(frames, ignore_index=True)
    sens = LOGS / "sensitivity"
    sens.mkdir(parents=True, exist_ok=True)
    cur.to_csv(sens / "preds_B4_val3.csv", index=False, encoding="utf-8")
    base_pred = pd.read_csv(ROOT / "results" / "preds" / "preds_B4.csv",
                            dtype={"match_id": str, "season": str, "date": str})
    n_test = np.array([b["n_test"] for b in blocks])

    def compare(tag: str, other: pd.DataFrame) -> dict:
        d = block_deltas(cur, other)
        ci = cluster_bootstrap(d, B=10_000, alpha=0.10, seed=SEED)
        print(f"  vs {tag:<28} {ci['point']:+.5f} [{ci['lo']:+.5f}, {ci['hi']:+.5f}]"
              f"  deff {design_effect(d)['deff']:.2f}")
        return ci

    print("\n" + "=" * 78)
    print(f"验证集 = 内层最后 {VAL_SEASONS} 季（交付版 1 季）")
    print(f"验证样本/折：中位 {int(df['n_val'].median()):,} 场（交付版约 306–380）")
    print(f"选中 vs 邻格的配对 SE：中位 {df['se_vs_neighbour'].median():.4f}"
          f"（交付版 0.0034）；信噪比中位 "
          f"{(df['dll_vs_neighbour'].abs() / df['se_vs_neighbour']).median():.2f}"
          f"（交付版 0.42）")
    print(f"池化 test log loss：交付 {np.average(df['test_logloss_base'], weights=n_test):.5f}"
          f" → 3 季验证集 {np.average(df['test_logloss'], weights=n_test):.5f}")
    print(f"3 季更好：{int((df['test_logloss'] < df['test_logloss_base']).sum())}/48 折")
    print("块级配对 90% 区间（负 = 3 季更好）：")
    compare("reported arm", base_pred)
    # 2026-11-24 起主口径就是常量 (0.0019, 0)，所以「交付版」与「固定中心」是同一条预测，
    # 不再并列打印两行（那只会打印两次同样的结果，看起来像两个独立证据）。
    print("    注：主口径已是常量超参，上一行即「固定中心 (0.0019, 0)」本身。")
    print(f"用时 {time.perf_counter() - t0:.0f}s → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
