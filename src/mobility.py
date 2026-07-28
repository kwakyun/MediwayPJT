"""Optional public-transit route estimates from ODsay."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MobilityError(RuntimeError):
    """Raised when the transit provider cannot return a usable route."""


def _request_json(url: str, headers: dict[str, str], timeout: float = 6.0) -> dict:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed HTTPS provider URL
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise MobilityError(f"대중교통 API 요청이 거절되었습니다(HTTP {exc.code}).") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise MobilityError("대중교통 API 응답을 받지 못했습니다.") from exc


def _walk_minutes(path: dict) -> float:
    info = path.get("info") or {}
    if info.get("totalWalkTime") is not None:
        return max(0.0, float(info.get("totalWalkTime") or 0))
    return max(0.0, sum(
        float(section.get("sectionTime", 0) or 0)
        for section in path.get("subPath", [])
        if int(section.get("trafficType", 0) or 0) == 3
    ))


def _route_label(path_type: int) -> str:
    return {1: "지하철", 2: "버스", 3: "버스+지하철"}.get(path_type, "대중교통")


def parse_odsay_response(payload: dict, limit: int = 3) -> list[dict]:
    error = payload.get("error")
    if error:
        message = error.get("msg") if isinstance(error, dict) else str(error)
        raise MobilityError(f"ODsay 경로 조회 실패: {message or '알 수 없는 오류'}")
    paths = (payload.get("result") or {}).get("path") or []
    if not paths:
        raise MobilityError("이용 가능한 버스·지하철 경로를 찾지 못했습니다.")
    estimates = []
    for path in paths[:limit]:
        info = path.get("info") or {}
        total = max(0.0, float(info.get("totalTime", 0) or 0))
        outdoor = min(total, _walk_minutes(path))
        estimates.append({
            "provider": "ODsay",
            "status": "live",
            "route_type": _route_label(int(path.get("pathType", 0) or 0)),
            "total_minutes": round(total, 1),
            "outdoor_minutes": round(outdoor, 1),
            "transit_minutes": round(max(0.0, total - outdoor), 1),
            "fare": int(info.get("payment", 0) or 0),
            "bus_transfers": int(info.get("busTransitCount", 0) or 0),
            "subway_transfers": int(info.get("subwayTransitCount", 0) or 0),
            "total_walk_meters": int(float(info.get("totalWalk", 0) or 0)),
            "first_station": str(info.get("firstStartStation") or "정보 없음"),
            "last_station": str(info.get("lastEndStation") or "정보 없음"),
            "captured_at": datetime.now().astimezone().isoformat(timespec="minutes"),
        })
    return estimates


def fetch_odsay_transit(
    origin: tuple[float, float], destination: tuple[float, float], api_key: str,
    path_type: int = 0, requester: Callable[[str, dict[str, str], float], dict] = _request_json,
) -> list[dict]:
    if not api_key:
        raise MobilityError("ODsay Server API 키가 없습니다.")
    start_lat, start_lon = origin
    goal_lat, goal_lon = destination
    query = urlencode({
        "SX": start_lon, "SY": start_lat, "EX": goal_lon, "EY": goal_lat,
        "OPT": 0, "SearchType": 0, "SearchPathType": path_type, "apiKey": api_key,
        "lang": 0, "output": "json",
    })
    payload = requester(
        f"https://api.odsay.com/v1/api/searchPubTransPathT?{query}",
        {"Content-Type": "application/json"},
        6.0,
    )
    return parse_odsay_response(payload)


def transport_options(
    walking_minutes: float, walking_outdoor_minutes: float, estimates: list[dict] | None = None,
) -> list[dict]:
    rows = [{
        "이동수단": "도보", "총 소요시간": round(float(walking_minutes), 1),
        "대중교통시간": 0.0, "야외시간": round(float(walking_outdoor_minutes), 1),
        "예상 요금": 0, "버스 환승": 0, "지하철 환승": 0, "도보거리(m)": 0,
        "승차": "-", "하차": "-", "데이터": "저장된 보행경로",
    }]
    for estimate in estimates or []:
        if estimate.get("status") != "live":
            continue
        rows.append({
            "이동수단": estimate.get("route_type", "대중교통"),
            "총 소요시간": round(float(estimate.get("total_minutes", 0)), 1),
            "대중교통시간": round(float(estimate.get("transit_minutes", 0)), 1),
            "야외시간": round(float(estimate.get("outdoor_minutes", 0)), 1),
            "예상 요금": int(estimate.get("fare", 0)),
            "버스 환승": int(estimate.get("bus_transfers", 0)),
            "지하철 환승": int(estimate.get("subway_transfers", 0)),
            "도보거리(m)": int(estimate.get("total_walk_meters", 0)),
            "승차": estimate.get("first_station", "정보 없음"),
            "하차": estimate.get("last_station", "정보 없음"),
            "데이터": "ODsay 대중교통",
        })
    return rows
