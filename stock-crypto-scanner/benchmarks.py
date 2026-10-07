"""Confirmed benchmark histories; never substitute an ETF for SET/S&P 500."""
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
import yfinance as yf
from market_history import clean_history
from quality_metrics import return_history
from refresh_policy import reusable, stock_session


def fetch_benchmark(symbol, name, market, previous=None):
    now = datetime.now(timezone.utc)
    target = stock_session(market, now) if market in ('Thai','US') else (now.date()-timedelta(days=1)).isoformat()
    if previous and previous.get('symbol') == symbol and len(previous.get('history',[]))>=61 and reusable(previous,target,now):
        return previous
    source = f'Yahoo Finance ({symbol}) daily close'
    try:
        if symbol == 'BTCUSDT':
            response=requests.get('https://data-api.binance.vision/api/v3/klines',params={'symbol':'BTCUSDT','interval':'1d','limit':250},timeout=12)
            response.raise_for_status()
            bars=[b for b in response.json() if b[6]<now.timestamp()*1000]
            frame=pd.DataFrame({'Close':[float(b[4]) for b in bars], 'High':[float(b[2]) for b in bars], 'Low':[float(b[3]) for b in bars], 'Volume':[float(b[5]) for b in bars]},index=pd.to_datetime([b[0] for b in bars],unit='ms',utc=True))
            source='Binance BTC/USDT confirmed daily close'
        else:
            ticker=yf.Ticker(symbol)
            frame=clean_history(ticker.history(period='1y',interval='1d',auto_adjust=False,timeout=20))
            frame=frame.loc[[stamp.date().isoformat()<=target for stamp in frame.index]]
            if symbol == '^SET.BK' and len(frame)<61:
                hourly=ticker.history(period='6mo',interval='1h',auto_adjust=False,timeout=20)
                hourly.index=hourly.index.tz_localize('Asia/Bangkok') if hourly.index.tz is None else hourly.index.tz_convert('Asia/Bangkok')
                derived=clean_history(hourly.resample('1D').agg({'High':'max','Low':'min','Close':'last','Volume':'sum'}))
                derived=derived.loc[[stamp.date().isoformat()<=target for stamp in derived.index]]
                if len(derived)>len(frame):
                    frame=derived
                    source='Yahoo Finance (^SET.BK) last hourly bar per confirmed SET session'
        frame=clean_history(frame)
        if frame.empty:
            raise ValueError('Benchmark history unavailable')
        return dict(symbol=symbol,name=name,source=source,history=return_history(frame),
                    priceDate=frame.index[-1].date().isoformat(),historyTarget=target,historyCheckedAt=now.isoformat())
    except Exception as error:
        print(f'{symbol} benchmark unavailable: {error}')
        return dict(previous,updateError='Benchmark update failed') if previous else dict(symbol=symbol,name=name,source=source,history=[],updateError='Benchmark unavailable')
