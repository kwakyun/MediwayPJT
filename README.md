# 메디웨이

질환별 진료 조건, 예상 이동·야외 노출, 시설 접근성을 함께 고려해 부산광역시 금정구의 병원·약국을 비교하는 Streamlit 서비스입니다. 후보를 고른 뒤 외부 지도에서 실제 길찾기를 이어갑니다.

브라우저에서 위치 권한을 허용하면 선택 생활권 대신 현재 위도·경도를 출발점으로 사용해 시설별 거리, 추천 점수, 위치 지도와 ODsay 대중교통 경로를 다시 계산합니다. 위치 기능은 HTTPS 배포 주소 또는 `localhost`에서 사용할 수 있습니다.

## 설치와 실행

PowerShell 기준:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

브라우저에서 안내되는 로컬 주소를 엽니다. 앱의 핵심 기능은 `data/processed/`의 저장 데이터만 사용하므로 인터넷 연결 없이 실행할 수 있습니다.

## 버스·지하철 대중교통 연동

ODsay Server API 키를 설정하면 추천 결과에서 도보와 대중교통을 나누어 총 소요시간, 버스·지하철 교통·대기시간, 도보·야외시간, 예상 요금, 환승 횟수와 승·하차 지점을 비교합니다.

로컬 개발 환경에서는 `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사해 키를 입력하거나 같은 이름의 환경변수를 설정합니다. 실제 키 파일은 Git에서 제외됩니다. 실행 방법은 `TEAM_RUN_GUIDE.md`를 참고하세요.

```toml
ODSAY_API_KEY = ""
```

키가 없거나 외부 API 요청이 실패해도 저장된 도보 추천은 계속 작동합니다. `추천`, `지하철`, `버스` 우선 경로를 선택할 수 있으며 대중교통 정보는 ODsay 응답을 사용하고 임의 요금을 만들지 않습니다.

## 메디웨이 상담봇

`메디웨이 상담` 화면은 API 키 없이도 등록 시설, 공개 운영 안내, 지역 통계, 최근 추천의 거리·교통과 질환별 관련 진료과를 안내합니다. 선택적으로 Gemini Developer API를 연결하면 같은 서비스 맥락에 일반 의료지식을 결합한 자연어 CS 답변을 제공합니다.

```toml
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-3.5-flash"
```

챗봇은 의료 진단·처방을 제공하지 않으며 응급 징후가 포함된 질문은 AI 호출보다 먼저 119 안내로 전환합니다. 정확한 현재 위치 좌표는 AI 맥락에 포함하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe scripts\validate_data.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\generate_scenario_results.py
```

## 프로젝트 구조

- `app.py`: 제출용 Streamlit 실행 파일
- `src/scoring.py`: UI와 분리된 접근성 점수·추천 이유 로직
- `src/evidence_scoring.py`: 공개 진료 가능 시간·접근성 근거·데이터 충실도 보강 계산
- `src/mobility.py`: ODsay 버스·지하철 경로 조회, 승차·야외시간과 요금·환승 분해
- `src/map_links.py`: 상세주소를 제거한 외부 지도용 기관명·행정구역 검색어 생성
- `src/geolocation.py`: 브라우저 위치 권한 요청과 현재 좌표 검증
- `src/chatbot.py`: 서비스 맥락 기반 CS 답변, 응급 안전 분기와 선택형 Gemini Developer API 연동
- `src/scenarios.py`: 빠른 검색 조건과 질환 선택 체계
- `data/processed/`: 서비스 실행용 정제 CSV
- `data/processed/facility_accessibility.csv`: 경로·시설 접근성 발표용 추정 프로필
- `data/processed/clinical_condition_inputs.csv`: 병원별 진료시간·재활·수술·전문의·협진 공개 근거
- `data/processed/facility_accessibility_inputs.csv`: 보행 관측과 확인 가능한 주차·물리 접근성 근거
- `data/processed/walking_routes.csv`: 생활권 4곳×병원 15곳 경로 준비도 데이터
- `data/processed/hospital_mvp_reference.csv`: 제공된 MVP 엑셀의 병원·진료·운영 통합 참고표
- `scripts/import_mvp_workbook.py`: 제공 엑셀을 실행용 CSV로 다시 생성하는 가져오기 스크립트
- `data/processed/operating_hours.csv`: 출처·확인일이 포함된 운영시간 스냅샷
- `src/operating_hours.py`: 정규 시간표 기준 운영·점심·휴무 상태 계산
- `data/source_notes.md`: 출처·기준일·정제·한계
- `tests/`: 점수 및 통합 검증
- `output/analysis/scenario_results.csv`: 빠른 검색 조건별 검증 결과

## 주의

이 서비스는 공개 데이터 기반 이동 접근성 참고 도구입니다. 의료 진단이나 치료 적합성을 보장하지 않습니다. 새 자료의 물리 접근성 `unknown`은 중립 처리하며, 공개 진료시간 점수는 의료 수준이 아니라 방문 가능 시간대의 폭을 뜻합니다. 실제 경로와 운영 여부는 외부 지도와 기관에 확인해야 합니다.
