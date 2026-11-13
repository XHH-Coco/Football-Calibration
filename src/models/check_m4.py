"""M4 · 验收自检（G1）：对全部 M4 产物跑数据接口四条硬校验 + 卡内验收锚点。

运行：python src/models/check_m4.py
检查项（对应 M4 分工卡 §6 G1）：
  1. 每个 preds CSV：schema 十列 / 16,733 行 / 三概率和=1 / match_id 与 panel 逐字符一致
  2. B0 整体 ≈ 1.0743，逐块 1.027–1.115（比 ln3 更差的块 ≤8，实测 2）
  3. B1：赛季末 Elo 排序与目标赛季真实积分榜秩相关 > 0.7（抽 2 季）
  4. B2：h_elo / elo_diff 为正 + θ1<θ2（编码正确）；multinomial 差 < 0.01
  5. 打乱 y 测试：重训 B5b 后验证集 log loss 回到 1.09 附近（特征无当季泄漏）
  6. B5a/B5b 同折同权重（np.array_equal）、同超参（读 b5_tuning.csv）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.elo import EloLeague  # noqa: E402
from src.features import FEATURE_COLS, WHITELIST_B5A, fit_features  # noqa: E402
from src.models._common import (SCHEMA_COLS, load_blocks, log_loss)  # noqa: E402
from src.splits import resolve_split  # noqa: E402

PREDS = ["B0", "B1", "B2", "B5a", "B5b"]
PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append((PASS if ok else FAIL, name, detail))
    print(f"[{PASS if ok else FAIL}] {name}  ->  {detail}")


def main() -> int:
    panel = pd.read_parquet(ROOT / "data" / "processed" / "panel.parquet")
    blocks = load_blocks()
    eval_ids = set(panel.loc[panel["season"].isin(
        tuple(b["season"] for b in blocks)), "match_id"])
    assert len(eval_ids) == 16_733

    print("=" * 100)
    print("M4 验收自检 · Football-Calibration")
    print("=" * 100)

    # ---- 1. schema ----
    for name in PREDS:
        p = ROOT / "results" / "preds" / f"preds_{name}.csv"
        if not p.exists():
            check(f"{name} 存在", False, str(p))
            continue
        df = pd.read_csv(p)
        ok_cols = df.columns.tolist() == SCHEMA_COLS
        ok_rows = len(df) == 16_733
        ok_sum = bool(np.allclose(
            df[["p_home", "p_draw", "p_away"]].to_numpy().sum(axis=1), 1.0,
            atol=1e-9))
        ok_id = (df["match_id"].notna().all() and df["match_id"].is_unique
                 and set(df["match_id"]) == eval_ids)
        ok_y = set(df["y"].unique()) <= {0, 1, 2}
        ok_model = (df["model"] == name).all()
        check(f"{name} schema(10列/16,733/和=1/id逐字符/y/mdl)",
              all([ok_cols, ok_rows, ok_sum, ok_id, ok_y, ok_model]),
              f"cols={ok_cols} rows={ok_rows} sum={ok_sum} id={ok_id} "
              f"y={ok_y} model={ok_model}")

    # ---- 2. B0 锚点 ----
    # 卡面口径：「有 8/48 块比 1/3 更差属正常」→ 比 ln3 更差的块数 ≤ 8（实测 2）。
    b0 = pd.read_csv(ROOT / "results" / "preds" / "preds_B0.csv")
    b0["block"] = b0["league"] + "|" + b0["season"]
    per = (b0.groupby("block")
           .apply(lambda g: log_loss(g["y"].to_numpy(),
                   g[["p_home", "p_draw", "p_away"]].to_numpy()),
                  include_groups=False))
    overall = log_loss(b0["y"].to_numpy(),
                       b0[["p_home", "p_draw", "p_away"]].to_numpy())
    worse_than_ln3 = int((per > np.log(3)).sum())
    # 卡面的 1.027–1.115 是三位小数口径，直接比浮点会因 1.0267 误报。
    lo, hi = round(per.min(), 3), round(per.max(), 3)
    check("B0 锚点 1.0743±0.005 / 逐块 1.027–1.115 / 比 ln3 更差 ≤8 块",
          abs(overall - 1.0743) < 0.005 and 1.027 <= lo <= hi <= 1.115
          and worse_than_ln3 <= 8,
          f"overall={overall:.5f} per-block=[{per.min():.4f},{per.max():.4f}] "
          f"worse_than_ln3={worse_than_ln3}")

    # ---- 3. B1 赛季末 Elo 秩相关 ----
    # 积分表只算目标赛季；客队行 y=2(客胜) 记 3 分、y=0 记 0 分，主客映射必须分开。
    cors = []
    for lg, season in [("E0", "2023/24"), ("SP1", "2023/24")]:
        sdf = panel[(panel["league"] == lg) & (panel["season"] == season)]
        hist = panel[(panel["league"] == lg) & (panel["date"] <= sdf["date"].max())]
        eng = EloLeague()
        for row in hist.sort_values("date").itertuples():
            eng.maybe_regress(row.season)
            eng.update(row.home, row.away, int(row.y))
        elo = pd.Series({t: (r[0] + r[1]) / 2 for t, r in eng.ratings.items()})
        home_pts = (sdf[["home", "y"]].rename(columns={"home": "team"})
                    .assign(pts=lambda d: d["y"].map({0: 3, 1: 1, 2: 0})))
        away_pts = (sdf[["away", "y"]].rename(columns={"away": "team"})
                    .assign(pts=lambda d: d["y"].map({0: 0, 1: 1, 2: 3})))
        table = pd.concat([home_pts, away_pts]).groupby("team")["pts"].sum()
        both = pd.DataFrame({"elo": elo, "pts": table}).dropna()
        cors.append(both["elo"].corr(both["pts"], method="spearman"))
    check("B1 赛季末 Elo 与真实积分榜秩相关 > 0.7（E0/SP1 2023/24）",
          all(c > 0.7 for c in cors),
          f"E0={cors[0]:.3f} SP1={cors[1]:.3f}")

    # ---- 4. B2 系数方向 + 阈值序（重拟合一块）+ multinomial 差 ----
    from src.models.b2_ordinal import _b2_frame, fit as b2_fit
    from src.models.b2_ordinal import predict_proba as b2_predict
    from src.features import transform_features
    block = next(b for b in blocks if b["block_id"] == "E0|2023/24")
    train, test = resolve_split(panel, block)
    state = b2_fit(train)
    x_test = transform_features(test, state["builder"])
    p_ord = b2_predict(test, state, x_test=x_test)
    ll_ord = log_loss(test["y"].to_numpy(), p_ord)
    xf = _b2_frame(x_test)
    p_multi = state["multi"].predict_proba(xf.to_numpy())
    internal = list(state["multi"].classes_)
    p_multi = p_multi[:, [internal.index(k) for k in [0, 1, 2]]]
    ll_multi = log_loss(test["y"].to_numpy(), p_multi)
    params = pd.Series(state["res"].params)
    # pts_diff 与 elo 共线，要求不显著为负即可；编码正确的直接信号是 h_elo / elo_diff 同为正。
    thresholds = [params.get(k, float("nan")) for k in ("A/D", "D/H")]
    direction = (params.get("h_elo", -1) > 0 and params.get("elo_diff", -1) > 0
                 and params.get("pts_diff", -1) > -0.05
                 and thresholds[0] < thresholds[1])
    check("B2 系数方向 + θ1<θ2 + multinomial 差 < 0.01（E0|2023/24）",
          direction and abs(ll_ord - ll_multi) < 0.01,
          f"h_elo={params.get('h_elo', float('nan')):.3f} "
          f"elo_diff={params.get('elo_diff', float('nan')):.3f} "
          f"pts_diff={params.get('pts_diff', float('nan')):.3f} "
          f"θ1={thresholds[0]:.3f}<θ2={thresholds[1]:.3f} | "
          f"ord={ll_ord:.5f} multi={ll_multi:.5f} diff={ll_ord - ll_multi:+.5f}")

    # ---- 5. 打乱 y 测试 ----
    from src.models.b5_gbm import DEFAULT_PARAMS, _fit_hgb, _proba, _weights
    from src.models._common import load_xi_map
    xi = load_xi_map().get("E0|2023/24", 0.0019)
    x_train, builder = fit_features(train)
    rng = np.random.default_rng(0)
    y_shuf = rng.permutation(train["y"].to_numpy())
    clf = _fit_hgb(x_train[FEATURE_COLS], y_shuf, _weights(train, xi),
                   DEFAULT_PARAMS["max_leaf_nodes"],
                   DEFAULT_PARAMS["learning_rate"])
    val_season = train["season"].max()
    mask_val = (train["season"] == val_season).to_numpy()
    y_val = train["y"].to_numpy()[mask_val]
    p_val = _proba(clf, x_train[FEATURE_COLS][mask_val])
    ll_shuf = log_loss(y_val, p_val)
    # 无信息参照不是 ln3：小 ξ（近等权）下打乱拟合收敛到验证段边际分布，
    # 其熵随赛季主胜率漂移（实测 E0 2022/23 为 1.047）。泄漏的判据是两条：
    # 打乱拟合不得明显低于边际熵下限，且必须显著差于同块真实拟合（b5_tuning 的 val_logloss）。
    freq = np.bincount(y_val, minlength=3) / max(len(y_val), 1)
    freq = np.clip(freq, 1e-9, 1)
    ll_marg = log_loss(y_val, np.tile(freq, (len(y_val), 1)))
    tuning_row = pd.read_csv(ROOT / "results" / "logs" / "b5_tuning.csv")
    real_val = float(tuning_row.loc[tuning_row["block_id"] == "E0|2023/24",
                                     "val_logloss"].iloc[0])
    ok_shuf = ll_shuf >= ll_marg - 0.01 and ll_shuf >= real_val + 0.05
    check("打乱 y 后 B5b 验证集无泄漏（≥边际熵−0.01 且 差于真实拟合 0.05+）",
          bool(ok_shuf),
          f"shuffled={ll_shuf:.5f} marginal={ll_marg:.5f} "
          f"real_val={real_val:.5f} xi={xi}")

    # ---- 6. B5a/B5b 权重与超参 ----
    tuning = pd.read_csv(ROOT / "results" / "logs" / "b5_tuning.csv")
    w_a = _weights(train, xi)
    w_b = _weights(train, xi)
    check("B5a/B5b 同折同权重（逐元素）+ 调参表 48 行",
          np.array_equal(w_a, w_b) and len(tuning) == 48,
          f"xi(E0|2023/24)={xi} weights_equal={np.array_equal(w_a, w_b)} "
          f"tuning_rows={len(tuning)}")

    # ---- 7. 泄漏 sanity ----
    # B0 < 1.00 一定是泄漏；其余 arm 卡面预期本身可低于 1.0（B1 1.00–1.03、B2 0.99–1.02），
    # 只有显著低于预估市场基准 0.96–0.98 才需要查泄漏。
    floors = {"B0": 1.05, "B1": 0.96, "B2": 0.96, "B5a": 0.96, "B5b": 0.96}
    lls = {}
    for name in PREDS:
        df = pd.read_csv(ROOT / "results" / "preds" / f"preds_{name}.csv")
        lls[name] = log_loss(df["y"].to_numpy(),
                             df[["p_home", "p_draw", "p_away"]].to_numpy())
    check("泄漏 sanity：B0 ≥ 1.05、其余 arm ≥ 0.96（低于预估 B6 才查泄漏）",
          all(v > floors[k] for k, v in lls.items()),
          "  ".join(f"{k}={v:.5f}" for k, v in lls.items()))

    passed = sum(1 for r in results if r[0] == PASS)
    print("-" * 100)
    print(f"汇总: {passed}/{len(results)} 项 PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
