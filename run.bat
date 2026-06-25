@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Membuat virtual environment EcoLens...
    python -m venv .venv
)

echo Memastikan dependency terpasang...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo Mengecek koneksi MySQL Laragon...
".venv\Scripts\python.exe" -c "import socket; sock=socket.create_connection(('127.0.0.1',3306),3); sock.close()" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] MySQL Laragon belum aktif atau port 3306 tidak dapat diakses.
    echo Buka Laragon lalu klik Start All, pastikan MySQL berwarna hijau, kemudian jalankan ulang .\run.bat
    echo.
    pause
    exit /b 1
)

echo Menjalankan EcoLens di http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
