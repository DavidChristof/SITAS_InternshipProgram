@echo off
rem ============================================
rem  SITAS local launcher (for defense demo)
rem  Double-click to run: opens a server window
rem  and auto-opens http://127.0.0.1:8000
rem  If port 8000 is busy, change --port 8000 to --port 8001
rem ============================================
cd /d "%~dp0"

echo [1/2] Init demo data (idempotent)...
.venv\Scripts\python.exe -m backend.scripts.init_db
if errorlevel 1 (
  echo [ERROR] init_db failed. Please check .venv dependencies.
  pause
  exit /b 1
)

echo [2/2] Starting service...
echo Server window opened. Browser will auto-open http://127.0.0.1:8000
start "SITAS-Server" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul
start "" http://127.0.0.1:8000
echo Done. You can close this window; stop the server with Ctrl+C in the server window.
pause
