"""S1 / T1.2-a 验收测试：稳健读取器 read_raw()。

对应 M1 分工卡 §6 验收项 2a。运行：``pytest -q tests/test_read_raw.py``。
仓库未打包（无 pyproject / setup.cfg），pytest 从任意目录启动时需显式把仓库根
加入 sys.path，后续 S5 的三份测试沿用同一写法。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.build_panel import (  # noqa: E402
    KEEP,
    ODDS_COLS,
    RAW_DIR,
    read_all,
    read_raw,
    selfcheck,
)


def test_132_files_readable_with_fixed_schema():
    files = sorted(RAW_DIR.glob("*.csv"))
    assert len(files) == 132, "S0 已确认快照为 132 个 CSV"
    for path in files:
        frame = read_raw(path)                       # 任何一个抛异常即失败
        assert list(frame.columns) == list(KEEP) + ["season"]
        assert len(frame) > 0
        assert frame["season"].str.match(r"^\d{4}/\d{2}$").all()


def test_whitelist_column_names_are_unique():
    assert len(set(KEEP)) == len(KEEP)
    assert len(set(KEEP + ("season",))) == len(KEEP) + 1


def test_row_count_conservation_46518_minus_11():
    panel = read_all()
    assert len(panel) == 46_507
    assert set(panel["FTR"].unique()) <= {"H", "D", "A"}
    assert panel["Div"].notna().all()
    assert panel[["FTHG", "FTAG"]].notna().all().all()
    assert pd.to_datetime(
        panel["Date"], dayfirst=True, format="mixed", errors="coerce"
    ).notna().all()


def test_missing_odds_columns_are_nan_not_keyerror():
    frame = read_raw(RAW_DIR / "0304_E0.csv")       # 前 9 季根本没有这三列
    assert frame[list(ODDS_COLS)].isna().all().all()
    assert list(frame.attrs["missing_odds_cols"]) == list(ODDS_COLS)
    assert frame.attrs["n_header_cols"] < 60


def test_ragged_rows_are_kept_and_columns_stay_aligned():
    frame = read_raw(RAW_DIR / "0304_F1.csv")       # 表头 41 列，行长 39–52 列
    assert len(frame) == 380, "on_bad_lines='skip' 会丢掉 365 场，必须保留"
    assert frame.attrs["n_short_rows"] == 208
    assert frame.attrs["n_long_rows"] == 157
    assert set(frame["FTR"].unique()) <= {"H", "D", "A"}
    assert pd.to_datetime(
        frame["Date"], dayfirst=True, format="mixed", errors="coerce"
    ).notna().all()


def test_latin1_fallback_only_for_0405_E0():
    frame = read_raw(RAW_DIR / "0405_E0.csv")
    assert frame.attrs["encoding"] == "latin-1"
    assert frame["HomeTeam"].notna().all()
    assert read_raw(RAW_DIR / "2425_E0.csv").attrs["encoding"] == "utf-8-sig"


def test_selfcheck_all_green():
    result = selfcheck()                            # 不落盘，只跑断言
    assert result["passed"] == result["total"]
    assert result["files"] == 132
    assert result["rows"] == 46_507
    assert result["bad_cells"] == 0, "短行错位会让 FTR / 日期 / 比分出现非法值"
    assert result["overflow_cells"] > 0, "必须真的覆盖到长行，否则断言形同虚设"
    assert result["nonempty_overflow"] == 0, "行尾溢出出现非空值 = 可能静默丢信息"


def test_overflow_cells_are_empty_in_every_raw_file():
    """r2 补强：全库 132 文件的行尾溢出必须 100% 为空（实测 2,895 格）。"""
    total_overflow = 0
    for path in sorted(RAW_DIR.glob("*.csv")):
        attrs = read_raw(path).attrs
        assert attrs["n_nonempty_overflow"] == 0, path.name
        total_overflow += attrs["n_overflow_cells"]
    assert total_overflow > 0


def test_nonempty_overflow_raises(tmp_path):
    """构造 4 格数据行 + 3 列表头，且溢出格非空 —— 必须当场拒绝。"""
    fake = tmp_path / "2425_E0.csv"
    fake.write_text(
        "Div,Date,HomeTeam\n"
        "E0,16/08/24,Arsenal,LEAKED_VALUE\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="非空"):
        read_raw(fake)


def test_empty_overflow_is_accepted(tmp_path):
    """对照组：同样多出的格子若是空的，应正常读入且不丢行。"""
    fake = tmp_path / "2425_E0.csv"
    fake.write_text(
        "Div,Date,HomeTeam\n"
        "E0,16/08/24,Arsenal,,\n",
        encoding="utf-8",
    )
    frame = read_raw(fake)
    assert len(frame) == 1
    assert frame.attrs["n_overflow_cells"] == 2
    assert frame.attrs["n_nonempty_overflow"] == 0
    assert frame.loc[0, "HomeTeam"] == "Arsenal"
