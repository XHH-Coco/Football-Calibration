"""M1 / S4 · T1.5 —— 48 块 rolling-origin 切分契约 ``configs/splits.json``。

为什么单独一个文件
------------------
S1–S3 都在 ``src/build_panel.py`` 同一文件里演进（读取 → 清洗 → 总表）；
S4 产出的是**入库的、全组必须逐字一致的小契约**，不是可再生的大数据文件，
所以按分工方案 v1.3 §5.2 的目录规划落到 ``src/splits.py``。
``python src/build_panel.py --stage s4`` 只是本文件的统一入口（延迟导入，避免循环）。

切分规则（唯一口径，写进 JSON 的 ``rule`` 段）
------------------------------------------------
    test  : panel 中 ``league == block.league`` 且 ``season == block.season`` 的全部比赛
    train : panel 中 ``league == block.league`` 且 ``date < block.test_start`` 的全部比赛
            —— **同联赛 + 严格更早**，跨季累积（expanding window）。

两个刻意的设计：
  1. train 用 **ISO 日期字符串** ``date < test_start`` 判定，而不是 ``season < 目标季``。
     前者是「预测时点能真正拿到的信息」的直接定义，防泄漏最不容易被绕过；
     后者只是它的一个等价复核。实测 48 块两者行数与 match_id 集合**完全相同**，
     且 train 中目标季及之后 **0 场**、``train_end < test_start`` 全部成立。
  2. ``n_new_team`` 用 **「历史累积 train」** 口径（test 里从未在 train 出现过的队数），
     与 S2 的 ``is_promoted_*``「上一季名单」口径**不同**，勿混用（M1 卡 §7 坑 9）。
     实测评估窗最大 2，满足 T1.6 的 ``≤ 3``。

入库与幂等
----------
``configs/splits.json`` 是 KB 级纯文本契约，**入库、随 Git 分发**（与不入库的
``data/processed/panel.parquet`` 正好相反）。序列化固定字段顺序、UTF-8、LF、
缩进 2、**不写时间戳**：同一份 raw 重跑两次得到逐字节相同的文本，Git diff 无噪音。
落盘前不依赖磁盘上的 ``panel.parquet``——由 ``build_panel()`` 从 132 个 raw 重建，
因此 clone 后直接 ``pytest -q tests/`` 也全绿。

运行（项目环境 DSC5001_Project，见 M1 卡 §7 坑 8）
----------------------------------------------------
    python src/build_panel.py --stage s4 --log results/logs/s4_splits_<date>.txt
    python src/splits.py --log results/logs/s4_splits_<date>.txt   # 等价
    pytest -q tests/test_splits.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:                       # 允许 ``python src/splits.py`` 直接跑
    sys.path.insert(0, str(ROOT))

from src.build_panel import (  # noqa: E402
    EVAL_SEASONS,
    EXPECTED_EVAL_BLOCKS,
    EXPECTED_EVAL_ROWS,
    EXPECTED_EVAL_TOTALS,
    build_panel,
)

SPLITS_PATH = ROOT / "configs" / "splits.json"
SCHEMA_VERSION = "1.0"
MIN_N_TRAIN = 4_284                 # 实测下界（1718_D1 / 1718_N1 = 14 季 × 306 场）
MAX_N_NEW_TEAM = 3                 # T1.6：升班马要「标记」而非断言不存在
EXPECTED_MIN_TRAIN_BLOCKS = {("D1", "2017/18"), ("N1", "2017/18")}
BLOCK_FIELDS: tuple[str, ...] = (
    "block_id", "league", "season",
    "test_start", "test_end", "train_start", "train_end",
    "n_train", "n_test", "n_new_team",
)
TRAIN_RULE = ("league == block.league AND date < block.test_start "
              "（ISO 字符串比较；同联赛、严格更早、跨季累积）")
TEST_RULE = "league == block.league AND season == block.season（该块全部比赛）"


def _serialise(data: dict) -> str:
    """固定格式序列化：字段顺序稳定 + LF + 无时间戳，保证重跑不产生 diff 噪音。"""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def make_splits(panel: pd.DataFrame | None = None) -> dict:
    """从 22 列 panel 生成 48 块切分契约（**只返回 dict，不落盘**）。

    每块都当场做防泄漏断言：train 不含目标季及之后的比赛、train 末日 < test 首日、
    train 与 test 的 ``match_id`` 交集为空。任一不满足直接抛 ``ValueError``，
    绝不静默放行。
    """
    frame = build_panel() if panel is None else panel
    needed = ("match_id", "league", "season", "date", "home", "away")
    absent = [c for c in needed if c not in frame.columns]
    if absent:
        raise ValueError(f"make_splits 缺少 panel 契约列：{absent}；请先跑 --stage s3")

    sub = frame.loc[frame["season"].isin(EVAL_SEASONS)]
    if len(sub) != EXPECTED_EVAL_ROWS:
        raise ValueError(f"评估窗应为 {EXPECTED_EVAL_ROWS} 场，实际 {len(sub)}")

    blocks: list[dict] = []
    for (league, season), test in sub.groupby(["league", "season"], sort=True):
        test_start, test_end = str(test["date"].min()), str(test["date"].max())
        train = frame.loc[(frame["league"] == league)
                          & (frame["date"] < test_start)]
        if train.empty:
            raise ValueError(f"{league}|{season}: train 为空，切分无意义")
        if bool((train["season"] >= season).any()):
            raise ValueError(f"{league}|{season}: train 含目标季及之后的比赛 → 泄漏")
        if str(train["date"].max()) >= test_start:
            raise ValueError(f"{league}|{season}: train_end 未严格早于 test_start")
        if not set(train["match_id"]).isdisjoint(set(test["match_id"])):
            raise ValueError(f"{league}|{season}: train 与 test 的 match_id 有交集")

        # 等价口径复核：按 season 严格早于过滤，必须与按 date 过滤得到同一批比赛。
        by_season = frame.loc[(frame["league"] == league)
                              & (frame["season"] < season)]
        if not set(train["match_id"]) == set(by_season["match_id"]):
            raise ValueError(
                f"{league}|{season}: 「date < test_start」与「season 严格更早」不等价，"
                "说明赛季日期发生重叠，必须人工复核切分规则")

        seen = set(train["home"]) | set(train["away"])
        new_teams = (set(test["home"]) | set(test["away"])) - seen
        if len(new_teams) > MAX_N_NEW_TEAM:
            raise ValueError(f"{league}|{season}: n_new_team={len(new_teams)} > 3，"
                             "先查是否扩军 / 改名未归一，不要改断言凑数")

        blocks.append({
            "block_id": f"{league}|{season}",
            "league": str(league),
            "season": str(season),
            "test_start": test_start,
            "test_end": test_end,
            "train_start": str(train["date"].min()),
            "train_end": str(train["date"].max()),
            "n_train": int(len(train)),
            "n_test": int(len(test)),
            "n_new_team": int(len(new_teams)),
        })

    if len(blocks) != EXPECTED_EVAL_BLOCKS:
        raise ValueError(f"应有 {EXPECTED_EVAL_BLOCKS} 块，实际 {len(blocks)}")
    if sum(b["n_test"] for b in blocks) != EXPECTED_EVAL_ROWS:
        raise ValueError("n_test 合计与评估窗 16,733 场不一致")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "src/splits.py::make_splits()",
        "source": "data/raw/*.csv → build_panel() → 22 列 panel（46,507 行）",
        "rule": {
            "test": TEST_RULE,
            "train": TRAIN_RULE,
            "equivalence_check": "逐块断言「date < test_start」与「season 严格更早」得到同一批 match_id",
            "cluster": "一个 (league, season) 块 = 一个 bootstrap 簇；48 块，绝不按 16,733 场比赛重采样",
            "n_new_team": "历史累积 train 口径；与 S2 的 is_promoted_*（上一季名单）不同",
        },
        "n_blocks": len(blocks),
        "n_test_total": sum(b["n_test"] for b in blocks),
        "n_train_min": min(b["n_train"] for b in blocks),
        "blocks": blocks,
    }


def write_splits(splits: dict | None = None,
                 out_path: str | Path | None = None) -> dict:
    """把切分契约写成 UTF-8 / LF 的 ``configs/splits.json``（**入库**）。

    重复运行直接覆盖，内容逐字节相同（不含时间戳、字段顺序固定）。
    """
    data = make_splits() if splits is None else splits
    p = Path(out_path) if out_path is not None else SPLITS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    text = _serialise(data)
    with p.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    if not p.exists() or p.stat().st_size == 0:
        raise ValueError(f"splits.json 写入失败或为空：{p}")
    return {"path": str(p), "bytes": p.stat().st_size,
            "n_blocks": data["n_blocks"],
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def load_splits(path: str | Path | None = None) -> dict:
    """读回契约并校验顶层结构与 48 块的字段完整性。"""
    p = Path(path) if path is not None else SPLITS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"splits.json schema_version 应为 {SCHEMA_VERSION}")
    if data.get("n_blocks") != EXPECTED_EVAL_BLOCKS:
        raise ValueError("splits.json 的 n_blocks 不是 48")
    blocks = data.get("blocks")
    if not isinstance(blocks, list) or len(blocks) != EXPECTED_EVAL_BLOCKS:
        raise ValueError("splits.json 的 blocks 必须是 48 条")
    for b in blocks:
        missing = [f for f in BLOCK_FIELDS if f not in b]
        if missing:
            raise ValueError(f"块 {b.get('block_id', '?')} 缺字段：{missing}")
    return data


def resolve_split(panel: pd.DataFrame, block: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """**给 M2 harness 用的唯一入口**：按规则从 panel 复算某一折的 train / test。

    切分由规则决定，JSON 里的 ``n_train`` / ``n_test`` 只用于校验：
    若契约被手工改坏（例如把 ``test_start`` 挪后让 train 吃到未来），
    这里会直接抛 ``ValueError``，而不是悄悄多给模型几百场比赛。
    """
    league, season, start = block["league"], block["season"], block["test_start"]
    test = panel.loc[(panel["league"] == league)
                     & (panel["season"] == season)]
    train = panel.loc[(panel["league"] == league)
                      & (panel["date"] < start)]
    if len(test) != block["n_test"] or len(train) != block["n_train"]:
        raise ValueError(
            f"{block['block_id']}: 按规则复算 test={len(test)}/train={len(train)}，"
            f"与契约 {block['n_test']}/{block['n_train']} 不符")
    if str(test["date"].min()) != block["test_start"] or \
            str(test["date"].max()) != block["test_end"]:
        raise ValueError(f"{block['block_id']}: test 日期边界与契约不符")
    if len(train) == 0 or str(train["date"].max()) >= start:
        raise ValueError(f"{block['block_id']}: train 未严格早于 test_start")
    if bool((train["season"] >= season).any()):
        raise ValueError(f"{block['block_id']}: train 含目标季及之后比赛 → 泄漏")
    if not set(train["match_id"]).isdisjoint(set(test["match_id"])):
        raise ValueError(f"{block['block_id']}: train 与 test 有交集")
    return train, test


def s4_selfcheck(log_path: str | Path | None = None,
                 out_path: str | Path | None = None) -> dict:
    """S4 验收：12 项硬断言 + 可复核日志。

    - ``out_path=None``：只在内存里验契约，不写仓库（测试用）。
    - ``out_path`` 给定：额外写正式 ``configs/splits.json`` 并读回逐项复核。
    """
    out: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    panel = build_panel()
    data = make_splits(panel)
    blocks = data["blocks"]
    sub = panel.loc[panel["season"].isin(EVAL_SEASONS)]

    # --- 独立复算，不复用 make_splits 的中间结果 ---
    keys = [(b["league"], b["season"]) for b in blocks]
    expected_keys = {(lg, s) for lg in sorted(panel["league"].unique())
                     for s in EVAL_SEASONS}
    shape_ok = (len(blocks) == EXPECTED_EVAL_BLOCKS
                and len(set(keys)) == EXPECTED_EVAL_BLOCKS
                and set(keys) == expected_keys
                and len({b["block_id"] for b in blocks}) == EXPECTED_EVAL_BLOCKS
                and all(re.fullmatch(r"\d{4}/\d{2}", b["season"]) for b in blocks)
                and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", b[f])
                        for b in blocks
                        for f in ("test_start", "test_end", "train_start", "train_end")))

    panel_bounds = (sub.groupby(["league", "season"])["date"]
                    .agg(["min", "max"]).to_dict("index"))
    bounds_ok = all(
        panel_bounds[(b["league"], b["season"])]["min"] == b["test_start"]
        and panel_bounds[(b["league"], b["season"])]["max"] == b["test_end"]
        and b["test_start"] <= b["test_end"]
        and b["train_start"] <= b["train_end"] < b["test_start"]
        for b in blocks
    )

    panel_counts = sub.groupby(["league", "season"]).size().to_dict()
    by_league = {lg: sum(b["n_test"] for b in blocks if b["league"] == lg)
                 for lg in sorted({k[0] for k in expected_keys})}
    counts_ok = (all(b["n_test"] == panel_counts[(b["league"], b["season"])]
                     for b in blocks)
                 and sum(b["n_test"] for b in blocks) == EXPECTED_EVAL_ROWS
                 and by_league == EXPECTED_EVAL_TOTALS)

    # test 两两不重叠 + 并集恰为评估窗（0 漏 0 重）
    test_ids: list[set[str]] = []
    for b in blocks:
        ids = set(panel.loc[(panel["league"] == b["league"])
                            & (panel["season"] == b["season"]), "match_id"])
        test_ids.append(ids)
    union = set().union(*test_ids)
    sum_sizes = sum(len(s) for s in test_ids)
    cover_ok = (sum_sizes == len(union) == EXPECTED_EVAL_ROWS
                and union == set(sub["match_id"]))

    # train 严格早于 / 限同联赛 / 两种口径等价 / 与 test 无交集
    future_rows = 0
    overlap = 0
    cross_league = 0
    mismatch_equiv = 0
    for b in blocks:
        train, test = resolve_split(panel, b)
        future_rows += int((train["season"] >= b["season"]).sum())
        overlap += len(set(train["match_id"]) & set(test["match_id"]))
        cross_league += int((train["league"] != b["league"]).sum())
        by_season = panel.loc[(panel["league"] == b["league"])
                              & (panel["season"] < b["season"])]
        mismatch_equiv += int(set(train["match_id"]) != set(by_season["match_id"]))
    boundary_ok = (future_rows == 0 and overlap == 0 and cross_league == 0
                   and mismatch_equiv == 0
                   and all(b["train_end"] < b["test_start"] for b in blocks))

    n_trains = [b["n_train"] for b in blocks]
    min_train = min(n_trains)
    min_blocks = {(b["league"], b["season"]) for b in blocks
                  if b["n_train"] == min_train}
    train_ok = (min_train >= MIN_N_TRAIN and min_train == MIN_N_TRAIN
                and min_blocks == EXPECTED_MIN_TRAIN_BLOCKS)

    new_teams = [b["n_new_team"] for b in blocks]
    new_team_ok = max(new_teams) <= MAX_N_NEW_TEAM and min(new_teams) >= 0

    # 幂等：两次 make_splits 序列化逐字节相同；JSON round-trip 对象相等；无时间戳
    again = _serialise(make_splits(panel))
    idem_ok = (again == _serialise(data)
               and json.loads(_serialise(data)) == data
               and "timestamp" not in _serialise(data).lower()
               and "generated_at" not in _serialise(data).lower())

    # 入库规则：splits.json 不被忽略；panel.parquet 仍被忽略
    gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    proc = subprocess.run(["git", "check-ignore", "-q", "configs/splits.json"],
                          cwd=ROOT, capture_output=True)
    proc_panel = subprocess.run(
        ["git", "check-ignore", "-q", "data/processed/panel.parquet"],
        cwd=ROOT, capture_output=True)
    ignore_ok = (proc.returncode != 0 and proc_panel.returncode == 0
                 and "*.parquet" in gitignore_text
                 and "/data/processed/*" in gitignore_text)

    # Round-trip：先在临时目录写一次并读回，指定 --out 时再写正式产物并再验一次。
    written: dict | None = None
    disk_ok = True
    with tempfile.TemporaryDirectory(prefix="wb_splits_") as tmp:
        tmp_path = Path(tmp) / "splits.json"
        write_splits(data, tmp_path)
        loaded = load_splits(tmp_path)
        disk_ok = loaded == data
        for b in loaded["blocks"]:
            tr, te = resolve_split(panel, b)
            if len(tr) != b["n_train"] or len(te) != b["n_test"]:
                disk_ok = False
    if out_path is not None:
        written = write_splits(data, out_path)
        disk_ok = disk_ok and load_splits(out_path) == data

    emit("=" * 100)
    emit("S4 切分契约自检 · Football-Calibration / M1 · T1.5")
    emit("=" * 100)
    emit(f"执行时间 : {pd.Timestamp.now().tz_localize('Asia/Shanghai').isoformat(timespec='seconds')}")
    emit(f"解释器   : Python / pandas {pd.__version__}")
    emit(f"输入     : data/raw/*.csv → build_panel() → {len(panel):,} 行 × {len(panel.columns)} 列")
    emit(f"切分规则 : test = {TEST_RULE}")
    emit(f"           train = {TRAIN_RULE}")
    emit("等价复核 : 逐块断言「date < test_start」与「season 严格更早」得到同一批 match_id")
    if written:
        try:
            rel = Path(written["path"]).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            rel = written["path"]
        out_desc = f"已写入 {rel} ({written['bytes']:,} B)"
    else:
        out_desc = "仅内存（未指定 --out）"
    emit(f"输出     : {len(blocks)} 块 / n_test 合计 "
         f"{sum(b['n_test'] for b in blocks):,}；产物 {out_desc}")
    emit("")
    emit("逐联赛 8 季 n_train 范围（expanding window，跨季累积）：")
    for lg in sorted({b["league"] for b in blocks}):
        vals = [b["n_train"] for b in blocks if b["league"] == lg]
        emit(f"  {lg:<4} {min(vals):>6,} → {max(vals):>6,} 场；"
             f"n_test 合计 {sum(b['n_test'] for b in blocks if b['league'] == lg):,}")
    emit("")
    emit("最紧的 3 块（train 最少）：")
    for b in sorted(blocks, key=lambda x: x["n_train"])[:3]:
        emit(f"  {b['block_id']:<12} train={b['n_train']:,} test={b['n_test']:,} "
             f"train_end={b['train_end']} test_start={b['test_start']} "
             f"n_new_team={b['n_new_team']}")
    emit("")
    emit("示例块（首 / 末）：")
    for b in (blocks[0], blocks[-1]):
        emit(f"  {b['block_id']} | {b['test_start']}→{b['test_end']} | "
             f"train {b['train_start']}→{b['train_end']} | "
             f"n_train={b['n_train']} n_test={b['n_test']} n_new_team={b['n_new_team']}")
    emit("")

    written_desc = f"{written['bytes']:,} B" if written else "N/A（未指定 --out）"
    checks: list[tuple[str, bool, str]] = [
        ("48 块 = 6 联赛 × 8 季；block_id 唯一、season 为 YYYY/YY",
         shape_ok, f"blocks={len(blocks)}, unique={len(set(keys))}"),
        ("test_start / test_end 为 ISO 且与 panel 逐块 min/max 一致；train_end < test_start",
         bounds_ok, f"bounds_ok={bounds_ok}"),
        ("n_test 逐块等于 panel 计数；合计 16,733；逐联赛合计全对",
         counts_ok, f"total={sum(b['n_test'] for b in blocks):,}"),
        ("48 块 test 两两不重叠，且并集恰为评估窗 16,733 场（0 漏 0 重）",
         cover_ok, f"sumSizes={sum_sizes:,}, union={len(union):,}"),
        ("防泄漏：train 中目标季及之后 0 场；train∩test 空；train 限同联赛",
         boundary_ok, f"future={future_rows}, overlap={overlap}, "
                      f"crossLeague={cross_league}, equivMismatch={mismatch_equiv}"),
        ("两种口径等价：date < test_start 与 season 严格更早得到同一批 match_id",
         mismatch_equiv == 0, f"mismatch={mismatch_equiv}"),
        ("train 严格早于：48 块 train_end < test_start，且无跨季日期重叠",
         all(b["train_end"] < b["test_start"] for b in blocks),
         f"maxTrainEnd={max(b['train_end'] for b in blocks)}"),
        (f"n_train ≥ {MIN_N_TRAIN:,}；最小值恰好在 1718_D1 / 1718_N1",
         train_ok, f"min={min_train:,}, blocks={sorted(min_blocks)}"),
        (f"n_new_team ≤ {MAX_N_NEW_TEAM}（历史累积口径；实测最大 {max(new_teams)}）",
         new_team_ok, f"max={max(new_teams)}, 非零块="
                      f"{sum(1 for v in new_teams if v > 0)}"),
        ("JSON round-trip 相等 + 两次生成逐字节相同 + 无时间戳字段",
         idem_ok, f"identical={idem_ok}"),
        ("入库规则：configs/splits.json 不被忽略；panel.parquet 仍被忽略",
         ignore_ok, f"splitsIgnored={proc.returncode == 0}, "
                    f"panelIgnored={proc_panel.returncode == 0}"),
        ("落盘后读回与契约相等，48 块按 resolve_split() 复算行数全对",
         disk_ok, f"disk_ok={disk_ok}, written={written_desc}"),
    ]

    emit("-" * 100)
    for name, ok, detail in checks:
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
    passed = sum(ok for _, ok, _ in checks)
    emit("-" * 100)
    emit(f"汇总: {passed}/{len(checks)} 项 PASS"
         f"{'  -> S4 通过，M1 数据底座 S0–S4 全部交付' if passed == len(checks) else '  -> 存在 FAIL，禁止进入建模'}")
    emit("")
    emit("边界: S4 只交付切分契约；T1.4 覆盖率矩阵 / T1.6 独立泄漏测试 / T1.7 复现包 /")
    emit("      T1.10 data-v1.0 冻结 tag 仍属后续任务。11/09 接口冻结需 M2 主签 + M3/M4 会签。")
    emit("      splits.json 是入库契约（KB 级纯文本）；panel.parquet 仍不入库，全组各自 --stage s3 生成。")
    emit("      簇 bootstrap 的重采样单位是这 48 块，绝不是 16,733 场比赛；每个区间附 design effect。")
    emit("复现: python src/build_panel.py --stage s4 --log results/logs/s4_splits_<date>.txt")
    emit("      pytest -q tests/test_splits.py")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks), "n_blocks": len(blocks),
            "n_test_total": sum(b["n_test"] for b in blocks),
            "n_train_min": min_train, "n_new_team_max": max(new_teams),
            "identical": idem_ok, "disk_ok": disk_ok, "written": written}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="M1 / S4：生成 48 块 rolling-origin 切分契约 configs/splits.json")
    ap.add_argument("--out", default=None,
                    help="切分文件落盘路径（默认 configs/splits.json，入库）")
    ap.add_argument("--log", default=None,
                    help=f"自检日志路径（默认不落盘）；建议 results/logs/s4_splits_{date.today()}.txt")
    args = ap.parse_args()
    summary = s4_selfcheck(args.log, args.out or str(SPLITS_PATH))
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
