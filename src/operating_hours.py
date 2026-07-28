"""Conservative schedule-based operating status for facilities."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd


DAY_COLUMNS = {
    0: ("mon", "월요일"),
    1: ("tue", "화요일"),
    2: ("wed", "수요일"),
    3: ("thu", "목요일"),
    4: ("fri", "금요일"),
    5: ("sat", "토요일"),
    6: ("sun", "일요일"),
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def parse_range(value: object) -> tuple[time, time] | None:
    text = clean_text(value)
    if not text or text in {"휴무", "확인 필요"}:
        return None
    try:
        start, end = [part.strip() for part in text.split("-", 1)]
        return time.fromisoformat(start), time.fromisoformat(end)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid operating-hour range: {text}") from exc


def operating_status(schedule: pd.Series | dict | None, now: datetime | None = None) -> dict[str, str]:
    """Return a non-live status based only on the stored weekly schedule."""
    if schedule is None:
        return {"code": "unknown", "label": "운영시간 확인 필요", "detail": "저장된 운영시간이 없습니다."}
    row = pd.Series(schedule)
    if clean_text(row.get("data_status")) == "unknown":
        return {"code": "unknown", "label": "운영시간 확인 필요", "detail": "공개 출처에서 운영시간을 확인하지 못했습니다."}

    current = now or datetime.now(ZoneInfo("Asia/Seoul"))
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    else:
        current = current.astimezone(ZoneInfo("Asia/Seoul"))
    day_column, day_name = DAY_COLUMNS[current.weekday()]
    today_text = clean_text(row.get(day_column))
    if today_text == "휴무":
        return {"code": "closed", "label": "오늘 휴무", "detail": f"{day_name} 정기 휴무로 표시된 시간표입니다."}
    hours = parse_range(today_text)
    if hours is None:
        return {"code": "unknown", "label": "오늘 운영 확인 필요", "detail": f"{day_name} 운영시간이 확인되지 않았습니다."}

    current_time = current.time().replace(tzinfo=None)
    lunch = parse_range(row.get("lunch"))
    if lunch and lunch[0] <= current_time < lunch[1]:
        return {"code": "lunch", "label": "점심시간", "detail": f"시간표 기준 {clean_text(row.get('lunch'))} 휴게시간입니다."}
    if hours[0] <= current_time < hours[1]:
        return {"code": "open", "label": "진료 중 · 시간표 기준", "detail": f"오늘 {today_text}로 표시되어 있습니다."}
    return {"code": "closed", "label": "현재 진료시간 아님", "detail": f"오늘 시간표는 {today_text}입니다."}


def today_schedule(schedule: pd.Series | dict, now: datetime | None = None) -> tuple[str, str]:
    current = now or datetime.now(ZoneInfo("Asia/Seoul"))
    if current.tzinfo is not None:
        current = current.astimezone(ZoneInfo("Asia/Seoul"))
    day_column, day_name = DAY_COLUMNS[current.weekday()]
    return day_name, clean_text(pd.Series(schedule).get(day_column)) or "확인 필요"
