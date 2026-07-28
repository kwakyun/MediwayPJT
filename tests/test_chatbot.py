import unittest

from src.chatbot import ask_gemini, emergency_answer, extract_gemini_text, local_cs_answer


class ChatbotTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "region": "부산광역시 금정구",
            "facility_counts": {"병원": 15, "약국": 12},
            "population": {"population": 206033, "elderly_population": 59484, "reference_date": "2026-03-31"},
            "facilities": [{
                "name": "지온병원", "type": "병원", "address": "부산광역시 금정구 온천장로 146 (장전동)",
                "specialty": "내과|정형외과", "phone": "051-714-5770", "schedule_text": "월~금 09:00-18:00",
                "schedule_status": "unknown",
            }],
            "last_recommendation": {
                "location": "현재 위치",
                "results": [{
                    "rank": 1, "name": "지온병원", "distance_km": 1.2,
                    "travel_minutes": 18, "outdoor_minutes": 7,
                    "transit": {"route_type": "버스", "total_minutes": 15, "fare": 1550},
                }],
            },
        }

    def test_emergency_message_precedes_normal_cs(self):
        answer = emergency_answer("숨을 못 쉬고 의식이 없어")
        self.assertIn("즉시 119", answer)

    def test_facility_and_transport_answers_use_context(self):
        self.assertIn("051-714-5770", local_cs_answer("지온병원 정보 알려줘", self.context))
        transport = local_cs_answer("최근 추천 거리와 교통 알려줘", self.context)
        self.assertIn("1.2km", transport)
        self.assertIn("1,550원", transport)

    def test_regional_answer_uses_registered_counts(self):
        answer = local_cs_answer("금정구 병원과 약국은 몇 곳이야?", self.context)
        self.assertIn("15곳", answer)
        self.assertIn("12곳", answer)

    def test_gemini_output_and_safety_prompt(self):
        captured = {}

        def requester(payload, api_key, model, timeout):
            captured.update({"payload": payload, "api_key": api_key, "model": model, "timeout": timeout})
            return {"candidates": [{"content": {"role": "model", "parts": [{"text": "안내 답변"}]}}]}

        answer = ask_gemini("어디로 가야 해?", [], self.context, "test-key", requester=requester)
        self.assertEqual(answer, "안내 답변")
        self.assertEqual(captured["model"], "gemini-3.5-flash")
        self.assertIn("진단", captured["payload"]["systemInstruction"]["parts"][0]["text"])
        self.assertEqual(captured["payload"]["generationConfig"]["maxOutputTokens"], 1200)
        self.assertEqual(captured["payload"]["generationConfig"]["thinkingConfig"]["thinkingLevel"], "minimal")
        self.assertEqual(extract_gemini_text({"candidates": [{"content": {"parts": [{"text": "확인"}]}}]}), "확인")

    def test_gemini_blocked_prompt_is_controlled(self):
        with self.assertRaisesRegex(Exception, "안전 필터"):
            extract_gemini_text({"promptFeedback": {"blockReason": "SAFETY"}})


if __name__ == "__main__":
    unittest.main()
