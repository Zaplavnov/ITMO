$ErrorActionPreference = "Stop"

$python = Join-Path ".venv" "Scripts/python.exe"
if (-Not (Test-Path $python)) {
    Write-Error "Venv not found. Run scripts/setup.ps1 first"
}

Write-Host "[1/2] Parsing pages" -ForegroundColor Cyan
& $python -m src.scrape

Write-Host "[2/2] Building TF-IDF index" -ForegroundColor Cyan
& $python -m src.indexer

Write-Host "Done: data at src/data/processed" -ForegroundColor Green
