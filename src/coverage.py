"""M1 / T1.4（S5）—— 覆盖率矩阵：**直接读 ``data/raw/``**，不经过 ``panel.parquet``。

为什么必须读 raw
----------------
``MaxCH/MaxCD/MaxCA`` 与部分射门列**不在 22 列建模总表里**（S3 有意不放，
见 ``data_interface.md`` §2：``Max*`` 不是市场基准，且会被误当成特征）。
从 ``panel.parquet`` 算覆盖率，这些列根本看不见，会得出「全库 0%」的假结论。
本模块复用 S1 的 ``read_all()``（按表头列名取 19 列白名单），逐
``(league, season)`` 统计 15 个关键列的**非空比例**，产出：

  * ``results/coverage_matrix.csv``   132 行宽表（入库，M5 写数据页用）
  * ``products/figures/fig_data_coverage.png``  6 联赛 × 22 季热力图（入库）

实测四条事实（2026-11-10，132 文件 / 46,507 场）
------------------------------------------------
1. ``PSCH/PSCD/PSCA`` 自 **2012/13** 起才有；前 9 季（0304–1112）整列缺失。
   评估窗 48 块中 **45 块满格**，另 3 块共缺 **5 场**
   （``1718_SP1`` 1 / ``1718_N1`` 3 / ``1819_D1`` 1）→ B6 / B6r 有效 n = 16,728。
2. 荷甲 ``N1`` 的**射门 4 列** ``HS/AS/HST/AST`` 在 0304–1617 全为 0，
   **2017/18 起满格**；但半场比分 ``HTHG/HTAG`` 全库 22 季都有——
   两者不是一回事，别混。
3. ``MaxCH/MaxCD/MaxCA`` 自 **2019/20** 起才有，6 个联赛一致，此前全为 0。
4. **订正（S5 新发现）**：评估窗射门列**并非 100% 可用**——
   ``2425_D1`` 的 ``Union Berlin vs Bochum``（2024-12-14）缺全部 6 个
   ``HTHG/HTAG/HS/AS/HST/AST``，但该场比分与三列收盘赔率齐全。
   评估窗射门覆盖率 = 16,732 / 16,733 = 0.999940。分工方案 v1.3 §3.1 T1.4
   旧稿「评估窗内射门列 100% 可用」据此订正；**任何以射门列为特征的 arm
   必须显式处理这一行，不能默认无 NaN**。

运行（项目环境 DSC5001_Project）
--------------------------------
    python src/coverage.py --log results/logs/s5_coverage_2026-11-10.txt
    pytest -q tests/test_coverage.py
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:                       # 允许 ``python src/coverage.py`` 直接跑
    sys.path.insert(0, str(ROOT))

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    EXPECTED_B6_ROWS,
    EXPECTED_BLOCKS,
    EXPECTED_EVAL_BLOCKS,
    EXPECTED_EVAL_ROWS,
    EXPECTED_ODDS_MISSING_BLOCKS,
    EXPECTED_ROWS,
    ODDS_COLS,
    read_all,
)

MATRIX_PATH = ROOT / "results" / "coverage_matrix.csv"
FIG_PATH = ROOT / "products" / "figures" / "fig_data_coverage.png"

# 顺序即 CSV 列顺序；身份列（Div/Date/HomeTeam/AwayTeam）恒 100%，不入矩阵。
COVERAGE_COLUMNS: tuple[str, ...] = (
    "FTHG", "FTAG", "FTR",
    "HTHG", "HTAG", "HS", "AS", "HST", "AST",
    "PSCH", "PSCD", "PSCA",
    "MaxCH", "MaxCD", "MaxCA",
)
SHOT_COLS: tuple[str, ...] = ("HS", "AS", "HST", "AST")          # 射门 4 列
HALFTIME_COLS: tuple[str, ...] = ("HTHG", "HTAG")                # 半场比分（**不是**射门）
EVAL_SHOT_CHECK_COLS: tuple[str, ...] = HALFTIME_COLS + SHOT_COLS  # 评估窗缺值核查用 6 列
MAX_COLS: tuple[str, ...] = ("MaxCH", "MaxCD", "MaxCA")
MATRIX_FIELDS: tuple[str, ...] = ("league", "season", "n_matches") + COVERAGE_COLUMNS

PRE_ODDS_SEASONS = tuple(f"{y}/{str(y + 1)[-2:]}" for y in range(2003, 2012))  # 0304–1112
ODDS_FIRST_SEASON = "2012/13"
MAX_FIRST_SEASON = "2019/20"
N1_SHOT_FIRST_FULL = "2017/18"
EVAL_SHOT_MISSING = {("D1", "2024/25"): 1}
EVAL_SHOT_MISSING_MATCH = ("D1", "2024/25", "14/12/2024",
                           "Union Berlin", "Bochum")


def build_coverage_matrix(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """逐 ``(league, season)`` 统计非空比例，返回 132 行宽表。

    用 ``groupby().count()``（自动忽略 NaN）而不是 ``notna().mean()`` 的
    ``apply`` 写法：前者在 pandas 3.x 返回稳定的 DataFrame，且不会因分组键
    为空列而变形。**全程不读 parquet**。
    """
    frame = read_all() if raw is None else raw
    grouped = frame.groupby(["Div", "season"], sort=True)
    n = grouped.size().rename("n_matches")
    counts = grouped[list(COVERAGE_COLUMNS)].count()
    rates = counts.div(n, axis=0).round(6)
    mat = rates.reset_index().rename(columns={"Div": "league"})
    n_table = n.reset_index().rename(columns={"Div": "league"})
    mat = mat.merge(n_table, on=["league", "season"], how="left",
                    validate="one_to_one")
    mat = mat[list(MATRIX_FIELDS)]
    mat["n_matches"] = mat["n_matches"].astype("int64")
    return mat.sort_values(["league", "season"], kind="mergesort").reset_index(drop=True)


def write_coverage_matrix(matrix: pd.DataFrame | None = None,
                          out_path: str | Path | None = None) -> dict:
    """写 UTF-8 / LF 的 CSV；固定 6 位小数、无时间戳，保证重跑字节相同。"""
    mat = build_coverage_matrix() if matrix is None else matrix
    path = Path(out_path) if out_path is not None else MATRIX_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    mat.to_csv(path, index=False, float_format="%.6f", lineterminator="\n",
               encoding="utf-8")
    payload = path.read_bytes()
    try:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:                      # 临时目录验证时不在仓库内
        rel = str(path).replace("\\", "/")
    return {"path": rel, "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def coverage_facts(raw: pd.DataFrame | None = None,
                   matrix: pd.DataFrame | None = None) -> dict:
    """把四条事实算成机器可读的值，供自检 / 测试 / M5 数据页共同引用。"""
    frame = read_all() if raw is None else raw
    mat = build_coverage_matrix(frame) if matrix is None else matrix
    ev = frame.loc[frame["season"].isin(EVAL_SEASONS)]

    odds_bad = ev.loc[ev[list(ODDS_COLS)].isna().any(axis=1)]
    odds_by_block = odds_bad.groupby(["Div", "season"]).size().to_dict()
    shot_bad = ev.loc[ev[list(EVAL_SHOT_CHECK_COLS)].isna().any(axis=1)]

    def first_season_with(col: str, league: str | None = None) -> str | None:
        sel = mat if league is None else mat.loc[mat["league"] == league]
        hit = sel.loc[sel[col] > 0, "season"]
        return str(hit.min()) if len(hit) else None

    return {
        "n_blocks": int(len(mat)),
        "n_matches": int(mat["n_matches"].sum()),
        "eval_blocks": int(len(ev.groupby(["Div", "season"]))),
        "odds_first_season": first_season_with("PSCH"),
        "max_first_season": first_season_with("MaxCH"),
        "n1_shot_first_full": first_season_with("HS", "N1"),
        "odds_missing_rows": int(len(odds_bad)),
        "odds_missing_by_block": {f"{k[0]}|{k[1]}": int(v)
                                  for k, v in sorted(odds_by_block.items())},
        "odds_full_eval_blocks": int(EXPECTED_EVAL_BLOCKS - len(odds_by_block)),
        "b6_effective_rows": int(len(ev) - len(odds_bad)),
        "eval_shot_missing_rows": int(len(shot_bad)),
        "eval_shot_missing_by_block": {f"{k[0]}|{k[1]}": int(v) for k, v in
                                       shot_bad.groupby(["Div", "season"])
                                       .size().to_dict().items()},
        "eval_shot_missing_match": " | ".join(EVAL_SHOT_MISSING_MATCH),
        "eval_shot_rate": round(1 - len(shot_bad) / len(ev), 6),
    }


def plot_coverage(matrix: pd.DataFrame | None = None,
                  out_path: str | Path | None = None) -> dict:
    """6 个联赛各一张 22 季 × 15 列热力图，共用一个 0–1 色标（英文标签免字体坑）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mat = build_coverage_matrix() if matrix is None else matrix
    path = Path(out_path) if out_path is not None else FIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    leagues = sorted(mat["league"].unique())
    fig, axes = plt.subplots(3, 2, figsize=(16, 13))
    fig.suptitle("Data coverage by league x season  (non-null rate, read from raw CSV)",
                 fontsize=14, fontweight="bold")
    im = None
    for ax, lg in zip(axes.ravel(), leagues):
        sub = mat.loc[mat["league"] == lg].sort_values("season")
        vals = sub[list(COVERAGE_COLUMNS)].to_numpy(dtype=float)
        im = ax.imshow(vals, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto",
                       interpolation="nearest")
        ax.set_title(f"{lg}  ({int(sub['n_matches'].sum()):,} matches)", fontsize=11)
        ax.set_yticks(range(len(sub)))
        ax.set_yticklabels(sub["season"], fontsize=7)
        ax.set_xticks(range(len(COVERAGE_COLUMNS)))
        ax.set_xticklabels(COVERAGE_COLUMNS, rotation=90, fontsize=6.5)
        ax.tick_params(axis="y", length=0)
        # 评估窗起点：2017/18 是第 14 季；只画虚线，文字统一放图底说明
        seasons = list(sub["season"])
        if "2017/18" in seasons:
            ax.axhline(seasons.index("2017/18") - 0.5, color="black",
                       linewidth=1.2, linestyle="--")
        ax.set_ylabel("")
    # 独立色标轴，避免挤在两列子图中间遮住数据
    cax = fig.add_axes([0.945, 0.13, 0.012, 0.76])
    fig.colorbar(im, cax=cax, label="non-null rate (0 = missing, 1 = complete)")
    fig.text(0.5, 0.045,
             "PSCH/PSCD/PSCA from 2012/13  |  MaxCH/MaxCD/MaxCA from 2019/20  |  "
             "N1 shot cols from 2017/18  |  1 eval-window match lacks shot cols (2425_D1)",
             ha="center", fontsize=8)
    fig.text(0.5, 0.022,
             "Dashed line = evaluation window starts 2017/18.  "
             "Cells with 0 < rate < 1 are single-match gaps (see results/coverage_matrix.csv).",
             ha="center", fontsize=7.5, color="#444444")
    fig.subplots_adjust(top=0.93, bottom=0.10, left=0.075, right=0.925,
                        hspace=0.34, wspace=0.13)
    fig.savefig(path, dpi=130, metadata={"Software": "Matplotlib"})
    plt.close(fig)
    payload = path.read_bytes()
    try:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:                      # 临时目录验证时不在仓库内
        rel = str(path).replace("\\", "/")
    return {"path": rel, "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def coverage_selfcheck(log_path: str | Path | None = None,
                       out_path: str | Path | None = None,
                       fig_path: str | Path | None = None) -> dict:
    """T1.4 验收：12 项硬断言 + 可复核日志。

    ``out_path=None`` 时只验内存矩阵不落盘（测试用）；给定路径时额外写
    正式 CSV / PNG 并读回复核。
    """
    out: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    raw = read_all()
    mat = build_coverage_matrix(raw)
    facts = coverage_facts(raw, mat)
    ev = raw.loc[raw["season"].isin(EVAL_SEASONS)]

    emit("=" * 100)
    emit("M1 / S5 · T1.4 覆盖率矩阵自检（直接读 data/raw/，不经过 panel.parquet）")
    emit(f"日期: {date.today()}    输入: 132 个原始 CSV / {len(raw):,} 场")
    emit("=" * 100)

    # --- 独立复算，不复用 coverage_facts 的中间结果 ---
    shape_ok = (len(mat) == EXPECTED_BLOCKS == 132
                and list(mat.columns) == list(MATRIX_FIELDS)
                and int(mat["n_matches"].sum()) == EXPECTED_ROWS == 46_507
                and mat["season"].nunique() == 22
                and mat["league"].nunique() == 6)
    rates = mat[list(COVERAGE_COLUMNS)].to_numpy(dtype=float)
    range_ok = bool(np.isfinite(rates).all() and (rates >= 0).all() and (rates <= 1).all())
    core_ok = bool((mat[["FTHG", "FTAG", "FTR"]].to_numpy() == 1.0).all())

    pre = mat.loc[mat["season"].isin(PRE_ODDS_SEASONS)]
    odds_ok = (bool((pre[list(ODDS_COLS)].to_numpy() == 0).all())
               and facts["odds_first_season"] == ODDS_FIRST_SEASON
               and all(first == ODDS_FIRST_SEASON for first in
                       (mat.loc[(mat["league"] == lg) & (mat[c] > 0), "season"].min()
                        for lg in sorted(mat["league"].unique()) for c in ODDS_COLS)))

    odds_bad = ev.loc[ev[list(ODDS_COLS)].isna().any(axis=1)]
    odds_by_block = {k: int(v) for k, v in
                     odds_bad.groupby(["Div", "season"]).size().to_dict().items()}
    odds_eval_ok = (len(odds_bad) == 5
                    and odds_by_block == EXPECTED_ODDS_MISSING_BLOCKS
                    and facts["odds_full_eval_blocks"] == 45
                    and facts["b6_effective_rows"] == EXPECTED_B6_ROWS == 16_728
                    and len(ev) == EXPECTED_EVAL_ROWS == 16_733)

    n1 = mat.loc[mat["league"] == "N1"].sort_values("season")
    n1_before = n1.loc[n1["season"] < N1_SHOT_FIRST_FULL]
    n1_after = n1.loc[n1["season"] >= N1_SHOT_FIRST_FULL]
    shot_ok = (bool((n1_before[list(SHOT_COLS)].to_numpy() == 0).all())
               and bool((n1_after[list(SHOT_COLS)].to_numpy() == 1).all())
               and len(n1_before) == 14 and len(n1_after) == 8)

    max_before = mat.loc[mat["season"] < MAX_FIRST_SEASON]
    max_after = mat.loc[mat["season"] >= MAX_FIRST_SEASON]
    max_ok = (bool((max_before[list(MAX_COLS)].to_numpy() == 0).all())
              and bool((max_after[list(MAX_COLS)].to_numpy() == 1).all())
              and facts["max_first_season"] == MAX_FIRST_SEASON
              and len(max_after) == 6 * 6)

    # S5 订正项：评估窗射门列有且仅有 1 场缺，且该场赔率齐全
    shot_bad = ev.loc[ev[list(EVAL_SHOT_CHECK_COLS)].isna().any(axis=1)]
    shot_by_block = {k: int(v) for k, v in
                     shot_bad.groupby(["Div", "season"]).size().to_dict().items()}
    shot_exception_ok = (len(shot_bad) == 1
                         and shot_by_block == EVAL_SHOT_MISSING
                         and bool(shot_bad[list(ODDS_COLS)].notna().all().all())
                         and bool(shot_bad[["FTHG", "FTAG", "FTR"]].notna().all().all())
                         and bool(shot_bad[list(EVAL_SHOT_CHECK_COLS)].isna().all().all())
                         and str(shot_bad.iloc[0]["HomeTeam"]) == "Union Berlin"
                         and str(shot_bad.iloc[0]["AwayTeam"]) == "Bochum"
                         and facts["eval_shot_rate"] == 0.99994)

    # 落盘验证：正式路径给定就写正式产物；否则在临时目录走同一条
    # 「写 -> 读回 -> 再写比 sha256」链路，保证 12 项断言在不落盘的测试场景下
    # 同样可判定，且不会往仓库里塞临时文件。
    written: dict | None = None
    fig_written: dict | None = None
    official = out_path is not None and fig_path is not None
    tmp = tempfile.TemporaryDirectory()
    try:
        base = Path(tmp.name)
        csv_target = (Path(out_path) if out_path is not None
                      else base / "coverage_matrix.csv")
        png_target = (Path(fig_path) if fig_path is not None
                      else base / "fig_data_coverage.png")
        w = write_coverage_matrix(mat, csv_target)
        w2 = write_coverage_matrix(mat, csv_target)
        idem_ok = w["sha256"] == w2["sha256"]
        back = pd.read_csv(csv_target)
        read_ok = (list(back.columns) == list(MATRIX_FIELDS)
                   and len(back) == EXPECTED_BLOCKS
                   and np.allclose(back[list(COVERAGE_COLUMNS)].to_numpy(),
                                   rates, atol=1e-6))
        f = plot_coverage(mat, png_target)
        png_ok = (f["bytes"] > 10_000
                  and png_target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n")
        disk_ok = bool(idem_ok and read_ok and png_ok)
        if official:
            written, fig_written = w, f
        csv_desc = (f"{w['sha256'][:16]}… / {w['bytes']:,} B"
                    + ("" if official else "（临时目录验证，未落盘）"))
        png_desc = (f"{f['bytes']:,} B"
                    + ("" if official else "（临时目录验证，未落盘）"))
    finally:
        tmp.cleanup()

    # 输入必须是 raw：build 函数体内不得出现 parquet 读取字样。
    # 拆串拼装，避免「被检查的字面量本身出现在源码里」造成自指失败。
    source = Path(__file__).read_text(encoding="utf-8")
    build_src = (source.split("def build_coverage_matrix")[1]
                 .split("def write_coverage_matrix")[0])
    forbidden = ("read_" + "parquet", "panel" + ".parquet")
    raw_only_ok = all(token not in build_src for token in forbidden)

    checks: list[tuple[str, bool, str]] = [
        ("矩阵 132 行 = 6 联赛 × 22 季，18 列顺序固定，n_matches 合计 46,507",
         shape_ok, f"rows={len(mat)}, cols={len(mat.columns)}, "
                   f"matches={int(mat['n_matches'].sum()):,}"),
        ("全部比例 ∈ [0,1] 且无 NaN / inf",
         range_ok, f"min={rates.min():.4f}, max={rates.max():.4f}"),
        ("核心结果列 FTHG/FTAG/FTR 全库 132 块 100%",
         core_ok, f"core_ok={core_ok}"),
        ("PSCH/PSCD/PSCA 前 9 季整列缺失，自 2012/13 起有，6 联赛一致",
         odds_ok, f"first={facts['odds_first_season']}, pre_blocks={len(pre)}"),
        ("评估窗 45/48 块赔率满格；缺 5 场按块分布与契约一致；B6 n = 16,728",
         odds_eval_ok, f"missing={len(odds_bad)}, by_block={facts['odds_missing_by_block']}, "
                       f"b6={facts['b6_effective_rows']:,}"),
        ("荷甲射门 4 列 HS/AS/HST/AST 0304–1617 全 0，2017/18 起 8 季全 1"
         "（半场比分 HTHG/HTAG 全库都有，不算射门）",
         shot_ok, f"before={len(n1_before)}, after={len(n1_after)}, "
                  f"first_full={facts['n1_shot_first_full']}"),
        ("MaxCH/MaxCD/MaxCA 2019/20 起才有，6 联赛 × 6 季全覆盖",
         max_ok, f"first={facts['max_first_season']}, after_blocks={len(max_after)}"),
        ("【S5 订正】评估窗射门列仅 1 场缺（2425_D1 Union Berlin–Bochum），"
         "该场比分与收盘赔率齐全",
         shot_exception_ok, f"missing={len(shot_bad)}, "
                            f"by_block={facts['eval_shot_missing_by_block']}, "
                            f"rate={facts['eval_shot_rate']}"),
        ("输入只走 read_all() 读 raw；build_coverage_matrix 不碰 parquet",
         raw_only_ok, f"raw_only_ok={raw_only_ok}"),
        ("CSV 落盘可读、列序与逐格数值一致、连续两次生成 sha256 相同",
         bool(idem_ok and read_ok), csv_desc),
        ("PNG 热力图已写入、非零、PNG 魔数正确",
         bool(png_ok), png_desc),
        ("覆盖率口径与 data_interface.md §2 一致：Max* 不进 panel，故必须读 raw",
         bool(raw_only_ok and max_ok), "Max* 仅在 raw 可见"),
    ]

    emit("-" * 100)
    for name, ok, detail in checks:
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
    passed = sum(ok for _, ok, _ in checks)
    emit("-" * 100)
    emit(f"汇总: {passed}/{len(checks)} 项 PASS"
         f"{'  -> T1.4 通过' if passed == len(checks) else '  -> 存在 FAIL'}")
    emit("")
    emit("四条实测事实（M5 写数据页照抄）:")
    emit("  1. 收盘赔率 PSCH/PSCD/PSCA 自 2012/13 起才有；评估窗 45/48 块满格，"
         "另 3 块共缺 5 场（1718_SP1 1 / 1718_N1 3 / 1819_D1 1）→ B6/B6r 有效 n = 16,728")
    emit("  2. 荷甲 N1 射门 4 列 HS/AS/HST/AST 2017/18 起满格，此前 14 季全缺；"
         "半场比分 HTHG/HTAG 全库 22 季都有，不是射门列")
    emit("  3. MaxCH/MaxCD/MaxCA 自 2019/20 起才有，6 联赛一致")
    emit("  4. 【订正】评估窗射门列并非 100%：2425_D1 的 Union Berlin–Bochum"
         "（2024-12-14）缺 6 个射门/半场列；该场比分与收盘赔率齐全。"
         "评估窗射门覆盖率 16,732/16,733 = 0.999940")
    emit("")
    emit("边界: 本模块只做覆盖率统计，不改 raw / panel / splits；"
         "缺值一律不回填。任何以射门列为特征的 arm 须显式处理上条 1 场 NaN。")
    emit("复现: python src/coverage.py --log results/logs/s5_coverage_<date>.txt")
    emit("      pytest -q tests/test_coverage.py")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks), "facts": facts,
            "written": written, "fig_written": fig_written, "disk_ok": bool(disk_ok)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="M1 / S5 · T1.4：直接读 raw 生成覆盖率矩阵 CSV 与热力图 PNG")
    ap.add_argument("--out", default=None,
                    help="覆盖率矩阵 CSV 路径（默认 results/coverage_matrix.csv，入库）")
    ap.add_argument("--fig", default=None,
                    help="热力图 PNG 路径（默认 products/figures/fig_data_coverage.png，入库）")
    ap.add_argument("--log", default=None,
                    help=f"自检日志路径（默认不落盘）；建议 results/logs/s5_coverage_{date.today()}.txt")
    args = ap.parse_args()
    summary = coverage_selfcheck(args.log, args.out or str(MATRIX_PATH),
                                 args.fig or str(FIG_PATH))
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
