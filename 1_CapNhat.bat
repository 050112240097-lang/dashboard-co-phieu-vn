@echo off
chcp 65001 >nul
title Cap Nhat Du Lieu Dashboard
cd /d "%~dp0"

echo ============================================================
echo   CAP NHAT DU LIEU DASHBOARD CO PHIEU
echo ============================================================
echo.
echo   Qua trinh nay mat khoang 1-2 phut.
echo   Vui long doi...
echo.

python main.py

echo.
echo ============================================================
echo   HOAN THANH! Du lieu da duoc cap nhat.
echo   Bay gio chay file "2_MoDashboard.vbs" de xem dashboard.
echo ============================================================
echo.
pause