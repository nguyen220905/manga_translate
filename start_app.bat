@echo off
title MangaDich App
echo ============================================
echo   MangaDich - Khoi dong App (Backend + Frontend)
echo ============================================

:: Kill process dang chiem port 8000
echo [*] Dang tat process cu tren port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    echo [OK] Da tat process PID: %%a
)

:: Cho 1 giay
timeout /t 1 /nobreak >nul

:: Chuyen vao thu muc backend va khoi dong
echo [*] Dang khoi dong Uvicorn...
echo.
cd /d d:\project_210\project\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
