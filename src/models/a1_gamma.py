"""附录 A1-a · γ 的 22 季轨迹（M3 / T3.5）。

口径（写进报告前先定死，避免"看图选参数"）：
  - 每季一个 γ_s：用**该联赛截至该季结束**的全部比赛拟合（expanding，不是 8 折那种 8 个点）；
  - 时间衰减固定 ξ = 0.0019（一年半衰期）：22 个点必须用同一个平滑强度，否则趋势里会混进
    调参噪声；ξ 若按折各取一个值，点与点之间的变化就不再是"主场优势在变"；
  - **不挂 τ**：τ 需要逐季选 ρ，同样会把调参噪声渗进趋势；A1 是描述性附录，不是主推断；
  - 标准误取观测信息矩阵：nll 的解析 Hessian（Poisson 部分 + L2；ρ=0 时无 τ 项），
    对减参 θ 做 J'HJ 变换后取逆，这样 γ 的方差已经对"α/β 也估不准"做了边缘化。

趋势线用 WLS（权重 1/se²）报斜率 + 95% 区间，平滑曲线用 LOWESS 只作画图。
22 个点的窗口彼此重叠 ⇒ 误差相关，独立误差的 WLS 区间**偏保守**，报告里照实写。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.b3_poisson import (  # noqa: E402
    DEFAULT_L2,
    PoissonModel,
    decay_weights,
    fit as fit_poisson,
    load_panel,
)

LEAGUES: tuple[str, ...] = ("E0", "SP1", "I1", "D1", "F1", "N1")
XI_FIXED = 0.0019          # = ln2/365/1 年，见分工卡 §4 的 ξ↔半衰期表
Z95 = 1.959964


def hessian_theta(model: PoissonModel, train: pd.DataFrame, w: np.ndarray) -> np.ndarray:
    """nll 在减参 θ 上的解析 Hessian（2n+1 阶）。

    主场速率对 (α_h, β_a, μ, γ) 的符号是 (+1, −1, +1, +1)，客场速率对 (α_a, β_h, μ) 是
    (+1, −1, +1)；每个观测贡献 ``w·λ·v v'``（Poisson 的 log-lik 二阶导就是 −wλ）。
    """
    teams = model.teams
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    hi = train["home"].map(idx).to_numpy(int)
    ai = train["away"].map(idx).to_numpy(int)
    lam = np.exp(model.mu + model.gamma + model.alpha[hi] - model.beta[ai])
    nu = np.exp(model.mu + model.alpha[ai] - model.beta[hi])

    p_full = 2 * n + 2                      # [α(n), β(n), μ, γ]
    m = len(train)
    h = np.zeros((p_full, p_full))
    i_mu, i_ga = 2 * n, 2 * n + 1

    ih = np.stack([hi, n + ai, np.full(m, i_mu), np.full(m, i_ga)], axis=1)
    s_h = np.array([1.0, -1.0, 1.0, 1.0])
    np.add.at(h, (ih[:, :, None], ih[:, None, :]),
              (w * lam)[:, None, None] * np.outer(s_h, s_h)[None])

    ia = np.stack([ai, n + hi, np.full(m, i_mu)], axis=1)   # α_a 在 0..n−1，β_h 在 n..2n−1
    s_a = np.array([1.0, -1.0, 1.0])
    np.add.at(h, (ia[:, :, None], ia[:, None, :]),
              (w * nu)[:, None, None] * np.outer(s_a, s_a)[None])

    d = np.arange(n)
    h[d, d] += model.l2
    h[n + d, n + d] += model.l2

    k = 2 * n                             # θ = [α̃(n−1), β̃(n−1), μ, γ]
    j = np.zeros((p_full, k))
    j[: n - 1, : n - 1] = np.eye(n - 1)
    j[n - 1, : n - 1] = -1.0               # α_{n−1} = −Σα̃
    j[n: 2 * n - 1, n - 1: 2 * n - 2] = np.eye(n - 1)
    j[2 * n - 1, n - 1: 2 * n - 2] = -1.0  # β_{n−1} = −Σβ̃
    j[2 * n, 2 * n - 2] = 1.0
    j[2 * n + 1, 2 * n - 1] = 1.0
    return j.T @ h @ j


def fit_gamma(train: pd.DataFrame, ref_date: str, xi: float = XI_FIXED,
              l2: float = DEFAULT_L2) -> dict:
    """一季一点的 γ̂ 与 SE。``train`` 必须是"截至该季结束"的同联赛全部比赛。"""
    model = fit_poisson(train, xi=xi, rho=0.0, ref_date=ref_date, l2=l2)
    w = decay_weights(train["date"], ref_date, xi)
    h = hessian_theta(model, train, w)
    cov = np.linalg.inv(h)
    k = 2 * len(model.teams)
    se = float(np.sqrt(cov[k - 1, k - 1]))
    return {"gamma": float(model.gamma), "se": se, "mu": float(model.mu),
            "n_train": int(len(train)), "n_teams": int(len(model.teams)),
            "converged": bool(model.converged), "n_iter": int(model.n_iter)}


def gamma_series(panel: pd.DataFrame, leagues: tuple[str, ...] = LEAGUES,
                 xi: float = XI_FIXED, verbose: bool = True) -> pd.DataFrame:
    seasons = sorted(panel["season"].unique())
    rows = []
    for lg in leagues:
        lg_all = panel.loc[panel["league"] == lg]
        for s in seasons:
            train = lg_all.loc[lg_all["season"] <= s]
            if train.empty:
                continue
            # 参考日 = 该季最后一场（这就是"截至该季结束"的时点）
            ref = str(train.loc[train["season"] == s, "date"].max())
            r = fit_gamma(train, ref, xi=xi)
            rows.append({"league": lg, "season": s, "ref_date": ref, **r})
        if verbose:
            sub = pd.DataFrame([x for x in rows if x["league"] == lg])
            print(f"  {lg}: {len(sub)} 季，γ {sub.gamma.min():.3f}–{sub.gamma.max():.3f}", flush=True)
    return pd.DataFrame(rows)


def to_wide(long: pd.DataFrame) -> pd.DataFrame:
    """22 行 × (6 联赛 γ + se) + 逆方差合并的 pooled，供 M5 直接画图。"""
    wide = pd.DataFrame({"season": sorted(long["season"].unique())})
    for lg in LEAGUES:
        sub = long.loc[long["league"] == lg].set_index("season")
        wide[f"gamma_{lg}"] = wide["season"].map(sub["gamma"])
        wide[f"se_{lg}"] = wide["season"].map(sub["se"])
    w = np.stack([1.0 / wide[f"se_{lg}"].to_numpy() ** 2 for lg in LEAGUES], axis=1)
    g = np.stack([wide[f"gamma_{lg}"].to_numpy() for lg in LEAGUES], axis=1)
    wide["gamma_pooled"] = (w * g).sum(axis=1) / w.sum(axis=1)
    wide["se_pooled"] = np.sqrt(1.0 / w.sum(axis=1))
    n = long.groupby("season")["n_train"].sum()
    wide["n_matches_cumulative"] = wide["season"].map(n)
    return wide


def trend(wide: pd.DataFrame, col: str = "gamma_pooled", se_col: str = "se_pooled") -> dict:
    """WLS γ ~ 年份；返回每年 / 每十年的斜率与 95% 区间。"""
    y = wide[col].to_numpy(float)
    se = wide[se_col].to_numpy(float)
    t = np.arange(len(y), dtype=float)                     # 0 = 首个赛季
    x = np.column_stack([np.ones_like(t), t])
    wt = 1.0 / se ** 2
    xtwx_inv = np.linalg.inv(x.T @ (wt[:, None] * x))
    beta = xtwx_inv @ (x.T @ (wt * y))
    cov = xtwx_inv                                          # se 视为已知
    slope = float(beta[1])
    s = float(np.sqrt(cov[1, 1]))
    return {"slope_per_year": slope, "se": s,
            "lo95": slope - Z95 * s, "hi95": slope + Z95 * s,
            "slope_per_decade": slope * 10,
            "lo95_decade": (slope - Z95 * s) * 10,
            "hi95_decade": (slope + Z95 * s) * 10,
            "first": float(y[0]), "last": float(y[-1])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A1-a γ 22 季轨迹")
    ap.add_argument("--xi", type=float, default=XI_FIXED)
    ap.add_argument("--leagues", default=None, help="逗号分隔，默认六联赛")
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)

    leagues = tuple(a.leagues.split(",")) if a.leagues else LEAGUES
    panel = load_panel()
    print("=" * 78)
    print(f"A1-a · γ 逐季轨迹 · ξ={a.xi}（半衰期 {np.log(2)/a.xi/365:.2f} 年）· 不挂 τ")
    print("-" * 78)
    long = gamma_series(panel, leagues, xi=a.xi)

    wide = to_wide(long) if leagues == LEAGUES else None
    out_dir = ROOT / "results" / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    if wide is not None:
        p = out_dir / "gamma_by_season.csv"
        wide.to_csv(p, index=False, encoding="utf-8")
        print(f"\n已写入 {p.relative_to(ROOT)}（{len(wide)} 行）")

    print("-" * 78)
    print(f"{'league':<8}{'slope/yr':>10}{'95% CI':>22}{'γ首→末':>18}{'同向?':>8}")
    signs = []
    for lg in leagues:
        col, sec = (f"gamma_{lg}", f"se_{lg}") if wide is not None else ("gamma", "se")
        d = wide if wide is not None else long.loc[long["league"] == lg]
        tr = trend(d, col, sec)
        signs.append(tr["slope_per_year"] < 0)
        print(f"{lg:<8}{tr['slope_per_year']:>10.5f}"
              f"[{tr['lo95']:>8.5f}, {tr['hi95']:>8.5f}]"
              f"{tr['first']:>9.3f}→{tr['last']:<8.3f}"
              f"{'是' if tr['slope_per_year'] < 0 else '否':>6}")
    if wide is not None:
        tr = trend(wide)
        print(f"{'pooled':<8}{tr['slope_per_year']:>10.5f}"
              f"[{tr['lo95']:>8.5f}, {tr['hi95']:>8.5f}]"
              f"{tr['first']:>9.3f}→{tr['last']:<8.3f}"
              f"{'是' if tr['slope_per_year'] < 0 else '否':>6}")
        print(f"\n合并口径：每十年 {tr['slope_per_decade']:.3f} "
              f"[{tr['lo95_decade']:.3f}, {tr['hi95_decade']:.3f}]；"
              f"六联赛同向 {'是' if all(signs) else '否'}")

    if not a.no_figure and wide is not None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from statsmodels.nonparametric.smoothers_lowess import lowess

        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(wide))
        for lg in LEAGUES:
            ax.plot(x, wide[f"gamma_{lg}"], lw=0.9, alpha=0.5, label=lg)
        ax.errorbar(x, wide["gamma_pooled"], yerr=1.96 * wide["se_pooled"],
                    fmt="o", ms=3, lw=1.2, color="black", label="pooled")
        sm = lowess(wide["gamma_pooled"], x, frac=0.45)
        ax.plot(sm[:, 0], sm[:, 1], color="crimson", lw=2, label="lowess")
        ax.set_xticks(x[::2])
        ax.set_xticklabels(wide["season"][::2], rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("home advantage γ (log scale)")
        ax.set_title("A1-a  Home advantage by season (expanding, ξ=0.0019)")
        ax.legend(ncol=4, fontsize=8)
        fig.tight_layout()
        fig_dir = ROOT / "products" / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)
        fp = fig_dir / "fig_a1_gamma.png"
        fig.savefig(fp, dpi=150)
        print(f"图已写入 {fp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
