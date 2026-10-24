import unittest
from datetime import datetime

from schedule import ZONE, allowed, next_slot


class QuietHoursTest(unittest.TestCase):
    def test_midnight_and_morning_do_not_collect(self):
        for time in ("2026-10-24T00:00:00+08:00", "2026-10-24T11:59:59+08:00"):
            current = datetime.fromisoformat(time)
            self.assertFalse(allowed(current))
            self.assertEqual(next_slot(current).hour, 12)

    def test_no_catch_up_overnight(self):
        self.assertEqual(next_slot(datetime.fromisoformat("2026-10-23T20:00:01+08:00")).isoformat(), "2026-10-24T12:00:00+08:00")

    def test_utc_is_converted_to_beijing_time(self):
        current = datetime.fromisoformat("2026-10-24T03:59:59+00:00")
        self.assertFalse(allowed(current))
        self.assertEqual(next_slot(current).isoformat(), "2026-10-24T12:00:00+08:00")

    def test_daily_slots_are_four_hours_apart(self):
        current = datetime.fromisoformat("2026-10-24T12:00:00+08:00")
        self.assertTrue(allowed(current))
        self.assertEqual(next_slot(current).hour, 16)
        self.assertEqual(next_slot(next_slot(current)).hour, 20)


if __name__ == "__main__":
    unittest.main()
