"""Browser geolocation component for Streamlit."""

from __future__ import annotations

from typing import Any

import streamlit as st


_LOCATION_HTML = """
<div class="location-control">
  <button type="button" class="location-button">◎ 현재 위치 받기</button>
  <div class="location-status" aria-live="polite">위치 권한을 허용하면 실제 출발지로 계산합니다.</div>
</div>
"""

_LOCATION_CSS = """
.location-control { font-family: var(--st-font); width: 100%; }
.location-button {
  width: 100%; min-height: 2.5rem; border: 1px solid var(--st-primary-color);
  border-radius: .65rem; background: transparent; color: var(--st-text-color);
  font-weight: 700; cursor: pointer;
}
.location-button:hover { background: color-mix(in srgb, var(--st-primary-color) 12%, transparent); }
.location-button:disabled { opacity: .65; cursor: wait; }
.location-status { margin-top: .4rem; color: var(--st-text-color); opacity: .72; font-size: .78rem; line-height: 1.35; }
"""

_LOCATION_JS = """
export default function(component) {
  const { setStateValue, parentElement, data } = component;
  const button = parentElement.querySelector('.location-button');
  const status = parentElement.querySelector('.location-status');
  const saved = data.location;

  if (saved && saved.error) {
    status.textContent = saved.error;
  } else if (saved && saved.latitude != null && saved.longitude != null) {
    button.textContent = '↻ 현재 위치 다시 받기';
    const accuracy = saved.accuracy ? ` · 정확도 약 ${Math.round(saved.accuracy)}m` : '';
    status.textContent = `현재 위치가 적용되었습니다${accuracy}`;
  }

  button.onclick = () => {
    if (!navigator.geolocation) {
      status.textContent = '이 브라우저는 위치 기능을 지원하지 않습니다.';
      return;
    }
    button.disabled = true;
    status.textContent = '현재 위치를 확인하고 있습니다…';
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setStateValue('location', {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          captured_at: Date.now(),
          error: null,
        });
      },
      (error) => {
        const messages = {
          1: '위치 권한이 거부되었습니다. 브라우저 설정에서 허용해 주세요.',
          2: '현재 위치를 확인할 수 없습니다.',
          3: '위치 확인 시간이 초과되었습니다. 다시 시도해 주세요.',
        };
        const message = messages[error.code] || '위치 확인 중 오류가 발생했습니다.';
        setStateValue('location', { error: message });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  };
}
"""

def _location_component():
    """Register in the active Streamlit app/test context."""
    return st.components.v2.component(
        "mediway_browser_geolocation",
        html=_LOCATION_HTML,
        css=_LOCATION_CSS,
        js=_LOCATION_JS,
    )


def _validated_location(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        latitude = float(value.get("latitude"))
        longitude = float(value.get("longitude"))
        accuracy = max(0.0, float(value.get("accuracy") or 0))
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {
        "latitude": round(latitude, 5),
        "longitude": round(longitude, 5),
        "accuracy": round(accuracy, 0),
    }


def browser_location(key: str = "mediway_browser_location") -> dict[str, float] | None:
    """Render the permission control and return a validated browser location."""
    stored = st.session_state.get(key, {})
    current = stored.get("location") if isinstance(stored, dict) else None
    result = _location_component()(
        data={"location": current},
        default={"location": current},
        key=key,
        on_location_change=lambda: None,
        height=78,
    )
    return _validated_location(getattr(result, "location", None))
