# 메디웨이 팀원 실행 안내

## 가장 간단한 실행 방법

1. ZIP 파일을 원하는 폴더에 압축 해제합니다.
2. Python 3.11 이상이 설치되어 있는지 확인합니다.
3. `run_app.bat`을 더블클릭합니다.
4. 최초 실행 시 가상환경과 필수 패키지가 자동으로 설치됩니다.
5. 브라우저에서 `http://localhost:8501`을 엽니다.

PowerShell 실행 정책과 관계없이 `.bat` 파일로 실행할 수 있습니다.

## 터미널에서 실행

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 선택 기능 API 설정

API 키 없이도 저장된 의료시설·진료조건·접근성 데이터로 핵심 기능을 사용할 수 있습니다.

ODsay 대중교통과 Gemini AI 상담을 사용하려면 `.streamlit` 폴더를 만들고 그 안에 `secrets.toml` 파일을 생성합니다.

```toml
ODSAY_API_KEY = "팀원이 발급받은 ODsay Server API 키"
GEMINI_API_KEY = "팀원이 발급받은 Gemini API 키"
GEMINI_MODEL = "gemini-3.5-flash"
```

실제 API 키는 메신저, Git 또는 공용 압축파일에 넣지 마세요. 설정을 변경한 뒤에는 Streamlit을 종료하고 다시 실행합니다.

## 검증

설치 후 `verify_app.bat`을 실행하면 자동 테스트를 수행합니다.

## 문제가 있을 때

- `Python을 찾을 수 없습니다`: Python 3.11 이상을 설치하면서 `Add Python to PATH`를 선택합니다.
- 패키지 설치 실패: 인터넷 연결을 확인하고 `run_app.bat`을 다시 실행합니다.
- API 기능만 실패: `.streamlit/secrets.toml`의 키 이름과 발급 플랫폼을 확인합니다.
- 앱 종료: 실행 중인 터미널에서 `Ctrl+C`를 누릅니다.
