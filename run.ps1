# VeritasVideo Launcher for PowerShell
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "      VeritasVideo AI Forensic Detection Studio       " -ForegroundColor White
Write-Host "=======================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[INFO] Setting up Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\pip install -r backend\requirements.txt
}

Write-Host "[INFO] Checking sample test videos..." -ForegroundColor Gray
.\.venv\Scripts\python create_samples.py

Write-Host "`n[SUCCESS] Launching VeritasVideo server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate.`n" -ForegroundColor DarkGray

Set-Location (Join-Path $scriptDir "backend")
& "..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
