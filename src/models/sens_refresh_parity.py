"""M4 · 「赛季内刷新」值多少：滚动臂 vs 冻结臂的同尺对照（复盘 P1-1 的仓库证据）。

问题：阶梯两边的尺不一样。
  - **批式臂**（B3 / B4）：整季参数在赛季开始前冻结，一场都不更新。
  - **滚动臂**（B1 / B2 / B5a / B5b）：`transform_features(test, builder)` 会在 test 段
    继续推进 Elo 与滚动窗口，于是第 20 轮的预测用了第 1–19 轮的结果。
这不是泄漏（每场只用更早场次），但它是**额外的信息刷新额度**：滚动臂可以在赛季内
自我修正，批式臂不能。C1（B4 → B5a）因此把"模型类别"和"刷新额度"两件事混在一起。

本脚本量化这份额度：把滚动臂的**结果类特征**（滚动进球/失球/射门、Elo、对手强度）
冻结成"赛季开始那一刻"的快照，只保留**赛前已知的日历类特征**（rest / matchday /
stage_ratio）实时，重训重评，得到冻结臂的损失。

三个约定，避免把额度算大或算小：
  1. 只冻结果类特征。`rest`（距上一场几天）是赛前公开信息，冻结它会**夸大**刷新的价值
     ——v1 就这么错过一次，故本版显式区分。
  2. 冻结快照取 `fit_features(train)` 结束时的 builder 状态，即"第一轮开打前"。
  3. 两臂都用现行主口径超参（B5b 固定 `FIXED_HP`，B2 无超参），只改特征来源。

产物 `results/logs/sens_refresh_parity.csv`（48 行），可被报告与测试引用。
用法：
  python -m src.models.sens_refresh_parity            # 有缓存则直接出表
  python -m src.models.sens_refresh_parity --rebuild  # 重算（约 5 分钟）
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

from src.eval.bootstrap import BlockDeltas, cluster_bootstrap  # noqa: E402
from src.features import (FEATURE_COLS, REST_CAP_DAYS, ROLL_GOALS,  # noqa: E402
                          ROLL_SHOTS, WHITELIST_B5A, _panel_rounds,
                          _parse_date, fit_features)
from src.models._common import load_blocks, load_panel, log_loss  # noqa: E402
from src.splits import resolve_split  # noqa: E402

LOGS = ROOT / "results" / "logs"
PREDS = ROOT / "results" / "preds"
CACHE = LOGS / "sens_refresh_parity.csv"


def _prev_dates(panel: pd.DataFrame) -> dict:
    """(league, team, date) → 该队在本联赛上一场的日期（赛前已知的日历信息）。"""
    long = pd.concat([
        panel[["league", "date", "home"]].rename(columns={"home": "team"}),
        panel[["league", "date", "away"]].rename(columns={"away": "team"}),
    ]).sort_values(["league", "team", "date"])
    long["prev"] = long.groupby(["league", "team"])["date"].shift(1)
    return {(r.league, r.team, r.date): r.prev for r in long.itertuples()}


def _frozen_walk(frame: pd.DataFrame, builder, prev: dict) -> pd.DataFrame:
    """结果类特征取赛季开始时的快照；日历类特征（rest/matchday）实时。"""
    rounds = _panel_rounds()
    srt = frame.sort_values("date", kind="stable")
    rows, idx = [], []
    for i, row in zip(srt.index, srt.itertuples()):
        d = _parse_date(row.date)
        h = builder._side_feats(row.home, d)      # 只读；不推进历史
        a = builder._side_feats(row.away, d)
        rest = {}
        for side, team in (("h", row.home), ("a", row.away)):
            p = prev.get((row.league, team, row.date))
            rest[side] = (REST_CAP_DAYS if p is None or pd.isna(p)
                          else min((d - _parse_date(p)).days, REST_CAP_DAYS))
        tr = rounds.get((row.league, row.season), 38)
        feats = {
            "matchday": float(row.matchday), "total_rounds": float(tr),
            "stage_ratio": float(row.matchday) / max(tr, 1),
            "h_rest": rest["h"], "a_rest": rest["a"],
            "rest_diff": rest["h"] - rest["a"],
            "h_elo": h["elo"], "a_elo": a["elo"],
            "elo_diff": h["elo"] - a["elo"],
            "h_opp_elo5": builder._opp_elo5(row.away),
            "a_opp_elo5": builder._opp_elo5(row.home),
        }
        for s, dd in (("h", h), ("a", a)):
            for c in ROLL_GOALS + ROLL_SHOTS:
                feats[f"{s}_{c}"] = dd[c]
            for c in ROLL_SHOTS:
                feats[f"{s}_{c}_miss"] = dd[c + "_miss"]
        rows.append(feats)
        idx.append(i)
    return pd.DataFrame(rows, index=idx).reindex(frame.index)[FEATURE_COLS]


def build() -> pd.DataFrame:
    from src.models.b2_ordinal import fit as b2_fit
    from src.models.b2_ordinal import predict_proba as b2_pred
    from src.models.b5_gbm import FIXED_HP, _fit_hgb, _proba, _weights

    panel, blocks = load_panel(), load_blocks()
    prev = _prev_dates(panel)
    rows: list[dict] = []
    for i, b in enumerate(blocks, 1):
        train, test = resolve_split(panel, b)
        x_tr, builder = fit_features(train)
        x_fr = _frozen_walk(test, builder, prev)
        y = test["y"].to_numpy()

        st2 = b2_fit(train)
        p2_frozen = b2_pred(test, st2, x_test=x_fr)

        w = _weights(train, 0.0019)
        clf_a = _fit_hgb(x_tr[WHITELIST_B5A], train["y"].to_numpy(), w,
                         FIXED_HP[0], FIXED_HP[1])
        p5a_frozen = _proba(clf_a, x_fr[WHITELIST_B5A])
        clf = _fit_hgb(x_tr[FEATURE_COLS], train["y"].to_numpy(), w,
                       FIXED_HP[0], FIXED_HP[1])
        p5_frozen = _proba(clf, x_fr[FEATURE_COLS])

        rows.append({"block_id": b["block_id"], "n": len(test),
                     "B2_frozen": log_loss(y, p2_frozen),
                     "B5a_frozen": log_loss(y, p5a_frozen),
                     "B5b_frozen": log_loss(y, p5_frozen)})
        print(f"[{i:02d}/48] {b['block_id']:<11} "
              f"B2f={rows[-1]['B2_frozen']:.5f} B5af={rows[-1]['B5a_frozen']:.5f} "
              f"B5bf={rows[-1]['B5b_frozen']:.5f}")
    return pd.DataFrame(rows)


def _block_ll(arm: str, block_ids: pd.Series) -> np.ndarray:
    df = pd.read_csv(PREDS / f"preds_{arm}.csv")
    df["block_id"] = df["league"] + "|" + df["season"]
    g = df.groupby("block_id").apply(
        lambda x: log_loss(x["y"].to_numpy(),
                           x[["p_home", "p_draw", "p_away"]].to_numpy()),
        include_groups=False)
    return g.reindex(block_ids).to_numpy()


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / 赛季内刷新额度")
    ap.add_argument("--rebuild", action="store_true", help="重算缓存")
    args = ap.parse_args()
    if args.rebuild or not CACHE.exists():
        build().to_csv(CACHE, index=False, encoding="utf-8")
    fr = pd.read_csv(CACHE)
    n = fr["n"].to_numpy(float)
    print("\n" + "=" * 88)
    print("「赛季内刷新」值多少：冻结结果类特征 vs 现行滚动口径")
    print("=" * 88)
    print(f"{'arm':<6}{'滚动（现行）':>14}{'冻结':>12}{'冻结−滚动':>12}"
          f"{'90% 区间':>26}{'冻结更好':>10}")
    for arm in ("B2", "B5a", "B5b"):
        roll = _block_ll(arm, fr["block_id"])
        d = fr[f"{arm}_frozen"].to_numpy() - roll
        blk = BlockDeltas(values=d, weights=n,
                          per_match=np.zeros(int(n.sum())), n_paired=int(n.sum()))
        ci = cluster_bootstrap(blk, B=10_000, alpha=0.10)
        print(f"{arm:<6}{np.sum(roll * n) / n.sum():>14.6f}"
              f"{np.sum(fr[f'{arm}_frozen'] * n) / n.sum():>12.6f}"
              f"{ci['point']:>+12.5f}   [{ci['lo']:+.5f}, {ci['hi']:+.5f}]"
              f"{int((d < 0).sum()):>8}/48")
    print("\n正数 = 冻结后更差，即「赛季内刷新」带来的那部分优势。")
    print("B5b 的刷新额度按现行固定超参重算；B2 无超参，与交付版同一模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
