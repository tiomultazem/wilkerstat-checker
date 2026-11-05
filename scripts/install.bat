@echo off
setlocal
cd /d "%~dp0.."
echo ========================================
echo  WilkerStat Checker - Instalasi
echo ========================================
echo.

REM 1. Deteksi ketersediaan Python di sistem
where python >nul 2>&1
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    )
)

where python >nul 2>&1
if errorlevel 1 (
    echo Python tidak ditemukan di komputer ini.
    echo Mengunduh installer resmi Python 3.12.7 64-bit...
    set "INSTALLER=%TEMP%\python-3.12.7-amd64.exe"
    curl -fSL -o "%INSTALLER%" https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
    if errorlevel 1 (
        echo [ERROR] Gagal mengunduh installer Python. Pastikan koneksi internet aktif.
        pause
        exit /b 1
    )

    echo Memasang Python 3.12.7 secara otomatis...
    start /wait "" "%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1
    del /f /q "%INSTALLER%" >nul 2>&1

    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python telah dipasang tetapi belum terbaca di sesi terminal ini.
        echo Silakan tutup jendela ini dan jalankan kembali install.bat.
        pause
        exit /b 1
    )
)

echo Python terdeteksi:
python --version
echo.

REM 2. Membuat virtual environment (venv)
echo Menyiapkan virtual environment (venv)...
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat venv.
        pause
        exit /b 1
    )
) else (
    echo Folder venv sudah ada, melanjutkan pembaruan paket...
)

REM 3. Mengaktifkan venv dan memasang dependensi
echo.
echo Mengaktifkan venv dan memperbarui package installer...
call venv\Scripts\activate.bat

python -m pip install --upgrade pip setuptools wheel

echo.
echo Memasang dependensi geospasial & server dari requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Gagal memasang dependensi dari requirements.txt.
    pause
    exit /b 1
)

REM 4. Generate icon system tray
echo.
if exist assets\make_icon.py (
    echo Menyiapkan icon system tray...
    python assets\make_icon.py
)

echo.
echo ========================================
echo  Instalasi selesai dan siap dijalankan!
echo  Jalankan run.bat untuk memulai server.
echo ========================================
pause
