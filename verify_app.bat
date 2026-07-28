@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 먼저 run_app.bat을 실행해 가상환경을 설치해 주세요.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 (
  echo 검증에 실패했습니다.
  pause
  exit /b 1
)

echo 모든 테스트를 통과했습니다.
pause
