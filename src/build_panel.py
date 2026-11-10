"""M1 / T1.2-a（S1）—— 稳健读取器 ``read_raw()``。

本文件按阶段在**同一文件**里演进，不另起炉灶：
  S1（已交付） ``read_raw()`` / ``read_all()`` / ``selfcheck()``：132 个原始 CSV → 规整 DataFrame；
  S2（已交付） ``build_team_alias()`` / ``clean_panel()`` / ``s2_selfcheck()``：
              队名归一、ISO 日期、``y`` 编码、``is_promoted_*`` 与 ``matchday``；
  S3（已交付） ``make_match_id()`` / ``build_panel()`` / ``write_panel()`` /
              ``s3_selfcheck()``：22 列建模总表 + ``data/processed/panel.parquet``；
  S4（已交付） ``src/splits.py``：48 块 rolling-origin 切分 → ``configs/splits.json``
              （**入库契约**）；本文件只提供 ``--stage s4`` 统一入口。
  S5（已交付） ``src/coverage.py`` / ``src/handover.py`` + ``tests/test_leakage.py`` /
              ``test_h3_features.py`` / ``appendix/`` + ``docs/plans/CHANGELOG_data.md``：
              覆盖率矩阵、五条泄漏断言、复现包、H3 独立测试、数据冻结；
              本文件只提供 ``--stage s5`` 收尾自检入口（转 ``src/handover.py``）。
**S1 / S2 仍不落盘**：S3 的 ``write_panel()`` 写不入库的数据文件，
S4 的 ``write_splits()`` 写**入库**的 KB 级纯文本契约。

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

2026-11-08 r2 补强：行尾超出表头的字段**没有列名**，按名取列永远取不到，
所以「忽略」必须附带一个前提——它们得是空的。实测 775 条长行的 2,895 个
溢出格 100% 为 ``''``；现把该前提写成硬断言：一旦出现非空值立即抛
``ValueError``，避免源站改版 / 整行错位时静默吞掉真实信息。

运行（项目环境 DSC5001_Project，见 M1 卡 §7 坑 8）
--------------------------------------------------
    python src/build_panel.py --log results/logs/s1_read_raw_2026-11-08.txt   # S1 自检
    python src/build_panel.py --stage s2 --log results/logs/s2_clean_2026-11-10.txt
    python src/build_panel.py --stage s3 --log results/logs/s3_panel_2026-11-10.txt
    python src/build_panel.py --stage s4 --log results/logs/s4_splits_2026-11-10.txt
    python src/build_panel.py --stage s5 --log results/logs/s5_handover_2026-11-10.txt
    pytest -q tests/

``--stage s3`` 默认把建模总表写到 ``data/processed/panel.parquet``（**不入库**，
README §3.6）；全组各自跑同一脚本得到同一张表，契约是「同一脚本 → 同一张表」。
``--stage s4`` 转到 ``src/splits.py``，把 48 块切分写到 ``configs/splits.json``
（**入库**，随 Git 分发）。``--stage s5`` 转到 ``src/handover.py`` 做收尾自检，
**不加工数据**，只跑 S1–S4 回归、全量 pytest、产物与文档契约检查。
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

# 白名单：顺序即输出列顺序，任何文件都返回同样的 19 + 1 列。
# 不进 panel 的 Max* / 射门列仍保留在此，供 S5 的 src/coverage.py 读 raw 时复用。
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

    S2 的 ``clean_panel()`` 才做队名 alias 归一、ISO 日期、``y`` 编码、H3 三列；
    ``match_id`` 与 ``panel.parquet`` 由 S3 的 ``build_panel()`` / ``write_panel()``
    负责（已在同一文件实现）。这里**都不做**。
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

    # 行尾溢出字段没有列名，按名取列必然取不到；必须确认它们全为空，
    # 否则「忽略」会在源站改版 / 整行错位时静默吞掉真实信息。
    overflow_cells = [
        cell for r in records if len(r) > len(header)
        for cell in r[len(header):]
    ]
    n_nonempty_overflow = sum(1 for cell in overflow_cells if cell.strip())
    if n_nonempty_overflow:
        raise ValueError(
            f"{path.name}: 行尾超出表头的 {n_nonempty_overflow} 个字段非空，"
            "可能是列错位或源站格式变化；禁止静默忽略"
        )

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
        n_overflow_cells=len(overflow_cells),
        n_nonempty_overflow=n_nonempty_overflow,
        n_duplicate_header_cols=len(header) - len(set(header)),
        duplicate_whitelist_cols=dup_whitelist,
        missing_whitelist_cols=tuple(c for c in KEEP if c not in header),
        missing_odds_cols=tuple(c for c in ODDS_COLS if c not in header),
    )
    return frame


def read_all(raw_dir: str | Path | None = None) -> pd.DataFrame:
    """按文件名顺序拼接全部 132 个 CSV（S2 / S3 会复用；本步**不落盘**）。"""
    d = Path(raw_dir) if raw_dir is not None else RAW_DIR
    files = sorted(d.glob("*.csv"))
    if len(files) != EXPECTED_FILES:
        raise ValueError(f"期望 {EXPECTED_FILES} 个原始 CSV，{d} 中实际 {len(files)} 个")
    return pd.concat([read_raw(p) for p in files], ignore_index=True)


def _row_integrity(frame: pd.DataFrame) -> int:
    """校验按名取列没有因短行发生错位，返回异常格数。

    只用于自检，不写回 frame；S2 的 ``clean_panel()`` 会重新做正式的日期与标签断言。
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
    total_overflow = total_overflow_nonempty = 0
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
        total_overflow += a["n_overflow_cells"]
        total_overflow_nonempty += a["n_nonempty_overflow"]
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
        ("按名取列无静默错位，且行尾溢出字段全空",
         total_bad == 0 and total_overflow_nonempty == 0,
         f"badCells={total_bad}；shortRows={total_short}, longRows={total_long}, "
         f"overflowCells={total_overflow}, overflowNonEmpty={total_overflow_nonempty}"),
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
    emit("说明: S1 只产出读取器与自检日志；S2 已在同一文件实现 alias / ISO / y / H3 三列（--stage s2），")
    emit("      并产出 configs/team_alias.csv；S3 才写 match_id 与 panel.parquet，S4 才切 splits.json。")
    emit("      read_raw() 对「行尾溢出字段非空」零容忍（直接抛 ValueError），防止换数据时静默吞信息。")
    emit("复现: python src/build_panel.py --log <path>  |  pytest -q tests/test_read_raw.py")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks), "rows": len(panel),
            "files": len(files), "bad_cells": total_bad,
            "overflow_cells": total_overflow,
            "nonempty_overflow": total_overflow_nonempty}


# =============================================================================
# S2 / T1.2 —— 字段统一：team_alias 归一 / ISO 日期 / y / H3 指示变量
#
# 边界：本步**只在同一文件里追加清洗层**，返回「加了列的 DataFrame」，
#      不写 match_id、不落 data/processed/panel.parquet（S3 已在同一文件实现）、
#      不切 48 块（S4 待做）。
# 依赖：只使用季前名单（上一季参赛队）与赛程（league/season/home/away/date），
#      绝不读取 FTR / 比分 / 射门等赛后信息；T1.9 的打乱测试即验证这一点。
# =============================================================================

CONFIG_DIR = ROOT / "configs"
ALIAS_PATH = CONFIG_DIR / "team_alias.csv"
ALIAS_COLUMNS = ("raw_name", "canonical_name", "league", "first_seen_season")
LABEL_MAP = {"H": 0, "D": 1, "A": 2}
POST_MATCH_COLS = (
    "FTR", "FTHG", "FTAG", "HTHG", "HTAG", "HS", "AS", "HST", "AST",
)
EVAL_SEASONS = tuple(f"{y}/{str(y + 1)[-2:]}" for y in range(2017, 2025))
EXPECTED_RAW_TEAM_NAMES = 243
EXPECTED_CANONICAL_TEAM_NAMES = 241

# 全库 243 个原始队名里，只有 2 组是「同一支队在不同年份用了两种写法」：
#   N1  Roda JC (2003/04–2009/10)  -> Roda (2010/11–2017/18)，赛季不重叠
#   N1  Sparta (2005/06–2009/10)   -> Sparta Rotterdam (2016/17–2024/25)
# 其余写法跨季完全一致。**不要合并**同城/同词的不同俱乐部，例如
# Ajaccio vs Ajaccio GFCO、Man City vs Man United、Bayern Munich vs Munich 1860、
# Den Bosch vs Den Haag、Ath Madrid vs Real Madrid（详见 configs/README.md）。
CANONICAL_MERGES: dict[tuple[str, str], str] = {
    ("N1", "Roda JC"): "Roda",
    ("N1", "Sparta"): "Sparta Rotterdam",
}


def build_team_alias(raw_dir: str | Path | None = None,
                     out_path: str | Path | None = None,
                     raw: pd.DataFrame | None = None) -> list[dict]:
    """从 raw 生成 ``configs/team_alias.csv`` 的内容（默认不落盘，便于自检比对）。

    每行覆盖一个 ``(league, raw_name)``，``canonical_name`` 默认等于原名，
    只有 ``CANONICAL_MERGES`` 里人工判定的 2 组改名会指向另一个**已在数据中出现过**
    的名字（禁止引入数据里不存在的「幽灵队名」）。
    """
    frame = read_all(raw_dir) if raw is None else raw
    first_seen: dict[tuple[str, str], str] = {}
    for lg, s, h, a in zip(frame["Div"], frame["season"],
                           frame["HomeTeam"], frame["AwayTeam"]):
        for name in (h, a):
            key = (lg, name)
            if key not in first_seen or s < first_seen[key]:
                first_seen[key] = s

    rows = []
    for (lg, name), season in sorted(first_seen.items()):
        canonical = CANONICAL_MERGES.get((lg, name), name)
        if (lg, canonical) not in first_seen:
            raise ValueError(f"canonical_name {canonical!r} 未在 {lg} 的原始队名中出现")
        rows.append({"raw_name": name, "canonical_name": canonical,
                     "league": lg, "first_seen_season": season})

    if out_path is not None:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(ALIAS_COLUMNS),
                                   lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return rows


def load_team_alias(path: str | Path | None = None
                    ) -> tuple[dict[tuple[str, str], str], list[dict]]:
    """读取并校验 ``team_alias.csv``，返回 ``(mapping, rows)``。"""
    p = Path(path) if path is not None else ALIAS_PATH
    with p.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != ALIAS_COLUMNS:
            raise ValueError(f"{p.name}: 列名应为 {ALIAS_COLUMNS}，实际 {reader.fieldnames}")
        rows = list(reader)
    mapping: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r["league"], r["raw_name"])
        if key in mapping:
            raise ValueError(f"{p.name}: 重复的 (league, raw_name)：{key}")
        if not r["canonical_name"]:
            raise ValueError(f"{p.name}: canonical_name 为空：{key}")
        mapping[key] = r["canonical_name"]
    for (lg, _), canonical in mapping.items():
        if (lg, canonical) not in mapping:
            raise ValueError(f"{p.name}: canonical_name 未在 {lg} 登记：{canonical}")
    return mapping, rows


def normalize_teams(frame: pd.DataFrame,
                    alias_map: dict[tuple[str, str], str]) -> pd.DataFrame:
    """按 ``(league, raw_name)`` 归一队名，产出 ``league/home/away``。

    原始 ``Div/HomeTeam/AwayTeam`` 保留，方便 S3 追溯与 ``match_id`` 对齐。
    **任何未登记的队名直接抛错**（M1 卡 §6 验收项 9：alias 差集必须为空）。
    """
    out = frame.copy()
    out["league"] = out["Div"]
    missing: set[tuple[str, str]] = set()
    for raw_col, new_col in (("HomeTeam", "home"), ("AwayTeam", "away")):
        values = []
        for lg, name in zip(out["league"], out[raw_col]):
            key = (lg, name)
            if key not in alias_map:
                missing.add(key)
            values.append(alias_map.get(key))
        out[new_col] = values
    if missing:
        raise ValueError(f"team_alias.csv 未覆盖 {len(missing)} 个队名，例如 {sorted(missing)[:5]}")
    if (out["home"] == out["away"]).any():
        raise ValueError("归一后出现 home == away，队名映射可能有误")
    return out


def to_iso_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """``Date``(dd/mm/yy 或 dd/mm/yyyy) -> ISO 字符串 ``date``，并防跨季错位。"""
    out = frame.copy()
    parsed = pd.to_datetime(out["Date"], dayfirst=True, format="mixed", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"日期解析失败 {int(parsed.isna().sum())} 行")
    out["date"] = parsed.dt.strftime("%Y-%m-%d")
    if not out["date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all():
        raise ValueError("date 不是 ISO YYYY-MM-DD")
    for season, block in pd.DataFrame({"season": out["season"], "d": parsed}).groupby("season"):
        start = int(season[:4])
        years = set(block["d"].dt.year)
        if not years <= {start, start + 1}:
            raise ValueError(f"{season}: 日期年份 {sorted(years)} 与赛季不符（两位年被猜错？）")
    return out


def encode_result(frame: pd.DataFrame) -> pd.DataFrame:
    """``FTR`` 的 H/D/A -> ``y = 0/1/2``（data_interface.md §1.1）。"""
    out = frame.copy()
    mapped = out["FTR"].map(LABEL_MAP)
    if mapped.isna().any():
        raise ValueError("FTR 出现 H/D/A 之外的值")
    out["y"] = mapped.astype("int8")
    if not np.array_equal(out["y"].to_numpy(), mapped.to_numpy()):
        raise ValueError("y 与 FTR.map(H=0,D=1,A=2) 不一致")
    if not set(out["y"].unique()) <= {0, 1, 2}:
        raise ValueError("y 出现 0/1/2 之外的值")
    return out


def _team_blocks(frame: pd.DataFrame) -> dict[tuple[str, str], set[str]]:
    """``(league, season)`` -> 该块参赛队集合。只用名单/赛程，不含赛后信息。"""
    teams: dict[tuple[str, str], set[str]] = {}
    for lg, s, h, a in zip(frame["league"], frame["season"],
                           frame["home"], frame["away"]):
        teams.setdefault((lg, s), set()).update((h, a))
    return teams


def new_teams_by_block(frame: pd.DataFrame,
                       cumulative: bool = False) -> dict[tuple[str, str], set[str]]:
    """每块新增队集合。``cumulative=False`` 相对**上一季**名单（H3 定义）；
    ``True`` 相对**历史累积**名单（T1.6 ``n_new_team`` 口径）。首季返回空集。
    """
    teams = _team_blocks(frame)
    seasons = sorted(frame["season"].unique())
    out: dict[tuple[str, str], set[str]] = {}
    for lg in sorted(frame["league"].unique()):
        history: set[str] = set()
        for i, s in enumerate(seasons):
            current = teams.get((lg, s), set())
            base = history if cumulative else (
                teams.get((lg, seasons[i - 1]), set()) if i else current)
            out[(lg, s)] = current - base
            history |= current
    return out


def add_h3_features(frame: pd.DataFrame) -> pd.DataFrame:
    """产出 ``is_promoted_home`` / ``is_promoted_away`` / ``matchday``。

    - 升班马：本季出现、但**该联赛上一季**名单里没有 -> 1；首季无上一季名单，全置 0。
    - ``matchday``：主队本季已完成联赛场次序号 + 1。把 home / away **两队展开**成
      2×46,507 行后按 ``(league, season, team, date, 原始行序)`` 排序、按队累计，
      再取主队侧；因此**包含该队作为客队出场的比赛**（只按 home 单列分组会漏算）。
      同队同日用原始行序作稳定 tiebreak。**这是「已完成场次」而非官方轮次，补赛时会偏**；
      H3 用 ``matchday <= 6`` 属近似，报告须注明（M1 卡 §4 T1.2）。
    - 只读 ``league/season/home/away/date`` 五列；打乱任何赛后列结果必须逐元素不变。
    """
    needed = ("league", "season", "home", "away", "date")
    absent = [c for c in needed if c not in frame.columns]
    if absent:
        raise ValueError(f"add_h3_features 缺少列：{absent}")

    out = frame.copy()
    teams = _team_blocks(out)
    seasons = sorted(out["season"].unique())
    prev: dict[tuple[str, str], set[str] | None] = {}
    for lg in sorted(out["league"].unique()):
        for i, s in enumerate(seasons):
            prev[(lg, s)] = None if i == 0 else teams.get((lg, seasons[i - 1]), set())

    def promoted(column: str) -> np.ndarray:
        return np.fromiter(
            (0 if prev[(lg, s)] is None else int(t not in prev[(lg, s)])
             for lg, s, t in zip(out["league"], out["season"], out[column])),
            dtype="int8", count=len(out),
        )

    n = len(out)
    rows = np.arange(n)
    long = pd.concat([
        pd.DataFrame({"league": out["league"], "season": out["season"],
                      "date": out["date"], "team": out["home"],
                      "row": rows, "side": "H"}),
        pd.DataFrame({"league": out["league"], "season": out["season"],
                      "date": out["date"], "team": out["away"],
                      "row": rows, "side": "A"}),
    ], ignore_index=True)
    long = long.sort_values(["league", "season", "team", "date", "row"],
                            kind="mergesort")
    long["seq"] = long.groupby(["league", "season", "team"], sort=False).cumcount() + 1
    agg = long.groupby(["league", "season", "team"])["seq"].agg(["min", "max", "count"])
    if not ((agg["min"] == 1) & (agg["max"] == agg["count"])).all():
        raise ValueError("matchday 不是从 1 连续到该队该季场次")
    home_seq = (long.loc[long["side"] == "H"].set_index("row")["seq"]
                .reindex(range(n)))
    if home_seq.isna().any():
        raise ValueError("存在没有 matchday 的比赛")

    out["is_promoted_home"] = promoted("home")
    out["is_promoted_away"] = promoted("away")
    out["matchday"] = home_seq.to_numpy().astype("int16")
    return out


def h3_invariant_to_post_match(frame: pd.DataFrame, seed: int = 20261110) -> bool:
    """T1.9 核心断言：打乱全部赛后列后重算 H3 三列，结果必须逐元素不变。"""
    rng = np.random.default_rng(seed)
    shuffled = frame.copy()
    for col in POST_MATCH_COLS:
        if col in shuffled.columns:
            values = shuffled[col].to_numpy().copy()
            rng.shuffle(values)
            shuffled[col] = values
    recomputed = add_h3_features(shuffled)
    cols = ["is_promoted_home", "is_promoted_away", "matchday"]
    return bool(frame[cols].equals(recomputed[cols]))


def clean_panel(raw: pd.DataFrame | None = None,
                alias_path: str | Path | None = None) -> pd.DataFrame:
    """S2 主入口：``read_all()`` -> 归一 / ISO 日期 / ``y`` / H3 三列。

    **只返回 DataFrame，不落盘**；``match_id`` 与 ``panel.parquet`` 由 S3 的
    ``build_panel()`` / ``write_panel()`` 负责（已在同一文件实现）。
    """
    frame = read_all() if raw is None else raw.copy()
    alias_map, _ = load_team_alias(alias_path)
    frame = normalize_teams(frame, alias_map)
    frame = to_iso_dates(frame)
    frame = encode_result(frame)
    frame = add_h3_features(frame)
    return frame


def s2_selfcheck(log_path: str | Path | None = None,
                 raw_dir: str | Path | None = None) -> dict:
    """S2 验收：13 项硬断言 + 可复核日志（不写任何数据文件）。"""
    out: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    raw = read_all(raw_dir)
    expected_rows = build_team_alias(raw=raw)
    alias_map, alias_rows = load_team_alias()
    frame = clean_panel(raw)

    emit("=" * 100)
    emit("S2 字段统一自检 · Football-Calibration / M1 · T1.2（alias / ISO / y / H3）")
    emit("=" * 100)
    emit(f"执行时间 : {pd.Timestamp.now().tz_localize('Asia/Shanghai').isoformat(timespec='seconds')}")
    emit(f"解释器   : Python / pandas {pd.__version__} · numpy {np.__version__}")
    emit(f"输入     : data/raw/*.csv 132 文件 → {len(raw):,} 行；configs/team_alias.csv {len(alias_rows)} 行")
    emit("")

    raw_names = {(lg, n) for lg, n in zip(
        pd.concat([raw["Div"], raw["Div"]], ignore_index=True),
        pd.concat([raw["HomeTeam"], raw["AwayTeam"]], ignore_index=True),
    )}
    alias_keys = set(alias_map)
    canonicals = set(alias_map.values())
    merges = [(r["league"], r["raw_name"], r["canonical_name"])
              for r in alias_rows if r["raw_name"] != r["canonical_name"]]
    do_not_merge = [
        ("F1", "Ajaccio", "Ajaccio GFCO"), ("E0", "Man City", "Man United"),
        ("D1", "Bayern Munich", "Munich 1860"), ("N1", "Den Bosch", "Den Haag"),
        ("SP1", "Ath Madrid", "Real Madrid"),
    ]
    kept_distinct = all(
        alias_map.get((lg, a)) != alias_map.get((lg, b)) and (lg, a) in alias_map
        and (lg, b) in alias_map for lg, a, b in do_not_merge
    )

    parsed = pd.to_datetime(frame["Date"], dayfirst=True, format="mixed", errors="coerce")
    season_years_ok = True
    for season, block in pd.DataFrame({"season": frame["season"], "d": parsed}).groupby("season"):
        start = int(season[:4])
        if not set(block["d"].dt.year) <= {start, start + 1}:
            season_years_ok = False

    per_block_teams = _team_blocks(frame)
    block_sizes = {len(v) for v in per_block_teams.values()}
    new_prev = new_teams_by_block(frame)
    new_hist = new_teams_by_block(frame, cumulative=True)
    eval_prev = {k: v for k, v in new_prev.items() if k[1] in EVAL_SEASONS}
    eval_hist = {k: v for k, v in new_hist.items() if k[1] in EVAL_SEASONS}
    exceptions = {k: sorted(v) for k, v in new_prev.items() if len(v) > 3}

    raw_view = frame.copy()
    raw_view["home"] = raw_view["HomeTeam"]
    raw_view["away"] = raw_view["AwayTeam"]
    unnormalized = add_h3_features(raw_view)
    prom_norm = int(frame["is_promoted_home"].sum())
    prom_raw = int(unnormalized["is_promoted_home"].sum())

    matchday_max = int(frame["matchday"].max())
    matchday_min = int(frame["matchday"].min())
    # 独立复算：两队展开 → 按队累计 → 取主队侧，与 matchday 逐元素比对。
    # 只按 home 单列分组会漏掉该队的客场比赛，是本步最容易写窄的一处。
    n, rows = len(frame), np.arange(len(frame))
    long_check = pd.concat([
        pd.DataFrame({"league": frame["league"], "season": frame["season"],
                      "date": frame["date"], "team": frame["home"],
                      "row": rows, "side": "H"}),
        pd.DataFrame({"league": frame["league"], "season": frame["season"],
                      "date": frame["date"], "team": frame["away"],
                      "row": rows, "side": "A"}),
    ], ignore_index=True)
    long_check = long_check.sort_values(
        ["league", "season", "team", "date", "row"], kind="mergesort")
    long_check["seq"] = (long_check.groupby(["league", "season", "team"], sort=False)
                         .cumcount() + 1)
    agg = long_check.groupby(["league", "season", "team"])["seq"].agg(
        ["min", "max", "count"])
    home_check = (long_check.loc[long_check["side"] == "H"]
                  .set_index("row")["seq"].reindex(range(n)).to_numpy())
    seq_ok = bool(
        ((agg["min"] == 1) & (agg["max"] == agg["count"])).all()
        and np.array_equal(frame["matchday"].to_numpy(), home_check)
    )
    invariant = h3_invariant_to_post_match(frame)
    five_tuple_dupes = int(frame.duplicated(["league", "season", "date", "home", "away"]).sum())
    y_counts = frame["y"].value_counts().sort_index().to_dict()

    emit("逐联赛队名归一：")
    for lg in sorted(frame["league"].unique()):
        n_raw = len({n for l, n in raw_names if l == lg})
        n_can = len({c for (l, _), c in alias_map.items() if l == lg})
        emit(f"  {lg:<4} 原始名 {n_raw:>3} → 归一名 {n_can:>3}")
    emit(f"真实改名 {len(CANONICAL_MERGES)} 组 / {len(merges)} 行：{merges}")
    emit(f"归一修正的升班马误判（home 列）：{prom_raw} → {prom_norm} 场，减少 {prom_raw - prom_norm} 场")
    emit("")
    emit("评估窗 48 块新增队（相对上一季）最大值：" +
         f"{max(len(v) for v in eval_prev.values())}；" +
         f"相对历史累积最大值：{max(len(v) for v in eval_hist.values())}")
    emit(f"全库 >3 支新增队的块（真实结构变化，非 bug）：{exceptions}")
    emit(f"y 分布：{y_counts}；matchday 范围 {matchday_min}–{matchday_max}")
    emit(f"五元组 (league,season,date,home,away) 重复：{five_tuple_dupes}")
    emit("")

    checks: list[tuple[str, bool, str]] = [
        ("team_alias.csv 可由 raw 一键重生成（243 行、4 列、逐行一致）",
         expected_rows == alias_rows and len(alias_rows) == EXPECTED_RAW_TEAM_NAMES,
         f"rows={len(alias_rows)}, reproducible={expected_rows == alias_rows}"),
        ("alias 覆盖全库所有 (league, raw_name)，差集 0",
         raw_names == alias_keys and len(alias_keys) == EXPECTED_RAW_TEAM_NAMES,
         f"raw={len(raw_names)}, alias={len(alias_keys)}, diff={len(raw_names ^ alias_keys)}"),
        ("仅 2 组真实改名，归一后 241 个队名",
         len(CANONICAL_MERGES) == 2 and len(merges) == 2
         and len(canonicals) == EXPECTED_CANONICAL_TEAM_NAMES,
         f"merges={len(merges)} 行非恒等映射, canonical={len(canonicals)}"),
        ("同城/同词的不同俱乐部未被误并", kept_distinct,
         "Ajaccio / Man City / Bayern / Den Bosch / Ath Madrid 均保持独立"),
        ("clean_panel 行数守恒 46,507，新增 8 列且原始列保留",
         len(frame) == EXPECTED_ROWS
         and all(c in frame.columns for c in
                 ("league", "home", "away", "date", "y",
                  "is_promoted_home", "is_promoted_away", "matchday")),
         f"rows={len(frame)}, cols={len(frame.columns)}"),
        ("ISO 日期 0 NaT / 格式合法 / 每季年份不跨季",
         int(parsed.isna().sum()) == 0 and season_years_ok
         and frame["date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
         and frame["date"].min() == "2003-08-01" and frame["date"].max() == "2025-05-25",
         f"NaT=0, range={frame['date'].min()} → {frame['date'].max()}"),
        ("y = FTR.map(H=0,D=1,A=2)，断言通过且值域 {0,1,2}",
         np.array_equal(frame["y"].to_numpy(), frame["FTR"].map(LABEL_MAP).to_numpy())
         and set(frame["y"].unique()) <= {0, 1, 2},
         f"y_counts={y_counts}"),
        ("归一后每 (联赛, 赛季) 参赛队仍为 18 或 20 支",
         block_sizes <= {18, 20} and len(per_block_teams) == 132,
         f"blocks={len(per_block_teams)}, sizes={sorted(block_sizes)}"),
        ("首季 2003/04 升班马全置 0（无上一季名单）",
         int(frame.loc[frame["season"] == "2003/04",
                       ["is_promoted_home", "is_promoted_away"]].to_numpy().sum()) == 0,
         "first season = 0"),
        ("评估窗 48 块新增队 ≤3；全库唯一例外 I1 2004/05 = 6（意甲扩军）",
         len(eval_prev) == 48 and max(len(v) for v in eval_prev.values()) <= 3
         and max(len(v) for v in eval_hist.values()) <= 3
         and set(exceptions) == {("I1", "2004/05")},
         f"evalBlocks={len(eval_prev)}, exceptions={list(exceptions)}"),
        ("matchday 从 1 连续到该队该季场次、无空值、范围 1–38",
         seq_ok and matchday_min == 1 and matchday_max == 38
         and frame["matchday"].notna().all()
         and frame[["is_promoted_home", "is_promoted_away"]].notna().all().all(),
         f"min={matchday_min}, max={matchday_max}, continuous={seq_ok}"),
        ("H3 三列对赛后信息不敏感（打乱 FTR / 比分 / 射门后逐元素不变，T1.9 核心）",
         invariant, f"invariant={invariant}"),
        ("五元组 0 重复，为 S3 的 match_id 铺路",
         five_tuple_dupes == 0, f"duplicates={five_tuple_dupes}"),
    ]

    emit("-" * 100)
    for name, ok, detail in checks:
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
    passed = sum(ok for _, ok, _ in checks)
    emit("-" * 100)
    emit(f"汇总: {passed}/{len(checks)} 项 PASS"
         f"{'  -> S2 通过，可进入 S3' if passed == len(checks) else '  -> 存在 FAIL，禁止进入 S3'}")
    emit("")
    emit("边界: S2 只返回内存中的清洗表；未写 match_id、未落 panel.parquet、未切 splits.json（S3 / S4）。")
    emit("      升班马按「上一季名单」判定；T1.6 的 n_new_team 是「历史累积」口径，两者不同，勿混用。")
    emit("复现: python src/build_panel.py --stage s2 --log results/logs/s2_clean_<date>.txt")
    emit("      python src/build_panel.py --build-alias   # 重生成 configs/team_alias.csv")
    emit("      pytest -q tests/test_s2_clean.py")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks), "rows": len(frame),
            "alias_rows": len(alias_rows), "canonical_names": len(canonicals),
            "promoted_home": prom_norm, "promoted_home_unnormalized": prom_raw,
            "dupes": five_tuple_dupes, "h3_invariant": invariant}


# =============================================================================
# S3 / T1.3 + T1.3-a —— 建模总表：match_id + 22 列窄表 + panel.parquet
#
# 边界：本步**第一次落盘**，且只落一个数据文件 data/processed/panel.parquet。
#      splits.json（48 块切分）不属于本步，由 S4 的 src/splits.py 交付（2026-11-10 已完成）；
#      覆盖率矩阵 / 泄漏测试 / 复现包属后续 T 任务。
# 契约：data_interface.md §1.0 / §1.1 —— match_id 逐字符一致、date 为 ISO 字符串、
#      season 为 YYYY/YY、y = FTR.map(H=0,D=1,A=2)。
#
# 两个刻意的设计（写进 M1 卡 §7 坑位）：
#   1. date 存 **ISO 字符串**而不是 datetime64。preds_*.csv 里 date 是字符串，
#      两边按 match_id 逐字符内连接；若 panel 存时间戳，读出来格式会漂移。
#   2. panel 保留比分 / 射门 / FTR 等**赛后观测列**，用途是 y 的审计与误差分析，
#      **不等于允许入模**。防泄漏由各 arm 的特征白名单 + splits.json 控制，
#      任何模型都不得把 FTR / 比分 / 射门当特征（data_interface.md §2）。
#      MaxCH/MaxCD/MaxCA 不进 panel，覆盖率矩阵按 T1.4 直接读 raw。
# =============================================================================

PANEL_PATH = ROOT / "data" / "processed" / "panel.parquet"
PANEL_COLUMNS: tuple[str, ...] = (
    "match_id", "league", "season", "date", "home", "away",
    "FTR", "y", "FTHG", "FTAG", "HTHG", "HTAG",
    "HS", "AS", "HST", "AST",
    "PSCH", "PSCD", "PSCA",
    "is_promoted_home", "is_promoted_away", "matchday",
)
H3_PANEL_COLS: tuple[str, ...] = (
    "is_promoted_home", "is_promoted_away", "matchday",
)
SORT_KEYS: tuple[str, ...] = ("league", "season", "date", "home", "away")
EXPECTED_LEAGUE_TOTALS = {"E0": 8_360, "SP1": 8_360, "I1": 8_286,
                          "D1": 6_732, "F1": 8_111, "N1": 6_658}
EXPECTED_EVAL_TOTALS = {"E0": 3_040, "SP1": 3_040, "I1": 3_040,
                        "D1": 2_448, "F1": 2_791, "N1": 2_374}
# 「相对 n 队满额赛程」少打了的块：都是真实世界事件，不是抓漏（T1.3-a）。
EXPECTED_SHORT_BLOCKS = {("F1", "2019/20"): 279, ("N1", "2019/20"): 232}
# 评估窗三列收盘赔率缺失的 5 场，按块分布（data_interface.md §1.0）。
EXPECTED_ODDS_MISSING_BLOCKS = {
    ("SP1", "2017/18"): 1, ("N1", "2017/18"): 3, ("D1", "2018/19"): 1,
}
EXPECTED_EVAL_ROWS = 16_733
EXPECTED_B6_ROWS = 16_728
EXPECTED_BLOCKS = 132
EXPECTED_EVAL_BLOCKS = 48


def make_match_id(frame: pd.DataFrame) -> pd.DataFrame:
    """``match_id = league|season|date|home|away``（ISO 字符串日期 + 归一队名）。

    与 ``data_interface.md`` §1.0 的 f-string **逐字符同构**：preds_*.csv 里的
    match_id 必须能直接和本列内连接。重复即抛错，绝不 dedup（会静默少比赛）。
    """
    needed = ("league", "season", "date", "home", "away")
    absent = [c for c in needed if c not in frame.columns]
    if absent:
        raise ValueError(f"make_match_id 缺少列：{absent}；请先跑 clean_panel()")
    out = frame.copy()
    out["match_id"] = (out["league"].astype(str) + "|" + out["season"] + "|"
                       + out["date"] + "|" + out["home"] + "|" + out["away"])
    if (out["match_id"].isna().any()
            or not out["match_id"].str.count(r"\|").eq(4).all()):
        raise ValueError("match_id 存在空值或字段数不等于 5")
    n_dupes = int(out["match_id"].duplicated().sum())
    if n_dupes:
        examples = out.loc[out["match_id"].duplicated(), "match_id"].head(3).tolist()
        raise ValueError(f"match_id 重复 {n_dupes} 行，例如 {examples}；禁止 dedup")
    return out


def build_panel(raw: pd.DataFrame | None = None,
                alias_path: str | Path | None = None) -> pd.DataFrame:
    """S3 主入口：S2 清洗表 → ``match_id`` → 22 列窄表 → 排序。

    **只返回 DataFrame，不落盘**；落盘是 ``write_panel()`` 的职责。
    幂等：同一份 raw 连续调用两次，结果逐元素相等（s3 自检第 12 项）。
    """
    frame = clean_panel(raw, alias_path)
    frame = make_match_id(frame)
    absent = [c for c in PANEL_COLUMNS if c not in frame.columns]
    if absent:
        raise ValueError(f"S2 清洗表缺少 panel 契约列：{absent}")
    panel = (frame.loc[:, list(PANEL_COLUMNS)]
             .sort_values(list(SORT_KEYS), kind="mergesort")
             .reset_index(drop=True))

    if len(panel) != EXPECTED_ROWS:
        raise ValueError(f"panel 行数应为 {EXPECTED_ROWS}，实际 {len(panel)}")
    if list(panel.columns) != list(PANEL_COLUMNS):
        raise ValueError("panel 列顺序与 PANEL_COLUMNS 契约不一致")
    if not panel["match_id"].is_unique:
        raise ValueError("排序后 match_id 不再唯一")
    if not np.array_equal(panel["y"].to_numpy(),
                          panel["FTR"].map(LABEL_MAP).to_numpy()):
        raise ValueError("y 与 FTR.map(H=0,D=1,A=2) 不一致")
    if panel[list(H3_PANEL_COLS)].isna().any().any():
        raise ValueError("H3 三列存在空值")
    return panel


def write_panel(panel: pd.DataFrame | None = None,
                out_path: str | Path | None = None) -> dict:
    """把 22 列窄表写成 ``data/processed/panel.parquet``（**不入库**，README §3.6）。

    ``index=False`` 保证读回时列序 / 行数完全一样；重复运行直接覆盖，幂等。
    """
    p = Path(out_path) if out_path is not None else PANEL_PATH
    frame = build_panel() if panel is None else panel
    p.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(p, index=False, engine="pyarrow")
    if not p.exists() or p.stat().st_size == 0:
        raise ValueError(f"panel.parquet 写入失败或为空：{p}")
    return {"path": str(p), "bytes": p.stat().st_size,
            "rows": len(frame), "cols": len(frame.columns)}


def s3_selfcheck(log_path: str | Path | None = None,
                 raw_dir: str | Path | None = None,
                 out_path: str | Path | None = None) -> dict:
    """S3 验收：12 项硬断言 + 可复核日志。

    - ``out_path=None``：只在临时目录验证 Parquet round-trip，不写仓库（测试用）。
    - ``out_path`` 给定：额外把正式主表写到该路径并读回再验一次（CLI 用）。
    """
    import tempfile

    out: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    raw = read_all(raw_dir)
    panel = build_panel(raw)
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]

    # --- 独立复算，不复用 build_panel 的中间结果 ---
    recomputed_id = (panel["league"].astype(str) + "|" + panel["season"] + "|"
                     + panel["date"] + "|" + panel["home"] + "|" + panel["away"])
    id_ok = bool(panel["match_id"].equals(recomputed_id)
                 and panel["match_id"].str.count(r"\|").eq(4).all()
                 and panel["match_id"].notna().all()
                 and panel["match_id"].is_unique)
    key_frame = panel[list(SORT_KEYS)].reset_index(drop=True)
    sorted_keys = (panel[list(SORT_KEYS)]
                   .sort_values(list(SORT_KEYS), kind="mergesort")
                   .reset_index(drop=True))
    sorted_ok = bool(key_frame.equals(sorted_keys))
    five_tuple_dupes = int(panel.duplicated(["league", "season", "date",
                                             "home", "away"]).sum())
    y_ok = bool(
        np.array_equal(panel["y"].to_numpy(), panel["FTR"].map(LABEL_MAP).to_numpy())
        and set(panel["y"].unique()) <= {0, 1, 2}
        and panel["y"].value_counts().sort_index().to_dict()
        == {0: 21_194, 1: 11_824, 2: 13_489}
    )
    date_ok = bool(
        panel["date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
        and panel["date"].min() == "2003-08-01"
        and panel["date"].max() == "2025-05-25"
        and panel["season"].str.match(r"^\d{4}/\d{2}$").all()
    )
    h3_invariant = h3_invariant_to_post_match(panel)
    h3_ok = bool(panel[list(H3_PANEL_COLS)].notna().all().all()
                 and panel["matchday"].between(1, 38).all()
                 and h3_invariant)

    # 赔率覆盖：前 9 季整列不存在 → 全 NaN；评估窗只缺 3 块共 5 场。
    odds_early_nan = bool(panel.loc[panel["season"] <= "2011/12",
                                    list(ODDS_COLS)].isna().all().all())
    eval_missing = sub[list(ODDS_COLS)].isna().any(axis=1)
    missing_by_block = (sub.loc[eval_missing].groupby(["league", "season"])
                        .size().to_dict())
    n_missing = int(eval_missing.sum())
    odds_ok = bool(odds_early_nan and n_missing == 5
                   and missing_by_block == EXPECTED_ODDS_MISSING_BLOCKS
                   and len(sub) - n_missing == EXPECTED_B6_ROWS)

    # T1.3-a 场次核查：n 队联赛满额 = n*(n-1)，只有 2 个真实腰斩块例外。
    teams = _team_blocks(panel)
    block_rows = panel.groupby(["league", "season"]).size().to_dict()
    block_ok = len(teams) == EXPECTED_BLOCKS and all(
        block_rows[k] == EXPECTED_SHORT_BLOCKS.get(k, len(v) * (len(v) - 1))
        for k, v in teams.items()
    )
    league_totals = panel.groupby("league").size().to_dict()
    eval_totals = sub.groupby("league").size().to_dict()
    totals_ok = bool(
        league_totals == EXPECTED_LEAGUE_TOTALS
        and eval_totals == EXPECTED_EVAL_TOTALS
        and sum(league_totals.values()) == EXPECTED_ROWS
        and len(sub) == EXPECTED_EVAL_ROWS
        and sub.groupby(["league", "season"]).ngroups == EXPECTED_EVAL_BLOCKS
    )

    # Parquet round-trip：先在临时目录验「落盘不会变形」，再写正式产物。
    roundtrip_ok = True
    with tempfile.TemporaryDirectory(prefix="wb_panel_") as tmp:
        tmp_path = Path(tmp) / "panel.parquet"
        panel.to_parquet(tmp_path, index=False, engine="pyarrow")
        try:
            pd.testing.assert_frame_equal(pd.read_parquet(tmp_path), panel)
        except AssertionError:
            roundtrip_ok = False
    written: dict | None = None
    if out_path is not None:
        written = write_panel(panel, out_path)
        back = pd.read_parquet(out_path)
        try:
            pd.testing.assert_frame_equal(back, panel)
        except AssertionError:
            roundtrip_ok = False
        if len(back) != EXPECTED_ROWS or not back["match_id"].is_unique:
            roundtrip_ok = False

    # 幂等 + 不入库规则
    repro_ok = bool(panel.equals(build_panel(raw)))
    gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    ignore_ok = "*.parquet" in gitignore_text and "/data/processed/*" in gitignore_text

    emit("=" * 100)
    emit("S3 建模总表自检 · Football-Calibration / M1 · T1.3 + T1.3-a")
    emit("=" * 100)
    emit(f"执行时间 : {pd.Timestamp.now().tz_localize('Asia/Shanghai').isoformat(timespec='seconds')}")
    emit(f"解释器   : Python / pandas {pd.__version__} · numpy {np.__version__}")
    emit(f"输入     : data/raw/*.csv 132 文件 → {len(raw):,} 行（S1 已剔除 11 行全空白）")
    if written:
        # 日志入库，写相对路径，避免各人机器上的绝对路径造成无意义 diff。
        try:
            rel = Path(written["path"]).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            rel = written["path"]
        out_desc = f"已写入 {rel} ({written['bytes']:,} B)"
    else:
        out_desc = "仅内存（未指定 --out）"
    emit(f"输出     : {len(panel):,} 行 × {len(panel.columns)} 列；产物 {out_desc}")
    emit("")
    emit(f"panel 列序（{len(PANEL_COLUMNS)} 列，顺序即契约）：")
    emit("  " + ", ".join(PANEL_COLUMNS))
    emit("match_id 示例：")
    for value in panel["match_id"].head(3):
        emit(f"  {value}")
    emit("")
    emit("场次核查（T1.3-a）：")
    for lg in sorted(panel["league"].unique()):
        emit(f"  {lg:<4} 全库 22 季 {league_totals[lg]:>6,} 场 / "
             f"评估窗 8 季 {eval_totals[lg]:>6,} 场")
    emit(f"  合计 全库 {sum(league_totals.values()):,} / "
         f"评估窗 {len(sub):,}（{sub.groupby(['league', 'season']).ngroups} 块）")
    emit(f"  非满额块（相对 n 队满额 n*(n-1) 少打的比赛）：{EXPECTED_SHORT_BLOCKS}")
    emit(f"  法甲 2023/24 起 18 队 → 306 场/季，由 n*(n-1) 规则覆盖，不是缺赛")
    emit(f"评估窗三列收盘赔率缺失：{n_missing} 场，按块 {missing_by_block}；"
         f"B6 / B6r 有效 n = {len(sub) - n_missing:,}")
    emit("")

    written_desc = (f"{written['bytes']:,} B" if written
                    else "N/A（未指定 --out）")

    checks: list[tuple[str, bool, str]] = [
        ("行数守恒：46,518 − 11 空白 = 46,507，且与 S2 清洗表一致",
         len(raw) == EXPECTED_ROWS and len(panel) == EXPECTED_ROWS,
         f"raw={len(raw):,}, panel={len(panel):,}"),
        (f"{len(PANEL_COLUMNS)} 列窄表、列序与 PANEL_COLUMNS 恒等；Max* 不进 panel",
         list(panel.columns) == list(PANEL_COLUMNS)
         and not any(c.startswith("Max") for c in panel.columns),
         f"cols={len(panel.columns)}"),
        ("match_id 唯一 / 非空 / 5 段 / 可由契约公式逐字符复算",
         id_ok, f"unique={panel['match_id'].is_unique}, reproducible={id_ok}"),
        ("按 league,season,date 单调排序，且五元组 0 重复",
         sorted_ok and five_tuple_dupes == 0,
         f"sorted={sorted_ok}, dupes={five_tuple_dupes}"),
        ("y = FTR.map(H=0,D=1,A=2)，值域 {0,1,2}，分布 21,194/11,824/13,489",
         y_ok, f"y_counts={panel['y'].value_counts().sort_index().to_dict()}"),
        ("date 为 ISO 字符串、season 为 YYYY/YY、范围 2003-08-01→2025-05-25",
         date_ok, f"range={panel['date'].min()} → {panel['date'].max()}"),
        ("H3 三列无空、matchday 1–38，且打乱赛后列后逐元素不变",
         h3_ok, f"invariant={h3_invariant}"),
        ("收盘赔率：前 9 季全 NaN；评估窗只缺 3 块共 5 场，B6 有效 16,728",
         odds_ok, f"earlyNaN={odds_early_nan}, missing={n_missing}, "
                  f"blocks={missing_by_block}"),
        ("T1.3-a：132 块均满足 n 队满额 n*(n−1)，仅 2 个真实腰斩块例外",
         block_ok, f"blocks={len(teams)}, short={EXPECTED_SHORT_BLOCKS}"),
        ("六联赛 22 季合计 46,507；评估窗 48 块 16,733 且逐联赛合计全对",
         totals_ok, f"leagueTotals={league_totals}, evalTotals={eval_totals}"),
        ("Parquet round-trip：读回逐元素相等；正式产物已写入且可读",
         roundtrip_ok, f"roundtrip={roundtrip_ok}, written={written_desc}"),
        ("幂等可复现（同一 raw 两次 build_panel 相等）+ 不入库规则仍在",
         repro_ok and ignore_ok,
         f"reproducible={repro_ok}, gitignore(*.parquet + /data/processed/*)={ignore_ok}"),
    ]

    emit("-" * 100)
    for name, ok, detail in checks:
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
    passed = sum(ok for _, ok, _ in checks)
    emit("-" * 100)
    emit(f"汇总: {passed}/{len(checks)} 项 PASS"
         f"{'  -> S3 通过，可进入 S4' if passed == len(checks) else '  -> 存在 FAIL，禁止进入 S4'}")
    emit("")
    emit("边界: S3 只交付建模总表；configs/splits.json（48 块）属 S4，覆盖率矩阵 / 泄漏测试 / 复现包属后续 T 任务。")
    emit("      panel.parquet 不入库（.gitignore *.parquet + /data/processed/*），全组各自跑同一脚本生成。")
    emit("      panel 保留比分 / 射门 / FTR 仅供 y 审计与误差分析，**不得入模**；赔率列除 B6/B6r 外不得入模。")
    emit("复现: python src/build_panel.py --stage s3 --log results/logs/s3_panel_<date>.txt")
    emit("      python src/build_panel.py --stage s3 --out <自定义路径>   # 指定落盘位置")
    emit("      pytest -q tests/")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks), "rows": len(panel),
            "cols": len(panel.columns), "eval_rows": len(sub),
            "b6_rows": len(sub) - n_missing, "blocks": len(teams),
            "roundtrip": roundtrip_ok, "reproducible": repro_ok,
            "written": written}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="M1 / build_panel.py：S1 读取器自检（默认）/ S2 字段统一 / "
                    "S3 建模总表 / S4 48 块切分 / S5 收尾自检")
    ap.add_argument("--stage", choices=["s1", "s2", "s3", "s4", "s5"], default="s1",
                    help="s1 = read_raw() 自检（默认）；s2 = 字段统一；"
                         "s3 = 拼总表并落盘；s4 = 生成 configs/splits.json；"
                         "s5 = 收尾自检（不加工数据）")
    ap.add_argument("--build-alias", action="store_true",
                    help="从 data/raw/ 重新生成 configs/team_alias.csv（S2 产物）")
    ap.add_argument("--raw-dir", default=None, help="原始 CSV 目录（默认 data/raw/）")
    ap.add_argument("--out", default=None,
                    help="s3 主表（默认 data/processed/panel.parquet，不入库）/ "
                         "s4 切分契约（默认 configs/splits.json，入库）的落盘路径")
    ap.add_argument("--log", default=None,
                    help=("自检日志路径（默认不落盘）；建议 "
                          f"s1: results/logs/s1_read_raw_{date.today()}.txt / "
                          f"s2: results/logs/s2_clean_{date.today()}.txt / "
                          f"s3: results/logs/s3_panel_{date.today()}.txt / "
                          f"s4: results/logs/s4_splits_{date.today()}.txt / "
                          f"s5: results/logs/s5_handover_{date.today()}.txt"))
    args = ap.parse_args()
    if args.build_alias:
        rows = build_team_alias(args.raw_dir, ALIAS_PATH)
        print(f"configs/team_alias.csv 已生成：{len(rows)} 行")
    if args.stage == "s5":
        # 延迟导入：handover.py 反过来 import 本文件，放到分支里避免循环。
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from src.handover import handover_selfcheck
        summary = handover_selfcheck(args.log)
    elif args.stage == "s4":
        # 延迟导入：splits.py 反过来 import 本文件，放到分支里避免循环。
        # 直接 ``python src/build_panel.py`` 时 sys.path[0] 是 src/，需补仓库根。
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from src.splits import SPLITS_PATH as S4_PATH, s4_selfcheck
        summary = s4_selfcheck(args.log, args.out or str(S4_PATH))
    elif args.stage == "s3":
        summary = s3_selfcheck(args.log, args.raw_dir, args.out or str(PANEL_PATH))
    elif args.stage == "s2":
        summary = s2_selfcheck(args.log, args.raw_dir)
    else:
        summary = selfcheck(args.raw_dir, args.log)
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
