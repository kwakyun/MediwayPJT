"""Pure, deterministic recommendation scoring for Mediway."""

from __future__ import annotations

import math
from typing import Iterable

import pandas as pd

from src.evidence_scoring import (
    care_availability_score,
    enriched_accessibility_score,
    evidence_confidence_score,
    service_tags,
)


WEIGHTS = {"fit": 0.35, "route": 0.30, "accessibility": 0.20, "operating": 0.10, "confidence": 0.05}
LEGACY_WEIGHTS = {"distance": 0.45, "weather": 0.20, "air_quality": 0.20, "user_fit": 0.15}

DISEASE_SPECIALTIES = {
    "천식": {"호흡기내과", "내과"}, "만성폐쇄성폐질환(COPD)": {"호흡기내과", "내과"},
    "알레르기 비염": {"이비인후과", "알레르기내과"}, "기타 호흡기 질환": {"호흡기내과", "내과"},
    "고혈압": {"내과", "가정의학과", "순환기내과"}, "심부전·관상동맥질환": {"순환기내과"},
    "뇌졸중 후유증": {"신경과", "재활의학과"}, "기타 심뇌혈관 질환": {"내과", "신경과", "순환기내과"},
    "당뇨병": {"내분비내과", "내과"}, "갑상선 질환": {"내분비내과"},
    "기타 대사·내분비 질환": {"내분비내과", "내과"},
    "관절염": {"정형외과", "재활의학과", "류마티스내과"},
    "골다공증": {"정형외과", "재활의학과", "류마티스내과"},
    "허리·척추 질환": {"정형외과", "재활의학과", "신경외과"},
    "기타 근골격계 질환": {"정형외과", "재활의학과", "류마티스내과"},
    "만성콩팥병": {"신장내과"}, "투석 치료 중": {"신장내과", "투석"}, "기타 신장 질환": {"신장내과"},
    "자가면역질환": {"류마티스내과"}, "중증 알레르기": {"알레르기내과", "내과"},
    "기타 면역·알레르기 질환": {"알레르기내과", "내과", "류마티스내과"},
}
RESPIRATORY_DISEASES = {"천식", "만성폐쇄성폐질환(COPD)", "알레르기 비염", "기타 호흡기 질환"}


def format_duration(minutes: float) -> str:
    """Format rounded minutes as a compact Korean hour/minute label."""
    total = max(0, int(round(float(minutes))))
    hours, remaining = divmod(total, 60)
    if hours and remaining:
        return f"{hours}시간 {remaining}분"
    if hours:
        return f"{hours}시간"
    return f"{remaining}분"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    values = [lat1, lon1, lat2, lon2]
    if any(pd.isna(value) for value in values):
        raise ValueError("Coordinates must not be missing")
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("Coordinates are outside WGS84 bounds")
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_component(distance_km: float) -> float:
    if pd.isna(distance_km) or distance_km < 0:
        raise ValueError("Distance must be a non-negative number")
    if distance_km <= 1:
        score = 100 - 20 * distance_km
    elif distance_km <= 3:
        score = 80 - 15 * (distance_km - 1)
    elif distance_km <= 5:
        score = 50 - 12.5 * (distance_km - 3)
    else:
        score = max(0, 25 - 2.5 * (distance_km - 5))
    return round(score, 1)


def weather_component(temperature: float, rainfall: float, weather_status: str = "") -> int:
    if pd.isna(temperature) or pd.isna(rainfall) or rainfall < 0:
        raise ValueError("Weather values are missing or invalid")
    if rainfall >= 10 or temperature <= 0 or temperature >= 33 or "폭우" in str(weather_status) or "폭설" in str(weather_status):
        return 40
    if rainfall > 0 or temperature < 10 or temperature > 28 or "비" in str(weather_status) or "눈" in str(weather_status):
        return 70
    return 100


def air_quality_component(air_grade: str) -> int:
    scores = {"좋음": 100, "보통": 80, "나쁨": 50, "매우 나쁨": 30, "매우나쁨": 30}
    try:
        return scores[str(air_grade).strip()]
    except KeyError as exc:
        raise ValueError(f"Unknown air quality grade: {air_grade}") from exc


def basic_fit_component(basic_type: str, distance_km: float) -> int:
    if basic_type == "고령자":
        return 100 if distance_km <= 2 else 60
    if basic_type == "보행·이동 취약자":
        return 100 if distance_km <= 1 else 70 if distance_km <= 3 else 50
    return 70


def disease_matches(specialty: str, selected_diseases: Iterable[str]) -> tuple[list[str], list[str]]:
    specialties = {value.strip() for value in str(specialty).split("|") if value.strip()}
    matched, unmatched = [], []
    for disease in selected_diseases:
        (matched if DISEASE_SPECIALTIES.get(disease, set()) & specialties else unmatched).append(disease)
    return matched, unmatched


def user_fit_component(basic_type: str, distance_km: float, specialty: str, selected_diseases: Iterable[str]) -> tuple[int, list[str], list[str]]:
    diseases = [value for value in selected_diseases if value and value != "선택 안 함"]
    basic_score = basic_fit_component(basic_type, distance_km)
    if not diseases:
        return basic_score, [], []
    matched, unmatched = disease_matches(specialty, diseases)
    return round((basic_score + (100 if matched else 60)) / 2), matched, unmatched


def weighted_score(distance: float, weather: int, air_quality: int, user_fit: int) -> tuple[float, float]:
    raw = sum((distance * LEGACY_WEIGHTS["distance"], weather * LEGACY_WEIGHTS["weather"], air_quality * LEGACY_WEIGHTS["air_quality"], user_fit * LEGACY_WEIGHTS["user_fit"]))
    return raw, round(raw, 1)


def accessibility_weighted_score(fit: float, route: float, accessibility: float, operating: float, confidence: float) -> tuple[float, float]:
    raw = fit * WEIGHTS["fit"] + route * WEIGHTS["route"] + accessibility * WEIGHTS["accessibility"] + operating * WEIGHTS["operating"] + confidence * WEIGHTS["confidence"]
    return raw, round(raw, 1)


def _record_for(frame: pd.DataFrame | None, facility_id: str) -> dict:
    if frame is None or frame.empty or "facility_id" not in frame:
        return {}
    rows = frame.loc[frame["facility_id"] == facility_id]
    return {} if rows.empty else rows.iloc[0].to_dict()


def _route_metrics(distance_km: float, basic_type: str, diseases: list[str], temperature: float, rainfall: float, air_grade: str, profile: dict) -> dict:
    speed = {"일반 성인": 4.5, "고령자": 3.2, "보행·이동 취약자": 2.6}.get(basic_type, 4.5)
    route_factor = float(profile.get("route_factor", 1.30) or 1.30)
    outdoor_ratio = float(profile.get("outdoor_ratio", 0.65) or 0.65)
    slope_level = int(profile.get("slope_level", 1) or 0)
    transfer_count = int(profile.get("transfer_count", 0) or 0)
    travel_minutes = distance_km * route_factor / speed * 60 + transfer_count * 6
    outdoor_minutes = travel_minutes * outdoor_ratio
    weather_multiplier = 0.65 if rainfall >= 10 else 0.35 if rainfall > 0 else 0.0
    if temperature <= 0 or temperature >= 33:
        weather_multiplier += 0.20
    air_multiplier = {"좋음": 0.0, "보통": 0.04, "나쁨": 0.22, "매우 나쁨": 0.40, "매우나쁨": 0.40}.get(str(air_grade).strip(), 0.10)
    if set(diseases) & RESPIRATORY_DISEASES:
        air_multiplier *= 1.8
    environment_penalty = outdoor_minutes * (weather_multiplier + air_multiplier)
    vulnerable = basic_type in {"고령자", "보행·이동 취약자"}
    mobility_penalty = slope_level * (0.9 if vulnerable else 0.35) + transfer_count * (2.0 if vulnerable else 1.0)
    route_burden = travel_minutes + environment_penalty + mobility_penalty
    return {
        "travel_minutes": round(travel_minutes, 1), "outdoor_minutes": round(outdoor_minutes, 1),
        "environment_penalty_minutes": round(environment_penalty, 1), "route_burden_minutes": round(route_burden, 1),
        "route_score": round(max(0.0, 100 - route_burden * 4.0), 1), "slope_level": slope_level,
        "transfer_count": transfer_count,
        "route_distance_km": round(distance_km * route_factor, 2), "route_data_status": "prototype_estimate",
    }


def _route_record(routes: pd.DataFrame | None, origin_id: str | None, facility_id: str) -> dict:
    if routes is None or routes.empty or not origin_id:
        return {}
    required = {"origin_id", "facility_id", "status"}
    if not required <= set(routes.columns):
        return {}
    rows = routes.loc[(routes["origin_id"] == origin_id) & (routes["facility_id"] == facility_id)]
    if rows.empty or rows.iloc[0]["status"] != "OSM 보행경로 계산":
        return {}
    return rows.iloc[0].to_dict()


def _apply_calculated_route(metrics: dict, route_record: dict, basic_type: str, diseases: list[str], temperature: float, rainfall: float, air_grade: str) -> dict:
    if not route_record:
        return metrics
    travel = float(route_record["estimated_minutes"])
    outdoor = float(route_record["outdoor_minutes"])
    mobility_factor = 1.25 if basic_type == "고령자" else 1.5 if basic_type == "보행·이동 취약자" else 1.0
    travel *= mobility_factor
    outdoor *= mobility_factor
    weather_multiplier = 0.65 if rainfall >= 10 else 0.35 if rainfall > 0 else 0.0
    if temperature <= 0 or temperature >= 33:
        weather_multiplier += 0.20
    air_multiplier = {"좋음": 0.0, "보통": 0.04, "나쁨": 0.22, "매우 나쁨": 0.40, "매우나쁨": 0.40}.get(str(air_grade).strip(), 0.10)
    if set(diseases) & RESPIRATORY_DISEASES:
        air_multiplier *= 1.8
    environment = outdoor * (weather_multiplier + air_multiplier)
    burden = travel + environment
    metrics.update({
        "travel_minutes": round(travel, 1), "outdoor_minutes": round(outdoor, 1),
        "environment_penalty_minutes": round(environment, 1), "route_burden_minutes": round(burden, 1),
        "route_score": round(max(0.0, 100 - burden * 1.2), 1),
        "route_distance_km": round(float(route_record["distance_km"]), 2),
        "route_data_status": "approximate_osm", "transfer_count": int(route_record.get("transfers", 0) or 0),
    })
    return metrics


def _accessibility_score(profile: dict, basic_type: str) -> float:
    if not profile:
        return 55.0
    values = [str(profile.get(key, "unknown")).lower() for key in ("step_free", "elevator", "accessible_parking")]
    score = 55 + sum(15 for value in values if value in {"true", "1", "yes"}) - sum(5 for value in values if value in {"false", "0", "no"})
    if basic_type in {"고령자", "보행·이동 취약자"}:
        score -= int(profile.get("slope_level", 0) or 0) * 4
    return round(min(100, max(0, score)), 1)


def recommend(facilities: pd.DataFrame, *, user_latitude: float, user_longitude: float, basic_type: str,
              selected_diseases: Iterable[str], facility_type: str, temperature: float, rainfall: float,
              weather_status: str, air_grade: str, top_n: int = 5, accessibility: pd.DataFrame | None = None,
              schedules: pd.DataFrame | None = None, routes: pd.DataFrame | None = None,
              origin_id: str | None = None, clinical_conditions: pd.DataFrame | None = None,
              accessibility_inputs: pd.DataFrame | None = None) -> pd.DataFrame:
    required = {"facility_id", "name", "type", "latitude", "longitude", "specialty"}
    missing = required - set(facilities.columns)
    if missing:
        raise ValueError(f"Missing facility columns: {sorted(missing)}")
    diseases = [value for value in selected_diseases if value and value != "선택 안 함"]
    candidates = facilities[facilities["type"] == facility_type].copy()
    if candidates.empty:
        return candidates.assign(rank=pd.Series(dtype="int64"))
    records = []
    for row in candidates.to_dict("records"):
        facility_id = row["facility_id"]
        distance_km = haversine_km(user_latitude, user_longitude, row["latitude"], row["longitude"])
        matched, unmatched = disease_matches(row.get("specialty", ""), diseases)
        fit_score = 82.0 if not diseases else 100.0 if matched else 45.0
        profile, schedule = _record_for(accessibility, facility_id), _record_for(schedules, facility_id)
        clinical = _record_for(clinical_conditions, facility_id)
        access_evidence = _record_for(accessibility_inputs, facility_id)
        route = _route_metrics(distance_km, basic_type, diseases, temperature, rainfall, air_grade, profile)
        route = _apply_calculated_route(route, _route_record(routes, origin_id, facility_id), basic_type, diseases, temperature, rainfall, air_grade)
        accessibility_score = enriched_accessibility_score(
            _accessibility_score(profile, basic_type), access_evidence, basic_type
        )
        legacy_operating_score = 100.0 if schedule.get("data_status") == "available" else 55.0
        operating_score = care_availability_score(clinical, legacy_operating_score)
        data_status = str(profile.get("data_status", "unknown"))
        confidence_score = evidence_confidence_score(
            route["route_data_status"], schedule, clinical, access_evidence
        )
        evidence_tags = service_tags(clinical, access_evidence)
        raw_score, final_score = accessibility_weighted_score(fit_score, route["route_score"], accessibility_score, operating_score, confidence_score)
        reasons = []
        reasons.append(f"공개 진료과목이 선택 질환({', '.join(matched)})과 연결됩니다." if matched else "진료과목과 이동 조건을 함께 비교한 후보입니다." if not diseases else "선택 질환과 일치하는 공개 진료과목이 없어 보수적으로 평가했습니다.")
        reasons.append(f"예상 이동 {format_duration(route['travel_minutes'])} 중 야외 노출은 약 {format_duration(route['outdoor_minutes'])}입니다.")
        if route["environment_penalty_minutes"] >= 0.5:
            reasons.append(f"현재 환경으로 인한 추가 이동 부담을 약 {format_duration(route['environment_penalty_minutes'])}으로 반영했습니다.")
        elif evidence_tags:
            reasons.append(f"공개 근거에서 {', '.join(evidence_tags[:2])} 정보를 확인했습니다.")
        else:
            reasons.append("운영 여부와 실제 경로는 방문 전에 다시 확인해야 합니다.")
        row.update({
            "distance_km": route["route_distance_km"], "straight_distance_km": round(distance_km, 2), "distance_score": distance_component(distance_km),
            "weather_score": weather_component(temperature, rainfall, weather_status), "air_quality_score": air_quality_component(air_grade),
            "user_fit_score": fit_score, "fit_score": fit_score, "accessibility_score": accessibility_score,
            "operating_score": operating_score, "confidence_score": confidence_score, "raw_score": raw_score,
            "final_score": final_score, "matched_diseases": matched, "unmatched_diseases": unmatched,
            "visit_status": "운영정보 확인" if operating_score >= 80 else "방문 전 전화 확인",
            "service_tags": evidence_tags,
            "availability_data_status": clinical.get("schedule_data_quality", "unknown"),
            "walk_route_observation_count": int(float(access_evidence.get("walk_route_observation_count", 0) or 0)),
            "accessibility_data_status": data_status, "reasons": reasons[:3], **route,
        })
        records.append(row)
    ranked = pd.DataFrame(records).sort_values(["raw_score", "distance_km", "facility_id"], ascending=[False, True, True], kind="stable")
    ranked = ranked.head(top_n).reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked
