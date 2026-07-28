from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data" / "processed" / "hospital_mvp_reference.csv"
ACCESSIBILITY = ROOT / "data" / "processed" / "facility_accessibility.csv"
WALKING_ROUTES = ROOT / "data" / "processed" / "walking_routes.csv"
HERO_INPUT = ROOT / "tmp" / "hero-data-collection" / "hero-pages.json"
RAW_EVIDENCE = ROOT / "data" / "raw" / "hero_public_page_evidence.json"


def truth(value: bool) -> str:
    return "yes" if value else "no"


def unknown_if_unverified(value: bool, verified: bool) -> str:
    return truth(value) if verified else "unknown"


def has_hit(item: dict, keyword: str) -> bool:
    return bool(item.get("keywordHits", {}).get(keyword))


def clean_departments(raw: str) -> list[str]:
    values = []
    for value in raw.split("|"):
        value = re.sub(r"\([^)]*\)", "", value).replace(" 등", "").strip()
        if value and value not in values:
            values.append(value)
    return values


def build() -> None:
    with REFERENCE.open(encoding="utf-8-sig", newline="") as handle:
        hospitals = list(csv.DictReader(handle))
    with ACCESSIBILITY.open(encoding="utf-8-sig", newline="") as handle:
        access_rows = {row["facility_id"]: row for row in csv.DictReader(handle)}
    with WALKING_ROUTES.open(encoding="utf-8-sig", newline="") as handle:
        walking_rows = list(csv.DictReader(handle))
    hero_items = json.loads(HERO_INPUT.read_text(encoding="utf-8"))
    hero_by_id = {item["id"]: item for item in hero_items}

    RAW_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERO_INPUT, RAW_EVIDENCE)

    clinical = []
    accessibility = []
    for hospital in hospitals:
        facility_id = hospital["facility_id"]
        schedule = hospital["regular_schedule"]
        departments = clean_departments(hospital["departments"])
        schedule_verified = not any(token in schedule for token in ("미확인", "확인 필요", "자동 확인 불가"))
        hero = hero_by_id.get(facility_id, {})
        hero_ok = hero.get("status") == "ok"

        night = bool(re.search(r"(19:|20:|21:|22:|야간|24시간)", schedule))
        saturday = ("토" in schedule or "매일" in schedule) and "주말 미확인" not in schedule
        sunday_holiday = bool(re.search(r"(매일|토[·/]일|일[·/]휴일|일 09:)", schedule)) and "일·공휴일 휴무" not in schedule
        emergency_24h = "24시간 응급" in schedule
        rehab = any("재활" in value for value in departments) or has_hit(hero, "재활")
        surgery = "수술" in hospital["departments"] or has_hit(hero, "수술")
        specialist = has_hit(hero, "전문의")
        collaborative = "협진" in " ".join(sum(hero.get("keywordHits", {}).values(), []))

        clinical.append({
            "facility_id": facility_id,
            "name": hospital["name"],
            "departments": "|".join(departments),
            "department_count": len(departments),
            "night_care": unknown_if_unverified(night, schedule_verified or night),
            "saturday_care": unknown_if_unverified(saturday, schedule_verified),
            "sunday_or_holiday_care": unknown_if_unverified(sunday_holiday, schedule_verified),
            "emergency_24h": truth(emergency_24h),
            "rehabilitation_capability": truth(rehab),
            "surgery_capability_public_evidence": truth(surgery),
            "specialist_public_evidence": truth(specialist),
            "collaborative_care_public_evidence": truth(collaborative),
            "schedule_data_quality": "verified" if schedule_verified else "partial_or_unknown",
            "hero_collection_status": hero.get("status", "not_collected"),
            "hero_collected_at": hero.get("fetchedAt", ""),
            "source_url": hospital["source_url"],
            "source_reliability": hospital["reliability"],
            "recommended_hira_fields": "specialist_count|doctor_count|bed_count|equipment|special_treatment|evaluation",
        })

        base = access_rows.get(facility_id, {})
        routes = [
            row for row in walking_rows
            if row["facility_id"] == facility_id and row.get("distance_km")
        ]
        route_distances = [float(row["distance_km"]) for row in routes]
        route_minutes = [float(row["estimated_minutes"]) for row in routes]
        parking_page = has_hit(hero, "주차")
        municipal_accessible_parking = facility_id == "GJH359"
        accessibility.append({
            "facility_id": facility_id,
            "name": hospital["name"],
            "step_free_entrance": base.get("step_free", "unknown") or "unknown",
            "elevator": base.get("elevator", "unknown") or "unknown",
            "accessible_parking_on_site": base.get("accessible_parking", "unknown") or "unknown",
            "accessible_toilet": "unknown",
            "accessible_entrance_route": "unknown",
            "walk_route_observation_count": len(routes),
            "nearest_origin_walk_km": round(min(route_distances), 3) if routes else "",
            "nearest_origin_walk_minutes": round(min(route_minutes), 1) if routes else "",
            "mean_origin_walk_km": round(sum(route_distances) / len(route_distances), 3) if routes else "",
            "mean_origin_walk_minutes": round(sum(route_minutes) / len(route_minutes), 1) if routes else "",
            "walking_route_source": routes[0]["route_source"] if routes else "",
            "walking_route_collected_at": routes[0]["collected_at"] if routes else "",
            "parking_information_published": truth(parking_page),
            "nearby_public_accessible_parking": truth(municipal_accessible_parking),
            "nearby_public_accessible_parking_spaces": "4" if municipal_accessible_parking else "",
            "nearby_public_accessible_parking_note": "서2동 공영주차장(세웅병원 앞), 총 106면 중 장애인 4면" if municipal_accessible_parking else "",
            "national_standard_match_status": "service_key_required",
            "hero_collection_status": hero.get("status", "not_collected"),
            "hero_collected_at": hero.get("fetchedAt", ""),
            "hospital_source_url": hospital["source_url"],
            "national_standard_source_url": "https://www.data.go.kr/data/15100058/standard.do?recommendDataYn=Y",
            "municipal_parking_source_url": "https://council.geumjeong.go.kr/board/view.geumj?boardId=BBS_0000047&dataSid=973084&menuCd=DOM_000000124001002000",
        })

    outputs = [
        (ROOT / "data" / "processed" / "clinical_condition_inputs.csv", clinical),
        (ROOT / "data" / "processed" / "facility_accessibility_inputs.csv", accessibility),
    ]
    for path, rows in outputs:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    sources = [
        {
            "evaluation_axis": "clinical_condition",
            "dataset": "건강보험심사평가원 병원정보서비스",
            "fields": "진료과목|의사·전문의 수|병상|의료장비|특수진료|평가정보",
            "collection_status": "metadata_collected_service_key_required",
            "source_url": "https://www.data.go.kr/data/15001698/openapi.do",
        },
        {
            "evaluation_axis": "clinical_condition",
            "dataset": "병원 공개 홈페이지 Hero 수집",
            "fields": "전문의 근거|재활|수술|협진|주차 안내",
            "collection_status": "collected",
            "source_url": "data/raw/hero_public_page_evidence.json",
        },
        {
            "evaluation_axis": "facility_accessibility",
            "dataset": "전국장애인편의시설표준데이터",
            "fields": "승강기|장애인사용가능화장실|장애인전용주차구역|주출입구 높이차이 제거|주출입구 접근로|주출입구 문",
            "collection_status": "metadata_collected_service_key_required",
            "source_url": "https://www.data.go.kr/data/15100058/standard.do?recommendDataYn=Y",
        },
        {
            "evaluation_axis": "facility_accessibility",
            "dataset": "금정구 공공기관 장애인 전용 주차구역 면수 현황",
            "fields": "공영주차장 총면수|장애인 주차면수|시설 위치 설명",
            "collection_status": "collected_one_matched_facility",
            "source_url": "https://council.geumjeong.go.kr/board/view.geumj?boardId=BBS_0000047&dataSid=973084&menuCd=DOM_000000124001002000",
        },
    ]
    source_path = ROOT / "data" / "processed" / "evaluation_dataset_sources.csv"
    with source_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sources[0]))
        writer.writeheader()
        writer.writerows(sources)

    print(json.dumps({
        "clinical_rows": len(clinical),
        "accessibility_rows": len(accessibility),
        "hero_pages_ok": sum(item.get("status") == "ok" for item in hero_items),
        "outputs": [str(path.relative_to(ROOT)) for path, _ in outputs] + [str(source_path.relative_to(ROOT)), str(RAW_EVIDENCE.relative_to(ROOT))],
    }, ensure_ascii=False))


if __name__ == "__main__":
    build()
