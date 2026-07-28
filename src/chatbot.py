"""Context-aware customer-service chatbot for Mediway."""

from __future__ import annotations

import json
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd

from src.map_links import compact_map_query
from src.scoring import DISEASE_SPECIALTIES, format_duration


class ChatbotError(RuntimeError):
    """Raised when an optional language-model response cannot be generated."""


EMERGENCY_TERMS = {
    "의식이 없어", "의식 없음", "숨을 못", "호흡곤란", "심한 흉통", "가슴이 찢어",
    "한쪽 마비", "말이 안 나", "심한 출혈", "피가 멈추지", "자살", "극단적 선택",
}


def emergency_answer(question: str) -> str | None:
    normalized = " ".join(str(question).lower().split())
    if not any(term in normalized for term in EMERGENCY_TERMS):
        return None
    return (
        "지금 말씀하신 내용은 긴급 평가가 필요할 수 있습니다. **즉시 119에 연락**하거나 주변 사람에게 도움을 요청하세요. "
        "직접 운전하지 말고 119 구급상황관리센터의 안내를 따르세요. 이 채팅으로 응급 여부를 판단하거나 기다리지 마세요."
    )


def build_service_context(
    facilities: pd.DataFrame,
    schedules: pd.DataFrame,
    population: pd.DataFrame,
    last_recommendation: dict | None = None,
    clinical_conditions: pd.DataFrame | None = None,
    accessibility_inputs: pd.DataFrame | None = None,
) -> dict:
    schedule_by_id = {
        str(row["facility_id"]): row for row in schedules.to_dict("records")
    }
    clinical_by_id = {
        str(row["facility_id"]): row
        for row in (clinical_conditions.to_dict("records") if clinical_conditions is not None else [])
    }
    accessibility_by_id = {
        str(row["facility_id"]): row
        for row in (accessibility_inputs.to_dict("records") if accessibility_inputs is not None else [])
    }
    facility_rows = []
    for row in facilities.to_dict("records"):
        schedule = schedule_by_id.get(str(row["facility_id"]), {})
        clinical = clinical_by_id.get(str(row["facility_id"]), {})
        access = accessibility_by_id.get(str(row["facility_id"]), {})
        facility_rows.append({
            "facility_id": row["facility_id"],
            "name": row["name"],
            "type": row["type"],
            "address": row["address"],
            "specialty": row.get("specialty") or "",
            "phone": row.get("phone") or "정보 없음",
            "schedule_text": schedule.get("schedule_text") or "정보 없음",
            "schedule_status": schedule.get("data_status") or "unknown",
            "schedule_verified_date": schedule.get("verified_date") or "정보 없음",
            "night_care": clinical.get("night_care") or "unknown",
            "saturday_care": clinical.get("saturday_care") or "unknown",
            "sunday_or_holiday_care": clinical.get("sunday_or_holiday_care") or "unknown",
            "emergency_24h": clinical.get("emergency_24h") or "unknown",
            "rehabilitation_capability": clinical.get("rehabilitation_capability") or "unknown",
            "nearby_public_accessible_parking": access.get("nearby_public_accessible_parking") or "unknown",
            "walk_route_observation_count": int(access.get("walk_route_observation_count") or 0),
        })
    total = population.loc[population["region"] == "부산광역시 금정구"]
    population_summary = {}
    if not total.empty:
        row = total.iloc[0]
        population_summary = {
            "population": int(row["population"]),
            "elderly_population": int(row["elderly_population"]),
            "reference_date": str(row["reference_date"]),
        }
    return {
        "region": "부산광역시 금정구",
        "facility_counts": facilities["type"].value_counts().to_dict(),
        "population": population_summary,
        "facilities": facility_rows,
        "disease_specialties": {key: sorted(value) for key, value in DISEASE_SPECIALTIES.items()},
        "last_recommendation": last_recommendation or {},
    }


def _matched_facility(question: str, context: dict) -> dict | None:
    candidates = [row for row in context.get("facilities", []) if str(row["name"]) in question]
    return max(candidates, key=lambda row: len(str(row["name"])), default=None)


def _facility_answer(facility: dict) -> str:
    specialties = " · ".join(filter(None, str(facility.get("specialty") or "").split("|"))) or "정보 없음"
    schedule = str(facility.get("schedule_text") or "정보 없음")
    if facility.get("schedule_status") == "unknown":
        schedule_notice = f"공개 운영 안내: {schedule}" if schedule != "정보 없음" else f"운영시간 문의: {facility['phone']}"
    else:
        schedule_notice = f"저장된 운영시간: {schedule}"
    query = quote(compact_map_query(facility["name"], facility["address"]))
    published = []
    for field, label in (
        ("night_care", "야간진료"), ("saturday_care", "토요일진료"),
        ("sunday_or_holiday_care", "일·공휴일진료"), ("emergency_24h", "24시간 응급"),
        ("rehabilitation_capability", "재활진료"),
        ("nearby_public_accessible_parking", "인근 장애인주차"),
    ):
        if str(facility.get(field)).lower() == "yes":
            published.append(label)
    evidence_text = " · ".join(published) if published else "확인된 추가 공개 근거 없음"
    return (
        f"**{facility['name']}**은(는) 메디웨이에 등록된 {facility['type']}입니다.\n\n"
        f"- 주소: {facility['address']}\n"
        f"- 진료과목: {specialties}\n"
        f"- 연락처: {facility['phone']}\n"
        f"- {schedule_notice}\n\n"
        f"- 추가 공개 근거: {evidence_text}\n"
        f"- 보행경로 관측: {facility.get('walk_route_observation_count', 0)}개\n\n"
        f"[네이버지도](https://map.naver.com/p/search/{query}) · "
        f"[카카오맵](https://map.kakao.com/?q={query})\n\n"
        "운영시간과 접수 마감은 변경될 수 있으므로 방문 전에 전화로 확인해 주세요."
    )


def local_cs_answer(question: str, context: dict) -> str:
    urgent = emergency_answer(question)
    if urgent:
        return urgent
    facility = _matched_facility(question, context)
    if facility:
        return _facility_answer(facility)

    normalized = str(question).replace(" ", "")
    recommendation = context.get("last_recommendation") or {}
    results = recommendation.get("results") or []
    if any(term in normalized for term in ["거리", "가까", "교통", "이동시간", "야외시간"]):
        if results:
            lines = []
            for row in results[:5]:
                transit = row.get("transit") or {}
                transit_text = ""
                if transit:
                    transit_text = f" · {transit.get('route_type', '대중교통')} {format_duration(transit.get('total_minutes', 0))} · 약 {int(transit.get('fare', 0)):,}원"
                lines.append(
                    f"- #{row['rank']} {row['name']}: 거리 {row['distance_km']:.1f}km · "
                    f"예상 이동 {format_duration(row['travel_minutes'])} · 야외 {format_duration(row['outdoor_minutes'])}{transit_text}"
                )
            return (
                f"최근 추천의 출발 기준은 **{recommendation.get('location', '저장된 기준 위치')}**입니다.\n\n"
                + "\n".join(lines)
                + "\n\n거리와 시간은 현재 저장 경로 또는 API 조회 시점 기준의 참고값입니다."
            )
        return "먼저 **의료기관 추천** 화면에서 현재 위치나 생활권을 선택해 추천을 실행하면 거리·이동시간·교통 정보를 이어서 설명할 수 있습니다."

    matched_disease = next((name for name in DISEASE_SPECIALTIES if name.replace(" ", "") in normalized), None)
    if matched_disease:
        specialties = DISEASE_SPECIALTIES[matched_disease]
        candidates = [
            row["name"] for row in context.get("facilities", [])
            if specialties.intersection(set(str(row.get("specialty") or "").split("|")))
        ]
        candidate_text = ", ".join(candidates[:5]) if candidates else "현재 등록 자료에서 확인되지 않음"
        return (
            f"**{matched_disease}**은(는) 일반적으로 메디웨이에서 {', '.join(sorted(specialties))} 진료과목과 연결해 검색합니다. "
            f"관련 진료과목이 등록된 후보는 {candidate_text}입니다. 이는 의료적 적합도나 진료 가능성을 보장하지 않으므로 증상과 예약 가능 여부를 기관에 확인하세요."
        )

    if any(term in normalized for term in ["금정구", "지역정보", "병원몇", "약국몇", "인구"]):
        counts = context.get("facility_counts", {})
        population = context.get("population", {})
        return (
            f"메디웨이에는 금정구 병원 **{int(counts.get('병원', 0))}곳**, 약국 **{int(counts.get('약국', 0))}곳**이 등록되어 있습니다. "
            f"금정구 인구는 {int(population.get('population', 0)):,}명, 65세 이상은 {int(population.get('elderly_population', 0)):,}명이며 "
            f"기준일은 {population.get('reference_date', '정보 없음')}입니다. 등록 시설 수는 금정구 전체 의료 공급량을 뜻하지 않습니다."
        )

    return (
        "메디웨이 상담봇은 **지역 의료기관·진료과목·운영 안내·최근 추천·거리·대중교통** 질문을 도와드릴 수 있습니다. "
        "예: `지온병원 운영시간`, `천식이면 어떤 진료과를 봐?`, `최근 추천 중 가까운 곳`, `금정구 병원은 몇 곳이야?`\n\n"
        "현재는 저장된 서비스 데이터로 답변했습니다. 일반 의료지식까지 자연어로 설명하려면 Gemini API 키를 설정할 수 있습니다."
    )


def _request_gemini(payload: dict, api_key: str, model: str, timeout: float = 20.0) -> dict:
    if not model or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in model):
        raise ChatbotError("Gemini 모델 이름이 올바르지 않습니다.")
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed Gemini HTTPS endpoint
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ChatbotError(f"AI 상담 요청이 거절되었습니다(HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ChatbotError("AI 상담 응답을 받지 못했습니다.") from exc


def extract_gemini_text(payload: dict) -> str:
    prompt_feedback = payload.get("promptFeedback") or {}
    if prompt_feedback.get("blockReason"):
        raise ChatbotError("Gemini 안전 필터로 답변이 생성되지 않았습니다.")
    texts = []
    for candidate in payload.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            if part.get("text"):
                texts.append(str(part["text"]).strip())
    if not texts:
        raise ChatbotError("AI 상담 응답에 표시할 문장이 없습니다.")
    return "\n\n".join(texts)


def ask_gemini(
    question: str,
    history: list[dict],
    context: dict,
    api_key: str,
    model: str = "gemini-3.5-flash",
    requester: Callable[[dict, str, str, float], dict] = _request_gemini,
) -> str:
    if not api_key:
        raise ChatbotError("Gemini API 키가 없습니다.")
    urgent = emergency_answer(question)
    if urgent:
        return urgent
    safe_history = [
        {
            "role": "model" if message["role"] == "assistant" else "user",
            "parts": [{"text": str(message["content"])[:1600]}],
        }
        for message in history[-6:]
        if message.get("role") in {"user", "assistant"}
    ]
    compact_context = json.dumps(context, ensure_ascii=False, default=str)[:24000]
    system_instruction = (
        "당신은 부산 금정구 의료 접근성 서비스 메디웨이의 한국어 CS 상담봇이다. "
        "제공된 서비스 데이터와 최근 추천 맥락을 우선 사용하고 없는 운영시간·거리·진료 가능 여부를 추측하지 마라. "
        "의료 질문은 일반 교육 정보와 적절한 진료과 안내까지만 제공하고 진단, 처방, 약물 용량 변경을 하지 마라. "
        "응급 가능성이 있으면 119 연락을 가장 먼저 안내하라. 추천 점수는 접근성 비교이며 의료 수준이나 치료 적합도가 아님을 명확히 하라. "
        "개인 위치의 정확한 좌표를 요구하거나 반복하지 마라. 답변은 간결하고 표나 짧은 목록을 활용하라."
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": safe_history + [{
            "role": "user",
            "parts": [{"text": f"[메디웨이 서비스 맥락]\n{compact_context}\n\n[현재 질문]\n{question}"}],
        }],
        "generationConfig": {
            "maxOutputTokens": 1200,
            "temperature": 0.3,
            "thinkingConfig": {"thinkingLevel": "minimal"},
        },
    }
    return extract_gemini_text(requester(payload, api_key, model, 20.0))
