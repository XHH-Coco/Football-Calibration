# =============================================================================
# M1 / T1.7 —— 一键复现入口（Windows PowerShell 5.1 版，与 run_all.sh 等价）
#
# 起点：已随 Git 入库的 132 个 data/raw/*.csv，全程不联网、不重下、不装包。
# 用法：
#   powershell -ExecutionPolicy Bypass -File appendix/run_all.ps1
#   powershell -ExecutionPolicy Bypass -File appendix/run_all.ps1 -Check
#   powershell -ExecutionPolicy Bypass -File appendix/run_all.ps1 -Python "D:\Miniconda3\envs\DSC5001_Project\python.exe"
#
# 干净环境冷启动：
#   python -m venv .venv
#   .\.venv\Scripts\python.exe -m pip install -r appendix\requirements.txt
#   powershell -ExecutionPolicy Bypass -File appendix\run_all.ps1
#
# 本机是 Windows：venv 解释器在 .venv\Scripts\python.exe，**不是** bin\python，
# 也不写死 Activate.ps1 路径——按优先级挑显式解释器。
# =============================================================================
param(
    [switch]$Check,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# --- 1. 选解释器：参数 / 环境变量 > Windows venv > POSIX venv > PATH ---
if (-not $Python) { $Python = $env:PYTHON }
if (-not $Python) {
    $WinVenv = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    $PosixVenv = Join-Path $RepoRoot ".venv\bin\python"
    if (Test-Path $WinVenv) { $Python = $WinVenv }
    elseif (Test-Path $PosixVenv) { $Python = $PosixVenv }
    else { $Python = "python" }
}

# --- 2. 前置检查：raw 快照必须在仓库里，缺文件就停，绝不联网补 ---
$RawDir = Join-Path $RepoRoot "data\raw"
$Nraw = @(Get-ChildItem -Path $RawDir -Filter "*.csv" -File).Count
if ($Nraw -ne 132) {
    Write-Error "data/raw 应有 132 个 CSV，实际 $Nraw 个。请从 Git 检出完整快照；复现包禁止联网重下。"
    exit 1
}

if ($Check) {
    Write-Output "REPO_ROOT=$RepoRoot"
    Write-Output "PYTHON=$Python"
    Write-Output "N_RAW=$Nraw"
    Write-Output "OFFLINE=1  (raw CSV already in Git; no network access required)"
    Write-Output "PLAN:"
    Write-Output "  $Python appendix/seed.py"
    Write-Output "  $Python src/build_panel.py --stage s3"
    Write-Output "  $Python src/build_panel.py --stage s4"
    Write-Output "  $Python src/coverage.py"
    Write-Output "  $Python -m src.eval.run_m2"
    Write-Output "  $Python -m pytest -q tests/"
    exit 0
}

# --- 3. 完整复现；需要留存日志时由调用方重定向（*.log 已被 .gitignore 忽略）---
#   powershell -File appendix\run_all.ps1 *> results\logs\repro_run.log
function Invoke-Step([string]$Label, [string[]]$PyArgs) {
    Write-Output ""
    Write-Output "--- $Label ---"
    & $Python @PyArgs
    if ($LASTEXITCODE -ne 0) { throw "步骤失败：$Label (exit $LASTEXITCODE)" }
}

Write-Output "=== T1.7 reproduce | $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
Write-Output "REPO_ROOT=$RepoRoot"
Write-Output "PYTHON=$Python"
Write-Output "N_RAW=$Nraw"

Invoke-Step "[1/6] seed" @("appendix/seed.py")
Invoke-Step "[2/6] S3 panel.parquet" @("src/build_panel.py", "--stage", "s3")
Invoke-Step "[3/6] S4 splits.json" @("src/build_panel.py", "--stage", "s4")
Invoke-Step "[4/6] S5 coverage" @("src/coverage.py")
Invoke-Step "[5/6] M2 eval + H1-H4" @("-m", "src.eval.run_m2")
Invoke-Step "[6/6] full pytest" @("-m", "pytest", "-q", "tests/")

Write-Output "=== DONE: panel / splits / coverage + M2 predictions, tables, H1-H4 rebuilt from tracked raw CSV only ==="
