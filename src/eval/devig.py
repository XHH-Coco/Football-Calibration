"""M2 / T2.5：三种去抽水（de-vig）+ B6 基准构造。

输入**只读**收盘价 ``PSCH / PSCD / PSCA``（``PSH/PSD/PSA`` 是开盘、``B365*`` 是别家、
``MaxC*`` 只作稳健性——一律不用，见 ``data_interface.md`` / 分工方案 §5.5）。

三种方法（人话见 M2 卡 §T2.5）：
- ``proportional`` 比例法：``p_i = (1/o_i) / Σ_j (1/o_j)``。**B6 主基准**。
- ``power``     幂法：解 ``k`` 使 ``Σ_i (1/o_i)^k = 1``（``brentq``，k ∈ [1, 100]），
  ``p_i = (1/o_i)^k``。抽水视为乘性。
- ``shin``      Shin 法（Štrumbelj 2014）：对 z（内幕交易比例）一维求根，z ∈ [0,1)，
  ``p_i = [√(z² + 4(1−z) b_i²/B) − z] / (2(1−z))``，``b_i = 1/o_i``，``B = Σ b_i``。

硬规则：``o_i > 1`` 才合法；任一列 ≤1 或 NaN 即 drop 该场、**不回填**。评估窗内
3 块共 5 场缺三列收盘赔率，故 B6 / B6r 有效 ``n = 16,728``。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scipy.optimize import brentq  # noqa: E402

ODDS_COLS = ["PSCH", "PSCD", "PSCA"]
B6_N = 16_728


def check_odds(odds: np.ndarray) -> np.ndarray:
    """返回「合法行」布尔掩码：三列都有限且都 > 1。"""
    o = np.asarray(odds, dtype=float)
    if o.ndim != 2 or o.shape[1] != 3:
        raise ValueError(f"odds 必须是 (n,3)，实际 {o.shape}")
    return np.isfinite(o).all(axis=1) & (o > 1.0).all(axis=1)


def proportional(odds: np.ndarray) -> np.ndarray:
    """比例法，向量化。返回 ``(n,3)`` 概率矩阵（每行和 = 1）。"""
    b = 1.0 / np.asarray(odds, dtype=float)
    return b / b.sum(axis=1, keepdims=True)


def power(odds: np.ndarray) -> np.ndarray:
    """幂法，逐行求 k：``Σ_i (1/o_i)^k = 1``，``k ∈ [1, 100]``。"""
    o = np.asarray(odds, dtype=float)
    n = len(o)
    p = np.empty_like(o)
    for r in range(n):
        inv = 1.0 / o[r]
        f = lambda k: float((inv ** k).sum() - 1.0)  # noqa: E731
        k = brentq(f, 1.0, 100.0, xtol=1e-12)
        p[r] = inv ** k
    return p


def shin(odds: np.ndarray) -> np.ndarray:
    """Shin 法（Štrumbelj 2014），逐行对 z 求根。

    数值上 z 的根总在 (0,1) 内（f(0)=√B−1>0、f(1⁻)<0）；若某行求根失败（病态赔率），
    退回比例法并把该行记入返回的第二项。
    """
    o = np.asarray(odds, dtype=float)
    n = len(o)
    p = np.empty_like(o)
    fallback = []
    for r in range(n):
        b = 1.0 / o[r]
        B = b.sum()

        def f(z: float) -> float:
            # z ∈ [0,1)：p_i = [√(z² + 4(1−z)b_i²/B) − z] / (2(1−z))
            s = np.sqrt(z * z + 4.0 * (1.0 - z) * (b ** 2) / B)
            pi = (s - z) / (2.0 * (1.0 - z))
            return float(pi.sum() - 1.0)

        try:
            z = brentq(f, 0.0, 1.0 - 1e-9, xtol=1e-12)
            s = np.sqrt(z * z + 4.0 * (1.0 - z) * (b ** 2) / B)
            p[r] = (s - z) / (2.0 * (1.0 - z))
        except ValueError:
            p[r] = proportional(o[r:r + 1])[0]
            fallback.append(r)
    return p, fallback


def devig(odds: np.ndarray, method: str = "proportional") -> np.ndarray:
    """三种去抽水统一入口，返回 ``(n,3)``（Shin 也返回概率，fallback 明细丢弃）。"""
    if method == "proportional":
        return proportional(odds)
    if method == "power":
        return power(odds)
    if method == "shin":
        prob, _ = shin(odds)
        return prob
    raise ValueError(f"未知去抽水方法：{method}")


def build_b6(panel: pd.DataFrame | None = None, out_path: str | Path | None = None,
             disagreement_log: str | Path | None = None,
             write_aux: bool = True) -> pd.DataFrame:
    """从 panel 构造 ``preds_B6.csv``（16,728 行，``model="B6"``）。

    - ``out_path=None``：只返回 DataFrame，不写盘（测试用）。
    - ``write_aux=False``：不写 power / Shin 逐场文件与 disagreement 审计（测试用）。
    - 另把 power / Shin 两法的逐场概率与 disagreement 审计写到
      ``results/logs/``（``disagreement_log=None`` 时用默认路径）。
    """
    from src.eval.harness import PRED_COLS, check_pred  # 延迟导入避免循环
    from src.models.b3_poisson import load_panel

    panel = load_panel() if panel is None else panel
    sub = panel.loc[panel["season"] >= "2017/18", :].copy()
    sub = sub.sort_values(["league", "season", "date", "home", "away"])
    ok = check_odds(sub[ODDS_COLS].to_numpy(dtype=float))
    sub = sub.loc[ok].reset_index(drop=True)

    odds = sub[ODDS_COLS].to_numpy(dtype=float)
    p_prop = proportional(odds)
    p_power = power(odds)
    p_shin, _ = shin(odds)

    frame = sub[["match_id", "league", "season", "date", "home", "away", "y"]].copy()
    frame["model"] = "B6"
    frame["p_home"] = p_prop[:, 0]
    frame["p_draw"] = p_prop[:, 1]
    frame["p_away"] = p_prop[:, 2]
    frame = frame[PRED_COLS]
    check_pred(frame, B6_N)

    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False, encoding="utf-8")

    # 三法互检：power / Shin 逐场落盘 + 差 > 0.05 的场次审计
    if not write_aux:
        return frame

    if disagreement_log is None:
        log_dir = ROOT / "results" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        aux = {
            "power": log_dir / "b6_devig_power.csv",
            "shin": log_dir / "b6_devig_shin.csv",
            "disagreement": log_dir / "b6_devig_disagreement.csv",
        }
    else:
        aux = {"power": None, "shin": None, "disagreement": Path(disagreement_log)}

    for method, prob in (("power", p_power), ("shin", p_shin)):
        if aux.get(method) is None:
            continue
        a = sub[["match_id", "league", "season", "date", "home", "away", "y"]].copy()
        a["model"] = "B6"
        a["p_home"] = prob[:, 0]
        a["p_draw"] = prob[:, 1]
        a["p_away"] = prob[:, 2]
        a[PRED_COLS].to_csv(aux[method], index=False, encoding="utf-8")

    worst = np.maximum.reduce([
        np.abs(p_prop - p_power).max(axis=1),
        np.abs(p_prop - p_shin).max(axis=1),
        np.abs(p_power - p_shin).max(axis=1),
    ])
    bad = sub.loc[worst > 0.05, ["match_id", "league", "season",
                                 *ODDS_COLS]].copy()
    bad["max_pairwise_diff"] = worst[worst > 0.05]
    if aux["disagreement"] is not None:
        Path(aux["disagreement"]).parent.mkdir(parents=True, exist_ok=True)
        bad.to_csv(aux["disagreement"], index=False, encoding="utf-8")

    return frame
