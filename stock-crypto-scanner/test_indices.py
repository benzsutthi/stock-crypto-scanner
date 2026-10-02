import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import tempfile
import json
from pathlib import Path
import pandas as pd
from build_indices import compose_set, build_snapshot


class IndexOverviewTest(unittest.TestCase):
    def bars(self):
        return pd.DataFrame({'Close':[99.,110.,111.]},index=pd.to_datetime([
            '2026-10-01T16:15:00+07:00','2026-10-02T10:00:00+07:00','2026-10-02T10:15:00+07:00']))

    def test_quote_change_uses_previous_session_close_not_chart_start(self):
        info={'regularMarketPrice':110.25,'regularMarketPreviousClose':100.,
              'regularMarketChange':999.,'regularMarketTime':int(datetime(2026,10,2,3,16,tzinfo=timezone.utc).timestamp()),
              'regularMarketOpen':105.,'regularMarketDayHigh':115.,'regularMarketDayLow':104.}
        result=compose_set(info,self.bars())
        self.assertEqual(result['value'],110.25)
        self.assertEqual(result['changePoints'],10.25)
        self.assertEqual(result['changePercent'],10.25)
        self.assertEqual(result['high'],115.)
        self.assertEqual(result['chartDate'],'2026-10-02')
        self.assertEqual([p['value'] for p in result['chart']],[110.,111.])

    def test_intraday_fallback_does_not_invent_previous_close(self):
        result=compose_set({'regularMarketPrice':0,'regularMarketChange':999},self.bars())
        self.assertEqual(result['value'],111.)
        self.assertEqual(result['quoteType'],'15m')
        self.assertIsNone(result['changePercent'])
        self.assertIsNone(result['previousClose'])

    def test_daily_fallback_and_invalid_quotes(self):
        daily=pd.DataFrame({'Close':[100.,108.]},index=pd.to_datetime(['2026-10-01','2026-10-02']))
        result=compose_set({},pd.DataFrame(),daily)
        self.assertEqual(result['changePoints'],8.)
        self.assertEqual(result['quoteType'],'daily-bar')
        with self.assertRaises(ValueError):
            compose_set({'regularMarketPrice':float('nan')},pd.DataFrame())

    def test_failed_provider_retains_original_quote_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            previous=Path(directory)/'previous.json'
            output=Path(directory)/'indices.json'
            original={'value':1500.,'quoteAt':'2026-10-01T09:00:00+00:00','chart':[]}
            previous.write_text(json.dumps({'indices':{'SET':original}}))
            ticker=Mock()
            ticker.get_info.side_effect=RuntimeError('unavailable')
            ticker.history.return_value=pd.DataFrame()
            with patch('build_indices.yf.Ticker',return_value=ticker):
                result=build_snapshot(output,previous)
            self.assertEqual(result['indices']['SET']['quoteAt'],original['quoteAt'])
            self.assertEqual(result['indices']['SET']['value'],1500.)
            self.assertTrue(result['indices']['SET']['updateError'])


if __name__=='__main__':
    unittest.main()
