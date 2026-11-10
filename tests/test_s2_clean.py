"""S2 / T1.2 验收测试：字段统一（alias / ISO 日期 / y / H3 三列）。

对应 M1 分工卡 §6 验收项 2 / 4 / 7 / 7a / 9，以及 T1.9 的打乱不变性核心断言。
运行：``pytest -q tests/test_s2_clean.py``（用项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    ALIAS_COLUMNS,
    EVAL_SEASONS,
    LABEL_MAP,
    add_h3_features,
    build_team_alias,
    clean_panel,
    h3_invariant_to_post_match,
    load_team_alias,
    new_teams_by_block,
    read_all,
    s2_selfcheck,
)

NEW_COLS = ("league", "home", "away", "date", "y",
            "is_promoted_home", "is_promoted_away", "matchday")
H3_COLS = ["is_promoted_home", "is_promoted_away", "matchday"]


@pytest.fixture(scope="module")
def raw():
    return read_all()


@pytest.fixture(scope="module")
def panel(raw):
    return clean_panel(raw)


def test_alias_table_reproducible_and_covers_every_name(raw):
    """契约表可由 raw 一键重生成，且覆盖全库所有 (league, raw_name)。"""
    rows = build_team_alias(raw=raw)
    _, on_disk = load_team_alias()
    assert rows == on_disk, "team_alias.csv 与脚本重生成结果不一致"
    assert len(on_disk) == 243
    assert tuple(on_disk[0]) == ALIAS_COLUMNS
    raw_names = {(lg, n) for lg, n in zip(
        pd.concat([raw["Div"], raw["Div"]], ignore_index=True),
        pd.concat([raw["HomeTeam"], raw["AwayTeam"]], ignore_index=True),
    )}
    mapping, _ = load_team_alias()
    assert raw_names == set(mapping), "alias 与全库队名的差集必须为空（§6 验收项 9）"


def test_alias_contains_exactly_two_real_renames():
    mapping, rows = load_team_alias()
    changed = [(r["league"], r["raw_name"], r["canonical_name"])
               for r in rows if r["raw_name"] != r["canonical_name"]]
    assert changed == [
        ("N1", "Roda JC", "Roda"),
        ("N1", "Sparta", "Sparta Rotterdam"),
    ]
    assert len(set(mapping.values())) == 241


def test_distinct_clubs_are_never_merged():
    """同城 / 同词不同队不能被模糊匹配误并（M1 卡 §7 坑 2 的反向保护）。"""
    mapping, _ = load_team_alias()
    for lg, a, b in (
        ("F1", "Ajaccio", "Ajaccio GFCO"),
        ("E0", "Man City", "Man United"),
        ("D1", "Bayern Munich", "Munich 1860"),
        ("N1", "Den Bosch", "Den Haag"),
        ("SP1", "Ath Madrid", "Real Madrid"),
    ):
        assert (lg, a) in mapping and (lg, b) in mapping
        assert mapping[(lg, a)] != mapping[(lg, b)]


def test_missing_alias_entry_raises(raw, tmp_path):
    """删掉一行 alias 后清洗必须当场拒绝，不许静默留白。"""
    rows = [r for r in build_team_alias(raw=raw)
            if not (r["league"] == "E0" and r["raw_name"] == "Arsenal")]
    path = tmp_path / "alias.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ALIAS_COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="未覆盖"):
        clean_panel(raw, alias_path=path)


def test_clean_panel_shape_and_columns(panel):
    assert len(panel) == 46_507
    assert all(c in panel.columns for c in NEW_COLS)
    assert "HomeTeam" in panel.columns and "Date" in panel.columns, "原始列保留供 S3 追溯"
    assert "match_id" not in panel.columns, "match_id 属 S3，本步不写"
    assert (panel["home"] != panel["away"]).all()


def test_iso_dates(panel):
    assert panel["date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    assert panel["date"].min() == "2003-08-01"
    assert panel["date"].max() == "2025-05-25"
    parsed = pd.to_datetime(panel["Date"], dayfirst=True, format="mixed", errors="coerce")
    assert parsed.notna().all()
    for season, block in pd.DataFrame({"season": panel["season"], "d": parsed}).groupby("season"):
        start = int(season[:4])
        assert set(block["d"].dt.year) <= {start, start + 1}, "两位年被猜错会跨季错位"


def test_y_encoding_matches_ftr(panel):
    assert np.array_equal(panel["y"].to_numpy(),
                          panel["FTR"].map(LABEL_MAP).to_numpy())
    assert set(panel["y"].unique()) <= {0, 1, 2}
    assert panel["y"].value_counts().sort_index().to_dict() == {
        0: 21_194, 1: 11_824, 2: 13_489,
    }


def test_first_season_has_no_promoted_teams(panel):
    first = panel.loc[panel["season"] == "2003/04", H3_COLS[:2]]
    assert int(first.to_numpy().sum()) == 0, "首季无上一季名单，必须全置 0 而非 1"


def test_promoted_flags_equal_independent_prev_season_rosters(panel):
    """用另一套实现（每块新增队集合）独立复算，逐元素比对。"""
    new = new_teams_by_block(panel)
    expected_home = np.fromiter(
        (int(h in new[(lg, s)]) for lg, s, h in
         zip(panel["league"], panel["season"], panel["home"])),
        dtype="int8", count=len(panel),
    )
    expected_away = np.fromiter(
        (int(a in new[(lg, s)]) for lg, s, a in
         zip(panel["league"], panel["season"], panel["away"])),
        dtype="int8", count=len(panel),
    )
    assert np.array_equal(panel["is_promoted_home"].to_numpy(), expected_home)
    assert np.array_equal(panel["is_promoted_away"].to_numpy(), expected_away)


def test_eval_window_new_teams_le_3_and_known_exception(panel):
    prev = new_teams_by_block(panel)
    hist = new_teams_by_block(panel, cumulative=True)
    eval_blocks = [k for k in prev if k[1] in EVAL_SEASONS]
    assert len(eval_blocks) == 48
    assert max(len(prev[k]) for k in eval_blocks) <= 3
    assert max(len(hist[k]) for k in eval_blocks) <= 3
    exceptions = {k: sorted(v) for k, v in prev.items() if len(v) > 3}
    assert set(exceptions) == {("I1", "2004/05")}, "意甲 2004/05 扩军是真实事实，不是 bug"
    assert len(exceptions[("I1", "2004/05")]) == 6


def test_matchday_is_continuous_and_bounded(panel):
    """matchday = 主队本季已完成场次序号+1，**含它作为客队出场的比赛**。

    所以独立复算必须把 home / away 展开成 2×46,507 行，按队累计后再取主队侧。
    """
    assert panel["matchday"].notna().all()
    assert panel["matchday"].between(1, 38).all()
    n, rows = len(panel), np.arange(len(panel))
    long = pd.concat([
        pd.DataFrame({"league": panel["league"], "season": panel["season"],
                      "date": panel["date"], "team": panel["home"],
                      "row": rows, "side": "H"}),
        pd.DataFrame({"league": panel["league"], "season": panel["season"],
                      "date": panel["date"], "team": panel["away"],
                      "row": rows, "side": "A"}),
    ], ignore_index=True)
    long = long.sort_values(["league", "season", "team", "date", "row"],
                            kind="mergesort")
    seq = long.groupby(["league", "season", "team"], sort=False).cumcount() + 1
    home_seq = (long.assign(seq=seq).loc[lambda d: d["side"] == "H"]
                .set_index("row")["seq"].reindex(range(n)).to_numpy())
    assert np.array_equal(panel["matchday"].to_numpy(), home_seq)
    assert home_seq.min() == 1 and home_seq.max() == 38


def test_h3_invariant_to_post_match_shuffle(panel):
    """T1.9 核心：打乱 FTR / 比分 / 射门后，三列必须逐元素不变。"""
    assert h3_invariant_to_post_match(panel)


def test_alias_removes_17_false_promoted_matches(panel):
    """归一前把改名队误判成升班马；归一后减少 17 场（home 列）。"""
    unnormalized = panel.copy()
    unnormalized["home"] = unnormalized["HomeTeam"]
    unnormalized["away"] = unnormalized["AwayTeam"]
    before = int(add_h3_features(unnormalized)["is_promoted_home"].sum())
    after = int(panel["is_promoted_home"].sum())
    assert before == 6_367 and after == 6_350
    assert before - after == 17


def test_five_tuple_unique_for_future_match_id(panel):
    assert int(panel.duplicated(["league", "season", "date", "home", "away"]).sum()) == 0


def test_s2_selfcheck_all_green():
    result = s2_selfcheck()                     # 不落盘，只跑断言
    assert result["passed"] == result["total"] == 13
    assert result["rows"] == 46_507
    assert result["alias_rows"] == 243
    assert result["canonical_names"] == 241
    assert result["dupes"] == 0
    assert result["h3_invariant"] is True
