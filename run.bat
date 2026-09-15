@echo off
title VeritasVideo - AI Video Forensics Lab
echo =======================================================
echo          VeritasVideo AI Forensic Detection Studio
echo =======================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Setting up...
    python -m venv .venv
    .\.venv\Scripts\pip install -r backend\requirements.txt
)

echo [INFO] Generating sample test videos if not already present...
.\.venv\Scripts\python create_samples.py

echo.
echo [SUCCESS] Starting VeritasVideo server at http://localhost:8000 ...
echo Press Ctrl+C to stop the server.
echo.

cd backend
..\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
