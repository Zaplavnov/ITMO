param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Creating virtualenv .venv" -ForegroundColor Cyan
& $Python -m venv .venv

$venvPython = Join-Path ".venv" "Scripts/python.exe"

Write-Host "[2/3] Upgrading pip" -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

Write-Host "[3/3] Installing dependencies from requirements.txt" -ForegroundColor Cyan
& $venvPython -m pip install -r requirements.txt

Write-Host "Done. Activate: .venv\Scripts\Activate.ps1" -ForegroundColor Green
