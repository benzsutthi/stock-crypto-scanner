import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pandas as pd
from market_history import clean_history
from build_market_data import confirmed_stock, stock_history_stale, extract_ticker_frame, build_snapshot
from build_crypto_data import history_ticker
from technicals import analyze


class MarketHistoryTest(unittest.TestCase):
    def frame(self):
        closes = [99., 101.] * 29 + [99., 101.2]
        return pd.DataFrame({'Close': closes, 'High': [102.] * 60,
                             'Low': [98.] * 60, 'Volume': [100.] * 59 + [150.]},
                            index=pd.date_range('2026-07-01', periods=60))

    def test_early_cycle_confirmed_and_not_chasing(self):
        frame = self.frame()
        result = analyze(frame)
        self.assertTrue(result['earlyCycle'], result['earlyConditions'])
        self.assertEqual(result['earlyScore'], 100)
        self.assertIn('early-cycle', [s['type'] for s in result['signals']])
        frame.iloc[-1, frame.columns.get_loc('Close')] = 120.
        self.assertFalse(analyze(frame)['earlyCycle'])

    def test_volume_and_wide_base_do_not_qualify(self):
        frame = self.frame()
        frame.iloc[-1, frame.columns.get_loc('Volume')] = 100.
        self.assertFalse(analyze(frame)['earlyCycle'])
        frame = self.frame()
        frame['Low'] = 70.
        self.assertFalse(analyze(frame)['earlyCycle'])

    def test_invalid_bars_duplicates_and_sorting(self):
        frame = self.frame().iloc[-4:].iloc[::-1]
        frame = pd.concat([frame, frame.iloc[:1]])
        frame.iloc[1, frame.columns.get_loc('Close')] = float('inf')
        frame.iloc[2, frame.columns.get_loc('Volume')] = -1
        result = clean_history(frame)
        self.assertEqual(len(result), 2)
        self.assertTrue(result.index.is_monotonic_increasing)
        self.assertFalse(result.index.has_duplicates)

    def test_close_buffer_and_future_bars(self):
        frame = self.frame().iloc[:3].copy()
        frame.index = pd.date_range('2026-09-30', periods=3)
        before = datetime(2026, 10, 1, 16, 29, tzinfo=ZoneInfo('America/New_York'))
        after = before.replace(minute=30)
        self.assertEqual(confirmed_stock(frame, 'US', before).index[-1].date().isoformat(), '2026-09-30')
        self.assertEqual(confirmed_stock(frame, 'US', after).index[-1].date().isoformat(), '2026-10-01')

    def test_weekend_is_not_a_missing_session(self):
        now = datetime(2026, 10, 4, 12, tzinfo=ZoneInfo('America/New_York'))
        self.assertFalse(stock_history_stale(pd.Timestamp('2026-10-02').date(), 'US', now))
        self.assertTrue(stock_history_stale(pd.Timestamp('2026-10-01').date(), 'US', now))

    def test_identity_not_just_symbol_and_multiindex_orientation(self):
        self.assertEqual(history_ticker({'symbol': 'BTC', 'id': 'btc-bitcoin'}), 'BTC-USD')
        self.assertIsNone(history_ticker({'symbol': 'BTC', 'id': 'other-bitcoin'}))
        self.assertIsNone(history_ticker({'symbol': 'UNKNOWN', 'id': 'unknown'}))
        frame = self.frame()
        downloaded = pd.concat({'BTC-USD': frame}, axis=1)
        pd.testing.assert_frame_equal(extract_ticker_frame(downloaded, 'BTC-USD'), frame)
        pd.testing.assert_frame_equal(extract_ticker_frame(downloaded.swaplevel(axis=1), 'BTC-USD'), frame)
        self.assertTrue(extract_ticker_frame(downloaded, 'WRONG').empty)

    def test_partial_download_retries_and_preserves_previous_asset(self):
        frame = self.frame()
        downloaded = pd.concat({'AAA': frame, 'CCC.BK': frame}, axis=1)
        response = Mock()
        response.json.return_value = {'assets': [{'market': 'US', 'symbol': 'BBB', 'price': 10.,
                                                 'earlyCycle': True, 'signals': [{'type': 'early-cycle'}]}]}
        with tempfile.TemporaryDirectory() as directory, \
                patch('build_market_data.US_STOCKS', ['AAA', 'BBB']), \
                patch('build_market_data.THAI_STOCKS', ['CCC.BK']), \
                patch('build_market_data.yf.download', return_value=downloaded), \
                patch('build_market_data.yf.Ticker') as ticker, \
                patch('build_market_data.stock_history_stale', return_value=False), \
                patch('build_market_data.requests.get', return_value=response):
            ticker.return_value.history.return_value = pd.DataFrame()
            result = build_snapshot(Path(directory)/'stocks.json')
            self.assertEqual(len(result['assets']), 3)
            self.assertEqual(result['failedSymbols'], ['BBB'])
            cached = next(a for a in result['assets'] if a['symbol'] == 'BBB')
            self.assertTrue(cached['historyStale'])
            self.assertFalse(cached['earlyCycle'])
            self.assertEqual(cached['signals'], [])
            ticker.assert_called_once_with('BBB')


if __name__ == '__main__':
    unittest.main()
