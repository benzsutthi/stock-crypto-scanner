import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import tempfile
import json
from pathlib import Path
import pandas as pd
import requests
from build_indices import compose_set, compose_index, compose_bitcoin, build_snapshot


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
            with patch('build_indices.yf.Ticker',return_value=ticker), patch('build_indices.requests.get',side_effect=requests.RequestException('offline')):
                result=build_snapshot(output,previous)
            self.assertEqual(result['indices']['SET']['quoteAt'],original['quoteAt'])
            self.assertEqual(result['indices']['SET']['value'],1500.)
            self.assertTrue(result['indices']['SET']['updateError'])

    def test_sp500_uses_new_york_session_date(self):
        bars=pd.DataFrame({'Close':[7600.,7610.]},index=pd.to_datetime(['2026-10-01T19:45:00Z','2026-10-02T00:05:00Z']))
        result=compose_index({'regularMarketPrice':7610.,'regularMarketPreviousClose':7500.},bars,symbol='^GSPC',name='S&P 500',zone='America/New_York')
        self.assertEqual(result['chartDate'],'2026-10-01')
        self.assertEqual(result['changePoints'],110.)
        self.assertIn('^GSPC',result['source'])

    def test_bitcoin_separates_24h_quote_from_utc_range_and_usdt_analysis(self):
        bars=pd.DataFrame({'Open':[99.,104.,108.,109.], 'Close':[100.,105.,109.,110.], 'High':[101.,106.,115.,112.], 'Low':[98.,103.,107.,109.]},index=pd.to_datetime(['2026-10-01T00:00:00Z','2026-10-01T12:00:00Z','2026-10-02T00:00:00Z','2026-10-02T01:30:00Z']))
        quote={'value':112.,'changePercent':2.34,'volume24h':2.5e9,'marketCap':2e12,'rank':1,'source':'CoinPaprika','quoteAt':'2026-10-02T01:35:00Z'}
        technical={'rsi':60.,'historyUnavailable':False,'techPrice':107.,'historySource':'Binance (USDT)','priceDate':'2026-10-01'}
        result=compose_bitcoin({},bars,quote,technical)
        self.assertEqual(result['value'],112.)
        self.assertEqual(result['changePercent'],2.34)
        self.assertEqual(result['changeBasis'],'24h')
        self.assertEqual(result['open'],108.)
        self.assertEqual(result['high'],115.)
        self.assertEqual(result['low'],107.)
        self.assertEqual(len(result['chart']),3)
        self.assertEqual(result['rsi'],60.)
        self.assertEqual(result['closedCurrency'],'USDT')

    def test_bitcoin_fallback_change_is_not_labelled_24h(self):
        result=compose_bitcoin({'regularMarketPrice':110.,'regularMarketPreviousClose':100.,'regularMarketTime':1790886937},self.bars())
        self.assertEqual(result['changeBasis'],'provider-close')
        self.assertAlmostEqual(result['changePercent'],10.)

    def test_bitcoin_fallback_can_use_explicit_prior_utc_bar(self):
        bars=pd.DataFrame({'Close':[100.,110.]},index=pd.to_datetime(['2026-10-01T23:45:00Z','2026-10-02T00:15:00Z']))
        result=compose_bitcoin({'regularMarketPrice':110.,'regularMarketTime':int(datetime(2026,10,2,0,16,tzinfo=timezone.utc).timestamp())},bars)
        self.assertEqual(result['changeBasis'],'utc-close')
        self.assertAlmostEqual(result['changePercent'],10.)


if __name__=='__main__':
    unittest.main()
