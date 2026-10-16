@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================
echo   DASHBOARD - WEB SERVER
echo ============================================
echo   Mo trinh duyet: http://localhost:5000
echo ============================================
python server.py
pause