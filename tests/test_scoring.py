import unittest

import pandas as pd

from src.scoring import (
    air_quality_component,
    disease_matches,
    distance_component,
    format_duration,
    haversine_km,
    recommend,
    user_fit_component,
    weather_component,
    weighted_score,
)


class ComponentTests(unittest.TestCase):
    def test_duration_display(self):
        self.assertEqual(format_duration(59), "59분")
        self.assertEqual(format_duration(60), "1시간")
        self.assertEqual(format_duration(73), "1시간 13분")

    def test_haversine_same_point(self):
        self.assertEqual(haversine_km(35.23, 129.08, 35.23, 129.08), 0)

    def test_distance_boundaries(self):
        self.assertEqual([distance_component(x) for x in [0, 1, 3, 5, 15]], [100, 80, 50, 25, 0])
        distances = [0.2, 0.5, 0.9, 1.5, 2.5, 4, 8]
        scores = [distance_component(value) for value in distances]
        self.assertTrue(all(left > right for left, right in zip(scores, scores[1:])))

    def test_environment_components(self):
        self.assertEqual(weather_component(24, 0, "맑음"), 100)
        self.assertEqual(weather_component(24, 2, "비"), 70)
        self.assertEqual(weather_component(24, 12, "비"), 40)
        self.assertEqual([air_quality_component(x) for x in ["좋음", "보통", "나쁨", "매우 나쁨"]], [100, 80, 50, 30])

    def test_disease_mapping_and_fallback(self):
        matched, unmatched = disease_matches("내과|신경과", ["고혈압", "관절염"])
        self.assertEqual(matched, ["고혈압"])
        self.assertEqual(unmatched, ["관절염"])
        score, matched, unmatched = user_fit_component("일반 성인", 0.5, "", ["천식", "관절염"])
        self.assertEqual((score, matched, unmatched), (65, [], ["천식", "관절염"]))

    def test_weighted_score_range(self):
        raw, shown = weighted_score(100, 70, 50, 85)
        self.assertAlmostEqual(raw, 81.75)
        self.assertEqual(shown, 81.8)


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.facilities = pd.DataFrame(
            [
                {"facility_id": "B", "name": "먼 내과", "type": "병원", "latitude": 35.245, "longitude": 129.08, "specialty": "내과"},
                {"facility_id": "A", "name": "가까운 정형외과", "type": "병원", "latitude": 35.2301, "longitude": 129.08, "specialty": "정형외과"},
                {"facility_id": "C", "name": "가까운 내과", "type": "병원", "latitude": 35.2301, "longitude": 129.08, "specialty": "내과"},
            ]
        )

    def recommend(self, **overrides):
        params = dict(
            user_latitude=35.23,
            user_longitude=129.08,
            basic_type="일반 성인",
            selected_diseases=[],
            facility_type="병원",
            temperature=25,
            rainfall=0,
            weather_status="맑음",
            air_grade="보통",
            top_n=5,
        )
        params.update(overrides)
        return recommend(self.facilities, **params)

    def test_tie_breaker_is_deterministic(self):
        first = self.recommend()
        second = self.recommend()
        self.assertEqual(first["facility_id"].tolist(), ["A", "C", "B"])
        self.assertEqual(first["facility_id"].tolist(), second["facility_id"].tolist())

    def test_different_distances_produce_different_scores(self):
        result = self.recommend()
        close = result.loc[result["facility_id"] == "A"].iloc[0]
        far = result.loc[result["facility_id"] == "B"].iloc[0]
        self.assertNotEqual(close["distance_score"], far["distance_score"])
        self.assertGreater(close["final_score"], far["final_score"])

    def test_specialty_changes_rank(self):
        result = self.recommend(selected_diseases=["고혈압"])
        self.assertEqual(result.iloc[0]["facility_id"], "C")

    def test_each_result_has_explanations_and_components(self):
        result = self.recommend(basic_type="고령자", rainfall=12, weather_status="비")
        self.assertTrue(result["reasons"].map(lambda value: len(value) >= 2).all())
        self.assertTrue(result["final_score"].between(0, 100).all())
        for column in ["fit_score", "route_score", "accessibility_score", "operating_score", "confidence_score"]:
            self.assertIn(column, result)

    def test_rain_can_favor_farther_sheltered_route(self):
        facilities = self.facilities.copy()
        facilities.loc[facilities["facility_id"] == "B", "latitude"] = 35.2315
        access = pd.DataFrame([
            {"facility_id": "A", "route_factor": 1.1, "outdoor_ratio": 1.0, "slope_level": 2, "transfer_count": 0, "step_free": False, "elevator": False, "accessible_parking": False, "data_status": "prototype_estimate"},
            {"facility_id": "B", "route_factor": 1.1, "outdoor_ratio": 0.1, "slope_level": 0, "transfer_count": 0, "step_free": True, "elevator": True, "accessible_parking": True, "data_status": "prototype_estimate"},
            {"facility_id": "C", "route_factor": 1.1, "outdoor_ratio": 1.0, "slope_level": 2, "transfer_count": 0, "step_free": False, "elevator": False, "accessible_parking": False, "data_status": "prototype_estimate"},
        ])
        result = recommend(facilities, user_latitude=35.23, user_longitude=129.08, basic_type="일반 성인", selected_diseases=[], facility_type="병원", temperature=25, rainfall=12, weather_status="비", air_grade="보통", accessibility=access)
        self.assertEqual(result.iloc[0]["facility_id"], "B")

    def test_missing_coordinates_raise(self):
        broken = self.facilities.copy()
        broken.loc[0, "latitude"] = None
        with self.assertRaises(ValueError):
            recommend(
                broken,
                user_latitude=35.23,
                user_longitude=129.08,
                basic_type="일반 성인",
                selected_diseases=[],
                facility_type="병원",
                temperature=25,
                rainfall=0,
                weather_status="맑음",
                air_grade="보통",
            )


if __name__ == "__main__":
    unittest.main()
