#!/usr/bin/env bash
# =============================================================================
# M1 / T1.7 —— 一键复现入口（Git Bash / Linux / macOS）
#
# 起点：**已随 Git 入库的 132 个 data/raw/*.csv**，全程不联网、不重下、不装包。
# 终点：data/processed/panel.parquet（不入库）+ configs/splits.json（入库契约）
#       + 覆盖率矩阵 CSV / 热力图 PNG + 全量 pytest 全绿。
#
# 用法：
#   bash appendix/run_all.sh            # 完整跑一遍
#   bash appendix/run_all.sh --check    # 只打印解释器和执行计划，不写任何文件
#   PYTHON=/path/to/python bash appendix/run_all.sh   # 显式指定解释器
#
# 干净环境冷启动：
#   python -m venv .venv
#   .venv/Scripts/python.exe -m pip install -r appendix/requirements.txt   # Windows
#   # Linux/macOS: .venv/bin/python -m pip install -r appendix/requirements.txt
#   bash appendix/run_all.sh
#
# Windows 注意：venv 的解释器在 .venv/Scripts/python.exe，**不是** bin/python；
# 本脚本不写死 `source .venv/bin/activate`，而是按优先级挑显式解释器路径。
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- 1. 选解释器：环境变量 > Windows venv > POSIX venv > PATH ---
if [[ -n "${PYTHON:-}" ]]; then
    PY="$PYTHON"
elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
    PY="$REPO_ROOT/.venv/Scripts/python.exe"
elif [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PY="$REPO_ROOT/.venv/bin/python"
else
    PY="python"
fi

# --- 2. 前置检查：raw 快照必须在仓库里，缺文件就停，绝不联网补 ---
N_RAW="$(find "$REPO_ROOT/data/raw" -maxdepth 1 -type f -name '*.csv' \
          | wc -l | tr -d '[:space:]')"
if [[ "$N_RAW" != "132" ]]; then
    echo "ERROR: data/raw 应有 132 个 CSV，实际 $N_RAW 个。" >&2
    echo "       请从 Git 检出完整快照；复现包禁止联网重下（源站改版会让数字漂移）。" >&2
    exit 1
fi

if [[ "${1:-}" == "--check" ]]; then
    echo "REPO_ROOT=$REPO_ROOT"
    echo "PYTHON=$PY"
    echo "N_RAW=$N_RAW"
    echo "OFFLINE=1  (raw CSV already in Git; no network access required)"
    echo "PLAN:"
    echo "  $PY appendix/seed.py"
    echo "  $PY src/build_panel.py --stage s3"
    echo "  $PY src/build_panel.py --stage s4"
    echo "  $PY src/coverage.py"
    echo "  $PY -m pytest -q tests/"
    exit 0
fi

# --- 3. 完整复现；整体 stdout 落到 *.log（已被 .gitignore 忽略，不污染仓库）---
LOG="$REPO_ROOT/results/logs/repro_run.log"
mkdir -p "$REPO_ROOT/results/logs"

{
    echo "=== T1.7 reproduce | $(date '+%Y-%m-%d %H:%M:%S') ==="
    echo "REPO_ROOT=$REPO_ROOT"
    echo "PYTHON=$PY"
    echo "N_RAW=$N_RAW"
    "$PY" -c "import sys, pandas, numpy, pyarrow, pytest, matplotlib, scipy, sklearn, statsmodels; print('python', sys.version.split()[0], '| 8 locked deps importable')"

    echo "--- [1/5] seed ---"
    "$PY" appendix/seed.py

    echo "--- [2/5] S3: panel.parquet (46,507 x 22, not tracked) ---"
    "$PY" src/build_panel.py --stage s3

    echo "--- [3/5] S4: configs/splits.json (48 blocks, tracked contract) ---"
    "$PY" src/build_panel.py --stage s4

    echo "--- [4/5] S5: coverage matrix CSV + heatmap PNG ---"
    "$PY" src/coverage.py

    echo "--- [5/5] full pytest ---"
    "$PY" -m pytest -q tests/

    echo "=== DONE: panel / splits / coverage rebuilt from tracked raw CSV only ==="
} 2>&1 | tee "$LOG"

# pipefail 已开：上面任一步失败，这里都会以非零码退出
echo "复现日志: $LOG"
