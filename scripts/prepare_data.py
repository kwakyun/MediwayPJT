"""Build the offline demo datasets from official Geumjeong-gu snapshots."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
CACHE_PATH = RAW / "geocode_cache.json"

MEDICAL_NAMES = [
    "세웅병원",
    "지온병원",
    "메드윌병원",
    "화창한병원",
    "부산마이크로병원",
    "새우리남산병원",
    "서동가정의학과의원",
    "김유정내과의원",
    "금정바른정형외과의원",
    "금정소아청소년과의원",
    "원이비인후과의원",
    "서재득신경과의원",
    "누가정형외과재활의학과의원",
    "민들레내과의원",
    "이준정형외과의원",
]

PHARMACY_NAMES = [
    "부곡온누리약국",
    "수강약국",
    "범어사메트로약국",
    "신제일약국",
    "스타약국",
    "봄약국",
    "미솜약국",
    "우리약국",
    "금성약국",
    "가온샘약국",
    "맑은약국",
    "장전 온누리약국",
]

PHONE_OVERRIDES = {
    # The district snapshot contains a placeholder; the clinic's official site lists this number.
    "서동가정의학과의원": "051-521-7818",
}


def clean_address(address: str) -> str:
    address = re.sub(r"\([^)]*\)", "", str(address))
    address = address.split(",", 1)[0]
    return re.sub(r"\s+", " ", address).strip()


def load_selected() -> pd.DataFrame:
    medical = pd.read_csv(RAW / "geumjeong_medical_2024.csv", encoding="cp949")
    medical = medical[medical["의료기관명"].isin(MEDICAL_NAMES)].copy()
    medical = medical.rename(
        columns={
            "의료기관명": "name",
            "의료기관주소(도로명)": "address",
            "의료기관전화번호": "phone",
        }
    )
    medical["type"] = "병원"

    pharmacy = pd.read_csv(RAW / "geumjeong_pharmacy_20250905.csv", encoding="cp949")
    pharmacy = pharmacy[pharmacy["약국명칭"].isin(PHARMACY_NAMES)].copy()
    pharmacy = pharmacy.rename(
        columns={"약국명칭": "name", "약국소재지(도로명)": "address", "약국전화번호": "phone"}
    )
    pharmacy["type"] = "약국"

    selected = pd.concat(
        [medical[["name", "type", "address", "phone"]], pharmacy[["name", "type", "address", "phone"]]],
        ignore_index=True,
    )
    selected["geocode_address"] = selected["address"].map(clean_address)
    return selected


def geocode(selected: pd.DataFrame, refresh: bool = False) -> None:
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    headers = {"User-Agent": "Mediway student project/1.0 (offline dataset preparation)"}
    for row in selected[["name", "geocode_address"]].drop_duplicates("geocode_address").itertuples(index=False):
        address = row.geocode_address
        if address in cache and (not refresh or cache[address].get("query")):
            continue
        results = []
        used_query = ""
        for candidate in (f"{row.name}, {address}", address):
            query = urllib.parse.urlencode({"q": candidate, "format": "jsonv2", "limit": 1, "countrycodes": "kr"})
            request = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/search?{query}", headers=headers
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                results = json.loads(response.read().decode("utf-8"))
            time.sleep(1.1)
            if results:
                used_query = candidate
                break
        if not results:
            raise RuntimeError(f"Geocoding returned no result: {address}")
        cache[address] = {
            "latitude": float(results[0]["lat"]),
            "longitude": float(results[0]["lon"]),
            "display_name": results[0]["display_name"],
            "query": used_query,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def specialty_for(name: str, facility_type: str) -> str:
    if facility_type == "약국":
        return "약국"
    rules = [
        ("소아청소년", "소아청소년과"),
        ("이비인후", "이비인후과"),
        ("정형외과재활", "정형외과|재활의학과"),
        ("정형외과", "정형외과"),
        ("신경과", "신경과"),
        ("내과", "내과"),
        ("가정의학", "가정의학과"),
    ]
    for token, specialty in rules:
        if token in name:
            return specialty
    hospital_rules = {
        "세웅병원": "내과|정형외과|신경과|응급의학과",
        "지온병원": "정형외과|신경외과|재활의학과",
        "메드윌병원": "재활의학과|내과|신경과",
        "화창한병원": "내과|외과|정형외과",
        "부산마이크로병원": "정형외과|신경외과|재활의학과",
        "새우리남산병원": "내과|정형외과|신경외과",
    }
    return hospital_rules.get(name, "일반진료")


def build_facilities(selected: pd.DataFrame) -> pd.DataFrame:
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    missing = sorted(set(selected["geocode_address"]) - set(cache))
    if missing:
        raise RuntimeError(f"Missing geocodes ({len(missing)}): {missing}")
    selected["latitude"] = selected["geocode_address"].map(lambda value: cache[value]["latitude"])
    selected["longitude"] = selected["geocode_address"].map(lambda value: cache[value]["longitude"])
    selected["specialty"] = [specialty_for(n, t) for n, t in zip(selected["name"], selected["type"])]
    selected["phone"] = selected["phone"].fillna("정보 없음")
    selected["phone"] = selected["name"].map(PHONE_OVERRIDES).fillna(selected["phone"])
    selected = selected.sort_values(["type", "name"], kind="stable").reset_index(drop=True)
    selected["facility_id"] = [f"GJ-{t}-{i:03d}" for i, t in enumerate(selected["type"].map({"병원": "H", "약국": "P"}), 1)]
    selected["source_date"] = selected["type"].map({"병원": "2024-03-05", "약국": "2025-09-05"})
    return selected[
        ["facility_id", "name", "type", "address", "latitude", "longitude", "specialty", "phone", "source_date"]
    ]


def build_population() -> pd.DataFrame:
    raw = pd.read_excel(RAW / "geumjeong_population_20260331.xlsx", sheet_name="금정구", header=None)
    records = []
    for _, row in raw.iloc[7:].iterrows():
        region = str(row.iloc[0]).replace(" ", "").strip()
        if region in {"nan", ""}:
            continue
        population = pd.to_numeric(row.iloc[1], errors="coerce")
        elderly = pd.to_numeric(row.iloc[9], errors="coerce")
        if pd.isna(population) or pd.isna(elderly):
            continue
        records.append(
            {
                "region": "부산광역시 금정구" if region == "계" else region,
                "population": int(population),
                "elderly_population": int(elderly),
                "reference_date": "2026-03-31",
            }
        )
    return pd.DataFrame(records)


def write_environment_samples() -> None:
    weather = pd.DataFrame(
        [
            ["DEMO-01", "기본 추천", 26.0, 0.0, "맑음"],
            ["DEMO-02", "고령자 이동 부담", 22.0, 12.0, "비"],
            ["DEMO-03", "호흡기 민감 상황", 25.0, 0.0, "맑음"],
            ["DEMO-04", "복합 특성 상황", 21.0, 18.0, "비"],
        ],
        columns=["scenario_id", "scenario_name", "temperature", "rainfall", "weather_status"],
    )
    weather["region"] = "부산광역시 금정구"
    weather["data_mode"] = "발표용 모의 시나리오"
    weather.to_csv(PROCESSED / "weather.csv", index=False, encoding="utf-8-sig")

    air = pd.DataFrame(
        [
            ["DEMO-01", "기본 추천", 45, 22, "보통"],
            ["DEMO-02", "고령자 이동 부담", 48, 24, "보통"],
            ["DEMO-03", "호흡기 민감 상황", 110, 55, "나쁨"],
            ["DEMO-04", "복합 특성 상황", 92, 42, "나쁨"],
        ],
        columns=["scenario_id", "scenario_name", "pm10", "pm25", "air_grade"],
    )
    air["region"] = "부산광역시 금정구"
    air["data_mode"] = "발표용 모의 시나리오"
    air.to_csv(PROCESSED / "air_quality.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geocode", action="store_true", help="Update the OSM Nominatim geocode cache")
    parser.add_argument("--refresh-geocode", action="store_true", help="Refresh cached coordinates using facility names")
    args = parser.parse_args()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    selected = load_selected()
    if len(selected) != len(MEDICAL_NAMES) + len(PHARMACY_NAMES):
        raise RuntimeError("One or more selected facility names were not found in the official snapshots")
    if args.geocode or args.refresh_geocode:
        geocode(selected, refresh=args.refresh_geocode)
    facilities = build_facilities(selected)
    facilities.to_csv(PROCESSED / "facilities.csv", index=False, encoding="utf-8-sig")
    build_population().to_csv(PROCESSED / "population.csv", index=False, encoding="utf-8-sig")
    write_environment_samples()
    shutil.copyfile(RAW / "operating_hours_snapshot.csv", PROCESSED / "operating_hours.csv")
    print(f"facilities={len(facilities)}, population_rows={len(build_population())}")


if __name__ == "__main__":
    main()
