import unittest
from datetime import datetime, timezone
import pandas as pd
from refresh_policy import stock_session, market_open, reusable, overlay_quote


class RefreshPolicyTest(unittest.TestCase):
    def at(self, value):
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)

    def test_closed_session_buffer_and_weekend(self):
        self.assertEqual(stock_session('US', self.at('2026-10-02T20:00:00')), '2026-10-01')
        self.assertEqual(stock_session('US', self.at('2026-10-02T20:30:00')), '2026-10-02')
        self.assertEqual(stock_session('US', self.at('2026-10-03T16:00:00')), '2026-10-02')

    def test_new_york_dst_market_hours(self):
        self.assertTrue(market_open('US', self.at('2026-07-06T13:30:00')))
        self.assertFalse(market_open('US', self.at('2026-11-02T13:30:00')))
        self.assertTrue(market_open('US', self.at('2026-11-02T14:30:00')))

    def test_cache_expires_when_a_new_session_is_due(self):
        asset={'historyTarget':'2026-10-01','priceDate':'2026-10-01','historyCheckedAt':'2026-10-01T12:00:00+00:00'}
        self.assertTrue(reusable(asset,'2026-10-01',self.at('2026-10-01T13:00:00')))
        self.assertFalse(reusable(asset,'2026-10-02',self.at('2026-10-01T13:00:00')))
        asset['priceDate']='2026-09-30'
        self.assertFalse(reusable(asset,'2026-10-01',self.at('2026-10-01T13:00:00')))

    def test_intraday_quote_preserves_daily_signals_and_uses_correct_baseline(self):
        asset={'price':100.,'techPrice':100.,'previousClose':95.,'priceDate':'2026-10-01','rsi':60.,'signals':[{'type':'breakout'}]}
        frame=pd.DataFrame({'Close':[110.]},index=pd.to_datetime(['2026-10-02T10:00:00+07:00']))
        result=overlay_quote(asset,frame)
        self.assertEqual(result['change'],10.)
        self.assertEqual(result['rsi'],60.)
        self.assertEqual(result['signals'],asset['signals'])
        frame.index=pd.to_datetime(['2026-10-01T15:00:00+07:00'])
        self.assertEqual(overlay_quote(asset,frame)['change'],15.79)
        frame.index=pd.to_datetime(['2026-09-30T15:00:00+07:00'])
        self.assertEqual(overlay_quote(asset,frame),asset)

    def test_previous_intraday_session_is_used_when_daily_history_lags(self):
        asset={'price':100.,'techPrice':100.,'previousClose':95.,'priceDate':'2026-09-30'}
        frame=pd.DataFrame({'Close':[97.,110.]},index=pd.to_datetime(['2026-10-01T16:15:00+07:00','2026-10-02T10:00:00+07:00']))
        self.assertEqual(overlay_quote(asset,frame)['change'],13.4)


if __name__=='__main__':
    unittest.main()
