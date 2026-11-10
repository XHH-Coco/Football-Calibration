"""M1 / S5 —— 收尾自检：把 T1.4 / T1.6 / T1.7 / T1.9 / T1.10 汇成一张验收单。

S0–S4 各有自己的自检日志，S5 不新增第六套「数据加工」，而是**收口**：
  * T1.4 覆盖率矩阵（``src/coverage.py``，12/12）
  * T1.6 独立泄漏测试（``tests/test_leakage.py``，五条断言）
  * T1.7 复现包（``appendix/``，``run_all.sh --check`` 冒烟）
  * T1.9 独立 H3 测试（``tests/test_h3_features.py``）
  * T1.10 数据冻结（``docs/plans/CHANGELOG_data.md`` + ``data-v1.0`` tag）

本模块**不加工数据**，只做回归、静态契约与全量 pytest，并输出一份可复核日志
``results/logs/s5_handover_2026-11-10.txt``。``data-v1.0`` tag 由提交流程在
最终 commit 上创建，本自检把 tag 状态作为信息行打印、不作为断言（否则
「先出日志 → 再打 tag」会自相矛盾）。

运行（项目环境 DSC5001_Project）：
    python src/build_panel.py --stage s5 --log results/logs/s5_handover_2026-11-10.txt
    python src/handover.py --log results/logs/s5_handover_2026-11-10.txt
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.build_panel import (  # noqa: E402
    selfcheck, s2_selfcheck, s3_selfcheck,
)
from src.coverage import (  # noqa: E402
    FIG_PATH, MATRIX_PATH, coverage_selfcheck,
)
from src.splits import s4_selfcheck  # noqa: E402

CHANGELOG_DATA = ROOT / "docs" / "plans" / "CHANGELOG_data.md"
S5_TEST_FILES = (
    "tests/test_leakage.py", "tests/test_h3_features.py",
    "tests/test_coverage.py", "tests/test_repro.py",
)
REPRO_FILES = (
    "appendix/requirements.txt", "appendix/seed.py",
    "appendix/run_all.sh", "appendix/run_all.ps1",
    "appendix/MANIFEST.md", "appendix/pip_freeze_2026-11-10.txt",
)
LEAKAGE_TESTS = (
    "test_01_train_is_strictly_before_test",
    "test_02_test_blocks_are_disjoint_and_complete",
    "test_03_n_train_lower_bound",
    "test_04_new_teams_are_flagged_not_forbidden",
    "test_05_odds_missing_exactly_five",
)
H3_TESTS = (
    "test_01_h3_columns_present_and_complete",
    "test_02_invariant_to_post_match_shuffle",
    "test_03_identity_columns_alone_reproduce_h3",
    "test_07_matchday_is_continuous_and_includes_away_appearances",
)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True)


def _md_table_issues() -> list[str]:
    """全仓 md 表格列数一致性（沿用 S3/S4 的口径：转义竖线先替换）。"""
    issues: list[str] = []
    files = sorted(p for p in ROOT.rglob("*.md")
                   if ".git" not in p.parts and ".workbuddy" not in p.parts)
    for p in files:
        block: list[tuple[int, str]] = []
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines() + [""]):
            if line.strip().startswith("|") and line.strip().endswith("|"):
                block.append((i + 1, line))
            else:
                if len(block) >= 2:
                    counts: dict[int, list[int]] = {}
                    for n, l in block:
                        c = len(l.replace(r"\|", "§").split("|")) - 2
                        counts.setdefault(c, []).append(n)
                    if len(counts) > 1:
                        issues.append(f"{p.relative_to(ROOT)}:{block[0][0]}-{block[-1][0]}")
                block = []
    return issues


def handover_selfcheck(log_path: str | Path | None = None) -> dict:
    """S5 验收：12 项硬断言 + 一份可复核日志。"""
    out: list[str] = []

    def emit(line: str = "") -> None:
        print(line)
        out.append(line)

    emit("=" * 100)
    emit("M1 / S5 收尾自检 —— T1.4 / T1.6 / T1.7 / T1.9 / T1.10 验收单")
    emit(f"日期: {date.today()}    仓库: {ROOT}")
    emit("=" * 100)

    # --- 1–4：S1–S4 回归（都不落盘，避免覆盖正式产物）---
    emit("回归自检运行中（S1 / S2 / S3 / S4 / T1.4）…")
    regressions = {
        "S1": selfcheck(),
        "S2": s2_selfcheck(),
        "S3": s3_selfcheck(),
        "S4": s4_selfcheck(),
        "T1.4": coverage_selfcheck(),
    }
    expected = {"S1": (8, 8), "S2": (13, 13), "S3": (12, 12),
                "S4": (12, 12), "T1.4": (12, 12)}
    reg_ok = all((regressions[k]["passed"], regressions[k]["total"]) == v
                 for k, v in expected.items())

    # --- 5：覆盖率产物在磁盘且不被忽略 ---
    cov_files_ok = (MATRIX_PATH.is_file() and FIG_PATH.is_file()
                    and MATRIX_PATH.stat().st_size > 10_000
                    and FIG_PATH.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n")
    cov_ignore_ok = all(_git("check-ignore", "-q", rel).returncode != 0
                        for rel in ("results/coverage_matrix.csv",
                                    "products/figures/fig_data_coverage.png"))

    # --- 6–8：三个独立测试文件的静态契约 ---
    leakage_src = (ROOT / "tests" / "test_leakage.py").read_text(encoding="utf-8")
    leakage_ok = all(f"def {name}" in leakage_src for name in LEAKAGE_TESTS)
    h3_src = (ROOT / "tests" / "test_h3_features.py").read_text(encoding="utf-8")
    h3_ok = all(f"def {name}" in h3_src for name in H3_TESTS)
    repro_ok = all((ROOT / rel).is_file() for rel in REPRO_FILES)
    req_lines = [l.strip() for l in
                 (ROOT / "appendix" / "requirements.txt").read_text(encoding="utf-8")
                 .splitlines() if l.strip() and not l.strip().startswith("#")]
    repro_ok &= len(req_lines) == 8

    # --- 9：复现包 --check 冒烟（不写任何文件）---
    check = subprocess.run(["bash", "appendix/run_all.sh", "--check"],
                           cwd=ROOT, capture_output=True, text=True)
    smoke_ok = (check.returncode == 0 and "N_RAW=132" in check.stdout
                and "OFFLINE=1" in check.stdout)

    # --- 10：全量 pytest（实质覆盖 6/7/8 的断言）---
    emit("全量 pytest 运行中…")
    pytest_run = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/"],
                                cwd=ROOT, capture_output=True, text=True)
    pytest_last = [l for l in pytest_run.stdout.strip().splitlines() if l.strip()]
    pytest_tail = pytest_last[-1] if pytest_last else "(no output)"
    pytest_ok = pytest_run.returncode == 0

    # --- 11：T1.10 数据变更日志 ---
    chlog_ok = (CHANGELOG_DATA.is_file()
                and "冻结基线" in CHANGELOG_DATA.read_text(encoding="utf-8")
                and "| 日期 |" in CHANGELOG_DATA.read_text(encoding="utf-8"))
    tag = _git("tag", "-l", "data-v1.0")
    tag_text = tag.stdout.strip()
    tag_desc = (f"已存在，指向 {_git('rev-parse', '--short', 'data-v1.0').stdout.strip()}"
                if tag_text else "PENDING（由提交流程在最终 commit 上创建；"
                                 "验收命令 `git tag -l data-v1.0`）")

    # --- 12：文档与红线 ---
    md_issues = _md_table_issues()
    diffcheck = _git("diff", "--check")
    untouched = _git("status", "--porcelain", "--", ".gitignore",
                     "appendix/requirements.txt")
    hygiene_ok = (not md_issues and diffcheck.returncode == 0
                  and untouched.stdout.strip() == "")

    checks: list[tuple[str, bool, str]] = [
        ("S1–S4 回归自检全绿（8/8、13/13、12/12、12/12）",
         all((regressions[k]["passed"], regressions[k]["total"]) == v
             for k, v in expected.items() if k != "T1.4"),
         ", ".join(f"{k} {regressions[k]['passed']}/{regressions[k]['total']}"
                   for k in ("S1", "S2", "S3", "S4"))),
        ("T1.4 覆盖率矩阵自检 12/12（含 S5 订正项）",
         (regressions["T1.4"]["passed"], regressions["T1.4"]["total"]) == (12, 12),
         f"{regressions['T1.4']['passed']}/{regressions['T1.4']['total']}"),
        ("覆盖率 CSV / PNG 在磁盘、非空、PNG 魔数正确",
         bool(cov_files_ok), f"csv={MATRIX_PATH.stat().st_size:,} B, "
                             f"png={FIG_PATH.stat().st_size:,} B"),
        ("覆盖率产物入库（git check-ignore 不命中）",
         bool(cov_ignore_ok), f"ignore_ok={cov_ignore_ok}"),
        ("T1.6 独立泄漏测试存在，五条断言函数齐全",
         bool(leakage_ok), f"{len(LEAKAGE_TESTS)} 条断言入口"),
        ("T1.9 独立 H3 测试存在，打乱不变性 / 只依赖 5 列 / matchday 连续齐全",
         bool(h3_ok), f"{len(H3_TESTS)} 个关键断言"),
        ("T1.7 复现包 6 个文件齐全，requirements.txt 恒 8 行",
         bool(repro_ok), f"{len(REPRO_FILES)} 个文件 / {len(req_lines)} 行依赖"),
        ("T1.7 `bash appendix/run_all.sh --check` 冒烟通过（132 raw / 不联网）",
         bool(smoke_ok), f"exit={check.returncode}"),
        ("全量 pytest -q tests/ 退出码 0（含 S5 新增四个测试文件）",
         bool(pytest_ok), pytest_tail[:110]),
        ("T1.10 `docs/plans/CHANGELOG_data.md` 已建，含表头与「冻结基线」首行",
         bool(chlog_ok), f"exists={CHANGELOG_DATA.is_file()}"),
        ("全仓 md 表格列数一致、git diff --check 通过、"
         ".gitignore / requirements.txt 未改",
         bool(hygiene_ok), f"md_issues={len(md_issues)}, "
                           f"diffcheck={diffcheck.returncode}"),
        ("S5 五项任务全部有对应产物（代码 / 测试 / 契约 / 日志）",
         bool(reg_ok and leakage_ok and h3_ok and repro_ok and chlog_ok),
         "T1.4 ✅ / T1.6 ✅ / T1.7 ✅ / T1.9 ✅ / T1.10 ✅"),
    ]

    emit("-" * 100)
    for name, ok, detail in checks:
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
    passed = sum(ok for _, ok, _ in checks)
    emit("-" * 100)
    emit(f"汇总: {passed}/{len(checks)} 项 PASS"
         f"{'  -> S5 通过，M1 数据底座 S0–S5 全部交付' if passed == len(checks) else '  -> 存在 FAIL'}")
    emit("")
    emit(f"data-v1.0 tag: {tag_desc}")
    emit("")
    emit("S5 五项交付:")
    emit("  T1.4  results/coverage_matrix.csv + products/figures/fig_data_coverage.png")
    emit("        （订正：评估窗射门列并非 100%，2425_D1 缺 1 场；旧稿已同步修订）")
    emit("  T1.6  tests/test_leakage.py（五条泄漏断言集中成全组安全带）")
    emit("  T1.7  appendix/seed.py / run_all.sh / run_all.ps1 / MANIFEST.md / pip_freeze")
    emit("  T1.9  tests/test_h3_features.py（H3 三列对赛后信息不敏感）")
    emit("  T1.10 docs/plans/CHANGELOG_data.md + data-v1.0 tag")
    emit("")
    emit("边界: S5 不碰 M2/M3/M4 建模、不代签 11/09 接口冻结、不动搁置的 U1/U2。")
    emit("      数据冻结后任何 raw / panel / splits 变更都要写 CHANGELOG_data.md。")
    emit("复现: bash appendix/run_all.sh   或   python src/build_panel.py --stage s5")

    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\n自检日志已写入: {lp}")
    return {"passed": passed, "total": len(checks),
            "pytest_ok": bool(pytest_ok), "pytest_tail": pytest_tail,
            "regressions": {k: (v["passed"], v["total"])
                            for k, v in regressions.items()},
            "tag": tag_text or None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="M1 / S5：收尾自检（T1.4/6/7/9/10）")
    ap.add_argument("--log", default=None,
                    help=f"自检日志路径；建议 results/logs/s5_handover_{date.today()}.txt")
    args = ap.parse_args()
    summary = handover_selfcheck(args.log)
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
