@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   모찌랩 웹사이트 - Cloudflare 배포
echo ==========================================
where node >nul 2>nul
if not %errorlevel%==0 (
  echo [오류] Node.js 가 설치되어 있지 않습니다.
  echo https://nodejs.org 에서 LTS 버전을 설치한 뒤 다시 실행하세요.
  start "" https://nodejs.org
  pause
  exit /b 1
)
echo 필요한 프로그램을 내려받는 중입니다... (처음 한 번, 1~3분)
call npm install --no-fund --no-audit
if not %errorlevel%==0 (
  echo [오류] 설치 실패. 인터넷 연결을 확인하세요.
  pause
  exit /b 1
)
node scripts\deploy.mjs
pause
