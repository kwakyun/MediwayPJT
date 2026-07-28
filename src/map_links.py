"""Build short, reliable search queries for external map services."""

from __future__ import annotations

import re


def compact_map_query(name: object, address: object) -> str:
    """Return facility name plus administrative area, excluding detailed address."""
    facility = " ".join(str(name or "").split())
    location = " ".join(str(address or "").split())
    parts = [facility]

    city_match = re.search(r"(?:^|\s)(부산광역시|부산시|부산)(?:\s|$)", location)
    if city_match:
        parts.append("부산")

    district_match = re.search(r"(?:^|\s)([가-힣]+구)(?:\s|$)", location)
    if district_match:
        parts.append(district_match.group(1))

    parenthesized_dong = re.search(r"\(([가-힣0-9]+동)(?:[,\s)]|$)", location)
    plain_dong = re.search(r"(?:^|\s)([가-힣0-9]+동)(?:[,\s]|$)", location)
    dong_match = parenthesized_dong or plain_dong
    if dong_match:
        parts.append(dong_match.group(1))

    return " ".join(dict.fromkeys(part for part in parts if part))
