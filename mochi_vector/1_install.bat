@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   모찌벡터 - 1단계: 필요한 프로그램 설치
echo ==========================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version >nul 2>nul
if not %errorlevel%==0 (
  echo [오류] 파이썬이 설치되어 있지 않습니다.
  echo https://www.python.org/downloads/ 에서 설치하세요.
  echo 설치 첫 화면에서 "Add python.exe to PATH" 를 꼭 체크하세요!
  pause
  exit /b 1
)
%PY% --version
echo.
echo [1/2] 이 폴더 안에 전용 가상환경(venv)을 만듭니다...
%PY% -m venv venv
if not %errorlevel%==0 (
  echo [오류] 가상환경을 만들지 못했습니다.
  pause
  exit /b 1
)
echo [2/2] 라이브러리를 내려받아 설치합니다. 몇 분 걸릴 수 있습니다...
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt pyinstaller
if not %errorlevel%==0 (
  echo [오류] 설치 중 문제가 생겼습니다. 인터넷 연결을 확인하세요.
  pause
  exit /b 1
)
echo.
echo 설치가 끝났습니다! 이제 2_run.bat 을 더블클릭해 실행해 보세요.
pause
