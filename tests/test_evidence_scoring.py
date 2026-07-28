import unittest

from src.evidence_scoring import care_availability_score, enriched_accessibility_score, evidence_confidence_score, service_tags


class SupplementalEvidenceScoringTests(unittest.TestCase):
    def test_unknown_physical_access_is_neutral(self):
        evidence = {field: "unknown" for field in ("step_free_entrance", "elevator", "accessible_parking_on_site", "accessible_toilet", "accessible_entrance_route")}
        self.assertEqual(enriched_accessibility_score(55, evidence, "보행·이동 취약자"), 55.0)

    def test_only_confirmed_access_evidence_changes_score(self):
        evidence = {"nearby_public_accessible_parking": "yes", "parking_information_published": "yes"}
        self.assertEqual(enriched_accessibility_score(55, evidence, "고령자"), 67.0)
        self.assertIn("인근 장애인주차", service_tags({}, evidence))

    def test_published_care_times_create_real_score_difference(self):
        broad = {"night_care": "yes", "saturday_care": "yes", "sunday_or_holiday_care": "yes", "emergency_24h": "yes"}
        limited = {"night_care": "no", "saturday_care": "yes", "sunday_or_holiday_care": "no", "emergency_24h": "no"}
        unknown = {"night_care": "unknown", "saturday_care": "unknown", "sunday_or_holiday_care": "unknown", "emergency_24h": "unknown"}
        self.assertGreater(care_availability_score(broad), care_availability_score(unknown))
        self.assertGreater(care_availability_score(unknown), care_availability_score(limited))

    def test_confidence_measures_coverage_not_quality(self):
        sparse = evidence_confidence_score("prototype_estimate", {}, {}, {})
        covered = evidence_confidence_score("approximate_osm", {"source_url": "https://example.test"}, {"schedule_data_quality": "verified", "hero_collection_status": "ok"}, {"walk_route_observation_count": 3})
        self.assertGreater(covered, sparse)
        self.assertLessEqual(covered, 95.0)


if __name__ == "__main__":
    unittest.main()
