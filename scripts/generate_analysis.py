"""Reproduce the metrics used in the dashboard and presentation."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = ROOT / "output" / "analysis"


def main() -> None:
    facilities = pd.read_csv(DATA / "facilities.csv")
    population = pd.read_csv(DATA / "population.csv")
    total = population.loc[population["region"] == "부산광역시 금정구"].iloc[0]
    counts = facilities["type"].value_counts()
    dong = population.loc[population["region"] != "부산광역시 금정구"].copy()
    dong["elderly_rate_pct"] = dong["elderly_population"] / dong["population"] * 100
    highest = dong.sort_values("elderly_rate_pct").iloc[-1]
    metrics = {
        "reference_date": "2026-03-31",
        "population": int(total["population"]),
        "elderly_population": int(total["elderly_population"]),
        "elderly_rate_pct": round(total["elderly_population"] / total["population"] * 100, 1),
        "selected_hospitals": int(counts.get("병원", 0)),
        "selected_pharmacies": int(counts.get("약국", 0)),
        "selected_hospitals_per_10000": round(counts.get("병원", 0) / total["population"] * 10000, 2),
        "selected_pharmacies_per_10000": round(counts.get("약국", 0) / total["population"] * 10000, 2),
        "elderly_per_selected_hospital": round(total["elderly_population"] / counts.get("병원", 1)),
        "highest_elderly_rate_dong": highest["region"],
        "highest_elderly_rate_pct": round(highest["elderly_rate_pct"], 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    dong.to_csv(OUT / "dong_elderly_rates.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
