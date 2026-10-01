import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pandas as pd
from technicals import analyze
from watchlist_alerts import select_new, main


class SignalsTest(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'Close': [100.] * 60, 'High': [101.] * 60, 'Volume': [100.] * 60})

    def test_flat_rsi_and_no_breakout(self):
        result = analyze(self.frame())
        self.assertEqual(result['rsi'], 50)
        self.assertEqual(result['signals'], [])

    def test_previous_high_and_volume_exclude_current_bar(self):
        frame = self.frame()
        frame.loc[59, ['Close', 'High', 'Volume']] = [102, 105, 200]
        result = analyze(frame)
        self.assertEqual(result['high20'], 101)
        self.assertEqual(result['volumeRatio'], 2)
        self.assertIn('breakout', [s['type'] for s in result['signals']])
        frame.loc[59, 'Close'] = 101
        self.assertNotIn('breakout', [s['type'] for s in analyze(frame)['signals']])

    def test_alert_only_new_types_and_never_replay_same_date(self):
        asset = dict(market='US', symbol='NVDA', priceDate='2026-10-01',
                     signals=[{'type': 'breakout'}, {'type': 'volume'}])
        state = {'US:NVDA': {'date': '2026-09-30', 'active': ['breakout']}}
        self.assertEqual(select_new(asset, state), [{'type': 'volume'}])
        state['US:NVDA']['date'] = '2026-10-01'
        self.assertEqual(select_new(asset, state), [])

    def test_failed_line_request_never_advances_dedup_state(self):
        frame = self.frame()
        frame['Low'] = 99.
        frame.index = pd.date_range(end=pd.Timestamp.now().normalize()-pd.Timedelta(days=2), periods=60)
        frame.loc[frame.index[-1], 'Close'] = 102
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            path.write_text('{}')
            response = Mock()
            response.raise_for_status.side_effect = RuntimeError('LINE rejected')
            with patch.dict('os.environ', {'LINE_CHANNEL_ACCESS_TOKEN':'test', 'WATCHLIST_JSON':'["US:NVDA"]', 'ALERT_STATE_PATH':str(path), 'ALERT_MARKET':'All'}), patch('watchlist_alerts.yf.Ticker') as ticker, patch('watchlist_alerts.requests.post', return_value=response):
                ticker.return_value.history.return_value = frame
                with self.assertRaises(RuntimeError):
                    main()
            self.assertEqual(json.loads(path.read_text()), {})


if __name__ == '__main__':
    unittest.main()
