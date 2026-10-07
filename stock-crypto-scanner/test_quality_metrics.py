import unittest
import pandas as pd
from technicals import analyze
from quality_metrics import relative_returns, attach_quality


class QualityMetricsTest(unittest.TestCase):
    def records(self, end):
        dates=pd.date_range('2026-01-01',periods=80)
        return [dict(date=stamp.date().isoformat(),close=100. if i<79 else end) for i,stamp in enumerate(dates)]

    def test_rs_is_return_difference_and_ignores_future_benchmark(self):
        asset=self.records(110.)
        benchmark=self.records(98.)+[{'date':'2026-03-22','close':1000.}]
        result=relative_returns(asset,benchmark)
        self.assertEqual(result['20']['difference'],12.)
        self.assertEqual(result['60']['difference'],12.)
        self.assertEqual(result['20']['assetReturn'],10.)
        self.assertEqual(result['20']['benchmarkReturn'],-2.)

    def test_missing_session_or_end_date_never_gets_forward_filled(self):
        asset=self.records(110.)
        del asset[-5]
        self.assertIsNone(relative_returns(asset,self.records(98.))['20'])
        self.assertIsNone(relative_returns(self.records(110.),self.records(98.)[:-1])['20'])
        short=self.records(110.)[-50:]
        self.assertIsNotNone(relative_returns(short,self.records(98.))['20'])
        self.assertIsNone(relative_returns(short,self.records(98.))['60'])

    def test_liquidity_units_and_quality_score_are_idempotent(self):
        asset={'market':'Thai','signals':[],'score':5,'liquidityCurrency':'THB','avgTurnover20':20_000_000.,'returnHistory':self.records(110.)}
        benchmark={'name':'SET','source':'test','history':self.records(98.)}
        attach_quality(asset,benchmark)
        self.assertTrue(asset['liquidityPassed'])
        self.assertTrue(asset['relativeStrengthLeader'])
        self.assertEqual(asset['score'],15)
        attach_quality(asset,benchmark)
        self.assertEqual(asset['score'],15)
        self.assertEqual(len([s for s in asset['signals'] if s['type']=='relative-strength']),1)
        asset['liquidityCurrency']=None
        attach_quality(asset,benchmark)
        self.assertFalse(asset['liquidityPassed'])

    def frame(self):
        return pd.DataFrame({'Close':[100.]*59+[107.5], 'High':[110.]*60,'Low':[90.]*59+[100.], 'Volume':[100.]*59+[150.]})

    def test_strong_close_requires_location_and_volume(self):
        frame=self.frame()
        self.assertTrue(analyze(frame)['strongClose'])
        frame.loc[59,'Volume']=149.
        self.assertFalse(analyze(frame)['strongClose'])
        frame.loc[59,['High','Low','Close']]=[100.,100.,100.]
        self.assertIsNone(analyze(frame)['closeLocation'])
        self.assertFalse(analyze(frame)['strongClose'])

    def test_crypto_reported_dollar_volume_is_not_multiplied_by_price(self):
        frame=self.frame()
        frame['Close']=50_000.
        frame['High']=51_000.
        frame['Low']=49_000.
        frame['Volume']=2_000_000.
        self.assertEqual(analyze(frame,volume_basis='quote')['avgTurnover20'],2_000_000.)
        frame['Volume']=100.
        frame['QuoteVolume']=3_000_000.
        self.assertEqual(analyze(frame)['avgTurnover20'],3_000_000.)


if __name__=='__main__':
    unittest.main()
