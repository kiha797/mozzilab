@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv\Scripts\pythonw.exe (
  echo 먼저 1_install.bat 을 실행하세요.
  pause
  exit /b 1
)
start "" venv\Scripts\pythonw.exe main.py
