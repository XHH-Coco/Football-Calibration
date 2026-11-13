"""M1 / T1.7（S5）验收：复现包在干净环境跑得起来，且数字可倒查。

对应分工方案 v1.3 §3.1 T1.7、M1 卡 §6 验收项 12 / 13 / 14：
  - `requirements.txt` 恒 8 行，与 README §5.2 第三方包行逐行一致；
  - `run_all.sh` / `run_all.ps1` 不写死 Windows 不存在的 `bin/activate`、
    不联网重下、从已入库 raw 起跑；
  - `MANIFEST.md`「数字 → 脚本 → 命令」三列齐全；
  - `--check` 模式可在一秒钟内验证解释器和执行计划。

运行：``pytest -q tests/test_repro.py``（项目环境 DSC5001_Project）。
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APPENDIX = ROOT / "appendix"
REQUIRED_FILES = (
    "requirements.txt", "seed.py", "run_all.sh", "run_all.ps1",
    "MANIFEST.md", "pip_freeze_2026-11-10.txt",
)
EXPECTED_DEPS = {
    "pandas": "3.1.1", "numpy": "2.5.4", "pyarrow": "26.0.1",
    "pytest": "9.2.0", "matplotlib": "3.11.2", "scipy": "1.18.1",
    "scikit-learn": "1.9.1", "statsmodels": "0.15.0",
}


def _text(name: str) -> str:
    return (APPENDIX / name).read_text(encoding="utf-8")


def test_01_appendix_is_complete():
    for name in REQUIRED_FILES:
        assert (APPENDIX / name).is_file(), f"缺 {name}"
        assert (APPENDIX / name).stat().st_size > 0


def test_02_requirements_has_exactly_eight_pinned_deps():
    lines = [l.strip() for l in _text("requirements.txt").splitlines()
             if l.strip() and not l.strip().startswith("#")]
    assert len(lines) == 8, f"依赖必须恒 8 行，实际 {len(lines)}"
    parsed = {}
    for line in lines:
        m = re.fullmatch(r"([A-Za-z0-9_.-]+)==(\d+\.\d+\.\d+(?:\.\w+)?)", line)
        assert m, f"不是精确的 `包名==x.y.z`：{line}"
        parsed[m.group(1)] = m.group(2)
    assert parsed == EXPECTED_DEPS


def test_03_requirements_matches_readme_section_5_2():
    """验收项 13：与 README §5.2 的第三方包行逐行一致（Python 运行时行不算）。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("### 5.2", 1)[1].split("### 5.3", 1)[0]
    found = {}
    for line in section.splitlines():
        m = re.match(r"\|\s*([A-Za-z0-9_.-]+)\s*\|\s*`(\d+\.\d+\.\d+)`\s*\|", line)
        if m:
            found[m.group(1)] = m.group(2)
    assert found == EXPECTED_DEPS, f"README §5.2 与 requirements 不一致：{found}"


def test_04_seed_module_exposes_default_and_warns_about_call_sites():
    spec = importlib.util.spec_from_file_location("wb_seed", APPENDIX / "seed.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert isinstance(module.DEFAULT_SEED, int) and module.DEFAULT_SEED > 0
    assert module.set_global_seeds() == module.DEFAULT_SEED
    src = _text("seed.py")
    assert "random_state" in src and "显式" in src


def _assert_no_online_or_activate(text: str, name: str) -> None:
    # 只看真正会执行的代码行：注释里的「冷启动安装说明」不算联网重下。
    body = "\n".join(l for l in text.splitlines()
                     if not l.lstrip().startswith("#")).lower()
    for forbidden in ("source .venv/bin/activate", "activate.ps1",
                      "curl ", "wget ", "invoke-webrequest", "pip install"):
        assert forbidden not in body, f"{name} 含禁止项：{forbidden}"
    assert "132" in text, f"{name} 未校验 132 个 raw CSV"


def test_05_run_all_sh_is_windows_safe_and_offline():
    src = _text("run_all.sh")
    _assert_no_online_or_activate(src, "run_all.sh")
    assert ".venv/Scripts/python.exe" in src
    assert ".venv/bin/python" in src
    for token in ("appendix/seed.py", "--stage s3", "--stage s4",
                  "src/coverage.py", "-m pytest -q tests/", "--check"):
        assert token in src, f"run_all.sh 缺步骤 {token}"


def test_06_run_all_ps1_is_equivalent():
    src = _text("run_all.ps1")
    _assert_no_online_or_activate(src, "run_all.ps1")
    assert ".venv\\Scripts\\python.exe" in src
    for token in ("appendix/seed.py", "--stage", "src/coverage.py", "pytest"):
        assert token in src, f"run_all.ps1 缺步骤 {token}"


def test_07_manifest_has_three_columns_and_key_numbers():
    src = _text("MANIFEST.md")
    header = [l for l in src.splitlines()
              if l.startswith("| 数字") or "数字 / 结论" in l]
    assert header, "MANIFEST 缺「数字 → 脚本 → 命令」三列表头"
    assert len(header[0].split("|")) - 2 == 3, "三列表必须恰好 3 列"
    for token in ("46,507", "16,733", "16,728", "48 块", "4,284",
                  "1,028,001", "243", "241", "2012/13", "2019/20",
                  "0.999940", "data-v1.0"):
        assert token in src, f"MANIFEST 缺关键数字 {token}"
    assert "football-data.co.uk" in src and "不联网" in src
    assert "HistGradientBoostingClassifier" in src


def test_08_manifest_rows_have_a_command_in_third_column():
    src = _text("MANIFEST.md")
    section = src.split("## 3.", 1)[1].split("## 4.", 1)[0]
    rows = [l for l in section.splitlines()
            if l.startswith("|") and not l.startswith("|---")
            and "数字 / 结论" not in l]
    assert len(rows) >= 14, f"可倒查的数字行太少：{len(rows)}"
    for row in rows:
        cells = [c.strip() for c in row.replace(r"\|", "§").split("|")[1:-1]]
        assert len(cells) == 3, f"三列不齐：{row[:80]}"
        assert cells[2].startswith(("`", "python", "pytest", "bash", "ls")), \
            f"第三列不是可执行命令：{cells[2][:60]}"


def test_09_pip_freeze_snapshot_covers_all_eight_deps():
    lines = [l.strip() for l in _text("pip_freeze_2026-11-10.txt").splitlines()
             if l.strip()]
    frozen = dict(l.split("==", 1) for l in lines if "==" in l)
    for name, version in EXPECTED_DEPS.items():
        assert frozen.get(name) == version, f"pip_freeze 缺 {name}=={version}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="本机无 bash（Git Bash / WSL）")
def test_10_run_all_check_smoke():
    """--check 只打印计划、不写文件；顺带验证 132 个 raw CSV 在位。"""
    # 用 which 解析出的完整路径：裸 "bash" 会被 CreateProcess 先解析到 System32 的
    # WSL 桩（装了 WSL 但无发行版时 returncode=1），从而跳过 PATH 里的 Git Bash。
    bash = shutil.which("bash")
    proc = subprocess.run([bash, "appendix/run_all.sh", "--check"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "N_RAW=132" in proc.stdout
    assert "OFFLINE=1" in proc.stdout
    assert "--stage s3" in proc.stdout and "--stage s4" in proc.stdout
