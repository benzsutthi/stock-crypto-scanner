import unittest
from unittest.mock import patch, MagicMock

import requests
import watchlist_alerts


class WatchlistAlertsTest(unittest.TestCase):
    def test_select_new_filters_existing_active_signals_and_same_date(self):
        state = {'US:NVDA': {'date': '2026-11-20', 'active': ['breakout']}}
        same_day = {'market': 'US', 'symbol': 'NVDA', 'priceDate': '2026-11-20', 'signals': [{'type': 'macd'}]}
        self.assertEqual(watchlist_alerts.select_new(same_day, state), [])
        next_day = {
            'market': 'US',
            'symbol': 'NVDA',
            'priceDate': '2026-11-21',
            'signals': [{'type': 'breakout'}, {'type': 'macd'}],
        }
        self.assertEqual(watchlist_alerts.select_new(next_day, state), [{'type': 'macd'}])

    def test_send_watchlist_broadcast_uses_retry_key_and_handles_409(self):
        resp_500 = MagicMock(status_code=500)
        resp_409 = MagicMock(status_code=409, headers={'x-line-accepted-request-id': 'req-123'})
        with patch('watchlist_alerts.requests.post', side_effect=[resp_500, resp_409]) as mock_post, \
             patch('watchlist_alerts.time.sleep'):
            watchlist_alerts.send_watchlist_broadcast('tok', 'hello', 'All/2026-11-23')
        self.assertEqual(mock_post.call_count, 2)
        headers0 = mock_post.call_args_list[0].kwargs['headers']
        headers1 = mock_post.call_args_list[1].kwargs['headers']
        self.assertEqual(headers0['X-Line-Retry-Key'], headers1['X-Line-Retry-Key'])

    def test_send_watchlist_broadcast_rejects_oversized_message(self):
        with self.assertRaises(RuntimeError):
            watchlist_alerts.send_watchlist_broadcast('tok', 'x' * 4901, 'All/2026-11-23')


if __name__ == '__main__':
    unittest.main()
