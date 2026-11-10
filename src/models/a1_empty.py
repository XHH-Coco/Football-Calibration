"""附录 A1-b · 空场期对照（M3 / T3.6）。

口径：
  - **按日期切窗，不按赛季切**。2019/20 是赛季中途断的（2020-03 停摆、2020-06 复赛），
    按赛季整块切会把"有观众的上半季"和"空场的下半季"混进同一个数；
  - 三个窗：pre = 2018-08-01 → 2020-06-01（2018/19 + 2019/20 停摆前），
    empty = 2020-06-01 → 2021-08-01（复赛 + 整个 2020/21），
    post = 2021-08-01 → 2023-07-01（2021/22 + 2022/23）；
  - 窗内拟合：只用该窗内的比赛，ξ=0（窗口本身就是时间切片，再叠衰减等于在窗内又挑近的），
    不挂 τ（A1 是描述性附录）；
  - 每联赛单独拟合再逆方差合并：六个联赛之间没有交叉比赛，拼在一起拟合会让 μ/γ 的
    可识别性依赖"各联赛水平相同"这个不成立的假设；
  - 窗与窗之间没有共同比赛，因此差值的 SE 取 sqrt(se_a²+se_b²)（近似独立）。

**只作描述性对照，不称自然实验**：空场期同时有赛季腰斩、赛程压缩、换人规则变化。
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

from src.models.a1_gamma import LEAGUES, Z95, fit_gamma, to_wide, gamma_series  # noqa: E402
from src.models.b3_poisson import load_panel  # noqa: E402

WINDOWS: tuple[tuple[str, str, str], ...] = (
    ("pre",   "2018-08-01", "2020-06-01"),
    ("empty", "2020-06-01", "2021-08-01"),
    ("post",  "2021-08-01", "2023-07-01"),
)


def select_window(panel: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """半开区间 [start, end)，只看日期，不看 season 标签（2019/20 是赛季中途断的）。"""
    return panel.loc[(panel["date"] >= start) & (panel["date"] < end)]


def window_fit(panel: pd.DataFrame, start: str, end: str,
               leagues: tuple[str, ...] = LEAGUES) -> pd.DataFrame:
    """一个窗 × 六联赛的 γ̂。窗内无比赛的联赛跳过（不该发生，发生了要看见）。"""
    rows = []
    for lg in leagues:
        sub = select_window(panel.loc[panel["league"] == lg], start, end)
        if sub.empty:
            print(f"  ! {lg} 在 {start}–{end} 无比赛", flush=True)
            continue
        r = fit_gamma(sub, ref_date=str(sub["date"].max()), xi=0.0)
        rows.append({"league": lg, "start": start, "end": end,
                     "n_matches": int(len(sub)), "n_seasons": int(sub["season"].nunique()),
                     **r})
    return pd.DataFrame(rows)


def pooled(d: pd.DataFrame) -> dict:
    w = 1.0 / d["se"].to_numpy(float) ** 2
    g = d["gamma"].to_numpy(float)
    return {"gamma": float((w * g).sum() / w.sum()),
            "se": float(np.sqrt(1.0 / w.sum())),
            "n_matches": int(d["n_matches"].sum()),
            "n_leagues": int(len(d)),
            "n_converged": int(d["converged"].sum())}


def compare(win: dict[str, dict]) -> list[dict]:
    out = []
    e = win["empty"]
    for other in ("pre", "post"):
        o = win[other]
        diff = e["gamma"] - o["gamma"]
        se = float(np.sqrt(e["se"] ** 2 + o["se"] ** 2))
        out.append({"contrast": f"empty − {other}", "diff": diff, "se": se,
                    "lo95": diff - Z95 * se, "hi95": diff + Z95 * se,
                    "pct": float(np.exp(diff) - 1)})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="A1-b 空场期 γ 对照（按日期切窗）")
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)

    panel = load_panel()
    print("=" * 84)
    print("A1-b · 空场期对照 · 按日期切窗 · 窗内 ξ=0 · 不挂 τ")
    print("-" * 84)
    for name, s, e in WINDOWS:
        print(f"  {name:<6}{s} → {e}")

    frames = []
    for name, s, e in WINDOWS:
        d = window_fit(panel, s, e)
        d.insert(0, "window", name)
        frames.append(d)
    long = pd.concat(frames, ignore_index=True)

    win: dict[str, dict] = {}
    print("-" * 84)
    print(f"{'window':<8}{'lg':<6}{'γ':>8}{'se':>8}{'n':>8}{'n赛季':>7}")
    for name, _, _ in WINDOWS:
        d = long.loc[long["window"] == name]
        for _, r in d.iterrows():
            print(f"{name:<8}{r.league:<6}{r.gamma:>8.3f}{r.se:>8.3f}"
                  f"{r.n_matches:>8d}{r.n_seasons:>7d}")
        win[name] = pooled(d)
        p = win[name]
        print(f"{name:<8}{'pooled':<6}{p['gamma']:>8.3f}{p['se']:>8.3f}"
              f"{p['n_matches']:>8d}   ← {p['n_leagues']}/6 联赛, "
              f"收敛 {p['n_converged']}/{p['n_leagues']}")

    print("-" * 84)
    print(f"{'window':<8}{'pooled γ':>10}{'95% CI':>22}{'主场加成':>12}")
    for name, _, _ in WINDOWS:
        p = win[name]
        print(f"{name:<8}{p['gamma']:>10.4f}"
              f"[{p['gamma'] - Z95 * p['se']:>8.4f}, {p['gamma'] + Z95 * p['se']:>8.4f}]"
              f"{np.exp(p['gamma']) - 1:>11.1%}")

    print("-" * 84)
    print(f"{'contrast':<18}{'Δγ':>9}{'95% CI':>22}{'p':>9}{'等价概率变化':>13}")
    from math import erf
    for c in compare(win):
        z = c["diff"] / c["se"]
        p = 2 * (1 - 0.5 * (1 + erf(abs(z) / np.sqrt(2))))
        print(f"{c['contrast']:<18}{c['diff']:>9.4f}"
              f"[{c['lo95']:>8.4f}, {c['hi95']:>8.4f}]"
              f"{p:>9.2e}{c['pct']:>12.1%}")

    # 逐联赛看方向，防止"合并显著"掩盖某个联赛反向
    print("-" * 84)
    piv = long.pivot_table(index="league", columns="window", values="gamma", sort=False)
    piv["empty−pre"] = piv["empty"] - piv["pre"]
    piv["empty−post"] = piv["empty"] - piv["post"]
    piv = piv.loc[list(LEAGUES)]
    print(piv.round(3).to_string())
    both = int(((piv["empty−pre"] < 0) & (piv["empty−post"] < 0)).sum())
    print(f"两个对照都为负的联赛：{both}/6")

    # "幅度大于普通赛季波动"：取不含空场跃迁的逐年变化，与 Δempty 比
    wide = to_wide(gamma_series(panel, verbose=False))
    d = wide["gamma_pooled"].diff()
    normal = d.drop(index=[17, 18]).dropna()          # 去掉 19/20→20/21、20/21→21/22 两跳
    print(f"普通逐年波动 SD = {normal.std():.4f}（{len(normal)} 个跳变）"
          f"，空场 Δ = {win['empty']['gamma'] - win['pre']['gamma']:+.4f}"
          f" = {abs(win['empty']['gamma'] - win['pre']['gamma']) / normal.std():.1f} 倍 SD")

    out_dir = ROOT / "results" / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "gamma_empty_window.csv"
    out = long[["window", "league", "start", "end", "gamma", "se", "mu",
                "n_matches", "n_seasons", "n_teams", "converged", "n_iter"]]
    out.to_csv(p, index=False, encoding="utf-8")
    print(f"\n已写入 {p.relative_to(ROOT)}（{len(out)} 行）")

    if not a.no_figure:
        draw(wide, win, long)
    return 0


def draw(wide: pd.DataFrame, win: dict[str, dict], long: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.arange(len(wide))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 5),
                                  gridspec_kw={"width_ratios": [2.2, 1]})
    for lg in LEAGUES:
        ax.plot(x, wide[f"gamma_{lg}"], lw=0.9, alpha=0.45, label=lg)
    ax.errorbar(x, wide["gamma_pooled"], yerr=1.96 * wide["se_pooled"],
                fmt="o", ms=3, lw=1.2, color="black", label="pooled")
    ax.axvspan(16.9, 18.0, color="grey", alpha=0.22, lw=0)
    ax.text(17.45, ax.get_ylim()[1] * 0.985, "empty\nstadiums", ha="center",
            va="top", fontsize=8, color="dimgrey")
    ax.set_xticks(x[::2])
    ax.set_xticklabels(wide["season"][::2], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("home advantage γ (log scale)")
    ax.set_title("A1-b  γ by season, empty-stadium window shaded")
    ax.legend(ncol=4, fontsize=8, loc="lower left")

    names = [w[0] for w in WINDOWS]
    g = [win[n]["gamma"] for n in names]
    se = [win[n]["se"] for n in names]
    ax2.errorbar(np.arange(3), g, yerr=1.96 * np.array(se), fmt="o",
                 color="black", ms=5, lw=1.5, capsize=4, zorder=3)
    for lg in LEAGUES:
        sub = long.loc[long["league"] == lg].set_index("window").loc[names]
        ax2.plot(np.arange(3), sub["gamma"], "o", ms=3, alpha=0.5, color="grey")
    ax2.set_xticks(np.arange(3))
    ax2.set_xticklabels(["pre\n2018/19–19/20", "empty\n2020-06→21/22",
                         "post\n2021/22–22/23"], fontsize=8)
    ax2.set_ylabel("γ (window fit)")
    ax2.set_title("window means, 95% CI")
    ax2.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig_dir = ROOT / "products" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fp = fig_dir / "fig_a1_empty_stadium.png"
    fig.savefig(fp, dpi=150)
    print(f"图已写入 {fp.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
