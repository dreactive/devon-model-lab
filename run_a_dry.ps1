param(
    [string]$DevonRoot = (Join-Path $PSScriptRoot '..\devon'),
    [string]$Output
)
$ErrorActionPreference = 'Stop'
$taskDevon = (Resolve-Path -LiteralPath $DevonRoot).Path
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create the model-lab virtual environment first.' }
if (-not $Output) {
    $taskRunId = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
    $Output = Join-Path $PSScriptRoot "runs\$taskRunId\question-dry-run.json"
}
$taskResolvedOutput = & $taskPython -B -c "import sys; from pathlib import Path; p=Path(sys.argv[1]).resolve(); d=Path(sys.argv[2]).resolve(); sys.exit(1) if p.is_relative_to(d) else print(p)" $Output $taskDevon
if ($LASTEXITCODE -ne 0) { throw 'Output inside the read-only DEVON checkout is rejected.' }
$Output = $taskResolvedOutput
$taskOldBytecode = $env:PYTHONDONTWRITEBYTECODE
try {
    $env:PYTHONDONTWRITEBYTECODE = '1'
    & $taskPython -B (Join-Path $taskDevon 'backend\scripts\run_ai_evaluation.py') `
        --cases (Join-Path $PSScriptRoot 'cases\question') `
        --manifest (Join-Path $PSScriptRoot 'manifests\baseline.json') `
        --output $Output --split all --dry-run
    $taskCode = $LASTEXITCODE
} finally {
    $env:PYTHONDONTWRITEBYTECODE = $taskOldBytecode
}
exit $taskCode
