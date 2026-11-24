"""M3 复盘 P0-1 的证据脚本：量化「逐折选参」这条规则的代价。

背景（`Project/M3_交付复盘_v1.0.md` P0-1）：预注册的逐折选参规则在每折只有
一个赛季（约 306–380 场）的验证集上做 argmin，而相邻 ξ 的真实差异约 0.001 nats、
配对 SE 中位 0.0034，信噪比 0.3 ⇒ argmin 近似抽签，且系统性偏向极端值。

**2026-11-24 结论已落地**：B4 主口径改为常量 ``(ξ=0.0019, ρ=0)``（见
``tune_b4.py``）。本脚本因此变成「对照组」，把四个固定配置与**已归档的 argmin 预测**
（``results/logs/selection_diagnostic/preds_B4_argmin.csv``）逐块配对比较，
并重算所有受 B4 影响的下游比较——报告 §4.2.5 的四张表就出自这里。

**它不写 `results/preds/`，不改 `table_main.csv`，不动九臂定义。**
产物全部落在 `results/logs/`：

    results/logs/sensitivity/preds_B4_<tag>.csv     逐场预测（仅作复核底稿）
    results/logs/b4_fixed_hp_by_fold.csv            48 折 × 4 配置的 test log loss
    results/logs/b4_fixed_hp_contrasts.csv          各配置 vs argmin / vs B3 的块级配对区间
    results/logs/b4_fixed_hp_downstream.csv         H2 / B2−B4 / C1 / H4 在该配置下的取值

运行：python -m src.models.sens_b4_fixed_hp         （48 折 × 4 配置 ≈ 90 s）
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
from src.eval.recalibrate import oracle_bound  # noqa: E402
from src.models.b3_poisson import load_panel, predict_proba  # noqa: E402
from src.models.b4_dixon_coles import fit, log_loss  # noqa: E402
from src.splits import load_splits, resolve_split  # noqa: E402

LOGS = ROOT / "results" / "logs"
SENS = LOGS / "sensitivity"
DIAG = LOGS / "selection_diagnostic"
SEED = 20261110
B_BOOT = 10_000

# (tag, ξ, ρ, 说明)：四个都**不做任何选择**，直接用同一组值跑满 48 折
CONFIGS: tuple[tuple[str, float, float, str], ...] = (
    ("centre", 0.0019, 0.0, "网格正中心（半衰期 1.00 年）——现行主口径"),
    ("centre_neg", 0.0019, -0.05, "中心 ξ + 相邻负 ρ"),
    ("min_xi", 0.0005, 0.0, "最常被选中的 ξ（半衰期 3.80 年）"),
    ("flat", 0.0, 0.0, "无衰减无 τ，等价于 B3（退化对照）"),
)


def load_arm(arm: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "preds" / f"preds_{arm}.csv",
                       dtype={"match_id": str, "season": str, "date": str})


def load_argmin() -> pd.DataFrame:
    """已归档的「逐折 argmin」B4 预测（被放弃的规则，作对照基线）。"""
    return pd.read_csv(DIAG / "preds_B4_argmin.csv",
                       dtype={"match_id": str, "season": str, "date": str})


def run_configs(panel: pd.DataFrame, blocks: list[dict]) -> pd.DataFrame:
    """48 折 × 4 配置全量重拟合；返回逐折表，并把预测落到 sensitivity/。"""
    SENS.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for tag, xi, rho, _note in CONFIGS:
        frames = []
        t0 = time.perf_counter()
        for i, b in enumerate(blocks, 1):
            train, test = resolve_split(panel, b)
            m = fit(train, xi=xi, rho=rho, ref_date=b["test_start"])
            p = predict_proba(m, test)
            frames.append(pred_frame(test, p, "B4"))
            rows.append({
                "block_id": b["block_id"], "league": b["league"],
                "season": b["season"], "config": tag, "xi": xi, "rho": rho,
                "n_test": int(len(test)), "converged": bool(m.converged),
                "n_iter": int(m.n_iter), "grad_norm": float(m.grad_norm),
                "test_logloss": log_loss(p, test["y"].to_numpy()),
            })
            print(f"  [{tag:<10}] {i:>2}/48 {b['block_id']:<12} "
                  f"ll={rows[-1]['test_logloss']:.5f}", flush=True)
        out = pd.concat(frames, ignore_index=True)
        out.to_csv(SENS / f"preds_B4_{tag}.csv", index=False, encoding="utf-8")
        print(f"  → {tag}: {len(out):,} 行，{time.perf_counter() - t0:.1f}s", flush=True)
    return pd.DataFrame(rows)


def _interval(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    d = block_deltas(a, b)                      # a − b，按 48 个 (league, season) 块
    r = cluster_bootstrap(d, B=B_BOOT, alpha=0.10, seed=SEED)
    return {"point": r["point"], "lo90": r["lo"], "hi90": r["hi"],
            "deff": design_effect(d)["deff"], "n_paired": len(d.values)}


def contrasts(by_fold: pd.DataFrame) -> pd.DataFrame:
    """每个固定配置 vs 已放弃的 argmin、vs B3：块级配对 90% 区间。"""
    base = load_argmin()
    b3 = load_arm("B3")
    rows = []
    for tag, *_ in CONFIGS:
        cur = pd.read_csv(SENS / f"preds_B4_{tag}.csv",
                          dtype={"match_id": str, "season": str, "date": str})
        vs_b4 = _interval(cur, base)            # 负 = 固定配置更好
        vs_b3 = _interval(cur, b3)              # 正 = 固定配置比 B3 好
        rows.append({"config": tag, "vs": "argmin_abandoned",
                     **vs_b4, "n_folds_better": _fold_wins(tag, base)})
        rows.append({"config": tag, "vs": "B3",
                     **vs_b3, "n_folds_better": _fold_wins(tag, b3)})
    return pd.DataFrame(rows).round(6)


def _fold_wins(tag: str, other_df: pd.DataFrame) -> int:
    """该配置在多少折上比 ``other_df`` 更好（逐块按场合并比较）。"""
    cur = pd.read_csv(SENS / f"preds_B4_{tag}.csv",
                      dtype={"match_id": str, "season": str, "date": str})
    m = cur[["match_id", "league", "season", "y", "p_home", "p_draw", "p_away"]].merge(
        other_df[["match_id", "p_home", "p_draw", "p_away"]], on="match_id",
        suffixes=("", "_o"))
    y = m["y"].to_numpy()
    idx = np.arange(len(m))
    own = -np.log(np.clip(
        m[["p_home", "p_draw", "p_away"]].to_numpy()[idx, y], 1e-15, None))
    oth = -np.log(np.clip(
        m[["p_home_o", "p_draw_o", "p_away_o"]].to_numpy()[idx, y], 1e-15, None))
    return int((pd.Series(own - oth).groupby(
        [m["league"], m["season"]]).mean() < 0).sum())


def _pooled_ll(df: pd.DataFrame, ids: pd.Series | None = None) -> float:
    d = df if ids is None else df.loc[df["match_id"].isin(set(ids))]
    p = d[["p_home", "p_draw", "p_away"]].to_numpy(float)
    y = d["y"].to_numpy()
    return float(-np.log(np.clip(p[np.arange(len(d)), y], 1e-15, None)).mean())


def _h4_rel(b4: pd.DataFrame, b6: pd.DataFrame, b6r: pd.DataFrame) -> float:
    """H4 主判据的 rel（B6r 版），符号与 ``run_m2`` 一致：``(gap_B6r − gap_B6)/gap_B6``。

    正 = B6r 把差距**放大**了（两参数重校准没帮上忙），负 = 缩小。
    三者取同一批 16,728 场次。
    """
    ids = set(b4["match_id"]) & set(b6["match_id"]) & set(b6r["match_id"])
    gap6 = _pooled_ll(b4, ids) - _pooled_ll(b6, ids)
    gap6r = _pooled_ll(b4, ids) - _pooled_ll(b6r, ids)
    return float((gap6r - gap6) / gap6)


def downstream() -> pd.DataFrame:
    """受 B4 影响的四条下游：H2 gap、B2−B4、C1（B5a−B4）、H4 rel（B6r 版 + oracle 上界）。"""
    b2, b5a, b6, b6r = (load_arm("B2"), load_arm("B5a"), load_arm("B6"),
                        load_arm("B6r"))
    base = load_argmin()
    rows = []
    for cfg, cur in ([("argmin(abandoned)", base)] +
                     [(tag, pd.read_csv(SENS / f"preds_B4_{tag}.csv",
                                        dtype={"match_id": str, "season": str,
                                               "date": str}))
                      for tag, *_ in CONFIGS]):
        h2 = _interval(cur, b6)                 # 正 = 模型比市场差
        b2v = _interval(b2, cur)                # 正 = B2 更好
        c1 = _interval(b5a, cur)                # 正 = B4 更好
        orc = oracle_bound(cur, b6)
        rows.append({"config": cfg,
                     "h2_gap": h2["point"], "h2_lo90": h2["lo90"], "h2_hi90": h2["hi90"],
                     "b2_minus_b4": b2v["point"], "b2_lo90": b2v["lo90"],
                     "b2_hi90": b2v["hi90"],
                     "c1_b5a_minus_b4": c1["point"], "c1_lo90": c1["lo90"],
                     "c1_hi90": c1["hi90"],
                     "h4_rel": _h4_rel(cur, b6, b6r),
                     "h4_rel_oracle": orc["rel"]})
    return pd.DataFrame(rows).round(6)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B4 固定超参敏感性（复核用）")
    ap.add_argument("--skip-run", action="store_true", help="复用已落盘的逐场预测")
    a = ap.parse_args(argv)

    panel = load_panel()
    blocks = load_splits()["blocks"]
    if a.skip_run:
        by_fold = pd.read_csv(LOGS / "b4_fixed_hp_by_fold.csv")
    else:
        print(f"B4 固定超参敏感性：48 折 × {len(CONFIGS)} 配置")
        by_fold = run_configs(panel, blocks)
        by_fold.round(6).to_csv(LOGS / "b4_fixed_hp_by_fold.csv",
                                index=False, encoding="utf-8")

    print("\n=== 逐配置池化 test log loss（按场合并）===")
    pooled = (by_fold.assign(w=by_fold["n_test"])
              .groupby("config", sort=False)
              .apply(lambda d: np.average(d["test_logloss"], weights=d["w"]),
                     include_groups=False))
    for tag, *_ in CONFIGS:
        print(f"  {tag:<12} {pooled[tag]:.4f}")
    conv = pd.read_csv(DIAG / "convergence_argmin.csv")
    base_ll = float(np.average(conv["test_logloss_b4"], weights=conv["n_test"]))
    print(f"  {'argmin':<12} {base_ll:.4f}（已放弃的逐折选中）")

    print("\n=== 块级配对 90% 区间 ===")
    ct = contrasts(by_fold)
    ct.to_csv(LOGS / "b4_fixed_hp_contrasts.csv", index=False, encoding="utf-8")
    print(ct.to_string(index=False))

    print("\n=== 下游（用该配置的 B4 重算）===")
    ds = downstream()
    ds.to_csv(LOGS / "b4_fixed_hp_downstream.csv", index=False, encoding="utf-8")
    print(ds.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
