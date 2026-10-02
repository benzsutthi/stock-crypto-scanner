"""SET Index overview with source quote time and actual intraday chart data."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and not isinstance(value, bool) else None
    except (ValueError, TypeError):
        return None


def source_time(value):
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            return None
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize('Asia/Bangkok')
        return stamp.tz_convert('UTC').to_pydatetime()
    except (ValueError, TypeError, OverflowError):
        return None


def positive(value):
    result = number(value)
    return result if result is not None and result > 0 else None


def compose_set(info, intraday, daily=None):
    info = info or {}
    daily = daily if daily is not None else pd.DataFrame()
    price = positive(info.get('regularMarketPrice'))
    quote_time = source_time(info.get('regularMarketTime'))
    quote_type = 'provider-quote'
    bars = intraday.copy()
    if not bars.empty and 'Close' in bars:
        bars['Close'] = pd.to_numeric(bars.Close, errors='coerce')
        bars = bars.loc[(bars.Close > 0) & bars.Close.map(math.isfinite)].sort_index()
        bars = bars.loc[~bars.index.duplicated(keep='last')]
        if not bars.empty:
            bars.index = pd.to_datetime(bars.index)
            bars.index = bars.index.tz_localize('Asia/Bangkok') if bars.index.tz is None else bars.index.tz_convert('Asia/Bangkok')
            if price is None or price <= 0:
                price = float(bars.Close.iloc[-1])
                quote_time = source_time(bars.index[-1])
                quote_type = '15m'
    if price is None or price <= 0:
        if daily.empty or 'Close' not in daily:
            raise ValueError('SET quote unavailable')
        price = number(daily.Close.iloc[-1])
        quote_time = source_time(daily.index[-1])
        quote_type = 'daily-bar'
    if price is None or price <= 0:
        raise ValueError('Invalid SET index value')
    previous = positive(info.get('regularMarketPreviousClose'))
    if previous is None and not daily.empty and quote_time:
        prior = daily.loc[[stamp.date() < quote_time.astimezone(ZoneInfo('Asia/Bangkok')).date() for stamp in daily.index]]
        if not prior.empty:
            previous = positive(prior.Close.iloc[-1])
    points = price-previous if previous is not None else number(info.get('regularMarketChange')) if quote_type == 'provider-quote' else None
    percent = points/previous*100 if previous is not None and points is not None else number(info.get('regularMarketChangePercent')) if quote_type == 'provider-quote' else None
    chart = []
    chart_date = None
    if not bars.empty and 'Close' in bars:
        chart_date = bars.index[-1].date().isoformat()
        current_day = bars.loc[[stamp.date().isoformat() == chart_date for stamp in bars.index]]
        chart = [dict(time=stamp.isoformat(), value=float(row.Close)) for stamp, row in current_day.iterrows()]
    return dict(symbol='^SET.BK', name='SET Index', value=price, previousClose=previous,
                changePoints=points, changePercent=percent, open=positive(info.get('regularMarketOpen')),
                high=positive(info.get('regularMarketDayHigh')), low=positive(info.get('regularMarketDayLow')),
                quoteAt=quote_time.isoformat() if quote_time else None, quoteType=quote_type,
                source='Yahoo Finance (^SET.BK)', chart=chart, chartDate=chart_date, interval='15m')


def read_previous(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8')) if path else {}
        return data.get('indices', {}).get('SET') if isinstance(data, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def build_snapshot(output, previous_path=None):
    previous = read_previous(previous_path)
    try:
        ticker = yf.Ticker('^SET.BK')
        try:
            info = ticker.get_info()
        except Exception:
            info = {}
        try:
            intraday = ticker.history(period='5d', interval='15m', auto_adjust=False, timeout=20)
        except Exception:
            intraday = pd.DataFrame()
        daily = pd.DataFrame()
        if positive(info.get('regularMarketPrice')) is None or positive(info.get('regularMarketPreviousClose')) is None:
            try:
                daily = ticker.history(period='5d', interval='1d', auto_adjust=False, timeout=20)
            except Exception:
                pass
        index = compose_set(info, intraday, daily)
    except Exception as error:
        if not previous:
            try:
                response = requests.get('https://benzsutthi.github.io/stock-crypto-scanner/data/indices.json', timeout=15)
                response.raise_for_status()
                previous = response.json().get('indices', {}).get('SET')
            except (requests.RequestException, ValueError, TypeError):
                previous = None
        index = dict(previous, updateError='Keeping previous SET quote') if previous else None
        print(f'SET update unavailable: {error}')
    result = dict(generatedAt=datetime.now(timezone.utc).isoformat(), refreshMinutes=30, indices={'SET':index})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f"SET overview: {index['value'] if index else 'unavailable'} points")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('data/indices.json'))
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    build_snapshot(args.output, args.previous)
