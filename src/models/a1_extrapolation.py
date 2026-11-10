"""附录 A1-c · 把主场优势当常数的代价（M3 / T3.7，可选）。

做法：每个联赛用**严格早于 2024/25** 的比赛估一次参数（ξ=0.0019，与 A1-a 同口径），
α/β/μ **冻结**，只允许 γ 在 2024/25 赛内重估（一维寻优，in-sample 上界），然后比：
  - log loss：冻结 γ（"把主场优势当常数"）vs 当季重估 γ；
  - 方向：冻结的 γ 是偏高还是偏低，p_home 是系统性系统性地多报还是少报主胜。

判据（分工卡 §6 项 10）：偏差方向与 A1-a 的斜率方向一致 —— A1-a 是负斜率，
所以这里应当看到 γ_stale > γ_oracle、p_home 系统性偏高。**这是描述性核对，不是因果推断。**
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.a1_gamma import LEAGUES, XI_FIXED  # noqa: E402
from src.models.b3_poisson import (  # noqa: E402
    _team_params,
    fit as fit_poisson,
    load_panel,
    predict_proba,
)

TARGET_SEASON = "2024/25"


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    return float(-np.mean(np.log(p[np.arange(len(y)), y])))


def gamma_nll(model, test: pd.DataFrame, gamma: float) -> float:
    """固定 α/β/μ，只动 γ 的负对数似然（不含 L2，测试段不做收缩）。"""
    a_h, b_h = _team_params(model, test["home"])
    a_a, b_a = _team_params(model, test["away"])
    eta_h = np.clip(model.mu + gamma + a_h - b_a, -30, 30)
    eta_a = np.clip(model.mu + a_a - b_h, -30, 30)
    lam, nu = np.exp(eta_h), np.exp(eta_a)
    yh = test["FTHG"].to_numpy(float)
    ya = test["FTAG"].to_numpy(float)
    return float(np.sum(lam - yh * eta_h) + np.sum(nu - ya * eta_a))


def run(panel: pd.DataFrame, leagues: tuple[str, ...] = LEAGUES) -> pd.DataFrame:
    rows = []
    for lg in leagues:
        lg_all = panel.loc[panel["league"] == lg]
        test = lg_all.loc[lg_all["season"] == TARGET_SEASON].sort_values("date")
        if test.empty:
            print(f"  ! {lg} 无 {TARGET_SEASON}", flush=True)
            continue
        test_start = str(test["date"].min())
        train = lg_all.loc[lg_all["date"] < test_start]
        model = fit_poisson(train, xi=XI_FIXED, rho=0.0, ref_date=test_start)
        g_stale = float(model.gamma)

        opt = minimize_scalar(lambda g: gamma_nll(model, test, g),
                              bounds=(-1.5, 1.5), method="bounded")
        g_oracle = float(opt.x)
        model.gamma = g_oracle
        p_oracle = predict_proba(model, test)
        model.gamma = g_stale
        p_stale = predict_proba(model, test)

        y = test["y"].to_numpy(int)
        rows.append({
            "league": lg, "season": TARGET_SEASON, "test_start": test_start,
            "n_test": int(len(test)), "n_train": int(len(train)),
            "n_new_team": len((set(test["home"]) | set(test["away"]))
                              - (set(train["home"]) | set(train["away"]))),
            "gamma_stale": g_stale, "gamma_oracle": g_oracle,
            "dgamma": g_stale - g_oracle,
            "ll_stale": log_loss(p_stale, y),
            "ll_oracle": log_loss(p_oracle, y),
            "dll": log_loss(p_stale, y) - log_loss(p_oracle, y),
            "p_home_stale": float(p_stale[:, 0].mean()),
            "p_home_oracle": float(p_oracle[:, 0].mean()),
            "home_share_actual": float((y == 0).mean()),
        })
        r = rows[-1]
        print(f"  {lg}: γ {g_stale:.3f}→{g_oracle:.3f} ({r['dgamma']:+.3f})  "
              f"logloss {r['ll_stale']:.4f}→{r['ll_oracle']:.4f} "
              f"({r['dll']:+.4f})  p_home {r['p_home_stale']:.3f} vs "
              f"实际 {r['home_share_actual']:.3f}", flush=True)
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A1-c 固定参数外推 2024/25")
    a = ap.parse_args(argv)
    panel = load_panel()
    print("=" * 92)
    print(f"A1-c · 冻结 2024/25 之前的参数，只重估 γ · ξ={XI_FIXED}")
    print("-" * 92)
    d = run(panel)

    n = d["n_test"].to_numpy(float)
    ll_stale = float(np.sum(d["ll_stale"] * n) / n.sum())
    ll_or = float(np.sum(d["ll_oracle"] * n) / n.sum())
    print("-" * 92)
    print(f"{'league':<8}{'n':>6}{'γ_stale':>9}{'γ_oracle':>10}{'Δγ':>8}"
          f"{'Δlogloss':>10}{'p_home 偏':>11}")
    for _, r in d.iterrows():
        print(f"{r.league:<8}{r.n_test:>6d}{r.gamma_stale:>9.3f}{r.gamma_oracle:>10.3f}"
              f"{r.dgamma:>+8.3f}{r.dll:>+10.4f}"
              f"{r.p_home_stale - r.home_share_actual:>+11.3f}")
    print(f"{'pooled':<8}{int(n.sum()):>6d}{d.gamma_stale.mean():>9.3f}"
          f"{d.gamma_oracle.mean():>10.3f}{d.dgamma.mean():>+8.3f}"
          f"{ll_stale - ll_or:>+10.4f}"
          f"{(d.p_home_stale - d.home_share_actual).mean():>+11.3f}")
    up_g = int((d.dgamma > 0).sum())
    up_ll = int((d.dll > 0).sum())
    bias = float((d.p_home_stale - d.home_share_actual).mean())
    print(f"\n把 γ 当常数在 {up_ll}/6 个联赛里更差（Δlogloss>0），合并 {ll_stale - ll_or:+.4f} nats；")
    print(f"合并口径 γ_stale 偏高 {d.dgamma.mean():+.3f}、p_home 多报 {bias:+.3f} "
          f"→ 与 A1-a 的负斜率同向"
          if d.dgamma.mean() > 0 and bias > 0 else
          f"合并口径与 A1-a 的负斜率不同向")
    print(f"逐联赛 γ_stale 偏高 {up_g}/6 —— 2024/25 并非全线回落，"
          f"报告里必须写'趋势不是单调律'")
    print("口径提醒：γ_oracle 是在 α/β 冻结下的一维重估，会吸收球队强弱漂移，"
          "它衡量的是'这个 γ 值配这套 α/β 能多准'，不是干净的 HA 估计。")

    out = ROOT / "results" / "logs" / "a1_extrapolation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False, encoding="utf-8")
    print(f"已写入 {out.relative_to(ROOT)}（{len(d)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
