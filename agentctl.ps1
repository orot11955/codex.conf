# Native Windows: Python 3.11+; does not require Unix symlinks for new installs.
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'scripts/agentctl.py'
if ($env:PYTHON_BIN) {
    & $env:PYTHON_BIN $scriptPath @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $scriptPath @args
} else {
    & python $scriptPath @args
}
exit $LASTEXITCODE
