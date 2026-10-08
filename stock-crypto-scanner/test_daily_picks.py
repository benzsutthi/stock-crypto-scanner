import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import requests
from daily_picks import select_daily_picks, make_report, send_once


class DailyPicksTest(unittest.TestCase):
    now=datetime(2026,10,8,2,tzinfo=timezone.utc)
    def asset(self,symbol='AAA',score=50,market='US',**extra):
        return dict(market=market,symbol=symbol,score=score,liquidityPassed=True,techPrice=100.,rsi=60.,ema20=95.,
                    volumeRatio=2.,priceDate='2026-10-07',signals=[{'type':'breakout','label':'20D Breakout'}],
                    liquidityCurrency='USD',**extra)
    def snapshot(self,assets,**extra):
        return dict(generatedAt=self.now.isoformat(),assets=assets,**extra)

    def test_three_total_across_markets_not_three_per_category(self):
        stocks=self.snapshot([self.asset('AAA',40),self.asset('BBB',70),self.asset('CCC',60),self.asset('DDD',50),self.asset('AAA',40)])
        crypto=self.snapshot([self.asset('ETH',80,'Crypto')])
        picks=select_daily_picks(stocks,crypto,self.now)
        self.assertEqual([a['symbol'] for a in picks],['ETH','BBB','CCC'])
        self.assertEqual(len(picks),3)

    def test_stale_or_unqualified_assets_are_never_used_to_fill_three(self):
        assets=[self.asset('OK'),dict(self.asset('OLD'),priceDate='2026-10-06'),dict(self.asset('THIN'),liquidityPassed=False),dict(self.asset('HOT'),rsi=80),dict(self.asset('BELOW'),ema20=110)]
        picks=select_daily_picks(self.snapshot(assets),self.snapshot([]),self.now)
        self.assertEqual(len(picks),1)
        self.assertIn('1/3',make_report(picks,self.now))

    def test_old_snapshots_and_crypto_fallback_are_excluded(self):
        old=dict(self.snapshot([self.asset()]),generatedAt=(self.now-timedelta(hours=4)).isoformat())
        fallback=self.snapshot([self.asset('ETH',80,'Crypto')],updateError='previous snapshot')
        self.assertEqual(select_daily_picks(old,fallback,self.now),[])

    def test_failed_request_keeps_original_pending_payload_and_same_day_dedup(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'
            failed=Mock(status_code=400,headers={})
            failed.raise_for_status.side_effect=requests.HTTPError('rejected')
            accepted=Mock(status_code=200,headers={})
            with patch('daily_picks.requests.post',side_effect=[failed,accepted]) as post:
                with self.assertRaises(requests.HTTPError):send_once(path,'test','original','2026-10-08',['US:AAA'])
                self.assertNotIn('sentDate',json.loads(path.read_text()))
                send_once(path,'test','changed','2026-10-08',['US:BBB'])
                self.assertEqual(post.call_args_list[1].kwargs['json']['messages'][0]['text'],'original')
                self.assertEqual(post.call_args_list[0].kwargs['headers']['X-Line-Retry-Key'],post.call_args_list[1].kwargs['headers']['X-Line-Retry-Key'])
                self.assertEqual(json.loads(path.read_text())['sentSymbols'],['US:AAA'])
                self.assertFalse(send_once(path,'test','another','2026-10-08',['US:CCC']))
                self.assertEqual(post.call_count,2)

    def test_line_already_accepted_retry_is_recorded_without_resending(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json'
            response=Mock(status_code=409,headers={'x-line-accepted-request-id':'accepted-id'})
            with patch('daily_picks.requests.post',return_value=response):
                self.assertTrue(send_once(path,'test','report','2026-10-08',[]))
            response.raise_for_status.assert_not_called()
            self.assertEqual(json.loads(path.read_text())['sentDate'],'2026-10-08')


if __name__=='__main__':
    unittest.main()
