"""Mediway Streamlit dashboard."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.scenarios import DISEASE_GROUPS, REFERENCE_LOCATIONS, REFERENCE_ORIGIN_IDS, SCENARIOS
from src.scoring import WEIGHTS, format_duration, recommend
from src.operating_hours import operating_status, today_schedule
from src.mobility import MobilityError, fetch_odsay_transit, transport_options
from src.map_links import compact_map_query
from src.geolocation import browser_location
from src.chatbot import ChatbotError, ask_gemini, build_service_context, local_cs_answer


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

st.set_page_config(page_title="메디웨이", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    :root {
      --navy-950:#0B1628; --navy-900:#10233F; --navy-800:#183153;
      --blue-600:#2563EB; --blue-500:#3B82F6; --teal-600:#0F8B8D;
      --slate-700:#334155; --slate-600:#475569; --slate-500:#64748B;
      --slate-300:#CBD5E1; --slate-200:#E2E8F0; --slate-100:#F1F5F9;
      --slate-50:#F8FAFC; --white:#FFFFFF; --success:#15803D; --warning:#B45309;
      --radius-sm:10px; --radius-md:16px; --radius-lg:22px;
      --shadow-sm:0 1px 2px rgba(15,23,42,.04),0 4px 14px rgba(15,23,42,.05);
      --shadow-md:0 16px 40px rgba(15,23,42,.09);
    }
    .stApp {color:var(--navy-950);background:var(--slate-50);}
    .block-container {max-width:1480px;padding-top:2rem;padding-bottom:4rem;}
    [data-testid="stSidebar"] {background:var(--white);color:var(--navy-950);border-right:1px solid var(--slate-200);}
    [data-testid="stSidebar"] > div:first-child {padding-top:1.4rem;}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {color:var(--navy-950) !important;}
    [data-testid="stSidebar"] .stButton button p {color:inherit !important;}
    h1 {font-size:2.25rem !important;letter-spacing:-.04em;color:var(--navy-950) !important;}
    h2 {font-size:1.55rem !important;letter-spacing:-.025em;color:var(--navy-950) !important;}
    h3 {font-size:1.12rem !important;color:var(--navy-900) !important;}
    p, li, label {font-size:1rem;color:var(--slate-700);}
    [data-testid="stHeader"] {background:rgba(248,250,252,.86);backdrop-filter:blur(12px);}
    .sidebar-brand {padding:.25rem 0 1rem;border-bottom:1px solid var(--slate-200);margin-bottom:1rem;}
    .sidebar-brand strong {display:block;font-size:1.3rem;color:var(--navy-950);letter-spacing:-.03em;}
    .sidebar-brand span {font-size:.82rem;color:var(--slate-500);}
    .app-header {padding:1.55rem 1.65rem;border-radius:var(--radius-lg);background:linear-gradient(135deg,var(--navy-950),var(--navy-800));box-shadow:var(--shadow-md);margin-bottom:1.25rem;}
    .app-header .eyebrow {font-size:.78rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase;color:#93C5FD;margin-bottom:.45rem;}
    .app-header h1 {color:#FFF !important;margin:0 0 .45rem;font-size:2.25rem !important;}
    .app-header p {color:#CBD5E1;margin:0;max-width:850px;font-size:1.02rem;}
    .service-badge {display:inline-flex;align-items:center;padding:.28rem .65rem;border-radius:999px;background:#DBEAFE;color:#1D4ED8;font-weight:750;font-size:.78rem;border:1px solid #BFDBFE;}
    .section-heading {margin:1.65rem 0 .8rem;}
    .section-heading .kicker {font-size:.76rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--blue-600);}
    .section-heading h2 {margin:.15rem 0 .1rem !important;}
    .section-heading p {color:var(--slate-500);margin:0;font-size:.92rem;}
    .filter-summary {padding:1rem 1.1rem;background:var(--white);border:1px solid var(--slate-200);border-radius:var(--radius-md);box-shadow:var(--shadow-sm);}
    .filter-summary strong {color:var(--navy-950);}
    .filter-pill {display:inline-block;margin:.25rem .25rem 0 0;padding:.32rem .62rem;border-radius:999px;background:var(--slate-100);border:1px solid var(--slate-200);color:var(--slate-700);font-size:.82rem;font-weight:650;}
    .hero {padding:1.5rem 1.6rem;border:1px solid #BFDBFE;border-radius:var(--radius-lg);background:linear-gradient(135deg,#FFFFFF,#EFF6FF);box-shadow:var(--shadow-md);}
    .hero-kicker {font-weight:800;color:var(--blue-600);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;}
    .hero-name {font-weight:850;font-size:2rem;line-height:1.2;margin:.35rem 0;color:var(--navy-950);}
    .hero-score {font-size:2.8rem;font-weight:900;color:var(--blue-600);font-variant-numeric:tabular-nums;}
    .hero-distance {font-size:1.2rem;font-weight:750;margin-left:1rem;color:var(--slate-700);}
    .hero-reason {font-size:.98rem;margin:.3rem 0;color:var(--slate-700);}
    .result-card {padding:1.05rem 1.15rem;border:1px solid var(--slate-200);border-radius:var(--radius-md);background:var(--white);margin-bottom:.75rem;box-shadow:var(--shadow-sm);transition:transform .15s ease,box-shadow .15s ease;}
    .result-card:hover {transform:translateY(-1px);box-shadow:0 8px 22px rgba(15,23,42,.08);}
    .result-card.first {border:1px solid #93C5FD;background:linear-gradient(135deg,#FFF,#F0F7FF);}
    .rank {font-size:1.08rem;font-weight:850;color:var(--blue-600);}
    .score {font-size:1.55rem;font-weight:900;color:var(--navy-950);float:right;font-variant-numeric:tabular-nums;}
    .card-meta {display:flex;flex-wrap:wrap;gap:.4rem;margin:.75rem 0 .65rem;}
    .meta-chip {display:inline-flex;align-items:center;padding:.26rem .55rem;border-radius:8px;background:var(--slate-100);color:var(--slate-700);font-size:.84rem;font-weight:750;}
    .meta-chip.fare {background:#DBEAFE;color:#1D4ED8;border:1px solid #BFDBFE;}
    .card-row {display:grid;grid-template-columns:3.6rem 1fr;gap:.45rem;margin:.34rem 0;line-height:1.45;}
    .card-label {color:var(--slate-500);font-size:.78rem;font-weight:800;letter-spacing:.04em;}
    .card-value {color:var(--slate-700);font-size:.9rem;}
    .card-reason {margin-top:.65rem;padding-top:.6rem;border-top:1px solid var(--slate-200);color:var(--slate-700);font-size:.9rem;}
    .notice {padding:1rem 1.1rem;background:#FFFBEB;border:1px solid #FDE68A;border-radius:var(--radius-md);color:#78350F;}
    .transport-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.85rem;align-items:stretch;}
    .transport-card {display:flex;flex-direction:column;min-height:260px;padding:1.1rem 1.15rem;background:var(--white);border:1px solid var(--slate-200);border-radius:var(--radius-md);box-shadow:var(--shadow-sm);}
    .transport-card.live {border-color:#93C5FD;background:linear-gradient(145deg,var(--white),#EFF6FF);}
    .transport-card-head {display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin-bottom:.9rem;}
    .transport-mode {display:flex;align-items:center;gap:.55rem;font-size:1.05rem;font-weight:850;color:var(--navy-950);}
    .transport-icon {display:inline-grid;place-items:center;width:2rem;height:2rem;border-radius:10px;background:var(--slate-100);font-size:1.05rem;}
    .transport-badge {padding:.23rem .5rem;border-radius:999px;background:var(--slate-100);color:var(--slate-600);font-size:.7rem;font-weight:800;letter-spacing:.03em;white-space:nowrap;}
    .transport-card.live .transport-badge {background:#DBEAFE;color:#1D4ED8;}
    .transport-primary {display:grid;grid-template-columns:1fr auto;gap:1rem;align-items:end;padding-bottom:.9rem;border-bottom:1px solid var(--slate-200);}
    .transport-primary-label {display:block;color:var(--slate-500);font-size:.74rem;font-weight:800;letter-spacing:.05em;margin-bottom:.15rem;}
    .transport-time {font-size:2rem;font-weight:900;line-height:1;color:var(--navy-950);font-variant-numeric:tabular-nums;}
    .transport-fare {text-align:right;}
    .transport-fare strong {display:block;font-size:1.45rem;line-height:1.1;color:var(--blue-600);font-weight:900;font-variant-numeric:tabular-nums;}
    .transport-details {display:grid;grid-template-columns:repeat(3,1fr);gap:.45rem;margin-top:.85rem;}
    .transport-detail {padding:.55rem .5rem;border-radius:10px;background:var(--slate-100);}
    .transport-detail span {display:block;color:var(--slate-500);font-size:.68rem;font-weight:800;margin-bottom:.1rem;}
    .transport-detail strong {display:block;color:var(--navy-950);font-size:.88rem;font-weight:850;white-space:nowrap;}
    .transport-route {margin-top:auto;padding-top:.8rem;color:var(--slate-600);font-size:.8rem;line-height:1.4;}
    .transport-route strong {color:var(--navy-900);}
    .insight-card {min-height:128px;padding:1rem 1.05rem;background:var(--white);border:1px solid var(--slate-200);border-radius:var(--radius-md);box-shadow:var(--shadow-sm);}
    .insight-card .label {font-size:.76rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--slate-500);}
    .insight-card .value {font-size:1.35rem;font-weight:850;color:var(--navy-950);margin:.3rem 0;}
    .insight-card .body {font-size:.88rem;color:var(--slate-600);}
    div[data-testid="stMetric"] {background:var(--white);border:1px solid var(--slate-200);padding:1rem 1.05rem;border-radius:var(--radius-md);box-shadow:var(--shadow-sm);}
    div[data-testid="stMetricValue"] {font-size:1.8rem;}
    [data-testid="stMetricLabel"] *,
    [data-testid="stMetricValue"] * {color:var(--navy-950) !important;}
    [data-testid="stMetricDelta"] * {color:var(--success) !important;}
    .stButton > button {border-radius:10px;font-weight:750;min-height:2.8rem;border:1px solid var(--slate-300);}
    .stButton > button[kind="primary"] {background:var(--blue-600);border-color:var(--blue-600);box-shadow:0 6px 16px rgba(37,99,235,.2);}
    [data-baseweb="tab-list"] {gap:.35rem;background:var(--slate-100);padding:.3rem;border-radius:12px;}
    [data-baseweb="tab"] {height:2.7rem;border-radius:9px;padding:0 1rem;}
    [data-baseweb="tab"][aria-selected="true"] {background:#FFF;box-shadow:var(--shadow-sm);}
    [data-testid="stExpander"] {background:var(--white);border:1px solid var(--slate-200);border-radius:12px !important;box-shadow:none;}
    @media (prefers-color-scheme: dark) {
      :root {--navy-950:#F8FAFC;--navy-900:#E2E8F0;--navy-800:#CBD5E1;--slate-700:#D7E0EA;--slate-600:#B8C5D4;--slate-500:#94A3B8;--slate-300:#475569;--slate-200:#334155;--slate-100:#1E293B;--slate-50:#0F172A;--white:#111C2E;}
      [data-testid="stHeader"] {background:rgba(15,23,42,.86);}
      .app-header {background:linear-gradient(135deg,#07111F,#102A43);}
      .hero,.result-card.first,.transport-card.live {background:linear-gradient(135deg,#111C2E,#10243B);border-color:#2563EB;}
      .meta-chip.fare {background:#172554;color:#BFDBFE;border-color:#1D4ED8;}
      .notice {background:#2A2112;border-color:#854D0E;color:#FDE68A;}
      [data-baseweb="tab"][aria-selected="true"] {background:#111C2E;}
      div[data-testid="stDataFrame"], .js-plotly-plot {color-scheme:dark;}
    }
    @media (max-width:1366px) {.block-container{padding-top:1.5rem}.app-header h1{font-size:1.9rem !important}.hero-score{font-size:2.25rem}.hero-name{font-size:1.6rem}}
    @media (max-width:768px) {.block-container{padding:1rem}.app-header{padding:1.2rem}.hero{padding:1.15rem}.hero-distance{display:block;margin:.25rem 0 0}.filter-pill{font-size:.75rem}.transport-grid{grid-template-columns:1fr}.transport-card{min-height:auto}.transport-time{font-size:1.75rem}}
    </style>
    """,
    unsafe_allow_html=True,
)


def render_page_header(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="app-header"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>',
        unsafe_allow_html=True,
    )


def render_section_heading(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="section-heading"><div class="kicker">{kicker}</div><h2>{title}</h2><p>{description}</p></div>',
        unsafe_allow_html=True,
    )


def compact_specialties(value: object, limit: int = 3) -> str:
    """Return a short, scannable specialty label without losing the total scope."""
    items = [item.strip() for item in str(value or "").split("|") if item.strip()]
    if not items:
        return "정보 없음"
    shown = " · ".join(items[:limit])
    return f"{shown} 외 {len(items) - limit}개" if len(items) > limit else shown


def distinctive_reason(reasons: object) -> str:
    """Choose one reason that does not repeat route time or the generic comparison label."""
    excluded = ("예상 이동", "진료과목과 이동 조건을 함께 비교한 후보입니다")
    for reason in list(reasons or []):
        if not any(text in str(reason) for text in excluded):
            return str(reason)
    return "세부 점수와 운영정보는 아래 상세 보기에서 확인할 수 있습니다."


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, ...]:
    return (
        pd.read_csv(DATA / "facilities.csv"),
        pd.read_csv(DATA / "weather.csv"),
        pd.read_csv(DATA / "air_quality.csv"),
        pd.read_csv(DATA / "population.csv"),
        pd.read_csv(DATA / "operating_hours.csv"),
        pd.read_csv(DATA / "facility_accessibility.csv"),
        pd.read_csv(DATA / "walking_routes.csv"),
        pd.read_csv(DATA / "clinical_condition_inputs.csv"),
        pd.read_csv(DATA / "facility_accessibility_inputs.csv"),
    )


def environment_for(scenario_id: str, weather: pd.DataFrame, air: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    return (
        weather.loc[weather["scenario_id"] == scenario_id].iloc[0],
        air.loc[air["scenario_id"] == scenario_id].iloc[0],
    )


def _secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def cached_transit_estimates(
    origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float,
    api_key: str, path_type: int,
) -> list[dict]:
    return fetch_odsay_transit(
        (origin_lat, origin_lon), (destination_lat, destination_lon), api_key, path_type=path_type
    )


def format_won(value: object) -> str:
    amount = int(float(value or 0))
    return "정보 없음" if amount <= 0 else f"약 {amount:,}원"


def render_transport_summary(
    top: pd.Series, estimates: list[dict] | None, transit_requested: bool = False,
) -> None:
    render_section_heading(
        "MOBILITY", "도보·버스·지하철 시간과 요금", "총시간을 대중교통·대기시간과 야외 도보시간으로 분리합니다."
    )
    rows = transport_options(top["travel_minutes"], top["outdoor_minutes"], estimates)
    display_rows = rows[:3]
    cards = []
    for row in display_rows:
        is_walking = row["이동수단"] == "도보"
        mode_icon = "🚶" if is_walking else ("🚇" if row["이동수단"] == "지하철" else "🚌")
        badge = "저장 경로" if is_walking else "ODsay 실시간"
        card_class = "transport-card" if is_walking else "transport-card live"
        fare = "0원" if is_walking else format_won(row["예상 요금"])
        transfer_count = int(row["버스 환승"]) + int(row["지하철 환승"])
        third_label = "거리" if is_walking else "총 환승"
        third_value = f"{top['distance_km']:.1f}km" if is_walking else f"{transfer_count}회"
        if is_walking:
            route_text = "별도 승차 없이 목적지까지 이동하는 저장된 보행경로입니다."
        else:
            first_station = escape(str(row.get("승차") or "출발지 인근"))
            last_station = escape(str(row.get("하차") or "도착지 인근"))
            walk_meters = int(row.get("도보거리(m)", 0) or 0)
            route_text = f"<strong>{first_station}</strong> → <strong>{last_station}</strong> · 경로 내 도보 {walk_meters:,}m"
        cards.append(
            f"""
            <div class="{card_class}">
              <div class="transport-card-head">
                <div class="transport-mode"><span class="transport-icon">{mode_icon}</span>{escape(str(row['이동수단']))}</div>
                <span class="transport-badge">{badge}</span>
              </div>
              <div class="transport-primary">
                <div><span class="transport-primary-label">총 소요시간</span><strong class="transport-time">{format_duration(row['총 소요시간'])}</strong></div>
                <div class="transport-fare"><span class="transport-primary-label">예상 요금</span><strong>{fare}</strong></div>
              </div>
              <div class="transport-details">
                <div class="transport-detail"><span>교통·대기</span><strong>{format_duration(row['대중교통시간'])}</strong></div>
                <div class="transport-detail"><span>야외 도보</span><strong>{format_duration(row['야외시간'])}</strong></div>
                <div class="transport-detail"><span>{third_label}</span><strong>{third_value}</strong></div>
              </div>
              <div class="transport-route">{route_text}</div>
            </div>
            """
        )
    st.html(f'<div class="transport-grid">{"".join(cards)}</div>')
    if estimates:
        captured_at = estimates[0]["captured_at"]
        st.caption(
            f"ODsay 조회 {captured_at} · 야외시간은 대중교통 경로의 도보 구간 합계입니다. "
            "총시간에는 도보·탑승·환승·대기 시간이 포함될 수 있으며 요금은 실제 결제액과 다를 수 있습니다."
        )
    elif transit_requested:
        st.warning("실시간 대중교통 경로를 불러오지 못해 현재는 저장된 도보 경로만 표시합니다. 아래 실패 기관에서 상세 원인을 확인하세요.")
    else:
        st.info("ODsay Server API 키를 설정하면 버스·지하철 시간, 요금, 환승과 야외 도보시간을 비교할 수 있습니다.")


def result_map(
    result: pd.DataFrame, user_latitude: float, user_longitude: float, user_location_name: str,
) -> go.Figure:
    plot = result.copy()
    plot["travel_label"] = plot["travel_minutes"].map(format_duration)
    plot["outdoor_label"] = plot["outdoor_minutes"].map(format_duration)
    # Small visual offsets separate facilities that share a building/road-centre geocode.
    duplicate_order = plot.groupby(["latitude", "longitude"]).cumcount()
    plot["map_latitude"] = plot["latitude"] + duplicate_order * 0.00018
    plot["map_longitude"] = plot["longitude"] + duplicate_order * 0.00018
    line_latitudes: list[float | None] = []
    line_longitudes: list[float | None] = []
    for row in plot.to_dict("records"):
        line_latitudes.extend([user_latitude, row["map_latitude"], None])
        line_longitudes.extend([user_longitude, row["map_longitude"], None])

    figure = go.Figure()
    figure.add_trace(
        go.Scattermap(
            lat=line_latitudes,
            lon=line_longitudes,
            mode="lines",
            line={"color": "#94A3B8", "width": 1.5},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scattermap(
            lat=plot["map_latitude"],
            lon=plot["map_longitude"],
            mode="markers+text",
            text=[f"#{rank}" for rank in plot["rank"]],
            textposition="middle center",
            textfont={"color": "white", "size": 12, "weight": 700},
            marker={"size": 34, "color": "#2563EB", "opacity": 0.96},
            customdata=plot[["name", "final_score", "travel_label", "outdoor_label", "distance_km", "address"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:.1f}점 · 이동 %{customdata[2]} · 야외 %{customdata[3]}<br>경로거리 %{customdata[4]:.2f}km<br>%{customdata[5]}<extra></extra>",
            name="추천 시설 (#순위)",
        )
    )
    figure.add_trace(
        go.Scattermap(
            lat=[user_latitude],
            lon=[user_longitude],
            mode="markers",
            marker={"size": 42, "color": "#14B8A6", "opacity": 0.3},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scattermap(
            lat=[user_latitude],
            lon=[user_longitude],
            mode="markers+text",
            text=[f"내 출발 위치<br>{user_location_name}"],
            textposition="top center",
            textfont={"color": "#0F172A", "size": 13, "weight": 700},
            marker={"size": 20, "color": "#0F172A"},
            hovertemplate=f"<b>내 출발 위치</b><br>{escape(user_location_name)}<extra></extra>",
            name="내 출발 위치",
        )
    )
    all_longitudes = list(plot["map_longitude"]) + [user_longitude]
    all_latitudes = list(plot["map_latitude"]) + [user_latitude]
    span = max(max(all_longitudes) - min(all_longitudes), max(all_latitudes) - min(all_latitudes))
    zoom = 14.0 if span < 0.012 else 13.0 if span < 0.025 else 12.0 if span < 0.05 else 11.2
    figure.update_layout(
        height=560,
        margin={"l": 0, "r": 0, "t": 52, "b": 0},
        title={"text": "내 위치와 추천 시설", "x": 0.02, "font": {"size": 18, "color": "#0F172A"}},
        map={
            "style": "open-street-map",
            "center": {"lat": sum(all_latitudes) / len(all_latitudes), "lon": sum(all_longitudes) / len(all_longitudes)},
            "zoom": zoom,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        legend={
            "orientation": "h", "x": 0.02, "y": 1.01,
            "bgcolor": "rgba(255,255,255,0.92)", "font": {"color": "#334155"},
        },
    )
    return figure


def render_operating_info(facility: dict, schedules: pd.DataFrame) -> None:
    matched = schedules.loc[schedules["facility_id"] == facility["facility_id"]]
    schedule = None if matched.empty else matched.iloc[0]
    status = operating_status(schedule)
    phone = str(facility.get("phone") or "").strip()
    published = str(schedule.get("schedule_text") or "").strip() if schedule is not None else ""
    has_published = bool(published and published.lower() != "nan" and "미확인" not in published)

    if schedule is None or str(schedule.get("data_status", "")) == "unknown":
        if has_published:
            st.info(f"공개된 운영 안내 — {published}")
            source_url = str(schedule.get("source_url") or "").strip()
            if source_url and source_url.lower() != "nan":
                st.markdown(f"[운영정보 출처 확인]({source_url})")
            st.caption("공개 안내는 변경될 수 있으므로 방문 전에 확인하세요.")
        elif phone:
            st.info(f"운영시간 문의: {phone}")
        else:
            st.info("운영시간은 해당 기관에 직접 확인해 주세요.")
        return

    message = {
        "open": st.success,
        "lunch": st.warning,
        "closed": st.info,
        "unknown": st.warning,
    }[status["code"]]
    message(f"{status['label']} — {status['detail']}")

    day_name, today_text = today_schedule(schedule)
    st.markdown(
        f"**오늘({day_name}) 진료시간:** {today_text}  \n"
        f"**점심시간:** {schedule.get('lunch') or '확인 필요'}  \n"
        f"**공휴일:** {schedule.get('holiday') or '확인 필요'}"
    )
    st.caption(
        "정규 시간표로 계산한 참고 상태이며 접수 마감·임시 휴진·진료과별 시간은 다를 수 있습니다. "
        f"확인일 {schedule.get('verified_date', '정보 없음')} · 방문 전 {facility.get('phone', '기관')}에 확인하세요."
    )
    source_name = str(schedule.get("source_name") or "출처 정보 없음")
    source_url = str(schedule.get("source_url") or "")
    source_level = "공식" if schedule.get("source_level") == "official" else "외부 참고"
    if source_url:
        st.markdown(f"출처({source_level}): [{source_name}]({source_url})")
    else:
        st.write(f"출처({source_level}): {source_name}")


def render_recommendation(
    facilities: pd.DataFrame, weather: pd.DataFrame, air: pd.DataFrame, schedules: pd.DataFrame,
    accessibility: pd.DataFrame, routes: pd.DataFrame, clinical_inputs: pd.DataFrame,
    accessibility_inputs: pd.DataFrame,
) -> None:
    render_page_header(
        "MEDIWAY ACCESSIBILITY INTELLIGENCE",
        "내 조건에 맞는 병원·약국 찾기",
        "질환별 진료 조건, 예상 이동·야외 노출, 시설 접근성을 분리해 비교하고 실제 길찾기로 연결합니다.",
    )

    scenario_labels = list(SCENARIOS)
    if "scenario_index" not in st.session_state:
        st.session_state.scenario_index = 0
    with st.sidebar:
        st.markdown("### 검색 설정")
        st.caption("프리셋을 선택하거나 세부 조건을 직접 조정하세요.")
        scenario_label = st.selectbox(
            "빠른 조건 설정",
            scenario_labels,
            index=st.session_state.scenario_index,
            help="자주 찾는 조건을 불러온 뒤 위치와 건강 정보를 직접 바꿀 수 있습니다.",
        )
        st.session_state.scenario_index = scenario_labels.index(scenario_label)
        scenario = SCENARIOS[scenario_label]
        scenario_id = scenario["scenario_id"]
        st.caption("질환 정보는 이동 접근성 비교에만 사용되며 진단이나 치료 판단에 사용하지 않습니다.")

        location_names = list(REFERENCE_LOCATIONS)
        location_name = st.selectbox(
            "기준 위치",
            location_names,
            index=location_names.index(scenario["location_name"]),
            key=f"location_{scenario_id}",
        )
        live_location = browser_location()
        use_live_location = bool(live_location) and st.toggle(
            "현재 위치를 추천 기준으로 사용", value=True,
            help="끄면 위에서 선택한 생활권 위치로 돌아갑니다.",
        )
        if live_location:
            st.caption(f"위치 정확도 약 {live_location['accuracy']:.0f}m · 실제 좌표는 화면에 공개하지 않습니다.")
        basic_options = ["일반 성인", "고령자", "보행·이동 취약자"]
        basic_type = st.selectbox(
            "기본 특성", basic_options, index=basic_options.index(scenario["basic_type"]), key=f"basic_{scenario_id}"
        )
        group_names = list(DISEASE_GROUPS)
        preset_groups = [
            group
            for group, values in DISEASE_GROUPS.items()
            if any(disease in values for disease in scenario["selected_diseases"])
        ]
        selected_groups = st.multiselect(
            "질환군(복수 선택)",
            group_names,
            default=preset_groups,
            placeholder="선택 안 함",
            key=f"groups_{scenario_id}",
        )
        disease_options = [
            disease
            for group in selected_groups
            for disease in DISEASE_GROUPS[group]
        ]
        default_diseases = [value for value in scenario["selected_diseases"] if value in disease_options]
        selected_diseases = st.multiselect(
            "세부 질환(복수 선택)",
            disease_options,
            default=default_diseases,
            placeholder="선택 안 함",
            key=f"diseases_{scenario_id}_{'_'.join(selected_groups) or 'none'}",
        )
        facility_type = st.radio(
            "시설 유형", ["병원", "약국"], index=0 if scenario["facility_type"] == "병원" else 1, horizontal=True,
            key=f"facility_{scenario_id}"
        )
        st.markdown("### 이동 정보")
        odsay_api_key = _secret("ODSAY_API_KEY")
        transit_enabled = bool(odsay_api_key) and st.toggle(
            "버스·지하철 경로 비교", value=True,
            help="ODsay가 제공하는 대중교통 경로의 시간·요금·환승·도보 구간을 비교합니다.",
        )
        transit_priority = st.radio(
            "우선 교통수단", ["추천", "지하철", "버스"], horizontal=True,
            disabled=not transit_enabled,
        )
        transit_path_type = {"추천": 0, "지하철": 1, "버스": 2}[transit_priority]
        if not odsay_api_key:
            st.caption("ODsay Server API 키를 설정하면 버스·지하철 시간과 요금 비교가 활성화됩니다.")
        st.markdown("---")
        run = st.button("추천 결과 보기", type="primary", width="stretch", icon="🔎")
        if st.button("검색 조건 초기화", width="stretch"):
            st.session_state.scenario_index = 0
            st.rerun()

    weather_row, air_row = environment_for(scenario_id, weather, air)
    latitude, longitude = REFERENCE_LOCATIONS[location_name]
    origin_id = REFERENCE_ORIGIN_IDS.get(location_name)
    active_location_name = location_name
    if use_live_location and live_location:
        latitude = live_location["latitude"]
        longitude = live_location["longitude"]
        origin_id = None
        active_location_name = "현재 위치"

    render_section_heading("OVERVIEW", "현재 환경 요약", "추천 계산에 반영되는 환경 데이터와 비교 후보를 확인하세요.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("날씨", f"{weather_row['weather_status']} {weather_row['temperature']:.0f}°C", f"강수 {weather_row['rainfall']:.0f}mm")
    c2.metric("PM10", f"{air_row['pm10']:.0f} µg/m³", air_row["air_grade"])
    c3.metric("PM2.5", f"{air_row['pm25']:.0f} µg/m³", air_row["air_grade"])
    c4.metric("비교 후보", f"{(facilities['type'] == facility_type).sum()}곳", "서비스 등록 시설")

    render_section_heading("INPUT", "활성 검색 조건", "세부 조건은 왼쪽 설정 패널에서 언제든 변경할 수 있습니다.")
    disease_text = ", ".join(selected_diseases) if selected_diseases else "질환 선택 안 함"
    pills = "".join(
        f'<span class="filter-pill">{value}</span>'
        for value in ["부산광역시 금정구", active_location_name, basic_type, disease_text, facility_type, scenario_label]
    )
    st.markdown(
        f'<div class="filter-summary"><strong>추천에 적용 중인 조건</strong><br>{pills}</div>',
        unsafe_allow_html=True,
    )

    try:
        with st.spinner("진료 조건과 경로별 이동 부담을 계산하고 있습니다…"):
            result = recommend(
                facilities,
                user_latitude=latitude,
                user_longitude=longitude,
                basic_type=basic_type,
                selected_diseases=selected_diseases,
                facility_type=facility_type,
                temperature=float(weather_row["temperature"]),
                rainfall=float(weather_row["rainfall"]),
                weather_status=str(weather_row["weather_status"]),
                air_grade=str(air_row["air_grade"]),
                accessibility=accessibility,
                schedules=schedules,
                routes=routes,
                origin_id=origin_id,
                clinical_conditions=clinical_inputs,
                accessibility_inputs=accessibility_inputs,
            )
    except Exception:
        st.error("추천 계산을 완료하지 못했습니다. 입력을 확인한 뒤 다시 실행하거나 검색 조건을 초기화하세요.")
        return
    if result.empty:
        st.markdown(
            '<div class="filter-summary"><strong>검색 결과가 없습니다.</strong><br>'
            '왼쪽 설정 패널에서 시설 유형, 기준 위치 또는 건강 조건을 조정해 보세요.</div>',
            unsafe_allow_html=True,
        )
        return
    if run:
        st.toast("검색 조건을 반영했습니다.", icon="✅")

    transit_estimates: dict[str, list[dict]] = {}
    mobility_errors: list[str] = []
    if transit_enabled:
        with st.spinner("ODsay에서 버스·지하철 경로와 요금을 확인하고 있습니다…"):
            for row in result.to_dict("records"):
                try:
                    transit_estimates[row["facility_id"]] = cached_transit_estimates(
                        latitude, longitude, float(row["latitude"]), float(row["longitude"]),
                        odsay_api_key, transit_path_type,
                    )
                except MobilityError as exc:
                    mobility_errors.append(f"{row['name']}: {exc}")

    recommendation_context_rows = []
    for row in result.to_dict("records"):
        route_options = transit_estimates.get(row["facility_id"], [])
        recommendation_context_rows.append({
            "rank": int(row["rank"]),
            "name": row["name"],
            "distance_km": float(row["distance_km"]),
            "travel_minutes": float(row["travel_minutes"]),
            "outdoor_minutes": float(row["outdoor_minutes"]),
            "final_score": float(row["final_score"]),
            "specialty": row.get("specialty") or "",
            "transit": route_options[0] if route_options else None,
        })
    st.session_state["last_recommendation_context"] = {
        "location": active_location_name,
        "basic_type": basic_type,
        "selected_diseases": selected_diseases,
        "facility_type": facility_type,
        "weather": str(weather_row["weather_status"]),
        "air_grade": str(air_row["air_grade"]),
        "results": recommendation_context_rows,
    }

    render_section_heading("RESULT", "추천 결과", "진료 조건과 실제 이동 부담이 어떻게 다른지 함께 비교하세요.")
    top = result.iloc[0]
    hero_specialties = escape(compact_specialties(top.get("specialty")))
    hero_reason = escape(distinctive_reason(top["reasons"]))
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-kicker">#1 지금 조건의 1순위</div>
          <div class="hero-name">{top['name']}</div>
          <span class="hero-score">{top['final_score']:.1f}점</span>
          <span class="hero-distance">예상 이동 {format_duration(top['travel_minutes'])} · 야외 {format_duration(top['outdoor_minutes'])} · 거리 {top['distance_km']:.1f}km</span>
          <div class="card-row"><span class="card-label">진료</span><span class="card-value">{hero_specialties}</span></div>
          <div class="hero-reason">✓ {hero_reason}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("점수가 높을수록 현재 설정에서 이동 접근성이 상대적으로 높습니다. 의료적 적합도나 진료 가능성을 뜻하지 않습니다.")

    render_transport_summary(top, transit_estimates.get(top["facility_id"]), transit_enabled)
    if mobility_errors:
        with st.expander("대중교통 정보를 가져오지 못한 기관"):
            st.write("\n".join(f"- {message}" for message in mobility_errors))

    views = st.columns(4)
    purpose_rows = [
        ("종합 추천", result.iloc[0]),
        ("야외 노출 최소", result.sort_values(["outdoor_minutes", "final_score"], ascending=[True, False]).iloc[0]),
        ("진료 조건 적합", result.sort_values(["fit_score", "final_score"], ascending=False).iloc[0]),
        ("시설 접근성", result.sort_values(["accessibility_score", "final_score"], ascending=False).iloc[0]),
    ]
    for column, (label, candidate) in zip(views, purpose_rows):
        column.metric(label, candidate["name"], f"{candidate['final_score']:.1f}점")

    recommendation_tab, mobility_tab, map_tab, comparison_tab = st.tabs(["추천 TOP 5", "버스·지하철", "위치 지도", "점수 비교"])
    with recommendation_tab:
        st.caption("순위는 진료 조건, 경로별 이동 부담, 시설 접근성, 운영정보를 함께 반영합니다.")
        for row in result.to_dict("records"):
            specialties = escape(compact_specialties(row.get("specialty")))
            reason = escape(distinctive_reason(row.get("reasons")))
            card_class = "result-card first" if row["rank"] == 1 else "result-card"
            transit_routes = transit_estimates.get(row["facility_id"], [])
            transit = transit_routes[0] if transit_routes else None
            transit_meta = ""
            service_meta = ""
            if row.get("service_tags"):
                service_meta = f'<span class="meta-chip">{escape(" · ".join(row["service_tags"][:2]))}</span>'
            if transit:
                transit_meta = (
                    f'<span class="meta-chip">{escape(transit["route_type"])} {format_duration(transit["total_minutes"])}</span>'
                    f'<span class="meta-chip fare">요금 {format_won(transit["fare"])}</span>'
                )
            st.markdown(
                f"""
                <div class="{card_class}">
                  <span class="rank">#{row['rank']} {row['name']}</span>
                  <span class="score">{row['final_score']:.1f}점</span>
                  <div class="card-meta">
                    <span class="meta-chip">거리 {row['distance_km']:.1f}km</span>
                    <span class="meta-chip">이동 {format_duration(row['travel_minutes'])}</span>
                    <span class="meta-chip">야외 {format_duration(row['outdoor_minutes'])}</span>
                    {service_meta}
                    {transit_meta}
                  </div>
                  <div class="card-row"><span class="card-label">진료</span><span class="card-value">{specialties}</span></div>
                  <div class="card-reason"><span class="card-label">근거</span> {reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander(f"#{row['rank']} 운영시간·상세 보기"):
                render_operating_info(row, schedules)
                st.write(f"주소: {row['address']}")
                st.write(f"연락처: {row.get('phone', '정보 없음')}")
                if row.get("service_tags"):
                    st.write(f"공개 서비스 근거: {' · '.join(row['service_tags'])}")
                st.write(
                    f"보행경로 관측: {row['walk_route_observation_count']}개 · "
                    f"운영 근거 상태: {row['availability_data_status']}"
                )
                route_label = "OSM 기반 근사 보행경로" if row["route_data_status"] == "approximate_osm" else "좌표 기반 발표용 추정"
                st.write(f"경로 데이터: {route_label} · 거리 {row['route_distance_km']:.2f}km")
                if transit:
                    st.write(
                        f"대중교통·대기 {format_duration(transit['transit_minutes'])} + "
                        f"도보·야외 {format_duration(transit['outdoor_minutes'])} = 총 {format_duration(transit['total_minutes'])}"
                    )
                    st.write(
                        f"{transit['route_type']} · 예상 요금 {format_won(transit['fare'])} · "
                        f"버스 환승 {transit['bus_transfers']}회 · 지하철 환승 {transit['subway_transfers']}회"
                    )
                    if transit.get("first_station") or transit.get("last_station"):
                        st.write(
                            f"승·하차: {transit.get('first_station') or '출발지 인근'} → "
                            f"{transit.get('last_station') or '도착지 인근'} · 도보 {transit['total_walk_meters']:.0f}m"
                        )
                st.dataframe(
                    pd.DataFrame(
                        {
                            "구성 요소": ["진료 조건 35%", "경로 편의 30%", "시설 접근성 20%", "진료 가능 시간 10%", "데이터 근거 5%"],
                            "점수": [row["fit_score"], row["route_score"], row["accessibility_score"], row["operating_score"], row["confidence_score"]],
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
                search_text = compact_map_query(row["name"], row["address"])
                query = quote(search_text)
                st.markdown(
                    f"[네이버지도에서 확인](https://map.naver.com/p/search/{query}) · "
                    f"[카카오맵에서 확인](https://map.kakao.com/?q={query}) · "
                    f"[Google 지도에서 확인](https://www.google.com/maps/search/?api=1&query={query})"
                )
                st.caption(f"지도 검색어: {search_text}")
    with mobility_tab:
        mobility_rows = []
        for row in result.to_dict("records"):
            estimates = transit_estimates.get(row["facility_id"])
            options = transport_options(row["travel_minutes"], row["outdoor_minutes"], estimates)
            for option in options:
                mobility_rows.append({"순위": row["rank"], "시설명": row["name"], **option})
        mobility_frame = pd.DataFrame(mobility_rows)
        st.dataframe(
            mobility_frame,
            hide_index=True,
            width="stretch",
            column_config={
                "총 소요시간": st.column_config.NumberColumn("총 소요(분)", format="%.1f"),
                "대중교통시간": st.column_config.NumberColumn("교통·대기(분)", format="%.1f"),
                "야외시간": st.column_config.NumberColumn("야외(분)", format="%.1f"),
                "예상 요금": st.column_config.NumberColumn("요금", format="%d원"),
                "버스 환승": st.column_config.NumberColumn("버스 환승", format="%d회"),
                "지하철 환승": st.column_config.NumberColumn("지하철 환승", format="%d회"),
                "도보거리(m)": st.column_config.NumberColumn("도보거리", format="%.0fm"),
            },
        )
        st.caption("도보와 대중교통은 별도 행입니다. 대중교통 야외시간은 경로 내 도보 구간의 합이며, 승차시간과 중복되지 않습니다.")
    with map_tab:
        accuracy_text = f" · 정확도 약 {live_location['accuracy']:.0f}m" if use_live_location and live_location else ""
        st.info(f"내 출발 위치: {active_location_name}{accuracy_text} · 청록색 테두리의 진한 점으로 표시됩니다.")
        st.plotly_chart(
            result_map(result, latitude, longitude, active_location_name),
            width="stretch",
            config={"displayModeBar": False, "scrollZoom": True},
        )
        st.caption("파란 숫자는 추천 순위이며 선은 출발 위치와 각 시설의 방향을 보여줍니다. 지도를 드래그하거나 확대해 주변 도로를 확인할 수 있습니다.")
    with comparison_tab:
        comparison = result[["rank", "name", "final_score", "travel_minutes", "outdoor_minutes", "fit_score", "route_score", "accessibility_score", "operating_score", "confidence_score"]].copy()
        comparison.columns = ["순위", "시설명", "최종 점수", "이동(분)", "야외(분)", "진료 조건", "경로 편의", "시설 접근성", "운영 접근", "근거 신뢰"]
        st.dataframe(
            comparison,
            hide_index=True,
            width="stretch",
            column_config={
                "최종 점수": st.column_config.ProgressColumn("최종 점수", min_value=0, max_value=100, format="%.1f점"),
                "이동(분)": st.column_config.NumberColumn("이동(분)", format="%.1f"),
            },
        )
        st.caption("날씨와 대기질은 시설별 야외 노출시간과 사용자 민감도에 적용되므로 같은 지역에서도 경로 부담이 달라집니다.")

    render_section_heading("INSIGHT", "이번 추천에서 읽을 점", "결과를 빠르게 해석할 수 있도록 핵심 차이를 요약했습니다.")
    score_gap = float(result.iloc[0]["final_score"] - result.iloc[-1]["final_score"])
    average_outdoor = float(result["outdoor_minutes"].mean())
    matching_count = int(result["matched_diseases"].map(bool).sum()) if selected_diseases else 0
    i1, i2, i3 = st.columns(3)
    i1.markdown(
        f'<div class="insight-card"><div class="label">추천 변별력</div><div class="value">{score_gap:.1f}점 차이</div>'
        '<div class="body">1위와 5위의 점수 차이입니다. 질환·경로·접근성 차이가 반영됩니다.</div></div>',
        unsafe_allow_html=True,
    )
    i2.markdown(
        f'<div class="insight-card"><div class="label">평균 야외 노출</div><div class="value">{format_duration(average_outdoor)}</div>'
        '<div class="body">현재 조건에서 TOP 5 후보의 평균 야외 노출시간입니다.</div></div>',
        unsafe_allow_html=True,
    )
    match_value = f"{matching_count}곳" if selected_diseases else "선택 없음"
    match_body = "선택 질환과 공개 진료과목이 연결된 후보 수입니다." if selected_diseases else "질환을 선택하면 관련 진료과목 일치 여부를 함께 보여줍니다."
    i3.markdown(
        f'<div class="insight-card"><div class="label">질환 연관 진료과목</div><div class="value">{match_value}</div>'
        f'<div class="body">{match_body}</div></div>',
        unsafe_allow_html=True,
    )

    render_section_heading("GUIDANCE", "데이터와 이용 안내", "추천의 적용 범위와 데이터 기준을 투명하게 제공합니다.")
    st.markdown(
        '<div class="notice"><b>이동 접근성 참고 정보</b><br>부산대역·구서역·노포역은 OSM 기반 근사 경로이며 서동역과 시설 접근성은 미확인 또는 추정값입니다. '
        "실제 경로, 임시 휴진·접수 마감·진료과별 시간은 외부 지도와 해당 기관에서 다시 확인하세요.</div>",
        unsafe_allow_html=True,
    )
    with st.expander("데이터 출처와 기준일"):
        st.markdown(
            "의료기관: 제공된 MVP 데이터(기본 명부 2026-03-05) · 약국: 금정구 공개자료(2025-09-05) · "
            "인구: 금정구청(2026-03-31) · 운영시간: 기관 공식 홈페이지·외부 참고정보(2026-07-14 확인) · "
            "날씨·대기질: 시설별 야외 노출과 사용자 민감도를 조정하는 기준 조건(실시간 관측 아님). 자세한 내용은 `data/source_notes.md`를 확인하세요."
        )
    with st.expander("버스·지하철 API 설정"):
        st.markdown(
            "`.streamlit/secrets.toml` 또는 환경변수에 다음 값을 설정합니다. 키가 없거나 API가 실패해도 저장된 도보 추천은 계속 작동합니다.\n\n"
            "- ODsay Server API: `ODSAY_API_KEY`\n\n"
            "추천·지하철·버스 우선 경로를 선택할 수 있으며 총시간, 요금, 환승 횟수, 승·하차 정류장과 도보 구간을 표시합니다."
        )


def render_regional(
    facilities: pd.DataFrame, population: pd.DataFrame, routes: pd.DataFrame,
    accessibility: pd.DataFrame, clinical_inputs: pd.DataFrame,
    accessibility_inputs: pd.DataFrame,
) -> None:
    render_page_header(
        "REGIONAL INTELLIGENCE",
        "우리 지역의 의료 접근성은 어떤가요?",
        "금정구 인구 구조와 서비스 등록 의료시설을 비교해 지역 단위의 접근성 맥락을 살펴봅니다.",
    )
    total = population.loc[population["region"] == "부산광역시 금정구"].iloc[0]
    counts = facilities["type"].value_counts().reindex(["병원", "약국"], fill_value=0)
    elderly_rate = total["elderly_population"] / total["population"] * 100
    render_section_heading("OVERVIEW", "지역 핵심 지표", "인구와 현재 서비스 등록 시설 규모를 함께 확인하세요.")
    columns = st.columns(4)
    columns[0].metric("전체 인구", f"{int(total['population']):,}명", "2026-03-31")
    columns[1].metric("65세 이상", f"{int(total['elderly_population']):,}명", f"{elderly_rate:.1f}%")
    columns[2].metric("등록 병원", f"{counts['병원']}곳", "서비스 내 시설")
    columns[3].metric("등록 약국", f"{counts['약국']}곳", "서비스 내 시설")

    render_section_heading("READINESS", "추천 데이터 준비도", "제공된 MVP 데이터에서 실제 계산 가능 범위와 검증 공백을 분리했습니다.")
    valid_routes = int((routes["status"] == "OSM 보행경로 계산").sum())
    missing_routes = int((routes["status"] != "OSM 보행경로 계산").sum())
    verified_schedules = int((clinical_inputs["schedule_data_quality"] == "verified").sum())
    observed_walks = int((accessibility_inputs["walk_route_observation_count"] >= 3).sum())
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("근사 보행경로", f"{valid_routes}건", "부산대역·구서역·노포역")
    r2.metric("경로 미확인", f"{missing_routes}건", "서동역 좌표 보완 필요")
    r3.metric("공개 운영 근거", f"{verified_schedules}곳", "병원 15곳 중 확인")
    r4.metric("보행 관측 보강", f"{observed_walks}곳", "기관별 3개 출발지")

    chart_data = pd.DataFrame({"시설 유형": counts.index, "시설 수": counts.values})
    per_ten_thousand = chart_data.copy()
    per_ten_thousand["인구 1만 명당 시설 수"] = per_ten_thousand["시설 수"] / total["population"] * 10000
    render_section_heading("ANALYSIS", "시설 공급 지표", "절대 시설 수와 인구 대비 참고 지표를 같은 기준에서 비교합니다.")
    count_tab, ratio_tab = st.tabs(["등록 시설 수", "인구 1만 명당 시설"])
    with count_tab:
        figure = px.bar(chart_data, x="시설 유형", y="시설 수", text="시설 수", color="시설 유형", color_discrete_sequence=["#0B6E99", "#0F8B8D"], title="서비스 등록 시설 유형별 수 · 단위: 곳")
        figure.update_layout(showlegend=False)
        st.plotly_chart(figure, width="stretch")
        st.caption("현재 서비스에서 비교할 수 있는 병원 15곳과 약국 12곳입니다.")
    with ratio_tab:
        figure = px.bar(per_ten_thousand, x="시설 유형", y="인구 1만 명당 시설 수", text_auto=".2f", color="시설 유형", color_discrete_sequence=["#0B6E99", "#0F8B8D"], title="인구 1만 명당 등록 시설 수 · 단위: 곳")
        figure.update_layout(showlegend=False)
        st.plotly_chart(figure, width="stretch")
        st.caption("금정구 전체 의료 공급량이 아니라 현재 서비스에 등록된 시설 규모를 인구와 비교한 참고 지표입니다.")

    render_section_heading("INSIGHT", "고령 인구 분포", "행정동별 65세 이상 주민 비율을 비교해 이동 취약 가능성이 큰 지역을 살펴봅니다.")
    dong = population[population["region"] != "부산광역시 금정구"].copy()
    dong["고령 인구 비율"] = dong["elderly_population"] / dong["population"] * 100
    dong = dong.sort_values("고령 인구 비율", ascending=True)
    figure = px.bar(dong, x="고령 인구 비율", y="region", orientation="h", text_auto=".1f", title="행정동별 65세 이상 주민 비율 · 단위: % · 2026-03-31")
    figure.update_traces(marker_color="#0B6E99")
    st.plotly_chart(figure, width="stretch")
    highest = dong.iloc[-1]
    st.success(f"핵심 해석: {highest['region']}의 65세 이상 주민 비율이 {highest['고령 인구 비율']:.1f}%로 가장 높습니다. 다만 이 수치만으로 실제 의료 접근성을 단정할 수는 없습니다.")


def render_chatbot(
    facilities: pd.DataFrame, schedules: pd.DataFrame, population: pd.DataFrame,
    clinical_inputs: pd.DataFrame, accessibility_inputs: pd.DataFrame,
) -> None:
    render_page_header(
        "MEDIWAY CARE DESK",
        "지역 의료·이동 상담",
        "금정구 시설 정보와 최근 추천 맥락을 바탕으로 운영·거리·교통·일반 의료정보 질문을 안내합니다.",
    )
    api_key = _secret("GEMINI_API_KEY")
    model = _secret("GEMINI_MODEL") or "gemini-3.5-flash"
    context = build_service_context(
        facilities, schedules, population, st.session_state.get("last_recommendation_context"),
        clinical_inputs, accessibility_inputs,
    )

    render_section_heading("STATUS", "상담 준비 상태", "답변에 사용하는 범위와 현재 연결 상태입니다.")
    c1, c2, c3 = st.columns(3)
    c1.metric("등록 의료시설", f"{len(facilities)}곳", "병원·약국")
    c2.metric("최근 추천 맥락", "연결됨" if context["last_recommendation"] else "아직 없음", "추천 화면과 연동")
    c3.metric("답변 모드", "AI 강화" if api_key else "기본 CS", model if api_key else "저장 데이터 기반")
    st.markdown(
        '<div class="notice"><b>안전 안내</b><br>이 상담은 의료 진단·처방을 제공하지 않습니다. '
        '심한 흉통, 호흡곤란, 의식 저하, 마비, 멈추지 않는 출혈 등 긴급 증상은 채팅을 기다리지 말고 119에 연락하세요.</div>',
        unsafe_allow_html=True,
    )

    if "mediway_chat_messages" not in st.session_state:
        st.session_state.mediway_chat_messages = [{
            "role": "assistant",
            "content": (
                "안녕하세요. 메디웨이 상담봇입니다. 병원·약국 정보, 운영 안내, 최근 추천의 거리와 교통, "
                "질환별 관련 진료과에 대해 질문해 주세요."
            ),
        }]

    render_section_heading("QUICK START", "자주 묻는 질문", "버튼을 누르거나 아래 입력창에 직접 질문하세요.")
    quick_prompts = [
        "금정구 병원과 약국은 몇 곳이야?",
        "최근 추천 중 가까운 곳을 알려줘",
        "천식이면 어떤 진료과를 봐야 해?",
        "지온병원 운영정보 알려줘",
    ]
    quick_columns = st.columns(4)
    selected_prompt = None
    for column, prompt_text in zip(quick_columns, quick_prompts):
        if column.button(prompt_text, width="stretch"):
            selected_prompt = prompt_text

    top_bar = st.columns([5, 1])
    top_bar[0].caption("시설·운영·추천 정보는 저장 기준일 또는 API 조회 시점 기준이며 방문 전 기관 확인이 필요합니다.")
    if top_bar[1].button("대화 초기화", width="stretch"):
        st.session_state.mediway_chat_messages = st.session_state.mediway_chat_messages[:1]
        st.rerun()

    for message in st.session_state.mediway_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    typed_prompt = st.chat_input("병원, 진료과, 거리, 교통, 운영시간 등을 물어보세요")
    prompt = typed_prompt or selected_prompt
    if not prompt:
        return

    st.session_state.mediway_chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("메디웨이 정보를 확인하고 있습니다…"):
            try:
                if api_key:
                    answer = ask_gemini(
                        prompt,
                        st.session_state.mediway_chat_messages[:-1],
                        context,
                        api_key,
                        model=model,
                    )
                else:
                    answer = local_cs_answer(prompt, context)
            except ChatbotError:
                answer = local_cs_answer(prompt, context)
                st.caption("AI 연결이 원활하지 않아 저장된 서비스 데이터로 답변했습니다.")
        st.markdown(answer)
    st.session_state.mediway_chat_messages.append({"role": "assistant", "content": answer})
    st.session_state.mediway_chat_messages = st.session_state.mediway_chat_messages[-20:]


def render_methodology() -> None:
    render_page_header(
        "METHODOLOGY",
        "추천 기준 안내",
        "진료 조건, 경로별 이동 부담, 시설 접근성이 최종 점수와 추천 이유로 변환되는 과정을 공개합니다.",
    )
    render_section_heading("WEIGHTING", "점수 구성", "같은 규칙에서 점수와 추천 이유를 함께 생성합니다.")
    weights = pd.DataFrame({"구성 요소": ["진료 조건", "경로 편의", "시설 접근성", "진료 가능 시간", "데이터 근거"], "가중치": [35, 30, 20, 10, 5]})
    figure = px.bar(weights, x="가중치", y="구성 요소", orientation="h", text="가중치", title="접근성 점수 가중치 · 단위: %", color="구성 요소", color_discrete_sequence=["#0B6E99", "#0F8B8D", "#B45309", "#6B5B95"])
    figure.update_layout(showlegend=False)
    st.plotly_chart(figure, width="stretch")
    st.code("최종 점수 = 진료 조건×0.35 + 경로 편의×0.30 + 시설 접근성×0.20 + 진료 가능 시간×0.10 + 데이터 근거×0.05", language=None)
    render_section_heading("PROCESS", "추천 처리 흐름", "입력부터 TOP 5와 설명 생성까지의 계산 순서입니다.")
    st.markdown("**① 방문 조건 확인** → **② 예상 이동·야외 노출 계산** → **③ 사용자별 환경 부담 적용** → **④ 시설·운영정보 결합** → **⑤ 목적별 추천·TOP 5 생성**")
    render_section_heading("REFERENCE", "경로 부담 기준", "같은 날씨라도 야외 노출과 사용자 민감도에 따라 시설별 부담이 달라집니다.")
    c1, c2 = st.columns(2)
    c1.dataframe(
        pd.DataFrame(
            {
                "경로 요소": ["예상 이동시간", "야외 노출 비율", "경사", "환승"],
                "반영 방식": ["거리·사용자 이동속도", "비·대기질 노출", "이동 취약 부담", "환승 부담"],
            }
        ),
        hide_index=True,
        width="stretch",
    )
    c1.caption("현재 이동시간은 직선거리에 발표용 경로계수와 사용자별 이동속도를 적용합니다.")
    c2.dataframe(pd.DataFrame({"환경·사용자 조건": ["비", "고온·저온", "대기질 나쁨", "호흡기 질환"], "달라지는 값": ["야외 노출 부담", "야외 노출 부담", "야외 노출 부담", "대기질 민감도"]}), hide_index=True, width="stretch")
    render_section_heading("GOVERNANCE", "데이터와 한계", "서비스가 제공하는 정보의 범위와 주의사항입니다.")
    st.markdown(
        "- 시설: 금정구 공개 의료기관·약국 정보 중 현재 서비스에 등록된 27곳을 비교합니다.\n"
        "- 인구: 금정구청 2026-03-31 주민등록 인구현황을 사용했습니다.\n"
        "- 환경: 검색 조건별 기준값을 시설별 야외 노출시간에 적용하며 실시간 관측 정보는 아닙니다.\n"
        "- 경로: 저장된 OSM 근사 경로를 우선 사용하며 새 보행 관측치는 데이터 근거 수준에만 반영해 이중 계산을 막습니다.\n"
        "- 접근성: 무단차·엘리베이터 등 `unknown`은 중립 처리하고 확인된 주차 정보만 제한적으로 반영합니다.\n"
        "- 진료 가능 시간: 공개된 야간·토요일·일·공휴일·24시간 응급 여부를 운영 접근성으로 계산하며 의료 수준을 뜻하지 않습니다.\n"
        "- 한계: 실시간 교통·정밀 경사·공사·보행 장애물·임시 휴진·접수 마감 미반영, 진료 가능 여부 미보장."
    )


def main() -> None:
    try:
        facilities, weather, air, population, schedules, accessibility, routes, clinical_inputs, accessibility_inputs = load_data()
    except Exception:
        st.error("서비스 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        st.stop()
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand"><strong>◆ 메디웨이</strong><span>Healthcare accessibility workspace</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("WORKSPACE")
        page = st.radio(
            "화면 이동", ["의료기관 추천", "메디웨이 상담", "지역 의료 현황", "추천 기준 안내"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("부산광역시 금정구 · 저장 데이터 기반 · 오프라인 실행 지원")
    if page == "의료기관 추천":
        render_recommendation(facilities, weather, air, schedules, accessibility, routes, clinical_inputs, accessibility_inputs)
    elif page == "메디웨이 상담":
        render_chatbot(facilities, schedules, population, clinical_inputs, accessibility_inputs)
    elif page == "지역 의료 현황":
        render_regional(facilities, population, routes, accessibility, clinical_inputs, accessibility_inputs)
    else:
        render_methodology()


if __name__ == "__main__":
    main()
