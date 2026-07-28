import unittest

from streamlit.testing.v1 import AppTest


class StreamlitSmokeTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file("app.py").run(timeout=45)

    def assert_clean(self):
        self.assertEqual([item.value for item in self.app.exception], [])

    def test_recommendation_first_view(self):
        self.assert_clean()
        self.assertTrue(any("내 조건에 맞는" in item.value for item in self.app.markdown))
        self.assertEqual([item.label for item in self.app.metric[:4]], ["날씨", "PM10", "PM2.5", "비교 후보"])
        self.assertEqual(self.app.selectbox[0].label, "빠른 조건 설정")
        self.assertFalse(any("DEMO" in option for option in self.app.selectbox[0].options))
        self.assertTrue(any("활성 검색 조건" in item.value for item in self.app.markdown))
        self.assertTrue(any("운영시간·상세 보기" in item.label for item in self.app.expander))
        self.assertTrue(any("도보·버스·지하철 시간과 요금" in item.value for item in self.app.markdown))
        self.assertTrue(any("버스·지하철" in item.label for item in self.app.tabs))
        self.assertGreaterEqual(len(self.app.get("plotly_chart")), 1)

    def test_all_navigation_pages(self):
        self.app.radio[0].set_value("메디웨이 상담").run(timeout=45)
        self.assert_clean()
        self.assertTrue(any("지역 의료·이동 상담" in item.value for item in self.app.markdown))
        self.assertGreaterEqual(len(self.app.chat_message), 1)
        self.app.radio[0].set_value("지역 의료 현황").run(timeout=45)
        self.assert_clean()
        self.assertTrue(any("우리 지역" in item.value for item in self.app.markdown))
        self.app.radio[0].set_value("추천 기준 안내").run(timeout=45)
        self.assert_clean()
        self.assertTrue(any("추천 기준" in item.value for item in self.app.markdown))

    def test_respiratory_preset(self):
        self.app.selectbox[0].set_value("대기질 민감 · 호흡기").run(timeout=45)
        self.assert_clean()
        self.assertIn("PM10", [item.label for item in self.app.metric])

    def test_operating_information_uses_public_notice_before_phone_fallback(self):
        self.assert_clean()
        status_messages = [item.value for item in self.app.info] + [item.value for item in self.app.warning]
        self.assertFalse(any("공개 출처에서 운영시간을 확인하지 못했습니다" in value for value in status_messages))
        self.assertTrue(any("공개된 운영 안내" in value for value in status_messages))

    def test_result_cards_do_not_repeat_route_time_in_reasons(self):
        self.assert_clean()
        cards = [item.value for item in self.app.markdown if 'class="result-card' in item.value]
        self.assertEqual(len(cards), 5)
        self.assertTrue(all("예상 이동" not in card for card in cards))
        self.assertTrue(all("card-label\">진료" in card and "card-label\">근거" in card for card in cards))

    def test_browser_location_can_replace_preset_origin(self):
        self.app.session_state["mediway_browser_location"] = {
            "location": {"latitude": 35.2309, "longitude": 129.0897, "accuracy": 20}
        }
        self.app.run(timeout=45)
        self.assert_clean()
        self.assertTrue(any("현재 위치" in item.value for item in self.app.markdown))
        cards = [item.value for item in self.app.markdown if 'class="result-card' in item.value]
        self.assertTrue(all("거리 " in card for card in cards))

    def test_complex_preset_keeps_both_disease_groups(self):
        self.app.selectbox[0].set_value("복합 건강 조건").run(timeout=45)
        self.assert_clean()
        selected_values = [value for widget in self.app.multiselect for value in widget.value]
        self.assertIn("심뇌혈관 질환", selected_values)
        self.assertIn("근골격계 질환", selected_values)
        self.assertIn("관절염", selected_values)
        self.assertIn("고혈압", selected_values)
        fallback_messages = [item.value for item in self.app.info]
        self.assertTrue(any("공개된 운영 안내" in value or "운영시간 문의" in value for value in fallback_messages))


if __name__ == "__main__":
    unittest.main()
