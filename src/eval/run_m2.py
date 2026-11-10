"""M2 全量复现入口（提交入库）：``python -m src.eval.run_m2``。

从已入库的 ``preds_B4.csv``（M3）+ 本机重跑的 ``panel.parquet`` / ``splits.json`` 起，
一步重建 M2 全部机器产物 + H1–H4 判定日志：

    results/preds/preds_B6.csv（16,728，比例法）
    results/preds/preds_B6r.csv（16,728，train-only 两参数重校准）
    results/logs/b6_devig_{power,shin,disagreement}.csv、b6r_n_fit.csv
    results/market_gap.csv、results/table_main.csv（9 行 + deff）
    products/figures/fig07_market_gap.png
    results/logs/m2_decisions_<date>.txt

不联网、不装包、不依赖 ``scripts/``（含会话沙箱绕行脚本）。由 ``appendix/run_all.sh``
第 5 步调用；判定规则与阈值见 ``docs/plans/m2_harness_spec.md`` §7。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.bootstrap import block_deltas, cluster_bootstrap  # noqa: E402
from src.eval.calibration import (  # noqa: E402
    calibration_by_block,
    h1_pipeline,
    tail_bin_bias,
)
from src.eval.decisions import (  # noqa: E402
    h1_ordering_verdict,
    h1_verdict,
    h2_verdict,
    h3_verdict,
    h4_verdict,
)
from src.eval.devig import ODDS_COLS, build_b6, check_odds, power, proportional, shin  # noqa: E402
from src.eval.localisation import build_h3_frame, h3_coefficients, h3_sweep  # noqa: E402
from src.eval.market_gap import build_market_gap, plot_market_gap  # noqa: E402
from src.eval.recalibrate import run_b6r  # noqa: E402
from src.eval.table_main import build_table_main  # noqa: E402
from src.models.b3_poisson import load_panel  # noqa: E402

SEED = 20261110


def _load(arm: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "preds" / f"preds_{arm}.csv",
                       dtype={"match_id": str, "season": str, "date": str})


def run() -> None:
    lines: list[str] = []

    def emit(s: str = "") -> None:
        lines.append(s)
        print(s, flush=True)

    emit("=" * 78)
    emit("[0] B6 去抽水（proportional 主基准 + power/shin 全 schema 互检）")
    b6 = build_b6(out_path=ROOT / "results" / "preds" / "preds_B6.csv")
    emit(f"    preds_B6.csv  {len(b6):,} 行")

    emit("[1] B6r（H4 工具，train-only 两参数重校准）")
    b6r = run_b6r(out_path=ROOT / "results" / "preds" / "preds_B6r.csv",
                  n_fit_log=ROOT / "results" / "logs" / "b6r_n_fit.csv")
    emit(f"    preds_B6r.csv  {len(b6r):,} 行")

    emit("[2] H2 市场差距（三法 × 可用臂）")
    mg = build_market_gap(out_path=ROOT / "results" / "market_gap.csv")
    plot_market_gap(mg, out_path=ROOT / "products" / "figures" / "fig07_market_gap.png")
    emit(mg.to_string(index=False))

    emit("[3] 主推断表 table_main.csv（9 行 + deff）")
    tm = build_table_main(out_path=ROOT / "results" / "table_main.csv")
    emit(tm[["arm", "n_matches", "log_loss", "ll_lo90", "ll_hi90", "deff",
             "delta_vs_B6", "n_paired_vs_B6", "note"]].to_string(index=False))

    emit("[4] H1 市场校准（三法斜率 + 尾箱偏差）")
    panel = load_panel()
    sub = panel.loc[panel["season"] >= "2017/18"].sort_values(
        ["league", "season", "date", "home", "away"])
    ok = check_odds(sub[ODDS_COLS].to_numpy(dtype=float))
    s = sub.loc[ok].reset_index(drop=True)
    odds = s[ODDS_COLS].to_numpy(dtype=float)
    y = s["y"].to_numpy()
    block = (s["league"] + "|" + s["season"]).to_numpy()
    p_prop = proportional(odds)
    p_pow = power(odds)
    p_shin, _ = shin(odds)
    h1 = h1_pipeline(p_prop, p_pow, p_shin, y, block, B=10_000, seed=SEED)
    for name, r in h1.items():
        emit(f"    {name:<12} slope {r['slope']:.4f}  [90% {r['lo']:.4f}, {r['hi']:.4f}]")
    low, high = tail_bin_bias(p_prop, y)
    emit(f"    尾箱偏差(prop) 低箱 {np.round(low, 4)}  高箱 {np.round(high, 4)}")
    h1v = h1_verdict(h1["proportional"]["slope"], h1["proportional"]["lo"],
                     h1["proportional"]["hi"])
    emit(f"    H1 主判据：{h1v['decision']}  （{h1v['reason']}）")
    rng = np.random.default_rng(SEED)
    uids, wgt = np.unique(block, return_counts=True)
    G = len(uids)
    sp = np.nanmean(calibration_by_block(p_prop, y, block), axis=1)
    ss = np.nanmean(calibration_by_block(p_shin, y, block), axis=1)
    idx = rng.integers(0, G, size=(10_000, G))
    d = (np.abs(sp[idx] - 1) * wgt[idx]).sum(axis=1) / wgt[idx].sum(axis=1) \
        - (np.abs(ss[idx] - 1) * wgt[idx]).sum(axis=1) / wgt[idx].sum(axis=1)
    dlo, dhi = np.quantile(d, [0.05, 0.95])
    ho = h1_ordering_verdict(float(d.mean()), float(dlo), float(dhi))
    emit(f"    H1 次判据：{ho['decision']}  （|Δ|={d.mean():.4f}, 90% [{dlo:.4f}, {dhi:.4f}]）")

    emit("[5] H2 判定（B4 vs B6）")
    d46 = block_deltas(_load("B4"), _load("B6"))
    ci95 = cluster_bootstrap(d46, B=10_000, alpha=0.05, seed=SEED)
    ci90 = cluster_bootstrap(d46, B=10_000, alpha=0.10, seed=SEED)
    h2v = h2_verdict(ci95["point"], ci95["lo"], ci95["hi"], ci90["lo"], ci90["hi"])
    emit(f"    Δ_46 = {ci95['point']:.4f}  (95% [{ci95['lo']:.4f}, {ci95['hi']:.4f}] / "
         f"90% [{ci90['lo']:.4f}, {ci90['hi']:.4f}])")
    emit(f"    {h2v['decision']}")

    emit("[6] H3 判定（差距局部化）")
    h3df = build_h3_frame()
    h3c = h3_coefficients(h3df, w=6, B=10_000, seed=SEED)
    emit(f"    promoted {h3c['promoted']}")
    emit(f"    early    {h3c['early']}")
    h3v = h3_verdict(h3c["promoted"]["coef"], h3c["promoted"]["lo"], h3c["promoted"]["hi"],
                     h3c["early"]["coef"], h3c["early"]["lo"], h3c["early"]["hi"])
    emit(f"    {h3v['decision']}  （{h3v['reason']}）")
    emit("    sweep：" + h3_sweep(h3df).to_string(index=False))

    emit("[7] H4 判定（信息 vs 校准）")
    d6 = block_deltas(_load("B4"), _load("B6"))
    d6r = block_deltas(_load("B4"), _load("B6r"))
    gap6 = cluster_bootstrap(d6, B=10_000, alpha=0.10, seed=SEED)
    gap6r = cluster_bootstrap(d6r, B=10_000, alpha=0.10, seed=SEED)
    rng = np.random.default_rng(SEED)
    v6, w6 = d6.values, d6.weights.astype(float)
    v6r, w6r = d6r.values, d6r.weights.astype(float)
    idx = rng.integers(0, d6.n_blocks, size=(10_000, d6.n_blocks))
    g6 = (v6[idx] * w6[idx]).sum(axis=1) / w6[idx].sum(axis=1)
    g6r = (v6r[idx] * w6r[idx]).sum(axis=1) / w6r[idx].sum(axis=1)
    rel = (g6r - g6) / g6
    rlo, rhi = np.quantile(rel, [0.05, 0.95])
    h4v = h4_verdict(float(rel.mean()), float(rlo), float(rhi), gap6["point"])
    emit(f"    gap_B6={gap6['point']:.4f}  gap_B6r={gap6r['point']:.4f}  "
         f"rel={rel.mean():.4f}  (90% [{rlo:.4f}, {rhi:.4f}])")
    emit(f"    {h4v['decision']}  （{h4v['reason']}）")

    log = ROOT / "results" / "logs" / f"m2_decisions_{date.today()}.txt"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emit(f"\n判定日志：{log.relative_to(ROOT)}")


if __name__ == "__main__":
    run()
