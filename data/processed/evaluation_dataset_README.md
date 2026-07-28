# 매디웨이 진료조건·시설접근성 평가 데이터

## 생성 파일

- `clinical_condition_inputs.csv`: 병원별 진료과 수, 야간·토요일·일요일/공휴일 진료, 24시간 응급, 재활·수술·전문의·협진 공개 근거
- `facility_accessibility_inputs.csv`: 병원별 생활권 기준점 보행거리·시간, 주차 안내 공개 여부, 인근 장애인 공영주차장, 국가 표준 내부 편의시설 필드
- `evaluation_dataset_sources.csv`: 원천 데이터, 수집 상태, 사용할 필드
- `../raw/hero_public_page_evidence.json`: Ulixee Hero가 수집한 공개 페이지 키워드 문맥과 수집 시각

## 점수 적용 원칙

진료조건은 기존의 단순 진료과 일치 여부 대신 아래 신호를 분리해서 사용한다.

1. 질환-진료과 일치
2. 진료과 폭(`department_count`)
3. 진료 가능 시간(`night_care`, `saturday_care`, `sunday_or_holiday_care`, `emergency_24h`)
4. 공개 확인 역량(`rehabilitation_capability`, `surgery_capability_public_evidence`, `specialist_public_evidence`, `collaborative_care_public_evidence`)

시설접근성은 다음 두 묶음을 분리한다.

1. 외부 접근: `nearest_origin_walk_minutes`, `mean_origin_walk_minutes`, 인근 장애인 주차
2. 건물 내부: 단차 없는 출입구, 승강기, 장애인 주차, 장애인 화장실, 접근로

`unknown`을 일괄 55점으로 바꾸지 않는다. 확인된 항목의 가중치만 다시 정규화해 점수를 계산하고, 확인된 가중치 비율을 별도 `data_confidence`로 표시한다. 내부 편의시설은 공공데이터포털 서비스키를 발급받은 뒤 `national_standard_match_status`를 실제 매칭 결과로 교체한다.

## 재생성

```powershell
python scripts/build_evaluation_datasets.py
```
