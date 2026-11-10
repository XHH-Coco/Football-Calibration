"""S3 / T1.3 + T1.3-a 验收测试：场次核查表 + 建模总表契约。

对应 M1 分工卡 §6 验收项 2 / 3 / 4 / 8 与 `data_interface.md` §1.0 / §1.1。
刻意**不依赖磁盘上的 panel.parquet**：主表由 `build_panel()` 在内存里重建，
落盘单独用 `tmp_path` 验证，因此 clone 后直接 `pytest -q tests/` 也是全绿的。

运行：``pytest -q tests/test_panel_counts.py``（项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    EXPECTED_B6_ROWS,
    EXPECTED_EVAL_BLOCKS,
    EXPECTED_EVAL_ROWS,
    EXPECTED_EVAL_TOTALS,
    EXPECTED_LEAGUE_TOTALS,
    EXPECTED_ODDS_MISSING_BLOCKS,
    EXPECTED_SHORT_BLOCKS,
    H3_PANEL_COLS,
    LABEL_MAP,
    ODDS_COLS,
    PANEL_COLUMNS,
    SORT_KEYS,
    build_panel,
    h3_invariant_to_post_match,
    make_match_id,
    s3_selfcheck,
    write_panel,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def panel():
    return build_panel()


@pytest.fixture(scope="module")
def sub(panel):
    """评估窗 2017/18–2024/25 × 6 联赛 = 48 块 / 16,733 场。"""
    return panel.loc[panel["season"].isin(EVAL_SEASONS)]


def test_panel_shape_and_column_order(panel):
    """22 列窄表，顺序即契约；不把 Max* 或其他赔率列带进来。"""
    assert len(panel) == 46_507
    assert list(panel.columns) == list(PANEL_COLUMNS)
    assert len(PANEL_COLUMNS) == 22
    assert not any(c.startswith("Max") for c in panel.columns)
    assert "Date" not in panel.columns and "HomeTeam" not in panel.columns, \
        "raw 原始列只留在 S1/S2 中间表，不进建模总表"


def test_match_id_contract(panel):
    """§1.0：唯一、非空、5 段、可由 f-string 公式逐字符复算。"""
    ids = panel["match_id"]
    assert ids.is_unique
    assert ids.notna().all()
    assert ids.str.count(r"\|").eq(4).all()
    recomputed = (panel["league"].astype(str) + "|" + panel["season"] + "|"
                  + panel["date"] + "|" + panel["home"] + "|" + panel["away"])
    assert ids.equals(recomputed), "preds_*.csv 必须能用同一公式生成同一串"
    assert ids.str.contains(r"\d{2}/\d{2}/\d{4}").sum() == 0, \
        "match_id 里不得出现 raw 的 dd/mm/yy 日期"


def test_match_id_joins_with_preds_style_frame(panel):
    """把前 20 行伪装成 preds_*.csv，用 match_id 内连接应逐行对上。

    这是 M2 配对差的前提：不同模型少 5 场时按交集算，不是按行号硬拼。
    """
    head = panel.head(20)
    preds = pd.DataFrame({
        "match_id": (head["league"] + "|" + head["season"] + "|"
                     + head["date"] + "|" + head["home"] + "|" + head["away"]),
        "model": "B0",
        "p_home": 1 / 3, "p_draw": 1 / 3, "p_away": 1 / 3,
        "y": head["y"].to_numpy(),
    })
    joined = preds.merge(head[["match_id", "y", "date"]],
                         on="match_id", how="inner", suffixes=("_pred", "_panel"))
    assert len(joined) == len(head)
    assert np.array_equal(joined["y_pred"].to_numpy(), joined["y_panel"].to_numpy())


def test_match_id_duplicates_are_rejected():
    """重复五元组必须当场报错，绝不 dedup（会静默少比赛）。"""
    small = pd.DataFrame({
        "league": ["E0", "E0"], "season": ["2024/25", "2024/25"],
        "date": ["2024-08-16", "2024-08-16"],
        "home": ["Arsenal", "Arsenal"], "away": ["Chelsea", "Chelsea"],
    })
    with pytest.raises(ValueError, match="match_id 重复"):
        make_match_id(small)


def test_sorted_and_five_tuple_unique(panel):
    """按 league, season, date 排序；同日多场用 home/away 作稳定 tiebreak。"""
    keys = panel[list(SORT_KEYS)].reset_index(drop=True)
    resorted = (panel[list(SORT_KEYS)]
                .sort_values(list(SORT_KEYS), kind="mergesort")
                .reset_index(drop=True))
    assert keys.equals(resorted)
    assert int(panel.duplicated(["league", "season", "date", "home", "away"]).sum()) == 0


def test_y_encoding(panel):
    assert np.array_equal(panel["y"].to_numpy(),
                          panel["FTR"].map(LABEL_MAP).to_numpy())
    assert set(panel["y"].unique()) <= {0, 1, 2}
    assert panel["y"].value_counts().sort_index().to_dict() == {
        0: 21_194, 1: 11_824, 2: 13_489,
    }


def test_iso_dates_and_season_format(panel):
    """date 必须是 ISO **字符串**，不能是 datetime64（否则 preds 内连接会漂移）。"""
    assert panel["date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
    assert panel["date"].min() == "2003-08-01"
    assert panel["date"].max() == "2025-05-25"
    assert panel["season"].str.match(r"^\d{4}/\d{2}$").all()
    assert len(panel.groupby(["league", "season"])) == 132


def test_h3_columns_present_and_leak_free(panel):
    assert all(c in panel.columns for c in H3_PANEL_COLS)
    assert panel[list(H3_PANEL_COLS)].notna().all().all()
    assert panel["matchday"].between(1, 38).all()
    assert h3_invariant_to_post_match(panel), \
        "打乱赛后列后 H3 三列必须逐元素不变（T1.9）"


def test_odds_coverage_and_b6_sample(panel, sub):
    """0304–1112 三列整列不存在；评估窗只缺 3 块共 5 场，B6 有效 16,728。"""
    assert panel.loc[panel["season"] <= "2011/12", list(ODDS_COLS)].isna().all().all()
    missing = sub[list(ODDS_COLS)].isna().any(axis=1)
    assert int(missing.sum()) == 5
    assert sub.loc[missing].groupby(["league", "season"]).size().to_dict() \
        == EXPECTED_ODDS_MISSING_BLOCKS
    assert len(sub) - int(missing.sum()) == EXPECTED_B6_ROWS


def test_block_count_rule(panel):
    """T1.3-a：n 队联赛满额 = n*(n−1)（双循环），只有 2 个真实腰斩块例外。"""
    teams: dict[tuple[str, str], set[str]] = {}
    for lg, s, h, a in zip(panel["league"], panel["season"],
                           panel["home"], panel["away"]):
        teams.setdefault((lg, s), set()).update((h, a))
    rows = panel.groupby(["league", "season"]).size().to_dict()
    assert len(teams) == 132
    for key, names in teams.items():
        expected = EXPECTED_SHORT_BLOCKS.get(key, len(names) * (len(names) - 1))
        assert rows[key] == expected, f"{key}: 实测 {rows[key]} 场，期望 {expected}"


def test_known_short_blocks(panel):
    """法甲 / 荷甲 2019/20 腰斩；法甲 2023/24 起 18 队 306 场不是缺赛。"""
    rows = panel.groupby(["league", "season"]).size().to_dict()
    assert rows[("F1", "2019/20")] == 279
    assert rows[("N1", "2019/20")] == 232
    assert rows[("F1", "2023/24")] == 306
    assert rows[("F1", "2024/25")] == 306
    assert rows[("E0", "2024/25")] == 380


def test_league_totals_and_eval_window(panel, sub):
    """六联赛 22 季合计 46,507；评估窗 48 块 16,733，且逐联赛合计全对。"""
    assert panel.groupby("league").size().to_dict() == EXPECTED_LEAGUE_TOTALS
    assert sub.groupby("league").size().to_dict() == EXPECTED_EVAL_TOTALS
    assert sum(EXPECTED_LEAGUE_TOTALS.values()) == 46_507
    assert len(sub) == EXPECTED_EVAL_ROWS
    assert sub.groupby(["league", "season"]).ngroups == EXPECTED_EVAL_BLOCKS


def test_parquet_roundtrip(panel, tmp_path):
    """落盘后读回必须逐元素相等（列序 / dtype / 值），且 index 不额外成列。"""
    target = tmp_path / "panel.parquet"
    info = write_panel(panel, target)
    back = pd.read_parquet(target)
    pd.testing.assert_frame_equal(back, panel)
    assert info["rows"] == 46_507 and info["cols"] == 22
    assert info["bytes"] > 0


def test_panel_is_ignored_by_git(panel):
    """README §3.6：主表不入库，靠「同一脚本 → 同一张表」分发。"""
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.parquet" in text and "/data/processed/*" in text
    proc = subprocess.run(
        ["git", "check-ignore", "-q", "data/processed/panel.parquet"],
        cwd=ROOT, capture_output=True,
    )
    assert proc.returncode == 0, "panel.parquet 必须被 Git 忽略"


def test_s3_selfcheck_all_green():
    """12 项硬断言，不落盘（正式产物由 CLI --stage s3 生成）。"""
    result = s3_selfcheck()
    assert result["passed"] == result["total"] == 12
    assert result["rows"] == 46_507
    assert result["cols"] == 22
    assert result["eval_rows"] == EXPECTED_EVAL_ROWS
    assert result["b6_rows"] == EXPECTED_B6_ROWS
    assert result["blocks"] == 132
    assert result["roundtrip"] is True
    assert result["reproducible"] is True
    assert result["written"] is None
