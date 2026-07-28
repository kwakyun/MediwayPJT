import unittest

from src.mobility import MobilityError, parse_odsay_response, transport_options


class MobilityTests(unittest.TestCase):
    def sample_payload(self):
        return {"result": {"path": [{
            "pathType": 3,
            "info": {
                "totalTime": 38, "payment": 1550, "busTransitCount": 1, "subwayTransitCount": 1,
                "totalWalk": 620, "firstStartStation": "구서역", "lastEndStation": "병원앞",
            },
            "subPath": [
                {"trafficType": 3, "sectionTime": 6},
                {"trafficType": 1, "sectionTime": 15},
                {"trafficType": 3, "sectionTime": 4},
                {"trafficType": 2, "sectionTime": 13},
            ],
        }]}}

    def test_parse_transit_time_fare_and_walk(self):
        estimate = parse_odsay_response(self.sample_payload())[0]
        self.assertEqual(estimate["route_type"], "버스+지하철")
        self.assertEqual(estimate["total_minutes"], 38.0)
        self.assertEqual(estimate["outdoor_minutes"], 10.0)
        self.assertEqual(estimate["transit_minutes"], 28.0)
        self.assertEqual(estimate["fare"], 1550)

    def test_total_walk_time_has_priority(self):
        payload = self.sample_payload()
        payload["result"]["path"][0]["info"]["totalWalkTime"] = 8
        self.assertEqual(parse_odsay_response(payload)[0]["outdoor_minutes"], 8.0)

    def test_transport_options_are_mece(self):
        estimate = parse_odsay_response(self.sample_payload())
        rows = transport_options(55, 55, estimate)
        self.assertEqual(rows[1]["총 소요시간"], 38.0)
        self.assertEqual(rows[1]["대중교통시간"], 28.0)
        self.assertEqual(rows[1]["야외시간"], 10.0)
        self.assertEqual(rows[1]["예상 요금"], 1550)

    def test_empty_route_is_controlled(self):
        with self.assertRaises(MobilityError):
            parse_odsay_response({"result": {"path": []}})


if __name__ == "__main__":
    unittest.main()
