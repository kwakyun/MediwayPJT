"""Generate auditable outputs for the four presentation scenarios."""

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scenarios import REFERENCE_LOCATIONS, REFERENCE_ORIGIN_IDS, SCENARIOS
from src.scoring import recommend


DATA = ROOT / "data" / "processed"
OUTPUT = ROOT / "output" / "analysis"


def main() -> None:
    facilities = pd.read_csv(DATA / "facilities.csv")
    weather = pd.read_csv(DATA / "weather.csv").set_index("scenario_id")
    air = pd.read_csv(DATA / "air_quality.csv").set_index("scenario_id")
    accessibility = pd.read_csv(DATA / "facility_accessibility.csv")
    schedules = pd.read_csv(DATA / "operating_hours.csv")
    routes = pd.read_csv(DATA / "walking_routes.csv")
    clinical_inputs = pd.read_csv(DATA / "clinical_condition_inputs.csv")
    accessibility_inputs = pd.read_csv(DATA / "facility_accessibility_inputs.csv")
    records = []
    for label, scenario in SCENARIOS.items():
        scenario_id = scenario["scenario_id"]
        latitude, longitude = REFERENCE_LOCATIONS[scenario["location_name"]]
        ranked = recommend(
            facilities,
            user_latitude=latitude,
            user_longitude=longitude,
            basic_type=scenario["basic_type"],
            selected_diseases=scenario["selected_diseases"],
            facility_type=scenario["facility_type"],
            temperature=float(weather.loc[scenario_id, "temperature"]),
            rainfall=float(weather.loc[scenario_id, "rainfall"]),
            weather_status=weather.loc[scenario_id, "weather_status"],
            air_grade=air.loc[scenario_id, "air_grade"],
            accessibility=accessibility,
            schedules=schedules,
            routes=routes,
            origin_id=REFERENCE_ORIGIN_IDS.get(scenario["location_name"]),
            clinical_conditions=clinical_inputs,
            accessibility_inputs=accessibility_inputs,
        )
        for row in ranked.to_dict("records"):
            records.append(
                {
                    "scenario_id": scenario_id,
                    "scenario_label": label,
                    "basic_type": scenario["basic_type"],
                    "selected_diseases": "|".join(scenario["selected_diseases"]) or "선택 안 함",
                    "location_name": scenario["location_name"],
                    "rank": row["rank"],
                    "facility_id": row["facility_id"],
                    "name": row["name"],
                    "distance_km": row["distance_km"],
                    "final_score": row["final_score"],
                    "travel_minutes": row["travel_minutes"],
                    "outdoor_minutes": row["outdoor_minutes"],
                    "route_burden_minutes": row["route_burden_minutes"],
                    "route_data_status": row["route_data_status"],
                    "fit_score": row["fit_score"],
                    "route_score": row["route_score"],
                    "accessibility_score": row["accessibility_score"],
                    "operating_score": row["operating_score"],
                    "confidence_score": row["confidence_score"],
                    "visit_status": row["visit_status"],
                    "service_tags": "|".join(row["service_tags"]),
                    "availability_data_status": row["availability_data_status"],
                    "walk_route_observation_count": row["walk_route_observation_count"],
                    "reasons": " | ".join(row["reasons"]),
                }
            )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(records)
    result.to_csv(OUTPUT / "scenario_results.csv", index=False, encoding="utf-8-sig")
    top = result[result["rank"] == 1][["scenario_id", "name", "distance_km", "final_score"]]
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
