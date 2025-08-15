$ErrorActionPreference = "Stop"

$python = Join-Path ".venv" "Scripts/python.exe"
if (-Not (Test-Path $python)) {
    Write-Error "Venv not found. Run scripts/setup.ps1 first"
}

& $python -m src.bot
