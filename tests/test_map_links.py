import unittest

from src.map_links import compact_map_query


class MapQueryTests(unittest.TestCase):
    def test_detailed_address_is_reduced_to_administrative_area(self):
        query = compact_map_query(
            "지온병원",
            "부산광역시 금정구 온천장로 146, 지하1,지상3~11층 (장전동)",
        )
        self.assertEqual(query, "지온병원 부산 금정구 장전동")
        self.assertNotIn("146", query)
        self.assertNotIn("지하", query)

    def test_query_remains_usable_without_address(self):
        self.assertEqual(compact_map_query("세웅병원", ""), "세웅병원")


if __name__ == "__main__":
    unittest.main()
