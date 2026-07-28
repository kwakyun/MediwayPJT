import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.operating_hours import operating_status, parse_range, today_schedule


KST = ZoneInfo("Asia/Seoul")


class OperatingHoursTests(unittest.TestCase):
    def setUp(self):
        self.schedule = {
            "data_status": "available",
            "mon": "09:00-18:00",
            "tue": "09:00-18:00",
            "wed": "09:00-18:00",
            "thu": "09:00-18:00",
            "fri": "09:00-18:00",
            "sat": "09:00-13:00",
            "sun": "휴무",
            "lunch": "12:30-13:30",
        }

    def test_open_lunch_closed_and_weekly_closure(self):
        self.assertEqual(operating_status(self.schedule, datetime(2026, 7, 13, 10, 0, tzinfo=KST))["code"], "open")
        self.assertEqual(operating_status(self.schedule, datetime(2026, 7, 13, 13, 0, tzinfo=KST))["code"], "lunch")
        self.assertEqual(operating_status(self.schedule, datetime(2026, 7, 13, 19, 0, tzinfo=KST))["code"], "closed")
        self.assertEqual(operating_status(self.schedule, datetime(2026, 7, 12, 10, 0, tzinfo=KST))["label"], "오늘 휴무")

    def test_unknown_is_never_guessed(self):
        self.assertEqual(operating_status({"data_status": "unknown"})["code"], "unknown")
        self.assertEqual(operating_status(None)["code"], "unknown")

    def test_parser_and_today_label(self):
        self.assertEqual([value.isoformat(timespec="minutes") for value in parse_range("09:00-18:00")], ["09:00", "18:00"])
        self.assertEqual(today_schedule(self.schedule, datetime(2026, 7, 13, 10, 0, tzinfo=KST)), ("월요일", "09:00-18:00"))


if __name__ == "__main__":
    unittest.main()
