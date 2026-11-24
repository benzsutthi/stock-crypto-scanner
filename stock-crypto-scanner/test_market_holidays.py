import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from build_market_data import stock_history_stale
from market_holidays import is_market_holiday, is_trading_day
from refresh_policy import stock_session


class MarketHolidaysTest(unittest.TestCase):
    def test_thanksgiving_and_thai_holiday_skipped_in_session_and_staleness(self):
        # 2026-11-26 is US Thanksgiving (Thursday)
        self.assertTrue(is_market_holiday(date(2026, 11, 26), 'US'))
        self.assertFalse(is_trading_day(date(2026, 11, 26), 'US'))
        us_thanksgiving_evening = datetime(2026, 11, 26, 17, 0, tzinfo=ZoneInfo('America/New_York'))
        self.assertEqual(stock_session('US', us_thanksgiving_evening), '2026-11-25')
        self.assertFalse(stock_history_stale(date(2026, 11, 25), 'US', us_thanksgiving_evening))

        # 2026-12-10 is Thai Constitution Day (Thursday)
        self.assertTrue(is_market_holiday(date(2026, 12, 10), 'Thai'))
        thai_holiday_evening = datetime(2026, 12, 10, 18, 0, tzinfo=ZoneInfo('Asia/Bangkok'))
        self.assertEqual(stock_session('Thai', thai_holiday_evening), '2026-12-09')
        self.assertFalse(stock_history_stale(date(2026, 12, 9), 'Thai', thai_holiday_evening))


if __name__ == '__main__':
    unittest.main()
