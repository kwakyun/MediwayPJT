"""Validate all processed datasets used by the Streamlit app."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = set(columns) - set(frame.columns)
    assert not missing, f"{name}: missing columns {sorted(missing)}"


def main() -> None:
    facilities = pd.read_csv(DATA / "facilities.csv")
    weather = pd.read_csv(DATA / "weather.csv")
    air = pd.read_csv(DATA / "air_quality.csv")
    population = pd.read_csv(DATA / "population.csv")
    hours = pd.read_csv(DATA / "operating_hours.csv")
    accessibility = pd.read_csv(DATA / "facility_accessibility.csv")
    routes = pd.read_csv(DATA / "walking_routes.csv")
    clinical = pd.read_csv(DATA / "clinical_condition_inputs.csv")
    access_inputs = pd.read_csv(DATA / "facility_accessibility_inputs.csv")

    require_columns(
        facilities,
        ["facility_id", "name", "type", "address", "latitude", "longitude", "specialty", "phone"],
        "facilities",
    )
    assert facilities["facility_id"].is_unique
    assert not facilities[["name", "type", "address", "latitude", "longitude"]].isna().any().any()
    assert set(facilities["type"]) == {"병원", "약국"}
    assert facilities["latitude"].between(35.18, 35.32).all()
    assert facilities["longitude"].between(129.02, 129.15).all()
    assert not facilities.duplicated(["name", "address"]).any()
    coordinate_clusters = facilities.groupby(["latitude", "longitude"]).size()
    assert coordinate_clusters.max() <= 3, "too many facilities collapsed to one geocoded road point"

    require_columns(weather, ["temperature", "rainfall", "weather_status"], "weather")
    require_columns(air, ["pm10", "pm25", "air_grade"], "air_quality")
    require_columns(population, ["region", "population", "elderly_population"], "population")
    assert (weather["rainfall"] >= 0).all()
    assert (air[["pm10", "pm25"]].min(axis=None) >= 0)
    assert (population["population"] >= population["elderly_population"]).all()
    assert (population[["population", "elderly_population"]] >= 0).all().all()
    assert "부산광역시 금정구" in set(population["region"])

    require_columns(
        hours,
        ["facility_id", "data_status", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "lunch", "holiday", "verified_date"],
        "operating_hours",
    )
    assert hours["facility_id"].is_unique
    assert set(hours["facility_id"]) == set(facilities["facility_id"])
    assert set(hours["data_status"]) <= {"available", "unknown"}
    require_columns(accessibility, ["facility_id", "route_factor", "outdoor_ratio", "slope_level", "transfer_count", "step_free", "elevator", "accessible_parking", "data_status", "verified_date"], "facility_accessibility")
    assert accessibility["facility_id"].is_unique
    assert set(accessibility["facility_id"]) <= set(facilities["facility_id"])
    assert accessibility["route_factor"].between(1.0, 3.0).all()
    assert accessibility["outdoor_ratio"].between(0.0, 1.0).all()
    assert set(accessibility["data_status"]) <= {"verified", "prototype_estimate", "unknown"}
    require_columns(routes, ["origin_id", "facility_id", "distance_km", "estimated_minutes", "outdoor_minutes", "status", "route_source"], "walking_routes")
    assert len(routes) == 60
    assert (routes["status"] == "OSM 보행경로 계산").sum() == 45
    assert set(routes["facility_id"]) <= set(facilities["facility_id"])

    hospital_ids = set(facilities.loc[facilities["type"] == "병원", "facility_id"])
    require_columns(clinical, ["facility_id", "departments", "department_count", "night_care", "saturday_care", "sunday_or_holiday_care", "emergency_24h", "schedule_data_quality", "source_url"], "clinical_condition_inputs")
    assert clinical["facility_id"].is_unique
    assert set(clinical["facility_id"]) == hospital_ids
    assert (clinical["department_count"] >= 1).all()
    care_fields = ["night_care", "saturday_care", "sunday_or_holiday_care", "emergency_24h", "rehabilitation_capability", "surgery_capability_public_evidence", "specialist_public_evidence", "collaborative_care_public_evidence"]
    for column in care_fields:
        assert set(clinical[column]) <= {"yes", "no", "unknown"}, f"clinical: invalid {column}"
    assert set(clinical["schedule_data_quality"]) <= {"verified", "partial_or_unknown"}
    assert set(clinical["hero_collection_status"]) <= {"ok", "error", "not_collected"}

    physical_fields = ["step_free_entrance", "elevator", "accessible_parking_on_site", "accessible_toilet", "accessible_entrance_route"]
    require_columns(access_inputs, ["facility_id", "walk_route_observation_count", "nearest_origin_walk_km", "nearest_origin_walk_minutes", "mean_origin_walk_km", "mean_origin_walk_minutes", "nearby_public_accessible_parking", *physical_fields], "facility_accessibility_inputs")
    assert access_inputs["facility_id"].is_unique
    assert set(access_inputs["facility_id"]) == hospital_ids
    assert (access_inputs["walk_route_observation_count"] >= 0).all()
    assert (access_inputs[["nearest_origin_walk_km", "nearest_origin_walk_minutes", "mean_origin_walk_km", "mean_origin_walk_minutes"]] >= 0).all().all()
    for column in physical_fields + ["nearby_public_accessible_parking", "parking_information_published"]:
        assert set(access_inputs[column]) <= {"yes", "no", "unknown"}, f"accessibility inputs: invalid {column}"
    assert set(access_inputs["hero_collection_status"]) <= {"ok", "error", "not_collected"}

    print(
        "PASS: "
        f"facilities={len(facilities)} (병원={(facilities['type'] == '병원').sum()}, "
        f"약국={(facilities['type'] == '약국').sum()}), weather={len(weather)}, "
        f"air={len(air)}, population={len(population)}, operating_hours={len(hours)}, accessibility_profiles={len(accessibility)}, routes={len(routes)}, clinical_inputs={len(clinical)}, accessibility_inputs={len(access_inputs)}"
    )


if __name__ == "__main__":
    main()
