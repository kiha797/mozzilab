@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo 먼저 1_install.bat 을 실행하세요.
  pause
  exit /b 1
)
echo 모찌포토 실행파일(exe)을 만드는 중입니다. 1~3분 정도 걸립니다...
venv\Scripts\pyinstaller --noconfirm --clean --windowed --name MochiPhoto --icon assets\app.ico --paths ..\shared --add-data "assets;assets" main.py
if not %errorlevel%==0 (
  echo [오류] exe 만들기에 실패했습니다. 위의 빨간 메시지를 확인하세요.
  pause
  exit /b 1
)
echo.
echo 완료! dist\MochiPhoto 폴더 안의 MochiPhoto.exe 를 실행하면 됩니다.
echo 설치 프로그램(Setup.exe)을 만들려면 installer.iss 를 Inno Setup 으로 여세요.
explorer dist\MochiPhoto
pause
