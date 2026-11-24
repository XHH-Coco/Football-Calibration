"""M2 全量复现入口（提交入库）：``python -m src.eval.run_m2``。

从已入库的 ``preds_B4.csv``（M3）+ 本机重跑的 ``panel.parquet`` / ``splits.json`` 起，
一步重建 M2 全部机器产物 + H1–H4 / C1 / C2 判定日志：

    results/preds/preds_B6.csv（16,728，比例法）
    results/preds/preds_B6r.csv（16,728，train-only 两参数重校准）
    results/logs/b6_devig_{power,shin,disagreement}.csv、b6r_n_fit.csv
    results/logs/bootstrap_selfcheck.txt（验收项 7：块级 vs 逐场宽度比 + deff）
    results/logs/h1_slope_by_class.csv（逐类校准斜率，H1 口径依赖的证据）
    results/logs/h3_sensitivity.csv（min / max / 仅主队三种 early 定义）
    results/logs/h4_oracle_bound.csv（两参数重校准能解释的 gap 上界）
    results/logs/m2_verdicts.csv（每条判定的 decision + 区间 + n_paired，供 §5 倒查）
    results/market_gap.csv、results/table_main.csv（9 行 + deff）
    products/figures/fig07_market_gap.png
    results/logs/m2_decisions_<date>.txt

不联网、不装包、不依赖 ``scripts/``（含会话沙箱绕行脚本）。由 ``appendix/run_all.sh``
第 5 步调用；判定规则与阈值见 ``docs/plans/m2_harness_spec.md`` §7（v1.4）。
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

from src.eval.bootstrap import (  # noqa: E402
    block_deltas,
    cluster_bootstrap,
    selfcheck_text,
)
from src.eval.calibration import (  # noqa: E402
    calibration_by_block,
    h1_pipeline,
    h1_slope_by_class,
    tail_bin_bias,
)
from src.eval.decisions import (  # noqa: E402
    c1_verdict,
    c2_verdict,
    h1_ordering_verdict,
    h1_verdict,
    h2_verdict,
    h3_verdict,
    h4_verdict,
)
from src.eval.devig import ODDS_COLS, build_b6, check_odds, power, proportional, shin  # noqa: E402
from src.eval.localisation import (  # noqa: E402
    build_h3_frame,
    h3_coefficients,
    h3_sensitivity,
    h3_sweep,
)
from src.eval.market_gap import build_market_gap, plot_market_gap  # noqa: E402
from src.eval.plots_h3h4 import plot_localisation_recal  # noqa: E402
from src.eval.plots_main import plot_arms, plot_c_equivalence  # noqa: E402
from src.eval.recalibrate import oracle_bound, run_b6r  # noqa: E402
from src.eval.table_main import build_table_main  # noqa: E402
from src.models.b3_poisson import load_panel  # noqa: E402

SEED = 20261110
LOGS = ROOT / "results" / "logs"
SPEC = "m2_harness_spec v1.4（2026-11-23：宽度比口径、逐类斜率、H3 min 口径、verdict 返回契约）"


def _load(arm: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / "results" / "preds" / f"preds_{arm}.csv",
                       dtype={"match_id": str, "season": str, "date": str})


def _verdict_row(hypothesis: str, v: dict, point: float | None = None,
                 detail: str = "", lo: float | None = None,
                 hi: float | None = None) -> dict:
    """把 verdict dict 摊平成 CSV 一行；``lo`` / ``hi`` 可覆盖（H3 有两个系数区间）。"""
    if lo is None or hi is None:
        if v.get("interval"):
            lo, hi = v["interval"]
        else:
            lo = hi = None
    return {"hypothesis": hypothesis, "decision": v["decision"],
            "point": point, "lo": lo, "hi": hi,
            "n_paired": v.get("n_paired"), "detail": detail or v["reason"]}


def run() -> None:
    lines: list[str] = []
    verdicts: list[dict] = []

    def emit(s: str = "") -> None:
        lines.append(s)
        print(s, flush=True)

    emit("=" * 78)
    emit(f"M2 全量复现 · {SPEC}")
    emit(f"python -m src.eval.run_m2 @ {date.today()} · seed={SEED}")
    emit("=" * 78)
    emit("[0] B6 去抽水（proportional 主基准 + power/shin 全 schema 互检）")
    b6 = build_b6(out_path=ROOT / "results" / "preds" / "preds_B6.csv")
    emit(f"    preds_B6.csv  {len(b6):,} 行")

    emit("[1] B6r（H4 工具，train-only 两参数重校准）")
    b6r = run_b6r(out_path=ROOT / "results" / "preds" / "preds_B6r.csv",
                  n_fit_log=LOGS / "b6r_n_fit.csv")
    emit(f"    preds_B6r.csv  {len(b6r):,} 行")

    emit("[2] H2 市场差距（三法 × 可用臂）")
    mg = build_market_gap(out_path=ROOT / "results" / "market_gap.csv")
    plot_market_gap(mg, out_path=ROOT / "products" / "figures" / "fig07_market_gap.png")
    emit(mg.to_string(index=False))

    emit("[3] 主推断表 table_main.csv（9 行 + deff）")
    tm = build_table_main(out_path=ROOT / "results" / "table_main.csv")
    emit(tm[["arm", "n_matches", "log_loss", "ll_lo90", "ll_hi90", "deff",
             "delta_vs_B6", "n_paired_vs_B6", "note"]].to_string(index=False))
    # fig03 画的就是这张表；放在这里，图与表永远同一个出口，不会各自过期。
    plot_arms(tm, out_path=ROOT / "products" / "figures" / "fig03_arms.png")

    emit("[4] bootstrap 自检（验收项 7：块级 vs 逐场区间宽度比）")
    frames = {a: _load(a) for a in ("B0", "B2", "B4", "B5a", "B6", "B6r")}
    text = selfcheck_text(frames, B=10_000, seed=SEED)
    (LOGS / "bootstrap_selfcheck.txt").write_text(text, encoding="utf-8")
    for ln in text.splitlines():
        emit("    " + ln)
    if "FAIL" in text:
        raise RuntimeError("bootstrap 自检未通过，见 results/logs/bootstrap_selfcheck.txt")

    emit("[5] H1 市场校准（三法斜率 + 逐类斜率 + 尾箱偏差）")
    panel = load_panel()
    sub = panel.loc[panel["season"] >= "2017/18"].sort_values(
        ["league", "season", "date", "home", "away"])
    ok = check_odds(sub[ODDS_COLS].to_numpy(dtype=float))
    s = sub.loc[ok].reset_index(drop=True)
    odds = s[ODDS_COLS].to_numpy(dtype=float)
    y = s["y"].to_numpy()
    block = (s["league"] + "|" + s["season"]).to_numpy()
    n_h1 = int(len(y))
    p_prop = proportional(odds)
    p_pow = power(odds)
    p_shin, _ = shin(odds)
    h1 = h1_pipeline(p_prop, p_pow, p_shin, y, block, B=10_000, seed=SEED)
    for name, r in h1.items():
        emit(f"    {name:<12} slope {r['slope']:.4f}  [90% {r['lo']:.4f}, {r['hi']:.4f}]")
    by_class = h1_slope_by_class(
        {"proportional": p_prop, "power": p_pow, "shin": p_shin}, y, block,
        B=10_000, seed=SEED)
    by_class.to_csv(LOGS / "h1_slope_by_class.csv", index=False, encoding="utf-8")
    emit("    逐类斜率（90% 簇区间）：")
    emit(by_class.round(4).to_string(index=False))
    low, high = tail_bin_bias(p_prop, y)
    emit(f"    尾箱偏差(prop) 低箱 {np.round(low, 4)}  高箱 {np.round(high, 4)}")
    h1v = h1_verdict(h1["proportional"]["slope"], h1["proportional"]["lo"],
                     h1["proportional"]["hi"], n_paired=n_h1)
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
    ho = h1_ordering_verdict(float(d.mean()), float(dlo), float(dhi), n_paired=n_h1)
    emit(f"    H1 次判据：{ho['decision']}  （|Δ|={d.mean():.4f}, 90% [{dlo:.4f}, {dhi:.4f}]）")
    verdicts.append(_verdict_row("H1 斜率>1（比例法）", h1v,
                                 h1["proportional"]["slope"],
                                 f"另两法：Shin {h1['shin']['slope']:.4f} "
                                 f"[{h1['shin']['lo']:.4f},{h1['shin']['hi']:.4f}]、"
                                 f"power {h1['power']['slope']:.4f} "
                                 f"[{h1['power']['lo']:.4f},{h1['power']['hi']:.4f}]"))
    verdicts.append(_verdict_row("H1 排序（比例法偏差最大）", ho, float(d.mean())))

    emit("[6] H2 判定（B4 vs B6）")
    d46 = block_deltas(_load("B4"), _load("B6"))
    ci95 = cluster_bootstrap(d46, B=10_000, alpha=0.05, seed=SEED)
    ci90 = cluster_bootstrap(d46, B=10_000, alpha=0.10, seed=SEED)
    h2v = h2_verdict(ci95["point"], ci95["lo"], ci95["hi"], ci90["lo"], ci90["hi"],
                     n_paired=d46.n_paired)
    emit(f"    Δ_46 = {ci95['point']:.4f}  (95% [{ci95['lo']:.4f}, {ci95['hi']:.4f}] / "
         f"90% [{ci90['lo']:.4f}, {ci90['hi']:.4f}])  n_paired={d46.n_paired:,}")
    emit(f"    {h2v['decision']}")
    verdicts.append(_verdict_row("H2（B4 vs B6）", h2v, ci90["point"]))

    # H2 稳健性：预注册主角是 B4，但 table_main 显示 B2 更好（配对区间不含 0）。
    # 用最佳透明臂重算一遍 gap，回答「换成最强的透明模型，H2 还成立吗」。
    d26 = block_deltas(_load("B2"), _load("B6"))
    ci26_95 = cluster_bootstrap(d26, B=10_000, alpha=0.05, seed=SEED)
    ci26_90 = cluster_bootstrap(d26, B=10_000, alpha=0.10, seed=SEED)
    emit(f"    [稳健性] 最佳透明臂 B2 vs B6：Δ = {ci26_90['point']:.4f}  "
         f"(95% [{ci26_95['lo']:.4f}, {ci26_95['hi']:.4f}] / "
         f"90% [{ci26_90['lo']:.4f}, {ci26_90['hi']:.4f}])  n={d26.n_paired:,}"
         f"  → {'仍高于 +0.02，H2 不变' if ci26_90['lo'] > 0.02 else '跌进等价带，需改口径'}")
    verdicts.append({
        "hypothesis": "H2 稳健性（最佳透明臂 B2 vs B6）",
        "decision": "仍高于 +0.02，H2 不变" if ci26_90["lo"] > 0.02 else "跌进等价带，需改口径",
        "point": ci26_90["point"], "lo": ci26_90["lo"], "hi": ci26_90["hi"],
        "n_paired": d26.n_paired,
        "detail": f"95% CI [{ci26_95['lo']:.4f}, {ci26_95['hi']:.4f}]；B2−B4 = "
                  f"{float(tm.set_index('arm').loc['B2', 'delta_vs_B4']):+.4f}",
    })

    emit("[7] H3 判定（差距局部化，主版 early = min(matchday_home, matchday_away) ≤ 6）")
    h3df = build_h3_frame()
    emit(f"    配对 {len(h3df):,} 场；两口径 early 标记不同的场次 "
         f"{int((h3df['matchday'] < h3df['matchday_home']).sum()):,}")
    h3c = h3_coefficients(h3df, w=6, B=10_000, seed=SEED)
    emit(f"    promoted {h3c['promoted']}")
    emit(f"    early    {h3c['early']}")
    h3v = h3_verdict(h3c["promoted"]["coef"], h3c["promoted"]["lo"], h3c["promoted"]["hi"],
                     h3c["early"]["coef"], h3c["early"]["lo"], h3c["early"]["hi"],
                     n_paired=h3c["n"])
    emit(f"    {h3v['decision']}  （{h3v['reason']}）")
    sens = h3_sensitivity(h3df, w=6, B=2_000, seed=SEED)
    sens.to_csv(LOGS / "h3_sensitivity.csv", index=False, encoding="utf-8")
    emit("    敏感性（描述性，B=2,000）：")
    emit(sens.round(4).to_string(index=False))
    emit("    sweep：" + h3_sweep(h3df).to_string(index=False))
    verdicts.append(_verdict_row("H3 promoted", h3v, h3c["promoted"]["coef"],
                                 f"early {h3c['early']['coef']:+.4f} "
                                 f"[{h3c['early']['lo']:+.4f},{h3c['early']['hi']:+.4f}]",
                                 lo=h3c["promoted"]["lo"], hi=h3c["promoted"]["hi"]))
    verdicts.append(_verdict_row("H3 early", h3v, h3c["early"]["coef"],
                                 f"promoted {h3c['promoted']['coef']:+.4f} "
                                 f"[{h3c['promoted']['lo']:+.4f},{h3c['promoted']['hi']:+.4f}]",
                                 lo=h3c["early"]["lo"], hi=h3c["early"]["hi"]))

    emit("[8] H4 判定（信息 vs 校准）")
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
    h4v = h4_verdict(float(rel.mean()), float(rlo), float(rhi), gap6["point"],
                     n_paired=d6.n_paired)
    emit(f"    gap_B6={gap6['point']:.4f}  gap_B6r={gap6r['point']:.4f}  "
         f"rel={rel.mean():.4f}  (90% [{rlo:.4f}, {rhi:.4f}])")
    emit(f"    {h4v['decision']}  （{h4v['reason']}）")
    verdicts.append(_verdict_row("H4 重校准相对变化", h4v, float(rel.mean())))

    orc = oracle_bound(_load("B4"), _load("B6"))
    pd.DataFrame([orc]).to_csv(LOGS / "h4_oracle_bound.csv", index=False, encoding="utf-8")
    emit(f"    oracle 上界（48 块各自用本块 test 标签拟合 c,d，含过拟合）："
         f"LL(B6) {orc['ll_B6']:.6f} → {orc['ll_B6r_oracle']:.6f}，"
         f"gap {orc['gap_B6']:.4f} → {orc['gap_oracle']:.4f}，rel={orc['rel']:+.2%}")
    emit(f"    （逐块 c ∈ [{orc['c_min']:.3f}, {orc['c_max']:.3f}]，"
         f"d ∈ [{orc['d_min']:+.3f}, {orc['d_max']:+.3f}]；这是「校准最多能解释多少」的上界）")

    emit("[9] C1 / C2 受控比较（B4↔B5a↔B5b）")
    for tag, a, b, vf in (("C1", "B5a", "B4", c1_verdict), ("C2", "B5b", "B5a", c2_verdict)):
        dlt = block_deltas(_load(a), _load(b))
        ci = cluster_bootstrap(dlt, B=10_000, alpha=0.10, seed=SEED)
        v = vf(ci["point"], ci["lo"], ci["hi"], n_paired=dlt.n_paired)
        emit(f"    {tag}: Δ = {ci['point']:+.4f}  90% [{ci['lo']:+.4f}, {ci['hi']:+.4f}]  "
             f"n={dlt.n_paired:,}  → {v['decision']}（{v['reason']}）")
        verdicts.append(_verdict_row(tag, v, ci["point"]))

    pd.DataFrame(verdicts).to_csv(LOGS / "m2_verdicts.csv", index=False, encoding="utf-8")
    emit(f"\n判定表：results/logs/m2_verdicts.csv（{len(verdicts)} 行）")
    # fig04 的标题里印着 C1/C2 的点估计与区间，必须从刚写的判定表读，不能手抄。
    plot_c_equivalence(pd.DataFrame(verdicts),
                       out_path=ROOT / "products" / "figures" / "fig04_c_equivalence.png")
    # fig08 此前没有生成脚本，于是 2026-11-24 之后图上三个数字全部过期（early −0.0108 /
    # H4 上界 0.011 / 点 0.0017）。接到出口后它和 fig03/fig04 一样跟着 CSV 走。
    plot_localisation_recal(pd.DataFrame(verdicts),
                            out_path=ROOT / "products" / "figures" / "fig08_localisation_recal.png")
    emit("图：fig03_arms.png（← table_main）、fig04_c_equivalence.png（← m2_verdicts）、"
         "fig08_localisation_recal.png（← h3_sensitivity / h4_oracle_bound / m2_verdicts）")

    log = LOGS / f"m2_decisions_{date.today()}.txt"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emit(f"判定日志：{log.relative_to(ROOT)}")


if __name__ == "__main__":
    run()
