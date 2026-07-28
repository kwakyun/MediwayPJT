"""Transparent scoring helpers for the supplemental evaluation datasets."""

from __future__ import annotations


YES = {"yes", "true", "1"}
NO = {"no", "false", "0"}


def _state(value: object) -> str:
    normalized = str(value or "unknown").strip().lower()
    if normalized in YES:
        return "yes"
    if normalized in NO:
        return "no"
    return "unknown"


def care_availability_score(clinical: dict, fallback_score: float = 55.0) -> float:
    """Score published time availability without treating it as clinical quality."""
    if not clinical:
        return round(float(fallback_score), 1)
    values = {"yes": 100.0, "no": 30.0, "unknown": 55.0}
    emergency_values = {"yes": 100.0, "no": 40.0, "unknown": 55.0}
    score = (
        values[_state(clinical.get("night_care"))] * 0.30
        + values[_state(clinical.get("saturday_care"))] * 0.25
        + values[_state(clinical.get("sunday_or_holiday_care"))] * 0.25
        + emergency_values[_state(clinical.get("emergency_24h"))] * 0.20
    )
    return round(score, 1)


def enriched_accessibility_score(
    base_score: float, evidence: dict, basic_type: str,
) -> float:
    """Add only confirmed accessibility evidence; unknown values remain neutral."""
    score = float(base_score)
    physical_fields = (
        "step_free_entrance", "elevator", "accessible_parking_on_site",
        "accessible_toilet", "accessible_entrance_route",
    )
    for field in physical_fields:
        state = _state(evidence.get(field))
        score += 7 if state == "yes" else -3 if state == "no" else 0
    if _state(evidence.get("nearby_public_accessible_parking")) == "yes":
        score += 10 if basic_type in {"고령자", "보행·이동 취약자"} else 6
    if _state(evidence.get("parking_information_published")) == "yes":
        score += 2
    return round(min(100.0, max(0.0, score)), 1)


def evidence_confidence_score(
    route_status: str, schedule: dict, clinical: dict, accessibility_evidence: dict,
) -> float:
    """Score data coverage and provenance, not facility quality."""
    score = 70.0 if route_status == "approximate_osm" else 40.0
    if int(float(accessibility_evidence.get("walk_route_observation_count", 0) or 0)) >= 3:
        score += 5
    quality = str(clinical.get("schedule_data_quality", ""))
    score += 8 if quality == "verified" else 3 if quality == "partial_or_unknown" else 0
    hero_status = str(clinical.get("hero_collection_status") or accessibility_evidence.get("hero_collection_status") or "")
    score += 5 if hero_status == "ok" else -3 if hero_status == "error" else 0
    if clinical.get("source_url") or schedule.get("source_url"):
        score += 4
    return round(min(95.0, max(0.0, score)), 1)


def service_tags(clinical: dict, accessibility_evidence: dict) -> list[str]:
    mapping = [
        ("night_care", "야간진료"),
        ("saturday_care", "토요일진료"),
        ("sunday_or_holiday_care", "일·공휴일진료"),
        ("emergency_24h", "24시간응급"),
        ("rehabilitation_capability", "재활진료 근거"),
        ("surgery_capability_public_evidence", "수술 공개근거"),
        ("specialist_public_evidence", "전문의 공개근거"),
        ("collaborative_care_public_evidence", "협진 공개근거"),
    ]
    tags = [label for field, label in mapping if _state(clinical.get(field)) == "yes"]
    if _state(accessibility_evidence.get("nearby_public_accessible_parking")) == "yes":
        tags.append("인근 장애인주차")
    return tags
