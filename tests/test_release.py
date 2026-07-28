import unittest
from pathlib import Path

import pandas as pd

from src.scenarios import REFERENCE_LOCATIONS, REFERENCE_ORIGIN_IDS, SCENARIOS
from src.scoring import recommend


ROOT = Path(__file__).resolve().parents[1]


class ReleaseCrossChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = ROOT / "data" / "processed"
        cls.facilities = pd.read_csv(data / "facilities.csv")
        cls.weather = pd.read_csv(data / "weather.csv")
        cls.air = pd.read_csv(data / "air_quality.csv")
        cls.population = pd.read_csv(data / "population.csv")
        cls.accessibility = pd.read_csv(data / "facility_accessibility.csv")
        cls.schedules = pd.read_csv(data / "operating_hours.csv")
        cls.routes = pd.read_csv(data / "walking_routes.csv")
        cls.clinical_inputs = pd.read_csv(data / "clinical_condition_inputs.csv")
        cls.accessibility_inputs = pd.read_csv(data / "facility_accessibility_inputs.csv")

    def run_scenario(self, label):
        scenario = SCENARIOS[label]
        weather = self.weather.loc[self.weather.scenario_id == scenario["scenario_id"]].iloc[0]
        air = self.air.loc[self.air.scenario_id == scenario["scenario_id"]].iloc[0]
        latitude, longitude = REFERENCE_LOCATIONS[scenario["location_name"]]
        return recommend(
            self.facilities,
            user_latitude=latitude,
            user_longitude=longitude,
            basic_type=scenario["basic_type"],
            selected_diseases=scenario["selected_diseases"],
            facility_type=scenario["facility_type"],
            temperature=float(weather.temperature),
            rainfall=float(weather.rainfall),
            weather_status=str(weather.weather_status),
            air_grade=str(air.air_grade),
            accessibility=self.accessibility,
            schedules=self.schedules,
            routes=self.routes,
            origin_id=REFERENCE_ORIGIN_IDS.get(scenario["location_name"]),
            clinical_conditions=self.clinical_inputs,
            accessibility_inputs=self.accessibility_inputs,
        )

    def test_all_presentation_scenarios_match_frozen_top_results(self):
        expected = {
            "기본 조건": ("지온병원", 64.6),
            "비 오는 날 · 고령자": ("더케이부산병원", 80.6),
            "대기질 민감 · 호흡기": ("지온병원", 64.6),
            "복합 건강 조건": ("세웅병원", 69.7),
        }
        for label, (name, score) in expected.items():
            with self.subTest(label=label):
                result = self.run_scenario(label)
                self.assertEqual(list(result["rank"]), [1, 2, 3, 4, 5])
                self.assertEqual(result.iloc[0]["name"], name)
                self.assertEqual(result.iloc[0]["final_score"], score)

    def test_three_results_match_manual_weighted_formula(self):
        result = self.run_scenario("대기질 민감 · 호흡기")
        for row in result.iloc[:3].itertuples():
            manual = round(
                row.fit_score * 0.35
                + row.route_score * 0.30
                + row.accessibility_score * 0.20
                + row.operating_score * 0.10
                + row.confidence_score * 0.05,
                1,
            )
            self.assertEqual(row.final_score, manual)

    def test_top_five_card_map_contract_and_reasons(self):
        result = self.run_scenario("복합 건강 조건")
        self.assertEqual(result["rank"].tolist(), list(range(1, 6)))
        for row in result.itertuples():
            self.assertTrue(row.reasons)
            self.assertTrue(any("이동" in reason or "야외" in reason for reason in row.reasons))
            self.assertEqual(row.type, "병원")

    def test_empty_and_invalid_data_paths_are_controlled(self):
        base = dict(
            user_latitude=35.23,
            user_longitude=129.09,
            basic_type="일반 성인",
            selected_diseases=[],
            temperature=25.0,
            rainfall=0.0,
            weather_status="맑음",
            air_grade="보통",
        )
        empty = recommend(self.facilities, facility_type="보건소", **base)
        self.assertTrue(empty.empty)
        with self.assertRaisesRegex(ValueError, "Missing facility columns"):
            recommend(self.facilities.drop(columns=["latitude"]), facility_type="병원", **base)

    def test_regional_metrics_match_report_values(self):
        total = self.population.loc[self.population.region == "부산광역시 금정구"].iloc[0]
        self.assertEqual(int(total.population), 206033)
        self.assertEqual(int(total.elderly_population), 59484)
        self.assertAlmostEqual(total.elderly_population / total.population * 100, 28.9, places=1)
        self.assertEqual(self.facilities.type.value_counts().to_dict(), {"병원": 15, "약국": 12})


if __name__ == "__main__":
    unittest.main()
