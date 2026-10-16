@echo off
chcp 65001 >nul
title Dashboard Co Phieu - Server
cd /d C:\Users\DELL\Desktop\AutoWebCoPhieu

echo ============================================================
echo   DASHBOARD CO PHIEU VIET NAM - AUTO START
echo ============================================================
echo.
echo  Thu muc: %CD%
echo  Thoi gian: %DATE% %TIME%
echo.

REM Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [LOI] Khong tim thay Python trong PATH
    echo  Vui long cai Python hoac them vao PATH
    pause
    exit /b 1
)

REM Kiem tra file server.py
if not exist "server.py" (
    echo  [LOI] Khong tim thay server.py trong thu muc nay
    pause
    exit /b 1
)

echo  Dang khoi dong server...
echo  Web: http://localhost:5000
echo.
echo  ============================================================
echo.

REM Chay server
python server.py

REM Neu server crash, giu cua so lai de xem loi
echo.
echo  ============================================================
echo  Server da dung. Bam phim bat ky de thoat.
echo  ============================================================
pause >nul