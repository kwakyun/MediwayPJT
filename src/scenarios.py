"""Quick-search presets and user-facing disease groups."""

DISEASE_GROUPS = {
    "호흡기 질환": ["천식", "만성폐쇄성폐질환(COPD)", "알레르기 비염", "기타 호흡기 질환"],
    "심뇌혈관 질환": ["고혈압", "심부전·관상동맥질환", "뇌졸중 후유증", "기타 심뇌혈관 질환"],
    "대사·내분비 질환": ["당뇨병", "갑상선 질환", "기타 대사·내분비 질환"],
    "근골격계 질환": ["관절염", "골다공증", "허리·척추 질환", "기타 근골격계 질환"],
    "신장 질환": ["만성콩팥병", "투석 치료 중", "기타 신장 질환"],
    "면역·알레르기 질환": ["자가면역질환", "중증 알레르기", "기타 면역·알레르기 질환"],
}

REFERENCE_LOCATIONS = {
    "부산대역 생활권": (35.2307, 129.0894),
    "구서역 생활권": (35.2470, 129.0915),
    "서동 생활권": (35.2168, 129.1040),
    "노포역 생활권": (35.2838, 129.0950),
}

REFERENCE_ORIGIN_IDS = {
    "부산대역 생활권": "장전부곡생활권_부산대역",
    "구서역 생활권": "구서남산생활권_구서역",
    "서동 생활권": "서금사생활권_서동역",
    "노포역 생활권": "청룡선두생활권_노포역",
}

SCENARIOS = {
    "기본 조건": {
        "scenario_id": "DEMO-01",
        "basic_type": "일반 성인",
        "selected_diseases": [],
        "facility_type": "병원",
        "location_name": "부산대역 생활권",
    },
    "비 오는 날 · 고령자": {
        "scenario_id": "DEMO-02",
        "basic_type": "고령자",
        "selected_diseases": [],
        "facility_type": "병원",
        "location_name": "구서역 생활권",
    },
    "대기질 민감 · 호흡기": {
        "scenario_id": "DEMO-03",
        "basic_type": "일반 성인",
        "selected_diseases": ["천식"],
        "facility_type": "병원",
        "location_name": "부산대역 생활권",
    },
    "복합 건강 조건": {
        "scenario_id": "DEMO-04",
        "basic_type": "고령자",
        "selected_diseases": ["관절염", "고혈압"],
        "facility_type": "병원",
        "location_name": "서동 생활권",
    },
}
