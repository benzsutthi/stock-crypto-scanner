import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from portfolio_report import build_portfolio_flex, parse_portfolio_csv, parse_sheet_csv_url, send_once


class PortfolioReportTest(unittest.TestCase):
    def test_parse_sheet_csv_url_handles_drivesdk_and_gid(self):
        self.assertEqual(
            parse_sheet_csv_url('https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/edit?usp=drivesdk'),
            'https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/gviz/tq?tqx=out:csv&gid=146811986',
        )

    def test_parse_portfolio_csv_and_build_flex(self):
        sample = '\n'.join([
            'Ticker,Asset Class,Shares/Units,avg invest,Current Price,Current Value THB,Total invest CostTHB,Profit/Loss ($/฿),Profit/Loss (%)',
            'JEPQ US,ETF (US),10,50,55,19250,17500,1750,10.0',
            'SCB,Stock (TH),,,150,0,,0,0',
            'BTCTHB,Crypto,0.01,3000000,2500000,25000,30000,-5000,-16.67',
        ])
        summary = parse_portfolio_csv(sample)
        self.assertEqual(len(summary['items']), 2)
        self.assertAlmostEqual(summary['total_value_thb'], 44250.0)
        self.assertAlmostEqual(summary['total_cost_thb'], 47500.0)
        flex = build_portfolio_flex(summary, now=datetime(2026, 11, 24, 1, 0, tzinfo=timezone.utc))
        self.assertEqual(flex['type'], 'flex')
        self.assertIn('44,250', flex['altText'])
        self.assertEqual(flex['contents']['type'], 'bubble')

    def test_send_once_dedup_and_409(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / 'state.json'
            resp_409 = MagicMock(status_code=409, headers={'x-line-accepted-request-id': 'ok'})
            flex = {'type': 'flex', 'altText': 'test', 'contents': {'type': 'bubble'}}
            with patch('portfolio_report.requests.post', return_value=resp_409) as m:
                self.assertTrue(send_once(state, 'tok', flex, '2026-11-24'))
                self.assertFalse(send_once(state, 'tok', flex, '2026-11-24'))
                self.assertEqual(m.call_count, 1)


if __name__ == '__main__':
    unittest.main()
