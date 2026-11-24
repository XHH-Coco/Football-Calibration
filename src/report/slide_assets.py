#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为幻灯片裁切 `products/figures/` 的成品图，产出 `products/slides/Market-Audit/assets/`。

放在 src/report/ 而非 scripts/：仓库 `.gitignore` 整体忽略 scripts/（见 README §4.2），
放那里会导致这份资产无法从仓库重建。

为什么需要它：报告用的成品图在图片内部带了 `figNN · ...` 的总标题，而幻灯片每页
自有页标题，二者叠加会重复；`fig08` 是 H3/H4 双面板，幻灯片页 7 与页 8 各只取一半。
本脚本只做**裁切**，不改任何像素内容，因此不会与报告图产生口径分歧。

只依赖 Pillow（matplotlib 的附属依赖），不新增锁定依赖。

用法：
    python -m src.report.slide_assets            # 生成并打印产物清单
    python -m src.report.slide_assets --check    # 只校验产物是否存在且尺寸正确
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "products" / "figures"
DST = ROOT / "products" / "slides" / "Market-Audit" / "assets"

# (源文件, 输出名, 左, 上, 右, 下)；右/下为 None 表示取到边界。
# 上边界的取值口径：切在「图内总标题」与「面板小标题」之间的空白带，保留面板小标题。
CROPS = [
    ("fig04_c_equivalence.png", "fig04.png", 0, 30, None, None),
    ("fig05_model_reliability.png", "fig05.png", 0, 90, None, None),
    ("fig06_market_calibration.png", "fig06.png", 0, 88, None, None),
    ("fig07_market_gap.png", "fig07.png", 0, 42, None, None),
    # fig08 双面板：左＝H3 系数，右＝H4 相对变化。切点落在两面板之间的空白，右侧
    # 保留 70px 重叠，避免切掉右面板的 y 轴类别标签。
    ("fig08_localisation_recal.png", "fig08_left.png", 0, 78, 1858, None),
    ("fig08_localisation_recal.png", "fig08_right.png", 1838, 78, None, None),
]


def main() -> int:
    check = "--check" in sys.argv
    DST.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, out, left, top, right, bottom in CROPS:
        src = SRC / name
        dst = DST / out
        if not src.exists():
            print(f"MISSING SOURCE: {src}")
            return 1
        im = Image.open(src)
        box = (
            left,
            top,
            right if right is not None else im.width,
            bottom if bottom is not None else im.height,
        )
        if check:
            if not dst.exists():
                print(f"MISSING OUTPUT: {dst.name}")
                return 1
            got = Image.open(dst).size
            want = (box[2] - box[0], box[3] - box[1])
            if got != want:
                print(f"SIZE MISMATCH: {dst.name} {got} != {want}")
                return 1
            rows.append((dst.name, *got))
            continue
        im.crop(box).save(dst, optimize=True)
        rows.append((dst.name, box[2] - box[0], box[3] - box[1]))

    print(f"{'asset':<18}{'w':>6}{'h':>7}{'ratio':>8}")
    for name, w, h in rows:
        print(f"{name:<18}{w:>6}{h:>7}{w / h:>8.2f}")
    print(f"\n{len(rows)} assets -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
