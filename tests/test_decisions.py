"""M2 判定层：H1–H4 / C1 的每一支分支都要走到（不是只在文档里写）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from src.eval.decisions import (  # noqa: E402
    EQUIV_MARGIN,
    H4_MIN_DENOM,
    H4_REL_THRESHOLD,
    _branch,
    c1_verdict,
    c2_verdict,
    controlled_verdict,
    h1_ordering_verdict,
    h1_verdict,
    h2_verdict,
    h3_verdict,
    h4_verdict,
)


def test_branch_four_cases():
    assert _branch(0.03, 0.025, 0.04) == "above"
    assert _branch(-0.03, -0.04, -0.025) == "below"
    assert _branch(0.001, -0.01, 0.01) == "equivalent"
    assert _branch(0.001, -0.03, 0.03) == "indeterminate"


def test_c1_four_branches():
    assert c1_verdict(0.001, -0.01, 0.01)["decision"] == "实际等价"
    assert c1_verdict(0.03, 0.025, 0.04)["decision"] == "B4 更好"
    assert c1_verdict(-0.03, -0.04, -0.025)["decision"] == "B5a 更好"
    assert "分辨率不足" in c1_verdict(0.0, -0.03, 0.03)["decision"]


def test_c2_four_branches_labels_are_c2_specific():
    assert c2_verdict(0.001, -0.01, 0.01)["decision"] == "实际等价"
    assert c2_verdict(0.03, 0.025, 0.04)["decision"] == "B5a 更好"
    assert c2_verdict(-0.03, -0.04, -0.025)["decision"] == "B5b 更好"
    assert "分辨率不足" in c2_verdict(0.0, -0.03, 0.03)["decision"]


def test_controlled_verdict_generic():
    v = controlled_verdict("X", "Y", 0.03, 0.025, 0.04)
    assert v["decision"] == "X 更好"
    v = controlled_verdict("X", "Y", -0.03, -0.04, -0.025)
    assert v["decision"] == "Y 更好"


def test_h1_slope_branches():
    assert h1_verdict(0.95, 0.90, 0.99)["decision"] == "证伪"
    assert h1_verdict(1.05, 1.02, 1.10)["decision"] == "支持"
    assert h1_verdict(1.01, 0.98, 1.05)["decision"] == "不确定"


def test_h1_ordering_claim_needs_lower_bound_above_zero():
    assert h1_ordering_verdict(0.03, 0.02, 0.05)["decision"] == "支持排序"
    assert h1_ordering_verdict(0.03, -0.01, 0.05)["decision"] == "不作排序宣称"


def test_h2_verdict_both_criteria():
    # B4 明显更差（Δ>0，95% 下界>0）+ 90% 区间整体 > +0.02 → 两判据都支持「追不上」
    v = h2_verdict(0.04, 0.01, 0.07, 0.025, 0.06)
    assert "支持(a)" in v["decision"] and "支持(b)" in v["decision"]
    # B4 明显更好（Δ<0，95% 上界<0）→ 判据(a) 证伪并提示查泄漏
    v2 = h2_verdict(-0.03, -0.05, -0.01, -0.04, -0.02)
    assert "证伪(a)" in v2["decision"] and "查泄漏" in v2["decision"]
    # 90% 区间完全落在 ±0.02 内 → 判据(b) 证伪（等价）
    v3 = h2_verdict(0.001, -0.02, 0.02, -0.01, 0.01)
    assert "证伪(b)" in v3["decision"]


def test_h3_requires_both_positive_and_lower_bounds_above_zero():
    assert h3_verdict(0.05, 0.02, 0.08, 0.03, 0.01, 0.05)["decision"] == "支持"
    assert h3_verdict(0.05, -0.01, 0.08, 0.03, 0.01, 0.05)["decision"] == "只作描述"
    assert h3_verdict(-0.05, -0.08, -0.02, 0.03, 0.01, 0.05)["decision"] == "只作描述"


def test_h4_thresholds_and_denominator_guard():
    # 上界 < 25% → 支持
    assert h4_verdict(0.10, 0.05, 0.20, denom_gap=0.05)["decision"] == "支持"
    # 下界 > 25% → 证伪
    assert h4_verdict(0.40, 0.30, 0.50, denom_gap=0.05)["decision"] == "证伪"
    # 跨 25% → 分辨率不足
    assert h4_verdict(0.30, 0.10, 0.40, denom_gap=0.05)["decision"] == "分辨率不足"
    # 分母过小 → 改报绝对差
    assert h4_verdict(0.5, 0.4, 0.6, denom_gap=0.005)["decision"] == "改报绝对差"


def test_threshold_constants_are_locked():
    assert EQUIV_MARGIN == 0.02
    assert H4_REL_THRESHOLD == 0.25
    assert H4_MIN_DENOM == 0.01
