"""M2 / T2.8 主推断表验收：9 行、行序、关键数字、pending_M4 标注。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from src.eval.table_main import ARMS, build_table_main  # noqa: E402


def _has_preds() -> bool:
    d = Path(__file__).resolve().parents[1] / "results" / "preds"
    return (d / "preds_B4.csv").exists() and (d / "preds_B6.csv").exists()


@pytest.mark.skipif(not _has_preds(), reason="预测文件未生成")
def test_table_main_nine_rows_and_order():
    tm = build_table_main()
    assert tm["arm"].tolist() == ARMS
    assert len(tm) == 9


@pytest.mark.skipif(not _has_preds(), reason="预测文件未生成")
def test_table_main_key_numbers():
    tm = build_table_main().set_index("arm")
    assert tm.loc["B4", "log_loss"] == pytest.approx(0.9939, abs=0.005)
    assert tm.loc["B6", "log_loss"] == pytest.approx(0.9585, abs=0.005)
    assert tm.loc["B3", "log_loss"] == pytest.approx(0.9986, abs=0.005)
    # 每行都有 deff（除 pending 行外）
    for arm in ("B3", "B4", "B6", "B6r"):
        assert tm.loc[arm, "deff"] > 0
        assert tm.loc[arm, "log_loss"] > 0


@pytest.mark.skipif(not _has_preds(), reason="预测文件未生成")
def test_table_main_m4_arms_filled_after_delivery():
    # M4（B0/B1/B2/B5a/B5b）已于 2026-11-11 交付预测文件；行应已填充而非 pending_M4
    preds = Path(__file__).resolve().parents[1] / "results" / "preds"
    for arm in ("B0", "B1", "B2", "B5a", "B5b"):
        if not (preds / f"preds_{arm}.csv").exists():
            pytest.skip(f"preds_{arm}.csv 缺失")
    tm = build_table_main().set_index("arm")
    for arm in ("B0", "B1", "B2", "B5a", "B5b"):
        assert tm.loc[arm, "note"] == ""
        assert tm.loc[arm, "log_loss"] > 0
        assert tm.loc[arm, "deff"] > 0
        assert tm.loc[arm, "n_matches"] > 0
    assert tm.loc["B6", "note"] == ""
