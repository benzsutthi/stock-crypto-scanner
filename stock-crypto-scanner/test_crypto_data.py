import unittest
from datetime import datetime, timezone
import pandas as pd
from build_crypto_data import confirmed, enrich


class CryptoDataTest(unittest.TestCase):
    def test_incomplete_current_utc_day_is_excluded(self):
        frame = pd.DataFrame({'Close':[100,200], 'High':[101,201], 'Low':[99,199], 'Volume':[10,20]},
                             index=pd.to_datetime(['2026-09-30','2026-10-01'], utc=True))
        result = confirmed(frame, today=pd.Timestamp('2026-10-01').date())
        self.assertEqual(len(result), 1)
        self.assertEqual(result.Close.iloc[-1], 100)

    def test_quotes_preserved_and_signals_come_from_confirmed_history(self):
        index = pd.date_range(end=pd.Timestamp(datetime.now(timezone.utc)).normalize()-pd.Timedelta(days=1), periods=60)
        frame = pd.DataFrame({'Close':[100.]*59+[102.], 'High':[101.]*59+[105.],
                              'Low':[99.]*60, 'Volume':[100.]*59+[200.]}, index=index)
        asset = enrich({'symbol':'BTC','price':103.,'change':3.}, frame, 'test')
        self.assertEqual(asset['price'],103.)
        self.assertEqual(asset['techPrice'],102.)
        self.assertEqual(asset['change'],3.)
        self.assertEqual(asset['volumeRatio'],2.)
        self.assertFalse(asset['historyUnavailable'])
        self.assertIn('breakout',[s['type'] for s in asset['signals']])

    def test_missing_history_never_invents_rsi_or_signals(self):
        asset = enrich({'symbol':'UNKNOWN','price':1.,'change':None}, pd.DataFrame(), None)
        self.assertIsNone(asset['rsi'])
        self.assertEqual(asset['signals'],[])
        self.assertTrue(asset['historyUnavailable'])

    def test_stale_history_and_quote_are_not_early_candidates(self):
        index = pd.date_range(end=pd.Timestamp(datetime.now(timezone.utc)).normalize()-pd.Timedelta(days=2), periods=60)
        frame = pd.DataFrame({'Close':[100.]*60, 'High':[101.]*60,
                              'Low':[99.]*60, 'Volume':[100.]*60}, index=index)
        asset = enrich({'symbol':'BTC','price':100.,'change':0.}, frame, 'test')
        self.assertTrue(asset['historyUnavailable'])
        self.assertEqual(asset['signals'], [])
        frame.index += pd.Timedelta(days=1)
        asset = enrich({'symbol':'BTC','price':100.,'change':0.,'quoteUpdatedAt':'invalid'}, frame, 'test')
        self.assertTrue(asset['quoteStale'])
        self.assertFalse(asset['earlyCycle'])


if __name__ == '__main__':
    unittest.main()
