@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [메디웨이] 실행 환경을 확인합니다.

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 가상환경을 생성합니다.
  where py >nul 2>nul
  if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 (
      echo Python을 찾을 수 없습니다. Python 3.11 이상을 설치해 주세요.
      pause
      exit /b 1
    )
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 goto :failed

  echo [2/3] 필수 패키지를 설치합니다. 최초 실행에는 몇 분이 걸릴 수 있습니다.
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 goto :failed
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
) else (
  echo [1/3] 기존 가상환경을 사용합니다.
  echo [2/3] 설치된 패키지를 사용합니다.
)

echo [3/3] 메디웨이를 시작합니다.
echo 브라우저가 자동으로 열리지 않으면 http://localhost:8501 을 여세요.
".venv\Scripts\python.exe" -m streamlit run app.py
exit /b %errorlevel%

:failed
echo 설치 또는 실행 중 오류가 발생했습니다.
pause
exit /b 1
