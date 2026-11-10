"""B3 · 独立 Poisson 进球模型（M3 / T3.1），也是 B4 的似然核心。

    log λ_home = μ + γ + α_home − β_away
    log λ_away = μ + α_away − β_home,   约束 Σα = 0 **且** Σβ = 0

B4 = 本文件 + 时间衰减权重 + Dixon–Coles τ（``b4_dixon_coles.py`` 只加两个补丁，
退化检验要求 ρ=0 且 w≡1 时两者输出在 1e-6 内一致）。

三条不显然的约定：
  1. **权重按均值归一到 1**（``sum(w) == n``）。纯似然对整体缩放不敏感，但 L2 收缩项
     不随权重缩放，不归一会让 ξ 越大等价于收缩越强，把"衰减"和"正则化"混进同一个网格。
  2. **新队映射到 α=β=0**（联赛平均）。test 里出现、train 里不存在的队（升班马，实测每块
     ≤ 2 支）没有可估的历史；返回对象里记 ``n_new_team`` 供日志核对，不静默吞掉。
  3. **两条约束都用"减参"实现**（最后一队的 α、β = −其余之和），不是罚项——罚项只能让和
     "接近"0，解仍不唯一。只约束 Σα=0 也不够：(α+c, β+c) 和 (β+2c, μ+2c) 两个方向都不改变
     任何 λ，一条约束只切掉一个，剩下的那条会让 Hessian 近奇异、γ 的标准误虚高几十倍。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_L2 = 1.0          # 对 α/β 的 L2 收缩强度；等价于给每队加 1 场"联赛平均"的伪观测
MAX_GOALS = 12            # 比分截断；λ 最大约 5 时 12 球的尾部质量 < 1e-7
_ETA_CLIP = 30.0


@dataclass
class PoissonModel:
    """一次拟合的全部结果。``warm`` 可直接作为下一折 ``fit(init=...)`` 的初值。"""

    teams: tuple[str, ...]
    alpha: np.ndarray
    beta: np.ndarray
    mu: float
    gamma: float
    xi: float = 0.0
    rho: float = 0.0
    ref_date: str | None = None
    l2: float = DEFAULT_L2
    converged: bool = True
    n_iter: int = 0
    grad_norm: float = float("nan")
    nll: float = float("nan")
    n_matches: int = 0
    n_new_team: int = 0
    elapsed_s: float = float("nan")
    extra: dict = field(default_factory=dict)

    @property
    def warm(self) -> dict[str, np.ndarray | float]:
        """下一折的 warm start（按队名对齐，不能按位置）。"""
        return {"teams": self.teams, "alpha": self.alpha, "beta": self.beta,
                "mu": self.mu, "gamma": self.gamma}


def load_panel(path: str | Path | None = None) -> pd.DataFrame:
    """读 ``data/processed/panel.parquet``；不存在则从 132 个 raw 现场重建。"""
    p = Path(path) if path is not None else ROOT / "data" / "processed" / "panel.parquet"
    if p.exists():
        return pd.read_parquet(p)
    from src.build_panel import build_panel
    return build_panel()


def decay_weights(dates: pd.Series, ref_date: str, xi: float) -> np.ndarray:
    """``w = exp(−ξ·Δ天)``，按均值归一到 1；ξ=0 时恒等于 1。

    参考日取 ``ref_date``（外层折用该块 ``test_start``）。它对结果无影响——所有 Δ 同时平移
    常数相当于整体乘一个常数，对 argmax 不改变——写进来只是为了让权重有可解释的量纲。
    """
    d = pd.to_datetime(dates).to_numpy(dtype="datetime64[D]").astype(np.int64)
    ref = np.datetime64(pd.Timestamp(ref_date), "D").astype(np.int64)
    if xi == 0.0:
        return np.ones(len(d), dtype=float)
    w = np.exp(-xi * (ref - d).astype(float))
    return w / w.mean()


def _design(train: pd.DataFrame, teams: tuple[str, ...]
            ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """主/客队下标 + 两队进球数；未知队返回 −1（预测时按 α=β=0 处理）。"""
    idx = {t: i for i, t in enumerate(teams)}
    hi = train["home"].map(idx).fillna(-1).to_numpy(dtype=np.int64)
    ai = train["away"].map(idx).fillna(-1).to_numpy(dtype=np.int64)
    if (hi < 0).any() or (ai < 0).any():
        raise ValueError("训练集里出现未登记队名，teams 应由同一批 train 生成")
    return hi, ai, train["FTHG"].to_numpy(float), train["FTAG"].to_numpy(float)


def _tau(lam: np.ndarray, nu: np.ndarray, yh: np.ndarray, ya: np.ndarray,
         rho: float) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Dixon–Coles τ 只改 0-0 / 1-0 / 0-1 / 1-1 四格，返回 (logτ, ∂logτ/∂η_h, ∂logτ/∂η_a)。

    ∂logτ/∂η 与 ∂logτ/∂logλ 相同（η=logλ），所以可以直接并进 Poisson 部分的梯度。
    任一 τ ≤ 0 时返回 None，由调用方给一个很大的惩罚值。
    """
    n = lam.shape[0]
    lt, dh, dz = np.zeros(n), np.zeros(n), np.zeros(n)
    if rho == 0.0:
        return lt, dh, dz

    m00 = (yh == 0) & (ya == 0)
    m01 = (yh == 0) & (ya == 1)
    m10 = (yh == 1) & (ya == 0)
    m11 = (yh == 1) & (ya == 1)

    if m00.any():
        a = lam[m00] * nu[m00] * rho
        t = 1.0 - a
        if (t <= 0).any():
            return None
        lt[m00] = np.log(t)
        dh[m00] = -a / t
        dz[m00] = -a / t
    if m01.any():
        t = 1.0 + lam[m01] * rho
        if (t <= 0).any():
            return None
        lt[m01] = np.log(t)
        dh[m01] = lam[m01] * rho / t
    if m10.any():
        t = 1.0 + nu[m10] * rho
        if (t <= 0).any():
            return None
        lt[m10] = np.log(t)
        dz[m10] = nu[m10] * rho / t
    if m11.any():
        t = 1.0 - rho
        if t <= 0:
            return None
        lt[m11] = np.log(t)
    return lt, dh, dz


def _unpack(theta: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray, float, float]:
    a_free = theta[: n - 1]
    b_free = theta[n - 1: 2 * n - 2]
    alpha = np.empty(n)
    beta = np.empty(n)
    alpha[:-1] = a_free
    alpha[-1] = -a_free.sum()
    beta[:-1] = b_free
    beta[-1] = -b_free.sum()
    return alpha, beta, float(theta[2 * n - 2]), float(theta[2 * n - 1])


def _nll_grad(theta: np.ndarray, hi, ai, yh, ya, w, rho, l2, n,
              return_grad: bool = True):
    alpha, beta, mu, gamma = _unpack(theta, n)
    eta_h = np.clip(mu + gamma + alpha[hi] - beta[ai], -_ETA_CLIP, _ETA_CLIP)
    eta_a = np.clip(mu + alpha[ai] - beta[hi], -_ETA_CLIP, _ETA_CLIP)
    lam, nu = np.exp(eta_h), np.exp(eta_a)

    tau = _tau(lam, nu, yh, ya, rho)
    if tau is None:
        return (1e12, np.zeros_like(theta)) if return_grad else 1e12
    log_tau, dtau_h, dtau_a = tau

    # 丢掉了 log(y!) 常数项：不影响 argmax，nll 只在同一折内部可比。
    nll = -(np.sum(w * (yh * eta_h - lam)) + np.sum(w * (ya * eta_a - nu))
            + np.sum(w * log_tau))
    nll += 0.5 * l2 * (alpha @ alpha + beta @ beta)

    if not return_grad:
        return nll

    g_h = w * (yh - lam) + w * dtau_h
    g_a = w * (ya - nu) + w * dtau_a

    ga = np.bincount(hi, weights=g_h, minlength=n) + \
        np.bincount(ai, weights=g_a, minlength=n) - l2 * alpha
    gb = -np.bincount(ai, weights=g_h, minlength=n) - \
        np.bincount(hi, weights=g_a, minlength=n) - l2 * beta

    grad = np.empty_like(theta)
    # 两条减参链式：α̃_j = α_j，α_{n-1} = −Σα̃；β 同理。
    # 只加 Σα=0 是不够的——(α+c, β+c) 与 (β+2c, μ+2c) 两个方向都不改变任何 λ，
    # Σα=0 只切掉其中一个，剩下的那条会让 Hessian 近奇异、把 γ 的标准误放大几十倍。
    grad[: n - 1] = ga[:-1] - ga[-1]
    grad[n - 1: 2 * n - 2] = gb[:-1] - gb[-1]
    grad[2 * n - 2] = np.sum(g_h + g_a)
    grad[2 * n - 1] = np.sum(g_h)
    return nll, -grad          # 上面组装的是 ∂logL/∂θ，返回目标函数 nll 的梯度


def _init_theta(train: pd.DataFrame, teams: tuple[str, ...],
                init: dict | None) -> np.ndarray:
    n = len(teams)
    theta = np.zeros(2 * n)
    if init is not None:
        pos = {t: i for i, t in enumerate(init["teams"])}
        alpha = np.zeros(n)
        beta = np.zeros(n)
        for j, t in enumerate(teams):
            if t in pos:
                alpha[j] = init["alpha"][pos[t]]
                beta[j] = init["beta"][pos[t]]
        alpha -= alpha.mean()          # 初值也要落在两条约束面上
        beta -= beta.mean()
        theta[: n - 1] = alpha[: n - 1]
        theta[n - 1: 2 * n - 2] = beta[: n - 1]
        theta[2 * n - 2] = init["mu"]
        theta[2 * n - 1] = init["gamma"]
        return theta

    home_mean = (train["FTHG"].sum() + train["FTAG"].sum()) / (2 * len(train))
    mu0 = np.log(max(home_mean, 1e-3))
    theta[2 * n - 2] = mu0
    theta[2 * n - 1] = np.log(max(train["FTHG"].mean(), 1e-3) / max(train["FTAG"].mean(), 1e-3))
    return theta


def fit(train: pd.DataFrame, *, xi: float = 0.0, rho: float = 0.0,
        ref_date: str | None = None, sample_weight: np.ndarray | None = None,
        l2: float = DEFAULT_L2, init: dict | None = None,
        maxiter: int = 500, tol: float = 1e-9) -> PoissonModel:
    """加权极大似然。``xi=0, rho=0`` 即 B3；B4 由 ``b4_dixon_coles.py`` 调用同一函数。"""
    import time
    t0 = time.perf_counter()

    teams = tuple(sorted(set(train["home"]) | set(train["away"])))
    n = len(teams)
    if n < 2 or len(train) < 2 * n:
        raise ValueError(f"样本太少，无法估 {n} 支队: n_matches={len(train)}")

    hi, ai, yh, ya = _design(train, teams)
    w = decay_weights(train["date"], ref_date or str(train["date"].max()), xi)
    if sample_weight is not None:
        sw = np.asarray(sample_weight, dtype=float)
        w = w * sw
        w = w / w.mean()

    theta = _init_theta(train, teams, init)
    res = minimize(_nll_grad, theta, args=(hi, ai, yh, ya, w, rho, l2, n),
                   jac=True, method="L-BFGS-B",
                   options={"maxiter": maxiter, "ftol": tol, "gtol": 1e-7})

    alpha, beta, mu, gamma = _unpack(res.x, n)
    model = PoissonModel(
        teams=teams, alpha=alpha, beta=beta, mu=mu, gamma=gamma,
        xi=xi, rho=rho, ref_date=ref_date, l2=l2,
        converged=bool(res.success), n_iter=int(res.nit),
        grad_norm=float(np.abs(res.jac).max()), nll=float(res.fun),
        n_matches=int(len(train)), elapsed_s=time.perf_counter() - t0,
    )
    model.extra["message"] = res.message
    model.extra["theta"] = res.x
    return model


def _team_params(model: PoissonModel, names: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """队名 → (α, β)；未知队（升班马）返回 0，即联赛平均。"""
    idx = {t: i for i, t in enumerate(model.teams)}
    pos = names.map(idx).to_numpy(dtype=float)
    known = ~np.isnan(pos)
    alpha = np.zeros(len(names))
    beta = np.zeros(len(names))
    alpha[known] = model.alpha[pos[known].astype(int)]
    beta[known] = model.beta[pos[known].astype(int)]
    return alpha, beta


def score_matrix(model: PoissonModel, home: pd.Series, away: pd.Series,
                 max_goals: int = MAX_GOALS) -> np.ndarray:
    """(m, G+1, G+1) 的比分概率矩阵，已乘 τ 并按行归一化。"""
    a_h, b_h = _team_params(model, home)
    a_a, b_a = _team_params(model, away)
    model.n_new_team = int((~home.isin(model.teams) | ~away.isin(model.teams)).sum())

    eta_h = np.clip(model.mu + model.gamma + a_h - b_a, -_ETA_CLIP, _ETA_CLIP)
    eta_a = np.clip(model.mu + a_a - b_h, -_ETA_CLIP, _ETA_CLIP)
    lam, nu = np.exp(eta_h), np.exp(eta_a)

    k = np.arange(max_goals + 1)
    log_fact = gammaln(k + 1)
    ph = np.exp(k[None, :] * eta_h[:, None] - lam[:, None] - log_fact[None, :])
    pa = np.exp(k[None, :] * eta_a[:, None] - nu[:, None] - log_fact[None, :])
    p = ph[:, :, None] * pa[:, None, :]

    if model.rho != 0.0:
        p[:, 0, 0] *= 1.0 - lam * nu * model.rho
        p[:, 0, 1] *= 1.0 + lam * model.rho
        p[:, 1, 0] *= 1.0 + nu * model.rho
        p[:, 1, 1] *= 1.0 - model.rho
    p = np.clip(p, 0.0, None)
    p /= p.sum(axis=(1, 2), keepdims=True)
    return p


def predict_proba(model: PoissonModel, test: pd.DataFrame,
                  max_goals: int = MAX_GOALS) -> np.ndarray:
    """(n, 3) 的 [p_home, p_draw, p_away]——列序就是 schema 的列序，不需要再重排。"""
    p = score_matrix(model, test["home"], test["away"], max_goals)
    g = p.shape[1]
    lo = np.tril_indices(g, k=-1)          # 行=主队进球、列=客队进球；主胜在 i>j
    home = p[:, lo[0], lo[1]].sum(axis=1)
    away = p[:, lo[1], lo[0]].sum(axis=1)
    draw = np.einsum("mii->m", p)
    out = np.column_stack([home, draw, away])
    return out / out.sum(axis=1, keepdims=True)


def count_new_teams(train: pd.DataFrame, test: pd.DataFrame) -> int:
    seen = set(train["home"]) | set(train["away"])
    return len((set(test["home"]) | set(test["away"])) - seen)


def sanity_epl(season: str = "2010/11", league: str = "E0") -> dict:
    """分工卡 §3 的 30 分钟自检：单季 B3，看 α 排序是否合常识。"""
    panel = load_panel()
    sub = panel.loc[(panel["league"] == league) & (panel["season"] == season)]
    if len(sub) != 380:
        raise ValueError(f"{league} {season} 应为 380 场，实际 {len(sub)}")
    model = fit(sub, ref_date=str(sub["date"].max()))
    order = np.argsort(-model.alpha)
    return {"model": model, "table": [(model.teams[j], model.alpha[j], model.beta[j])
                                      for j in order]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B3 独立 Poisson 自检")
    ap.add_argument("--season", default="2010/11")
    ap.add_argument("--league", default="E0")
    a = ap.parse_args(argv)

    out = sanity_epl(a.season, a.league)
    m: PoissonModel = out["model"]
    panel = load_panel()
    sub = panel.loc[(panel["league"] == a.league) & (panel["season"] == a.season)]
    p = predict_proba(m, sub)
    pmat = score_matrix(m, sub["home"], sub["away"])
    e_home = float((pmat.sum(axis=2) * np.arange(pmat.shape[1])).sum(axis=1).mean())
    y = sub["y"].to_numpy()
    actual_home = float(sub["FTHG"].mean())
    pred_home = float(p[:, 0].mean())
    ll = float(-np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1.0))))

    print("=" * 72)
    print(f"B3 自检 · {a.league} {a.season} · {m.n_matches} 场 · "
          f"{len(m.teams)} 队 · {m.n_iter} 次迭代 · {m.elapsed_s:.2f}s")
    print(f"收敛 {m.converged} · |grad|∞ {m.grad_norm:.2e} · Σα {m.alpha.sum():.2e}")
    print(f"μ={m.mu:.4f}  γ={m.gamma:.4f}  (exp(γ)={np.exp(m.gamma):.3f})")
    print("-" * 72)
    print(f"{'rank':>4}  {'team':<22}{'alpha':>9}{'beta':>9}")
    for r, (t, al, be) in enumerate(out["table"], 1):
        print(f"{r:>4}  {t:<22}{al:>9.3f}{be:>9.3f}")
    print("-" * 72)
    print(f"主场进球均值 实际 {actual_home:.3f} / 模型 E[λ] {e_home:.3f}"
          f"  （相对误差 {abs(e_home / actual_home - 1):.2%}）")
    print(f"样本内 log loss {ll:.4f}（同季训练+评估，只用来确认没写反）")
    print(f"预测主场进球比例 {pred_home:.3f} / 实际 {float(np.mean(y == 0)):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
