@echo off
setlocal
cd /d "%~dp0"
cls

echo ===================================================
echo  WilkerStat Checker — Instalasi Otomatis Lingkungan
echo ===================================================
echo.

REM 1. Cek Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di PATH sistem!
    echo Silakan pasang Python 3.10 - 3.12 terlebih dahulu dari python.org.
    echo Pastikan centang opsi "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

REM 2. Buat Virtual Environment jika belum ada
if not exist "venv\Scripts\activate.bat" (
    echo [1/4] Membuat Virtual Environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual Environment (venv) sudah tersedia.
)

REM 3. Pasang Dependensi
echo [2/4] Memasang dan memperbarui pustaka dari requirements.txt...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Terjadi kesalahan saat instalasi paket pip!
    pause
    exit /b 1
)

REM 4. Konfigurasi .env
echo [3/4] Memeriksa berkas konfigurasi (.env)...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo    -> .env berhasil dibuat dari .env.example.
    )
) else (
    echo    -> .env sudah ada.
)

REM 5. Sinkronisasi Logo Aset
echo [4/4] Memeriksa aset logo statis...
if not exist "static\logo.png" (
    if exist "assets\logo.png" (
        copy "assets\logo.png" "static\logo.png" >nul
        echo    -> Logo statis disinkronkan.
    )
)

echo.
echo ===================================================
echo  Instalasi selesai dengan sukses!
echo  Jalankan run.bat untuk memulai server WilkerStat.
echo ===================================================
echo.
pause

