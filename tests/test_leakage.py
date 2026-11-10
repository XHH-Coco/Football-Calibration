"""M1 / T1.6（S5）—— **全组安全带**：五条防泄漏断言集中在一个文件。

分工方案 v1.3 §3.1 把前四条写在 `tests/test_splits.py`、第五条写在
`tests/test_panel_counts.py`（各自随 S3/S4 落地）。本文件是 G1 前补齐的
**独立入口**：只读入库契约 `configs/splits.json` + 内存重建的 `panel`，
按规则独立复算，不复用那两个测试文件的中间结果。`pytest -q tests/test_leakage.py`
变红 = 全组立刻停工，不许在红的测试上继续建模。

运行：``pytest -q tests/test_leakage.py``（项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    EXPECTED_B6_ROWS,
    EXPECTED_EVAL_BLOCKS,
    EXPECTED_EVAL_ROWS,
    EXPECTED_ODDS_MISSING_BLOCKS,
    ODDS_COLS,
    build_panel,
)
from src.splits import (  # noqa: E402
    EXPECTED_MIN_TRAIN_BLOCKS,
    MAX_N_NEW_TEAM,
    MIN_N_TRAIN,
    load_splits,
    resolve_split,
)


@pytest.fixture(scope="module")
def panel():
    return build_panel()


@pytest.fixture(scope="module")
def blocks():
    return load_splits()["blocks"]


def _recompute(panel, block):
    """按契约规则独立复算，故意不走 resolve_split()（那是被测对象之一）。"""
    test = panel.loc[(panel["league"] == block["league"])
                     & (panel["season"] == block["season"])]
    train = panel.loc[(panel["league"] == block["league"])
                      & (panel["date"] < block["test_start"])]
    return train, test


def test_01_train_is_strictly_before_test(panel, blocks):
    """① train 最大日期 < test 最小日期；train 不含目标季及之后、不含别的联赛。"""
    assert len(blocks) == EXPECTED_EVAL_BLOCKS == 48
    for b in blocks:
        train, test = _recompute(panel, b)
        assert len(train) == b["n_train"] and len(test) == b["n_test"]
        assert str(train["date"].max()) < str(test["date"].min())
        assert not (train["season"] >= b["season"]).any(), b["block_id"]
        assert set(train["league"]) <= {b["league"]}, b["block_id"]
        assert set(train["match_id"]).isdisjoint(set(test["match_id"]))


def test_02_test_blocks_are_disjoint_and_complete(panel, blocks):
    """② 48 块 test 两两不重叠，且并集恰为评估窗 16,733 场（0 漏 0 重）。"""
    sets = [set(_recompute(panel, b)[1]["match_id"]) for b in blocks]
    union = set().union(*sets)
    assert sum(len(s) for s in sets) == len(union) == EXPECTED_EVAL_ROWS == 16_733
    expected = set(panel.loc[panel["season"].isin(EVAL_SEASONS), "match_id"])
    assert union == expected


def test_03_n_train_lower_bound(panel, blocks):
    """③ 每块 n_train ≥ 4,284（实测下界，原 > 2000 写了等于没写）。"""
    sizes = {b["block_id"]: len(_recompute(panel, b)[0]) for b in blocks}
    assert min(sizes.values()) == MIN_N_TRAIN == 4_284
    tightest = {(b["league"], b["season"]) for b in blocks
                if sizes[b["block_id"]] == MIN_N_TRAIN}
    assert tightest == EXPECTED_MIN_TRAIN_BLOCKS


def test_04_new_teams_are_flagged_not_forbidden(panel, blocks):
    """④ 升班马要「显式标记」，不是断言不存在：每块 ≤ 3，实测最大 2、20 块非零。"""
    counts = []
    for b in blocks:
        train, test = _recompute(panel, b)
        seen = set(train["home"]) | set(train["away"])
        new = (set(test["home"]) | set(test["away"])) - seen
        assert len(new) == b["n_new_team"], b["block_id"]
        counts.append(len(new))
    assert max(counts) <= MAX_N_NEW_TEAM == 3
    assert max(counts) == 2 and sum(1 for c in counts if c > 0) == 20


def test_05_odds_missing_exactly_five(panel):
    """⑤ 评估窗三列收盘赔率缺 5 场，按块分布固定；B6 / B6r 有效 n = 16,728。"""
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]
    assert len(sub) == EXPECTED_EVAL_ROWS == 16_733
    missing = sub.loc[sub[list(ODDS_COLS)].isna().any(axis=1)]
    by_block = {k: int(v) for k, v in
                missing.groupby(["league", "season"]).size().to_dict().items()}
    assert len(missing) == 5
    assert by_block == EXPECTED_ODDS_MISSING_BLOCKS
    assert len(sub) - len(missing) == EXPECTED_B6_ROWS == 16_728
    # 缺值不回填：三列同时缺，且该场比分与 y 仍在
    assert missing[list(ODDS_COLS)].isna().all().all()
    assert missing[["FTR", "FTHG", "FTAG", "y"]].notna().all().all()


def test_06_disk_contract_matches_rule(panel, blocks):
    """附加：磁盘契约每块都能被 resolve_split() 复算通过（篡改会当场拒读）。"""
    for b in blocks:
        train, test = resolve_split(panel, b)
        assert len(train) == b["n_train"] and len(test) == b["n_test"]
