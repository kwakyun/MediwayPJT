import unittest

from src.geolocation import _validated_location


class GeolocationTests(unittest.TestCase):
    def test_valid_location_is_rounded_for_stable_route_caching(self):
        value = _validated_location({"latitude": 35.2312349, "longitude": 129.0876549, "accuracy": 18.4})
        self.assertEqual(value, {"latitude": 35.23123, "longitude": 129.08765, "accuracy": 18.0})

    def test_invalid_location_is_rejected(self):
        self.assertIsNone(_validated_location({"latitude": 135, "longitude": 129, "accuracy": 20}))
        self.assertIsNone(_validated_location(None))


if __name__ == "__main__":
    unittest.main()
