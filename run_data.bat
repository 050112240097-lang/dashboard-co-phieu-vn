@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================
echo   DASHBOARD - CAP NHAT DU LIEU
echo ============================================
python main.py
pause