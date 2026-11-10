"""B4 · Dixon–Coles（M3 / T3.2）：B3 + 时间衰减权重 + 低比分 τ 修正。

两个补丁只在 ``b3_poisson`` 的同一个似然里生效，所以 ρ=0 且 ξ=0 时它**就是** B3——
这不是"凑"出来的等价，而是同一个目标函数在参数取端点时的同一组解（退化检验见
``python -m src.models.b4_dixon_coles --degeneracy``）。

    w_t = exp(−ξ·Δ天)                      Δ 以该折 test_start 为参考日；按均值归一到 1
    τ(0,0)=1−λμρ, τ(0,1)=1+λρ, τ(1,0)=1+μρ, τ(1,1)=1−ρ，其余格子 =1

τ 会在四个格子上改变总概率质量，所以比分矩阵乘完 τ 必须**重新归一化**再汇总成
主/平/客——漏了这一步，三概率之和会偏离 1（偏差约 ρ 量级）。
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
    fit as fit_poisson,
    load_panel,
    predict_proba,
    score_matrix,
)

XI_GRID: tuple[float, ...] = (0.0005, 0.0010, 0.0019, 0.0030, 0.0050, 0.0080)
RHO_GRID: tuple[float, ...] = (-0.15, -0.05, 0.0, 0.05, 0.15)
MODEL_NAME = "B4"


def half_life_years(xi: float) -> float:
    """``ln2 / ξ / 365``；分工卡 §4 那张表就是按这个算的，不要另推。"""
    return float("inf") if xi == 0 else float(np.log(2) / xi / 365)


def fit(train: pd.DataFrame, *, xi: float, rho: float, ref_date: str | None = None,
        sample_weight: np.ndarray | None = None, l2: float = DEFAULT_L2,
        init: dict | None = None) -> PoissonModel:
    """B4 的一折拟合。参数合法性与收敛信息都留在返回对象里，供 convergence.csv。"""
    if xi < 0 or rho <= -1.0 or rho >= 1.0:
        raise ValueError(f"非法超参：xi={xi}, rho={rho}")
    model = fit_poisson(train, xi=xi, rho=rho, ref_date=ref_date,
                        sample_weight=sample_weight, l2=l2, init=init)
    model.extra["model"] = MODEL_NAME
    model.extra["half_life_years"] = half_life_years(xi)
    return model


def log_loss(proba: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(proba[np.arange(len(y)), y], 1e-15, 1.0)
    return float(-np.mean(np.log(p)))


def degeneracy_check(season: str = "2010/11", league: str = "E0",
                     atol: float = 1e-6) -> dict:
    """验收项 2：ρ=0 且 w≡1 时 B4 与 B3 在 1e-6 内一致；动超参必须真的改变结果。"""
    panel = load_panel()
    sub = panel.loc[(panel["league"] == league) & (panel["season"] == season)]
    ref = str(sub["date"].max())

    b3 = fit_poisson(sub, ref_date=ref)
    b4_same = fit(sub, xi=0.0, rho=0.0, ref_date=ref)
    b4_decay = fit(sub, xi=0.0030, rho=-0.05, ref_date=ref)

    p3 = predict_proba(b3, sub)
    p4 = predict_proba(b4_same, sub)
    p4d = predict_proba(b4_decay, sub)

    same_par = (np.allclose(b3.alpha, b4_same.alpha, atol=atol, rtol=0)
                and np.allclose(b3.beta, b4_same.beta, atol=atol, rtol=0)
                and abs(b3.mu - b4_same.mu) <= atol
                and abs(b3.gamma - b4_same.gamma) <= atol)
    same_prob = np.max(np.abs(p3 - p4)) <= atol
    # 退化保证不能掩盖"补丁根本没接上"：动 ξ/ρ 后参数必须明显不同
    patch_wired = (np.max(np.abs(b3.alpha - b4_decay.alpha)) > 1e-3
                   and np.max(np.abs(p3 - p4d)) > 1e-3)

    # 独立复算：直接按定义逐个比分格算 pmf，核对 score_matrix 的 τ 与归一化
    pmat = score_matrix(b4_decay, sub["home"].iloc[:3], sub["away"].iloc[:3])
    lam = np.exp(b4_decay.mu + b4_decay.gamma
                 + b4_decay.alpha[[b4_decay.teams.index(t) for t in sub["home"].iloc[:3]]]
                 - b4_decay.beta[[b4_decay.teams.index(t) for t in sub["away"].iloc[:3]]])
    nu = np.exp(b4_decay.mu
                + b4_decay.alpha[[b4_decay.teams.index(t) for t in sub["away"].iloc[:3]]]
                - b4_decay.beta[[b4_decay.teams.index(t) for t in sub["home"].iloc[:3]]])
    brute = np.zeros_like(pmat)
    rho = b4_decay.rho
    from math import exp, factorial
    for m in range(pmat.shape[0]):
        for i in range(pmat.shape[1]):
            for j in range(pmat.shape[2]):
                v = exp(-lam[m]) * lam[m] ** i / factorial(i) \
                    * exp(-nu[m]) * nu[m] ** j / factorial(j)
                if (i, j) == (0, 0):
                    v *= 1 - lam[m] * nu[m] * rho
                elif (i, j) == (0, 1):
                    v *= 1 + lam[m] * rho
                elif (i, j) == (1, 0):
                    v *= 1 + nu[m] * rho
                elif (i, j) == (1, 1):
                    v *= 1 - rho
                brute[m, i, j] = v
        brute[m] /= brute[m].sum()
    tau_ok = np.max(np.abs(brute - pmat)) < 1e-10

    return {"same_params": bool(same_par), "same_proba": bool(same_prob),
            "patch_wired": bool(patch_wired), "tau_matches_bruteforce": bool(tau_ok),
            "max_param_diff": float(np.max(np.abs(b3.alpha - b4_same.alpha))),
            "max_prob_diff": float(np.max(np.abs(p3 - p4))),
            "decay_param_diff": float(np.max(np.abs(b3.alpha - b4_decay.alpha))),
            "logloss_b3": log_loss(p3, sub["y"].to_numpy()),
            "logloss_b4": log_loss(p4d, sub["y"].to_numpy()),
            "b3": b3, "b4": b4_decay}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B4 Dixon–Coles 退化检验")
    ap.add_argument("--degeneracy", action="store_true")
    ap.add_argument("--league", default="E0")
    ap.add_argument("--season", default="2010/11")
    a = ap.parse_args(argv)

    out = degeneracy_check(a.season, a.league)
    print("=" * 72)
    print(f"B4 退化检验 · {a.league} {a.season}")
    print("-" * 72)
    print(f"[{'PASS' if out['same_params'] else 'FAIL'}] B4(ξ=0,ρ=0) ≡ B3：参数最大差 "
          f"{out['max_param_diff']:.2e}")
    print(f"[{'PASS' if out['same_proba'] else 'FAIL'}] 预测概率最大差 "
          f"{out['max_prob_diff']:.2e}")
    print(f"[{'PASS' if out['patch_wired'] else 'FAIL'}] 补丁已接线：ξ=0.003, ρ=−0.05 时 "
          f"α 最大移动 {out['decay_param_diff']:.3f}")
    print(f"[{'PASS' if out['tau_matches_bruteforce'] else 'FAIL'}] τ 与逐格暴力复算一致")
    b4: PoissonModel = out["b4"]
    print("-" * 72)
    print(f"样本内 log loss  B3 {out['logloss_b3']:.4f} → "
          f"B4(ξ={b4.xi}, ρ={b4.rho}) {out['logloss_b4']:.4f}")
    print(f"B4 收敛 {b4.converged} · {b4.n_iter} 次迭代 · γ={b4.gamma:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
