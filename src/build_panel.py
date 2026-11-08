"""M1 / T1.2-a（S1）—— 稳健读取器 ``read_raw()``。

本文件目前**只实现「把 132 个原始 CSV 读成规整 DataFrame」这一步**。
字段统一（S2）、拼 ``panel.parquet``（S3）、切 48 块（S4）后续在**同一文件**里追加，
不要在 S1 里偷跑，也不要把 ``data/processed/`` 的产出提前落盘。

为什么不能用裸 ``pd.read_csv``（2026-11-08 全库 132 文件实测）
------------------------------------------------------------------
1. **11 个文件行长 ≠ 表头**：9 个含「多字段」行、8 个含「少字段」行、6 个两者兼有。
   ``0304_F1.csv`` 表头 41 列，有效数据行长度 39–52 列，365 行不齐。
   裸 ``pd.read_csv`` 会抛 ``ParserError: Expected N fields``；
   ``on_bad_lines='skip'`` 会**静默丢掉这 365 场真实比赛**，禁止使用。
2. **14 个文件表头有重复列名**（含空串 ``''``）：整表 ``pd.concat`` / ``reindex``
   会抛 ``InvalidIndexError``。只按白名单列名构造 dict，天然免疫。
3. **54 个文件（0304–1112 共 9 季 × 6 联赛）根本没有 ``PSCH/PSCD/PSCA`` 列**：
   是「列不存在」而非「值为空」，必须补 NaN，不能 ``df['PSCH']``。
4. **7 个文件共 11 行全空白**：显式丢弃，``46,518 → 46,507``。
5. 表头有 2 种变体（96 个无 ``Time``、36 个有）；编码 131 个 ``utf-8-sig``、
   仅 ``0405_E0.csv`` 需回退 ``latin-1``。

按名取列**按位置索引**，只有「短行缺的是末尾列」时才安全。``selfcheck()``
因此对每行校验 ``FTR ∈ {H,D,A}`` / 日期可解析 / 比分非空 / ``Div`` 非空：
全库 46,507 行 0 异常，证明没有发生列错位（详见 S1 自检日志）。

运行
----
    python src/build_panel.py --log results/logs/s1_read_raw_2026-11-08.txt
    pytest -q tests/test_read_raw.py
"""

from __future__ import annotations

import argparse
import csv
import io
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

# 白名单：顺序即输出列顺序，任何文件都返回同样的 19 + 1 列。
# 不进 panel 的 Max* / 射门列仍保留在此，供 S6 覆盖率矩阵读 raw 时复用。
KEEP: tuple[str, ...] = (
    "Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
    "HTHG", "HTAG", "HS", "AS", "HST", "AST",
    "PSCH", "PSCD", "PSCA", "MaxCH", "MaxCD", "MaxCA",
)
TEXT_COLS: tuple[str, ...] = ("Div", "Date", "HomeTeam", "AwayTeam", "FTR")
NUMERIC_COLS: tuple[str, ...] = tuple(c for c in KEEP if c not in TEXT_COLS)
ODDS_COLS: tuple[str, ...] = ("PSCH", "PSCD", "PSCA")
EXPECTED_FILES = 132
EXPECTED_BODY_ROWS = 46_518
EXPECTED_BLANK_ROWS = 11
EXPECTED_ROWS = 46_507


def _decode(raw: bytes) -> tuple[str, str]:
    """先 utf-8-sig（自动去 BOM），失败再回退 latin-1（实测仅 0405_E0.csv）。"""
    try:
        return raw.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def read_raw(path: str | Path) -> pd.DataFrame:
    """读单个 ``data/raw/*.csv``，返回列顺序固定的规整 DataFrame。

    - 只取 ``KEEP`` 白名单列；缺列补 ``None`` → 数值列经 ``to_numeric`` 变 ``NaN``。
    - 行长超过表头的**多余字段直接忽略**；行长不足表头的**缺列补空**。
    - 全空白行显式丢弃（不产生一行全 NaN 的「幽灵比赛」）。
    - 附加 ``season`` 列：文件名 4 位码 ``2425`` → ``2024/25``（``YYYY/YY``）。
    - 逐文件元信息挂在 ``df.attrs``，供自检与覆盖率矩阵使用（``pd.concat`` 后不保留）。

    S2 才做队名 alias 归一、日期转 ISO、``y`` 编码、H3 两列；
    S3 才写 ``match_id`` 与 ``panel.parquet``。这里**都不做**。
    """
    path = Path(path)
    text, encoding = _decode(path.read_bytes())
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise ValueError(f"{path.name}: 空文件（无表头）")

    header = [c.strip() for c in rows[0]]
    body = rows[1:]
    blank_rows = [r for r in body if not any(c.strip() for c in r)]
    records = [r for r in body if any(c.strip() for c in r)]
    if not records:
        raise ValueError(f"{path.name}: 没有有效数据行")

    # 白名单列若在表头重复，按名取列会有歧义 → 直接报错，不静默取第一个。
    dup_whitelist = tuple(c for c in KEEP if header.count(c) > 1)
    if dup_whitelist:
        raise ValueError(f"{path.name}: 白名单列在表头重复：{dup_whitelist}")

    index = {c: (header.index(c) if c in header else None) for c in KEEP}
    data: dict[str, list] = {}
    for col in KEEP:
        pos = index[col]
        if pos is None:
            data[col] = [None] * len(records)
        else:
            data[col] = [
                (r[pos].strip() or None) if pos < len(r) else None
                for r in records
            ]

    frame = pd.DataFrame(data, columns=list(KEEP))
    for col in NUMERIC_COLS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    code = path.stem.split("_")[0]
    if len(code) != 4 or not code.isdigit():
        raise ValueError(f"{path.name}: 无法从文件名解析 4 位赛季码，得到 {code!r}")
    frame["season"] = "20" + code[:2] + "/" + code[2:]

    frame.attrs.update(
        source_file=path.name,
        encoding=encoding,
        n_header_cols=len(header),
        n_body_rows=len(body),
        n_blank_rows=len(blank_rows),
        n_rows=len(records),
        n_short_rows=sum(len(r) < len(header) for r in records),
        n_long_rows=sum(len(r) > len(header) for r in records),
        n_duplicate_header_cols=len(header) - len(set(header)),
        duplicate_whitelist_cols=dup_whitelist,
        missing_whitelist_cols=tuple(c for c in KEEP if c not in header),
        missing_odds_cols=tuple(c for c in ODDS_COLS if c not in header),
    )
    return frame


def read_all(raw_dir: str | Path | None = None) -> pd.DataFrame:
    """按文件名顺序拼接全部 132 个 CSV（S3 会复用；本步**不落盘**）。"""
    d = Path(raw_dir) if raw_dir is not None else RAW_DIR
    files = sorted(d.glob("*.csv"))
    if len(files) != EXPECTED_FILES:
        raise ValueError(f"期望 {EXPECTED_FILES} 个原始 CSV，{d} 中实际 {len(files)} 个")
    return pd.concat([read_raw(p) for p in files], ignore_index=True)


def _row_integrity(frame: pd.DataFrame) -> int:
    """校验按名取列没有因短行发生错位，返回异常格数。

    只用于自检，不写回 frame；S2 会重新做正式的日期与标签断言。
    """
    bad_ftr = ~frame["FTR"].isin(["H", "D", "A"])
    bad_date = pd.to_datetime(
        frame["Date"], dayfirst=True, format="mixed", errors="coerce"
    ).isna()
    bad_score = frame[["FTHG", "FTAG"]].isna().any(axis=1)
    bad_div = frame["Div"].isna()
    return int(bad_ftr.sum() + bad_date.sum() + bad_score.sum() + bad_div.sum())


def selfcheck(raw_dir: str | Path | None = None,
              log_path: str | Path | None = None) -> dict:
    """S1 验收：132 文件全读入 + 行数守恒 + 白名单唯一 + 无静默错位。"""
    d = Path(raw_dir) if raw_dir is not None else RAW_DIR
    files = sorted(d.glob("*.csv"))
    out: list[str] = []
    frames: list[pd.DataFrame] = []
    checks: list[tuple[str, bool, str]] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    emit("=" * 100)
    emit("S1 read_raw() 自检 · Football-Calibration / M1 · T1.2-a")
    emit("=" * 100)
    emit(f"执行时间 : {pd.Timestamp.now().tz_localize('Asia/Shanghai').isoformat(timespec='seconds')}")
    emit(f"raw 目录 : {d}")
    emit(f"Python   : {pd.__version__} (pandas)")
    emit("")
    emit(f"{'file':<14} {'rows':>5} {'blank':>5} {'short':>5} {'long':>5} "
         f"{'hdr':>4} {'dup':>4} {'missOdds':>9} {'badCells':>8}  encoding")
    emit("-" * 100)

    total_blank = total_short = total_long = total_body = total_bad = 0
    fallback, ragged, no_odds, dup_header = [], [], [], []
    for p in files:
        f = read_raw(p)
        a = f.attrs
        bad = _row_integrity(f)
        frames.append(f)
        total_body += a["n_body_rows"]
        total_blank += a["n_blank_rows"]
        total_short += a["n_short_rows"]
        total_long += a["n_long_rows"]
        total_bad += bad
        if a["encoding"] != "utf-8-sig":
            fallback.append(p.name)
        if a["n_short_rows"] or a["n_long_rows"]:
            ragged.append(p.name)
        if a["missing_odds_cols"]:
            no_odds.append(p.name)
        if a["n_duplicate_header_cols"]:
            dup_header.append(p.name)
        emit(f"{p.name:<14} {a['n_rows']:>5} {a['n_blank_rows']:>5} "
             f"{a['n_short_rows']:>5} {a['n_long_rows']:>5} "
             f"{a['n_header_cols']:>4} {a['n_duplicate_header_cols']:>4} "
             f"{len(a['missing_odds_cols']):>9} {bad:>8}  {a['encoding']}")

    panel = pd.concat(frames, ignore_index=True)
    checks += [
        ("132 个 CSV 全部读入且不抛异常", len(files) == EXPECTED_FILES and len(frames) == EXPECTED_FILES,
         f"files={len(files)}, frames={len(frames)}"),
        ("行数守恒 46,518 − 11 = 46,507",
         total_body == EXPECTED_BODY_ROWS and total_blank == EXPECTED_BLANK_ROWS
         and len(panel) == EXPECTED_ROWS,
         f"body={total_body}, blank={total_blank}, valid={len(panel)}"),
        ("白名单列名唯一且输出列恒定", len(set(KEEP)) == len(KEEP)
         and all(list(f.columns) == list(KEEP) + ["season"] for f in frames),
         f"KEEP={len(KEEP)} 列 + season"),
        ("重复表头 / 行长不齐 / 缺赔率列均被正确处理",
         len(dup_header) == 14 and len(ragged) == 11 and len(no_odds) == 54,
         f"dupHeader={len(dup_header)}, ragged={len(ragged)}, noOdds={len(no_odds)}"),
        ("0304–1112 的收盘赔率列是 NaN 而非 KeyError",
         bool(panel.loc[panel["season"] <= "2011/12", list(ODDS_COLS)].isna().all().all()),
         "前 9 季三列全 NaN"),
        ("按名取列无静默错位（FTR / 日期 / 比分 / Div）", total_bad == 0,
         f"badCells={total_bad}；shortRows={total_short}, longRows={total_long}"),
        ("编码回退仅 0405_E0.csv", fallback == ["0405_E0.csv"], f"fallback={fallback}"),
        ("season 格式 YYYY/YY", bool(panel["season"].str.match(r"^\d{4}/\d{2}$").all()),
         f"例：{sorted(panel['season'].unique())[0]} … {sorted(panel['season'].unique())[-1]}"),
    ]

    emit("")
    emit("-" * 100)
    for name, ok, detail in checks:
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
    passed = sum(ok for _, ok, _ in checks)
    emit("-" * 100)
    emit(f"汇总: {passed}/{len(checks)} 项 PASS"
         f"{'  -> S1 通过，可进入 S2' if passed == len(checks) else '  -> 存在 FAIL，禁止进入 S2'}")
    emit("")
    emit("说明: 本步只产出读取器与自检日志，未写 panel.parquet / team_alias.csv / splits.json；")
    emit("      队名 alias 归一、日期转 ISO、y 编码、H3 两列、match_id 均留到 S2 / S3。")
    emit("复现: python src/build_panel.py --log <path>  |  pytest -q tests/test_read_raw.py")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks), "rows": len(panel),
            "files": len(files), "bad_cells": total_bad}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="S1 / T1.2-a: read_raw() 自检")
    ap.add_argument("--raw-dir", default=None, help="原始 CSV 目录（默认 data/raw/）")
    ap.add_argument("--log", default=None,
                    help=f"自检日志路径（默认不落盘；建议 results/logs/s1_read_raw_{date.today()}.txt）")
    args = ap.parse_args()
    summary = selfcheck(args.raw_dir, args.log)
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
