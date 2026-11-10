"""M1 / T1.4（S5）验收：覆盖率矩阵必须**直接读 raw**，四条事实逐条可复算。

分工方案 v1.3 §3.1 T1.4 说「若你的图和这三条不符，先查列名拼写」。
S5 实测还发现第 4 条：评估窗射门列并非 100%（`2425_D1` 缺 1 场）。
本文件把四条事实连同这个订正一起钉成断言。

运行：``pytest -q tests/test_coverage.py``（项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    EXPECTED_B6_ROWS,
    EXPECTED_ODDS_MISSING_BLOCKS,
    EXPECTED_ROWS,
    ODDS_COLS,
    read_all,
)
from src.coverage import (  # noqa: E402
    COVERAGE_COLUMNS,
    EVAL_SHOT_CHECK_COLS,
    FIG_PATH,
    HALFTIME_COLS,
    MATRIX_FIELDS,
    MATRIX_PATH,
    MAX_COLS,
    MAX_FIRST_SEASON,
    N1_SHOT_FIRST_FULL,
    ODDS_FIRST_SEASON,
    PRE_ODDS_SEASONS,
    SHOT_COLS,
    build_coverage_matrix,
    coverage_facts,
    coverage_selfcheck,
    write_coverage_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def raw():
    return read_all()


@pytest.fixture(scope="module")
def mat(raw):
    return build_coverage_matrix(raw)


def test_01_matrix_shape_and_totals(mat):
    assert list(mat.columns) == list(MATRIX_FIELDS)
    assert len(mat) == 132
    assert len(mat.groupby(["league", "season"])) == 132
    assert mat["league"].nunique() == 6 and mat["season"].nunique() == 22
    assert int(mat["n_matches"].sum()) == EXPECTED_ROWS == 46_507
    rates = mat[list(COVERAGE_COLUMNS)].to_numpy(dtype=float)
    assert np.isfinite(rates).all() and ((rates >= 0) & (rates <= 1)).all()


def test_02_core_result_columns_always_complete(mat):
    assert (mat[["FTHG", "FTAG", "FTR"]].to_numpy() == 1.0).all()


def test_03_closing_odds_start_2012_13(mat):
    pre = mat.loc[mat["season"].isin(PRE_ODDS_SEASONS)]
    assert len(pre) == 54                     # 9 季 × 6 联赛
    assert (pre[list(ODDS_COLS)].to_numpy() == 0).all()
    firsts = {lg: mat.loc[(mat["league"] == lg) & (mat["PSCH"] > 0), "season"].min()
              for lg in sorted(mat["league"].unique())}
    assert set(firsts.values()) == {ODDS_FIRST_SEASON}


def test_04_eval_window_odds_gaps(mat, raw):
    ev = raw.loc[raw["season"].isin(EVAL_SEASONS)]
    bad = ev.loc[ev[list(ODDS_COLS)].isna().any(axis=1)]
    by_block = {k: int(v) for k, v in
                bad.groupby(["Div", "season"]).size().to_dict().items()}
    assert len(ev) == 16_733 and len(bad) == 5
    assert by_block == EXPECTED_ODDS_MISSING_BLOCKS
    assert len(ev) - len(bad) == EXPECTED_B6_ROWS == 16_728
    full = mat.loc[mat["season"].isin(EVAL_SEASONS)]
    assert int((full["PSCH"] == 1).sum()) == 45


def test_05_n1_shots_start_2017_18_halftime_always_present(mat):
    n1 = mat.loc[mat["league"] == "N1"].sort_values("season")
    before = n1.loc[n1["season"] < N1_SHOT_FIRST_FULL]
    after = n1.loc[n1["season"] >= N1_SHOT_FIRST_FULL]
    assert len(before) == 14 and len(after) == 8
    assert (before[list(SHOT_COLS)].to_numpy() == 0).all()
    assert (after[list(SHOT_COLS)].to_numpy() == 1).all()
    # 半场比分不是射门列：全库 22 季都有，别混
    assert (n1[list(HALFTIME_COLS)].to_numpy() == 1).all()


def test_06_max_odds_start_2019_20(mat):
    before = mat.loc[mat["season"] < MAX_FIRST_SEASON]
    after = mat.loc[mat["season"] >= MAX_FIRST_SEASON]
    assert (before[list(MAX_COLS)].to_numpy() == 0).all()
    assert (after[list(MAX_COLS)].to_numpy() == 1).all()
    assert len(after) == 36                   # 6 联赛 × 6 季


def test_07_eval_window_shot_gap_is_exactly_one_match(raw):
    """S5 订正：评估窗射门列并非 100%，缺的恰好是 2425_D1 那一场。"""
    ev = raw.loc[raw["season"].isin(EVAL_SEASONS)]
    bad = ev.loc[ev[list(EVAL_SHOT_CHECK_COLS)].isna().any(axis=1)]
    assert len(bad) == 1
    assert (bad["Div"] == "D1").all() and (bad["season"] == "2024/25").all()
    assert bad.iloc[0]["HomeTeam"] == "Union Berlin"
    assert bad.iloc[0]["AwayTeam"] == "Bochum"
    assert bad[list(EVAL_SHOT_CHECK_COLS)].isna().all().all()
    assert bad[list(ODDS_COLS)].notna().all().all()   # 赔率齐全 → 不影响 B6
    assert bad[["FTHG", "FTAG", "FTR"]].notna().all().all()


def test_08_facts_are_machine_readable(raw, mat):
    f = coverage_facts(raw, mat)
    assert f["n_blocks"] == 132 and f["n_matches"] == 46_507
    assert f["odds_first_season"] == "2012/13"
    assert f["max_first_season"] == "2019/20"
    assert f["n1_shot_first_full"] == "2017/18"
    assert f["odds_full_eval_blocks"] == 45
    assert f["b6_effective_rows"] == 16_728
    assert f["eval_shot_missing_rows"] == 1
    assert f["eval_shot_rate"] == 0.99994


def test_09_disk_csv_equals_regenerated_matrix(mat):
    disk = pd.read_csv(MATRIX_PATH)
    assert list(disk.columns) == list(MATRIX_FIELDS)
    assert len(disk) == 132
    assert disk[["league", "season", "n_matches"]].equals(
        mat[["league", "season", "n_matches"]])
    assert np.allclose(disk[list(COVERAGE_COLUMNS)].to_numpy(),
                       mat[list(COVERAGE_COLUMNS)].to_numpy(), atol=1e-6)


def test_10_csv_is_byte_identical_on_rerun(mat, tmp_path):
    p1, p2 = tmp_path / "a.csv", tmp_path / "b.csv"
    write_coverage_matrix(mat, p1)
    write_coverage_matrix(mat, p2)
    assert hashlib.sha256(p1.read_bytes()).hexdigest() == \
           hashlib.sha256(p2.read_bytes()).hexdigest()
    assert MATRIX_PATH.read_bytes().startswith(b"league,season,n_matches,")


def test_11_figure_exists_and_is_png():
    assert FIG_PATH.exists()
    assert FIG_PATH.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert FIG_PATH.stat().st_size > 10_000


def test_12_never_reads_parquet(monkeypatch, raw):
    """把 pd.read_parquet 换成炸弹：覆盖率矩阵仍必须算得出来。"""
    def boom(*args, **kwargs):
        raise AssertionError("覆盖率矩阵不得读取 panel.parquet，必须直接读 raw")

    monkeypatch.setattr(pd, "read_parquet", boom)
    result = build_coverage_matrix(raw)
    assert len(result) == 132 and int(result["n_matches"].sum()) == 46_507


def test_13_selfcheck_all_green():
    r = coverage_selfcheck()
    assert r["passed"] == r["total"] == 12


def test_14_outputs_are_not_git_ignored():
    import subprocess
    for rel in ("results/coverage_matrix.csv",
                "products/figures/fig_data_coverage.png"):
        proc = subprocess.run(["git", "check-ignore", "-q", rel],
                              cwd=ROOT, capture_output=True)
        assert proc.returncode != 0, f"{rel} 被 .gitignore 挡住了"
