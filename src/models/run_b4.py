"""48 折 B3 / B4 全量跑数（M3 / T3.4）：落 preds + 收敛诊断 + 参数轨迹。

每折流程：``resolve_split`` 拿 (train, test) → 定 (ξ,ρ) → 完整 train 重拟合 → 预测该块
test。B3 用同一批 train、``ξ=0, ρ=0``，保证两个 arm 预测的是同一批比赛。

**B4 的 (ξ,ρ) 现行主口径是固定值** ``(0.0019, 0)``（见 ``tune_b4.py`` 模块 docstring），
不使用任何在线选择；``--selection argmin`` 可复现已放弃的逐折网格搜索，产物一律写入
``results/logs/selection_diagnostic/``，**不覆盖主产物**。

产物（全部按 ``data_interface.md`` §1 的 schema）：

固定口径（默认，``--selection fixed``）：
    results/preds/preds_B3.csv            16,733 行
    results/preds/preds_B4.csv            16,733 行
    results/logs/convergence.csv          48 行
    results/logs/xi_rho_by_block.csv      48 行（xi/rho 为常量，val_* 置 NaN）

诊断口径（``--selection argmin``）：
    results/logs/selection_diagnostic/preds_B4_argmin.csv
    results/logs/selection_diagnostic/convergence_argmin.csv
    results/logs/selection_diagnostic/xi_rho_by_block_argmin.csv          48 行
    results/logs/selection_diagnostic/xi_rho_paired_se_argmin.csv         1,440 行
    results/logs/selection_diagnostic/xi_rho_paired_summary_argmin.csv    48 行
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

from src.eval.harness import PRED_COLS, check_pred, pred_frame  # noqa: E402
from src.models.b3_poisson import fit as fit_b3  # noqa: E402
from src.models.b3_poisson import load_panel, predict_proba  # noqa: E402
from src.models.b4_dixon_coles import XI_GRID, log_loss  # noqa: E402
from src.models.tune_b4 import SELECTIONS, fit_fixed, tune_block  # noqa: E402
from src.splits import EXPECTED_EVAL_ROWS, load_splits, resolve_split  # noqa: E402

DIAG = ROOT / "results" / "logs" / "selection_diagnostic"


def paired_summary(d: pd.DataFrame) -> pd.DataFrame:
    """每折两行对照：全体 runner-up，以及**同 ρ̂ 下最强 ξ 对手**（验收项 6 的证据）。"""
    rows = []
    for bid, g in d.groupby("block_id", sort=False):
        sel = g.loc[g["is_selected"]].iloc[0]
        others = g.loc[~g["is_selected"]]
        if others.empty:
            continue
        ru = others.loc[others["val_logloss"].idxmin()]
        alt = others.loc[(others["rho"] == sel["rho"]) & (others["xi"] != sel["xi"])]
        nb = alt.loc[alt["val_logloss"].idxmin()] if len(alt) else None
        rows.append({
            "block_id": bid, "league": sel["league"], "season": sel["season"],
            "xi": sel["xi"], "rho": sel["rho"],
            "xi_interior": sel["xi"] not in (XI_GRID[0], XI_GRID[-1]),
            "runner_up_xi": ru["xi"], "runner_up_rho": ru["rho"],
            "dll_runner_up": ru["dll_vs_selected"], "se_runner_up": ru["paired_se"],
            "t_runner_up": ru["t"],
            "runner_up_significant": bool(abs(ru["t"]) > 1.96),
            "xi_neighbour": nb["xi"] if nb is not None else np.nan,
            "dll_xi_neighbour": nb["dll_vs_selected"] if nb is not None else np.nan,
            "se_xi_neighbour": nb["paired_se"] if nb is not None else np.nan,
            "t_xi_neighbour": nb["t"] if nb is not None else np.nan,
            "xi_neighbour_significant":
                bool(nb is not None and abs(nb["t"]) > 1.96),
        })
    return pd.DataFrame(rows)


def run(blocks: list[dict] | None = None, panel: pd.DataFrame | None = None,
        verbose: bool = True, selection: str = "fixed") -> dict[str, pd.DataFrame]:
    if selection not in SELECTIONS:
        raise ValueError(f"selection 只能是 {SELECTIONS}，收到 {selection!r}")
    panel = load_panel() if panel is None else panel
    data = load_splits()
    todo = data["blocks"] if blocks is None else blocks

    preds_b3, preds_b4, conv, tune = [], [], [], []
    paired: list[dict] = []
    t_all = time.perf_counter()
    for i, block in enumerate(todo, 1):
        t0 = time.perf_counter()
        train, test = resolve_split(panel, block)
        if selection == "fixed":
            rec, m_b4 = fit_fixed(train, block)
        else:
            rec, m_b4 = tune_block(panel, block, paired_out=paired)
        m_b3 = fit_b3(train, xi=0.0, rho=0.0, ref_date=block["test_start"])

        p3 = predict_proba(m_b3, test)
        p4 = predict_proba(m_b4, test)
        f3 = pred_frame(test, p3, "B3")
        f4 = pred_frame(test, p4, "B4")
        check_pred(f3, block["n_test"])
        check_pred(f4, block["n_test"])

        y = test["y"].to_numpy()
        conv.append({
            "block_id": block["block_id"], "league": block["league"],
            "season": block["season"], "n_train": block["n_train"],
            "n_test": block["n_test"], "n_new_team": block["n_new_team"],
            "selection": selection,
            "b3_converged": bool(m_b3.converged), "b3_iter": int(m_b3.n_iter),
            "b3_grad_norm": float(m_b3.grad_norm),
            "b4_converged": bool(m_b4.converged), "b4_iter": int(m_b4.n_iter),
            "b4_grad_norm": float(m_b4.grad_norm),
            "b4_nll_train": float(m_b4.nll),
            "xi": rec["xi"], "rho": rec["rho"],
            "test_logloss_b3": log_loss(p3, y), "test_logloss_b4": log_loss(p4, y),
            "elapsed_s": time.perf_counter() - t0,
        })
        tune.append(rec)
        preds_b3.append(f3)
        preds_b4.append(f4)
        if verbose:
            print(f"[{i:>2}/{len(todo)}] {block['block_id']:<12} "
                  f"ξ={rec['xi']:<7} ρ={rec['rho']:<6.2f} "
                  f"ll B3 {conv[-1]['test_logloss_b3']:.4f} / "
                  f"B4 {conv[-1]['test_logloss_b4']:.4f} "
                  f"{conv[-1]['elapsed_s']:.1f}s", flush=True)

    out = {"preds_B3": pd.concat(preds_b3, ignore_index=True),
           "preds_B4": pd.concat(preds_b4, ignore_index=True),
           "convergence": pd.DataFrame(conv),
           "xi_rho_by_block": pd.DataFrame(tune)}
    if selection == "argmin":          # 配对证据只属于「被放弃的规则」，不外流到主产物
        paired_df = pd.DataFrame(paired)
        out["xi_rho_paired_se"] = paired_df
        out["xi_rho_paired_summary"] = paired_summary(paired_df)
    if verbose:
        print(f"\n48 折合计 {time.perf_counter() - t_all:.1f}s")
    return out


def write_outputs(out: dict[str, pd.DataFrame],
                  selection: str = "fixed") -> dict[str, str]:
    """固定口径写 ``results/preds`` + ``results/logs``；诊断口径单独一个目录、加后缀。"""
    pred_dir = ROOT / "results" / "preds" if selection == "fixed" else DIAG
    log_dir = ROOT / "results" / "logs" if selection == "fixed" else DIAG
    pred_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, df in out.items():
        if selection == "fixed":
            fn = f"{name}.csv"
        else:                               # 诊断目录里一律带 _argmin，一眼可辨来历
            if name == "preds_B3":
                continue                    # B3 与选参规则无关，不重复落盘
            fn = f"{name}_argmin.csv"
        p = (pred_dir if name.startswith("preds_") else log_dir) / fn
        df.to_csv(p, index=False, encoding="utf-8")
        paths[name] = str(p)
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B3 / B4 48 折全量跑数")
    ap.add_argument("--league", default=None, help="只跑一个联赛（冒烟用）")
    ap.add_argument("--dry-run", action="store_true", help="不落盘")
    ap.add_argument("--selection", choices=SELECTIONS, default="fixed",
                    help="fixed（默认，主口径：常量超参）| argmin（已放弃的逐折选参，只写诊断目录）")
    a = ap.parse_args(argv)

    data = load_splits()
    blocks = [b for b in data["blocks"] if a.league in (None, b["league"])]
    print(f"选参口径：{a.selection}")
    out = run(blocks, selection=a.selection)

    print("-" * 78)
    b4 = out["preds_B4"]
    y = b4["y"].to_numpy()
    p4 = b4[["p_home", "p_draw", "p_away"]].to_numpy()
    p3 = out["preds_B3"][["p_home", "p_draw", "p_away"]].to_numpy()
    conv = out["convergence"]
    print(f"行数 B3={len(out['preds_B3']):,} / B4={len(b4):,}"
          f"（全量应为 {EXPECTED_EVAL_ROWS:,}）")
    print(f"log loss  B3 {log_loss(p3, y):.4f}  B4 {log_loss(p4, y):.4f}")
    print(f"失败折  B3 {int((~conv['b3_converged']).sum())} / "
          f"B4 {int((~conv['b4_converged']).sum())}（阈值 ≤ 2）")

    if a.selection == "fixed":
        print(f"B4 超参   ξ={conv['xi'].unique().tolist()}  ρ={conv['rho'].unique().tolist()}"
              f"（常量，48 折共用，无在线选择）")
    else:
        xi_counts = conv["xi"].value_counts().sort_index()
        print("ξ 分布：" + "  ".join(f"{k}:{v}" for k, v in xi_counts.items()))
        # 「中间 4 个值」按网格端点定义，不按本批观测到的最小/最大值 ——
        # 某一端没有折选中时，按观测值取首尾会把内侧相邻值误判成端点（26 vs 33）。
        inner = int((~conv["xi"].isin([XI_GRID[0], XI_GRID[-1]])).sum())
        print(f"落在网格中间 4 个值的折数 {inner}/{len(conv)}"
              f"（原验收要求 ≥ 90% = {int(np.ceil(0.9 * len(conv)))}）")
        print("ρ 分布：" + "  ".join(
            f"{k}:{v}" for k, v in conv["rho"].value_counts().sort_index().items()))
        ps = out["xi_rho_paired_summary"]
        sig = int(ps["xi_neighbour_significant"].sum())
        print(f"配对 SE：选中 ξ vs 同 ρ̂ 下最强 ξ 对手，显著不同 {sig}/{len(ps)} 折（|t|>1.96）；"
              f"中位 |Δ| {ps['dll_xi_neighbour'].median():.4f} nats、"
              f"中位配对 SE {ps['se_xi_neighbour'].median():.4f}")

    if not a.dry_run:
        paths = write_outputs(out, selection=a.selection)
        for k, v in paths.items():
            print(f"  {Path(v).relative_to(ROOT)}  {Path(v).stat().st_size:,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
