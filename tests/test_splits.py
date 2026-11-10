"""S4 / T1.5 验收测试：48 块 rolling-origin 切分契约 + T1.6 的前四条泄漏断言。

对应 M1 分工卡 §6 验收项 5 / 6 / 7、分工方案 v1.3 §5.1 与
`data_interface.md` §2 / §3。刻意**不依赖磁盘上的 panel.parquet**：
主表由 `build_panel()` 在内存里重建，切分由 `make_splits(panel)` 重算，
因此 clone 后直接 `pytest -q tests/` 也是全绿的。唯一例外是
`configs/splits.json` —— 它是**入库契约**，本来就应随 Git 分发。

运行：``pytest -q tests/test_splits.py``（项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    EXPECTED_EVAL_BLOCKS,
    EXPECTED_EVAL_ROWS,
    EXPECTED_EVAL_TOTALS,
    build_panel,
)
from src.splits import (  # noqa: E402
    BLOCK_FIELDS,
    EXPECTED_MIN_TRAIN_BLOCKS,
    MAX_N_NEW_TEAM,
    MIN_N_TRAIN,
    SPLITS_PATH,
    SCHEMA_VERSION,
    _serialise,
    load_splits,
    make_splits,
    resolve_split,
    s4_selfcheck,
    write_splits,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def panel():
    return build_panel()


@pytest.fixture(scope="module")
def splits(panel):
    return make_splits(panel)


@pytest.fixture(scope="module")
def blocks(splits):
    return splits["blocks"]


def test_contract_shape_and_fields(splits, blocks):
    """顶层结构 + 48 块，字段齐全、block_id 唯一、日期 / 赛季格式合规。"""
    assert splits["schema_version"] == SCHEMA_VERSION
    assert splits["n_blocks"] == EXPECTED_EVAL_BLOCKS == 48
    assert splits["n_test_total"] == EXPECTED_EVAL_ROWS == 16_733
    assert splits["n_train_min"] == MIN_N_TRAIN == 4_284
    assert len(blocks) == 48
    assert len({b["block_id"] for b in blocks}) == 48
    for b in blocks:
        assert tuple(b.keys()) == BLOCK_FIELDS
        assert b["block_id"] == f"{b['league']}|{b['season']}"
        assert b["season"] in EVAL_SEASONS
        assert len(b["season"]) == 7 and b["season"][4] == "/"
        for f in ("test_start", "test_end", "train_start", "train_end"):
            assert len(b[f]) == 10 and b[f][4] == "-" and b[f][7] == "-"
        assert b["train_start"] <= b["train_end"] < b["test_start"] <= b["test_end"]


def test_blocks_cover_six_leagues_eight_seasons(blocks, panel):
    """48 块 = 6 联赛 × 8 季，不多不少。"""
    expected = {(lg, s) for lg in sorted(panel["league"].unique())
                for s in EVAL_SEASONS}
    assert {(b["league"], b["season"]) for b in blocks} == expected
    assert len(expected) == 48


def test_test_bounds_equal_panel_min_max(blocks, panel):
    """test_start / test_end 必须与 panel 逐块 min / max 逐字符一致。"""
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]
    bounds = sub.groupby(["league", "season"])["date"].agg(["min", "max"])
    for b in blocks:
        row = bounds.loc[(b["league"], b["season"])]
        assert b["test_start"] == row["min"]
        assert b["test_end"] == row["max"]


def test_n_test_matches_panel_and_totals(blocks, panel):
    """T1.3-a：n_test 逐块等于 panel 计数，合计 16,733、逐联赛合计全对。"""
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]
    counts = sub.groupby(["league", "season"]).size().to_dict()
    assert all(b["n_test"] == counts[(b["league"], b["season"])] for b in blocks)
    assert sum(b["n_test"] for b in blocks) == EXPECTED_EVAL_ROWS
    by_league = {lg: sum(b["n_test"] for b in blocks if b["league"] == lg)
                 for lg in EXPECTED_EVAL_TOTALS}
    assert by_league == EXPECTED_EVAL_TOTALS


def test_test_blocks_are_disjoint_and_complete(blocks, panel):
    """T1.6 断言②：48 块 test 两两不重叠；并集恰好覆盖评估窗（0 漏 0 重）。"""
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]
    sets = [set(panel.loc[(panel["league"] == b["league"])
                          & (panel["season"] == b["season"]), "match_id"])
            for b in blocks]
    union = set().union(*sets)
    assert sum(len(s) for s in sets) == len(union) == EXPECTED_EVAL_ROWS
    assert union == set(sub["match_id"])


def test_train_strictly_earlier_and_same_league(blocks, panel):
    """T1.6 断言①：train 末日 < test 首日；train 限同联赛；train 无目标季及之后。"""
    for b in blocks:
        train, _ = resolve_split(panel, b)
        assert b["train_end"] < b["test_start"]
        assert str(train["date"].max()) == b["train_end"]
        assert (train["league"] == b["league"]).all()
        assert int((train["season"] >= b["season"]).sum()) == 0
        assert int((train["date"] >= b["test_start"]).sum()) == 0


def test_train_and_test_never_overlap(blocks, panel):
    """按 match_id 判定 train ∩ test = ∅（不是按行号，也不是按日期近似）。"""
    for b in blocks:
        train, test = resolve_split(panel, b)
        assert set(train["match_id"]).isdisjoint(set(test["match_id"]))


def test_two_filter_rules_are_equivalent(blocks, panel):
    """「date < test_start」与「season 严格更早」必须得到同一批 match_id。

    这是把「rolling-origin」写死成可复核规则的关键：若赛季日期重叠，
    两种口径会分叉，说明切分定义需要人工复核，不能静默选一个。
    """
    for b in blocks:
        train, _ = resolve_split(panel, b)
        by_season = panel.loc[(panel["league"] == b["league"])
                              & (panel["season"] < b["season"])]
        assert set(train["match_id"]) == set(by_season["match_id"])
        assert len(train) == len(by_season)


def test_n_train_lower_bound(blocks):
    """T1.6 断言③：每块 n_train ≥ 4,284；最紧的两块恰是 1718_D1 / 1718_N1。"""
    assert all(b["n_train"] >= MIN_N_TRAIN for b in blocks)
    smallest = {(b["league"], b["season"]) for b in blocks
                if b["n_train"] == min(x["n_train"] for x in blocks)}
    assert min(b["n_train"] for b in blocks) == MIN_N_TRAIN
    assert smallest == EXPECTED_MIN_TRAIN_BLOCKS


def test_n_new_team_is_flagged_not_forbidden(blocks):
    """T1.6 断言④：升班马要被标记，不是断言它不存在；评估窗实测最大 2。"""
    values = [b["n_new_team"] for b in blocks]
    assert all(0 <= v <= MAX_N_NEW_TEAM for v in values)
    assert max(values) == 2, "历史累积 train 口径下评估窗最大 2，≤3 的界成立"
    assert sum(1 for v in values if v > 0) == 20, "确实存在新队，契约不能假装没有"


def test_resolve_split_recomputes_every_block(blocks, panel):
    """给 M2 harness 的入口：48 块逐块按规则复算，行数与边界与契约一致。"""
    for b in blocks:
        train, test = resolve_split(panel, b)
        assert len(train) == b["n_train"]
        assert len(test) == b["n_test"]
        assert str(test["date"].min()) == b["test_start"]
        assert str(test["date"].max()) == b["test_end"]


def test_resolve_split_rejects_tampered_contract(blocks, panel):
    """把 test_start 往后挪会悄悄多给 train 一批比赛 → 必须当场抛错。"""
    bad = copy.deepcopy(blocks[0])
    bad["test_start"] = "2025-01-01"
    with pytest.raises(ValueError, match="与契约|不符|泄漏"):
        resolve_split(panel, bad)


def test_make_splits_is_deterministic(panel):
    """同一 panel 两次生成：对象相等、序列化逐字节相等、无时间戳字段。"""
    a, b = make_splits(panel), make_splits(panel)
    assert a == b
    text = _serialise(a)
    assert text == _serialise(b)
    assert text.endswith("\n") and "\r" not in text
    assert "timestamp" not in text.lower() and "generated_at" not in text.lower()


def test_write_and_load_roundtrip(splits, tmp_path):
    """写盘 → 读回对象相等；UTF-8 / LF、可 diff。"""
    target = tmp_path / "splits.json"
    info = write_splits(splits, target)
    assert info["n_blocks"] == 48 and info["bytes"] > 0
    assert load_splits(target) == splits
    assert json.loads(target.read_text(encoding="utf-8")) == splits
    assert b"\r\n" not in target.read_bytes()


def test_load_splits_rejects_broken_contract(tmp_path):
    """schema_version 错 / 缺字段 / 块数不是 48 都要拒读，不能静默放行。"""
    good = copy.deepcopy(make_splits(build_panel()))
    bad_version = copy.deepcopy(good)
    bad_version["schema_version"] = "0.1"
    p1 = tmp_path / "v.json"
    p1.write_text(json.dumps(bad_version), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_splits(p1)

    missing_field = copy.deepcopy(good)
    del missing_field["blocks"][0]["n_train"]
    p2 = tmp_path / "m.json"
    p2.write_text(json.dumps(missing_field), encoding="utf-8")
    with pytest.raises(ValueError, match="缺字段"):
        load_splits(p2)

    short = copy.deepcopy(good)
    short["blocks"] = short["blocks"][:47]
    p3 = tmp_path / "s.json"
    p3.write_text(json.dumps(short), encoding="utf-8")
    with pytest.raises(ValueError, match="48"):
        load_splits(p3)


def test_on_disk_contract_matches_regenerated(panel):
    """入库的 configs/splits.json 必须与脚本重生成的完全一致（禁止手工漂移）。"""
    assert SPLITS_PATH.exists(), "configs/splits.json 是入库契约，clone 后必须存在"
    assert load_splits() == make_splits(panel)


def test_splits_json_is_tracked_and_panel_is_not():
    """入库 / 不入库的边界：契约 ✅ 入库，Parquet ❌ 忽略。"""
    tracked = subprocess.run(["git", "check-ignore", "-q", "configs/splits.json"],
                             cwd=ROOT, capture_output=True)
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "data/processed/panel.parquet"],
        cwd=ROOT, capture_output=True)
    assert tracked.returncode != 0, "splits.json 必须入库，不能被 .gitignore 命中"
    assert ignored.returncode == 0, "panel.parquet 必须仍被忽略（README §3.6）"


def test_s4_selfcheck_all_green():
    """12 项硬断言，不落盘（正式产物由 --stage s4 生成）。"""
    result = s4_selfcheck()
    assert result["passed"] == result["total"] == 12
    assert result["n_blocks"] == 48
    assert result["n_test_total"] == EXPECTED_EVAL_ROWS
    assert result["n_train_min"] == MIN_N_TRAIN
    assert result["n_new_team_max"] == 2
    assert result["identical"] is True
    assert result["disk_ok"] is True
    assert result["written"] is None
