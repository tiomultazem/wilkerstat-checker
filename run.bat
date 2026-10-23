@echo off
setlocal
cls

if "%~1"=="--child" goto :main
start "WilkerStat Checker" cmd /k "%~f0" --child
exit /b

:main
cd /d "%~dp0"
cls

echo ========================================
echo  WilkerStat Checker
echo ========================================
echo.

REM Baca PORT dari .env (default 11750)
set "APP_PORT=11750"
for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
    if /I "%%A"=="PORT" set "APP_PORT=%%B"
)

echo Menghentikan proses lama di port %APP_PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$port = %APP_PORT%; $pids = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 -and $_.OwningProcess -ne $PID } | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($id in $pids) { try { Write-Host ('Stopping PID ' + $id); Stop-Process -Id $id -Force -ErrorAction Stop } catch {} }"

taskkill /F /FI "WINDOWTITLE eq WilkerStat Checker" /T >nul 2>&1

echo Memulai server...
echo.

call venv\Scripts\activate.bat
python run.py

pause
