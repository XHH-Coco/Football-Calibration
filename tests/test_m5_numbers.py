"""守门测试：报告正文里的每个关键数字都必须等于产物 CSV 里的值。

`src/report/m5_report_tables.py` 的三条来历写在它的模块 docstring 里：2026-11-24 一天之内
犯过三次同类事故（摘要/幻灯片的 B4 差距写成 0.035、§5.2 的 ECE 方向写反、页 8 的 H4 数字
过期），三次都通过了 `pytest` / `check_m4` / `m3_report_tables --check`——那三道关卡检查的是
代码与产物，没有一道检查**正文数字**。

这个测试把校验器接进 `pytest`，于是「改了模型没改正文」和「改了正文没改模型」都会红。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.report.m5_report_tables import main  # noqa: E402


def test_report_numbers_match_artifacts(capsys):
    code = main([])
    out = capsys.readouterr().out
    assert code == 0, "报告数字与产物不一致：\n" + "\n".join(
        line for line in out.splitlines() if line.startswith("FAIL"))


def test_checker_covers_the_three_historical_mistakes():
    """校验规则必须覆盖复盘里点名的三处事故，否则这个文件就是摆设。"""
    from src.report.m5_report_tables import build_checks

    checks, _ = build_checks()
    joined = " ".join(label for _f, label, *_ in checks)
    assert "B2 的 H2 差距" in joined      # 事故 1：头条挂在 B4 上、数字写成 0.035
    assert "§5.4 · H4 相对变化" in joined   # 事故 3：页 8 的 0.0017 / 0.011
    assert "§5.2 · H1 主斜率与区间" in joined  # 事故 2 所在章节，至少斜率一侧被钉住
