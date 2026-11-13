"""M4 · T4.4 特征表（B2 / B5a / B5b 共用，全组唯一特征引擎）。

口径（M4 卡 T4.4 + data_interface.md §2 防泄漏红线）：
  - 所有滚动特征只用 **t 之前** 的比赛（至少 shift 一场），Elo 逐场顺序更新；
  - 射门列覆盖不全：窗口含 NaN 或该队无历史 → 缺失指示列置 1，取值用
    「该队历史均值 → 联赛历史均值 → 0」回填（绝不插补成 0 冒充真值，M4 卡 §7 坑 5）；
  - 无当季泄漏：特征只依赖严格更早场次；全表 46,507 行与 panel 一一对应；
  - 禁止全样本标准化（HGB 尺度无关，B2 用原始量纲）。

列清单（39 个特征 + match_id）：
  赛季阶段: matchday, total_rounds, stage_ratio
  双方滚动(shift 1): {h,a}_{gf5,gf10,ga5,ga10,pts5,pts10}              共 12
  射门/射正滚动5 + 缺失指示: {h,a}_{shf5,sha5,sotf5,sota5}(+_miss)      共 16
  休整: {h,a}_rest, rest_diff                                           共 3
  Elo: {h,a}_elo, elo_diff                                              共 3
  对手强度: {h,a}_opp_elo5                                              共 2
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.elo import EloLeague  # noqa: E402
from src.models._common import PANEL_PATH  # noqa: E402

REST_CAP_DAYS = 21.0

ROLL_GOALS = ("gf5", "gf10", "ga5", "ga10", "pts5", "pts10")
ROLL_SHOTS = ("shf5", "sha5", "sotf5", "sota5")
SIDES = ("h", "a")

FEATURE_COLS = (
    ["matchday", "total_rounds", "stage_ratio"]
    + [f"{s}_{c}" for s in SIDES for c in ROLL_GOALS]
    + [f"{s}_{c}" for s in SIDES for c in ROLL_SHOTS]
    + [f"{s}_{c}_miss" for s in SIDES for c in ROLL_SHOTS]
    + ["h_rest", "a_rest", "rest_diff"]
    + ["h_elo", "a_elo", "elo_diff"]
    + ["h_opp_elo5", "a_opp_elo5"]
)

# T4.5 白名单：只喂 B4 能看到的信息（M3 签字前以此为准，见 configs/feature_whitelist_b5a.csv）
WHITELIST_B5A = (
    ["h_gf5", "h_gf10", "h_ga5", "h_ga10",
     "a_gf5", "a_gf10", "a_ga5", "a_ga10", "elo_diff"]
)

_K = {"gf5": 5, "gf10": 10, "ga5": 5, "ga10": 10, "pts5": 5, "pts10": 10}
_BASE = {"gf5": "gf", "gf10": "gf", "ga5": "ga", "ga10": "ga",
         "pts5": "pts", "pts10": "pts"}
_SHOT_KEYS = {c: c[:-1] for c in ROLL_SHOTS}  # shf5→shf ...（窗口 5）


def _parse_date(value: str) -> datetime:
    return pd.to_datetime(value).to_pydatetime()


class _Builder:
    """单联赛逐场状态机：Elo + 每队近 10 场窗口 + 历史均值累加器。"""

    _KEYS = ("gf", "ga", "pts", "shf", "sha", "sotf", "sota")

    def __init__(self) -> None:
        self.elo = EloLeague()
        self.team: dict[str, dict] = {}
        self.lg_sums: dict[str, float] = {k: 0.0 for k in self._KEYS}
        self.lg_n: dict[str, int] = {k: 0 for k in self._KEYS}

    @classmethod
    def _new_team(cls) -> dict:
        return {"deq": deque(maxlen=10),
                "sums": {k: 0.0 for k in cls._KEYS},
                "n": {k: 0 for k in cls._KEYS}}

    def _side_feats(self, team: str, date: datetime) -> dict:
        t = self.team.setdefault(team, self._new_team())
        deq = t["deq"]
        out: dict[str, float] = {}
        for c in ROLL_GOALS:
            vals = [e[_BASE[c]] for e in list(deq)[-_K[c]:]]
            out[c] = float(np.mean(vals)) if vals else self._fallback(t, _BASE[c])
        for c in ROLL_SHOTS:
            key = _SHOT_KEYS[c]
            vals = [(e[key]) for e in list(deq)[-5:]]
            if not vals or any(pd.isna(v) for v in vals):
                out[c] = self._fallback(t, key)
                out[c + "_miss"] = 1.0
            else:
                out[c] = float(np.mean(vals))
                out[c + "_miss"] = 0.0
        last_days = ((date - deq[-1]["date"]).days if deq
                     else REST_CAP_DAYS)
        out["rest"] = min(last_days, REST_CAP_DAYS)
        out["elo"] = self.elo.blended(team)
        return out

    def _fallback(self, t: dict, key: str) -> float:
        if t["n"][key] > 0:
            return t["sums"][key] / t["n"][key]
        if self.lg_n[key] > 0:
            return self.lg_sums[key] / self.lg_n[key]
        return 0.0

    def _opp_elo5(self, team: str) -> float:
        deq = self.team.get(team, {}).get("deq", deque())
        vals = [e["elo_b"] for e in list(deq)[-5:]]
        return float(np.mean(vals)) if vals else EloLeague.MEAN

    def process(self, date: str, season: str, home: str, away: str, y: int,
                matchday: float, fthg: float, ftag: float, hs: float,
                as_: float, hst: float, ast: float, total_rounds: int) -> dict:
        date = _parse_date(date)
        self.elo.maybe_regress(season)
        y = int(y)

        h = self._side_feats(home, date)
        a = self._side_feats(away, date)
        h_opp = self._opp_elo5(away)
        a_opp = self._opp_elo5(home)
        feats: dict[str, float] = {
            "matchday": float(matchday),
            "total_rounds": float(total_rounds),
            "stage_ratio": float(matchday) / max(total_rounds, 1),
            "h_rest": h["rest"], "a_rest": a["rest"],
            "rest_diff": h["rest"] - a["rest"],
            "h_elo": h["elo"], "a_elo": a["elo"],
            "elo_diff": h["elo"] - a["elo"],
            "h_opp_elo5": h_opp, "a_opp_elo5": a_opp,
        }
        for s, d in (("h", h), ("a", a)):
            for c in ROLL_GOALS + ROLL_SHOTS:
                feats[f"{s}_{c}"] = d[c]
            for c in ROLL_SHOTS:
                feats[f"{s}_{c}_miss"] = d[c + "_miss"]

        # —— 事后更新：本场结果只进窗口与累加器，不进本行特征 ——
        h_pts = 3.0 if y == 0 else (1.0 if y == 1 else 0.0)
        stats = {
            home: {"gf": float(fthg), "ga": float(ftag),
                   "pts": h_pts, "shf": float(hs),
                   "sha": float(as_), "sotf": float(hst),
                   "sota": float(ast)},
            away: {"gf": float(ftag), "ga": float(fthg),
                   "pts": 0.0 if y == 0 else (1.0 if y == 1 else 3.0),
                   "shf": float(as_), "sha": float(hs),
                   "sotf": float(ast), "sota": float(hst)},
        }
        for team, s in stats.items():
            t = self.team.setdefault(team, self._new_team())
            t["deq"].append({"date": date, "elo_b": self.elo.blended(team),
                             "gf": s["gf"], "ga": s["ga"], "pts": s["pts"],
                             "shf": s["shf"], "sha": s["sha"],
                             "sotf": s["sotf"], "sota": s["sota"]})
            for k in ("gf", "ga", "pts", "shf", "sha", "sotf", "sota"):
                if not pd.isna(s[k]):
                    t["sums"][k] += s[k]
                    t["n"][k] += 1
                    self.lg_sums[k] += s[k]
                    self.lg_n[k] += 1
        self.elo.update(home, away, y)
        return feats


_PANEL_ROUNDS: dict | None = None


def _panel_rounds() -> dict:
    """各 (联赛, 赛季) 的总轮数（全表口径；赛季阶段是赛程信息，不属赛后）。"""
    global _PANEL_ROUNDS
    if _PANEL_ROUNDS is None:
        panel = pd.read_parquet(PANEL_PATH)
        _PANEL_ROUNDS = (panel.groupby(["league", "season"])["matchday"]
                         .max().to_dict())
    return _PANEL_ROUNDS


def _walk(frame: pd.DataFrame, builder: _Builder | None) -> pd.DataFrame:
    """对 frame（单联赛、任意行序）逐场生成特征；builder=None 时从零开始。"""
    b = builder if builder is not None else _Builder()
    rounds = _panel_rounds()
    srt = frame.sort_values("date")
    idx_list: list = []
    rows: list[dict] = []
    for idx, row in zip(srt.index, srt.itertuples()):
        key = (row.league, row.season)
        rows.append(b.process(row.date, row.season, row.home, row.away, row.y,
                              row.matchday, row.FTHG, row.FTAG, row.HS, row.AS,
                              row.HST, row.AST, rounds.get(key, 38)))
        idx_list.append(idx)
    out = pd.DataFrame(rows, index=idx_list)
    return out.reindex(frame.index)[FEATURE_COLS], b


def fit_features(train_df: pd.DataFrame) -> tuple[pd.DataFrame, _Builder]:
    """harness 入口：从零走完 train（单联赛），返回 (X_train, 状态机)。"""
    return _walk(train_df, None)


def transform_features(test_df: pd.DataFrame, builder: _Builder) -> pd.DataFrame:
    """harness 入口：沿用状态机继续走 test（保持逐场推进），返回 X_test。"""
    x, _ = _walk(test_df, builder)
    return x


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """全表 46,507 行 × 39 特征，行序与 panel 一致。"""
    parts = []
    for lg, sub in panel.groupby("league", sort=False):
        sub = sub.sort_values("date")
        x, _ = _walk(sub, None)
        parts.append(x)
    out = pd.concat(parts).reindex(panel.index)
    out.insert(0, "match_id", panel["match_id"])
    assert len(out) == len(panel)
    assert not out[FEATURE_COLS].isna().any().any(), "特征表存在 NaN"
    return out


def _sample_check(panel: pd.DataFrame, feats: pd.DataFrame, seed: int = 0) -> bool:
    """抽样验证：随机取 3 场，手工用前 5 场算 h_gf5 / a_pts5，与表里一致。"""
    rng = np.random.default_rng(seed)
    ok = True
    for _ in range(3):
        idx = int(rng.integers(0, len(panel)))
        row = panel.iloc[idx]
        lg = row["league"]
        hist = panel[(panel["league"] == lg) & (panel["date"] < row["date"])]
        for side, team in (("h", row["home"]), ("a", row["away"])):
            tm = hist[(hist["home"] == team) | (hist["away"] == team)]
            tm = tm.sort_values("date").tail(5)
            if len(tm) == 0:
                continue
            gf = np.where(tm["home"].to_numpy() == team,
                          tm["FTHG"].to_numpy(), tm["FTAG"].to_numpy())
            pts = np.where(tm["home"].to_numpy() == team,
                           tm["y"].map({0: 3, 1: 1, 2: 0}).to_numpy(),
                           tm["y"].map({0: 0, 1: 1, 2: 3}).to_numpy())
            expect_gf = float(gf.mean())
            expect_pts = float(pts.mean())
            got_gf = float(feats.loc[idx, f"{side}_gf5"])
            got_pts = float(feats.loc[idx, f"{side}_pts5"])
            if not (abs(expect_gf - got_gf) < 1e-9
                    and abs(expect_pts - got_pts) < 1e-9):
                print(f"  抽样 {row['match_id']} {side}: 期望 gf5={expect_gf:.4f} "
                      f"pts5={expect_pts:.4f}，表里 gf5={got_gf:.4f} pts5={got_pts:.4f}")
                ok = False
            else:
                print(f"  抽样 {row['match_id']} {side}: gf5={got_gf:.4f} "
                      f"pts5={got_pts:.4f} 一致")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="M4 / T4.4 特征表")
    ap.add_argument("--out", default=str(ROOT / "data" / "processed" / "features_v1.parquet"))
    ap.add_argument("--panel", default=str(PANEL_PATH))
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    panel = pd.read_parquet(args.panel)
    feats = build_features(panel)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    feats.to_parquet(out, index=False)
    print(f"features_v1.parquet: {feats.shape[0]} 行 × {feats.shape[1]} 列 → {out}")
    ok = _sample_check(panel, feats)
    print("抽样验证:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
