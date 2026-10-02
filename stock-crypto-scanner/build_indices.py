"""SET, S&P 500 and Bitcoin overviews with source times and real charts."""
import argparse
import json
import math
from datetime import datetime, timezone, timedelta
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


def source_time(value, zone='Asia/Bangkok'):
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            return None
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize(zone)
        return stamp.tz_convert('UTC').to_pydatetime()
    except (ValueError, TypeError, OverflowError):
        return None


def positive(value):
    result = number(value)
    return result if result is not None and result > 0 else None


def compose_index(info, intraday, daily=None, symbol='^SET.BK', name='SET Index', zone='Asia/Bangkok'):
    info = info or {}
    daily = daily if daily is not None else pd.DataFrame()
    price = positive(info.get('regularMarketPrice'))
    quote_time = source_time(info.get('regularMarketTime'), zone)
    quote_type = 'provider-quote'
    bars = intraday.copy()
    if not bars.empty and 'Close' in bars:
        bars['Close'] = pd.to_numeric(bars.Close, errors='coerce')
        bars = bars.loc[(bars.Close > 0) & bars.Close.map(math.isfinite)].sort_index()
        bars = bars.loc[~bars.index.duplicated(keep='last')]
        if not bars.empty:
            bars.index = pd.to_datetime(bars.index)
            bars.index = bars.index.tz_localize(zone) if bars.index.tz is None else bars.index.tz_convert(zone)
            if price is None or price <= 0:
                price = float(bars.Close.iloc[-1])
                quote_time = source_time(bars.index[-1], zone)
                quote_type = '15m'
    if price is None or price <= 0:
        if daily.empty or 'Close' not in daily:
            raise ValueError(f'{name} quote unavailable')
        price = number(daily.Close.iloc[-1])
        quote_time = source_time(daily.index[-1], zone)
        quote_type = 'daily-bar'
    if price is None or price <= 0:
        raise ValueError(f'Invalid {name} value')
    previous = positive(info.get('regularMarketPreviousClose'))
    if previous is None and not daily.empty and quote_time:
        prior = daily.loc[[stamp.date() < quote_time.astimezone(ZoneInfo(zone)).date() for stamp in daily.index]]
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
    return dict(symbol=symbol, name=name, value=price, previousClose=previous,
                changePoints=points, changePercent=percent, open=positive(info.get('regularMarketOpen')),
                high=positive(info.get('regularMarketDayHigh')), low=positive(info.get('regularMarketDayLow')),
                quoteAt=quote_time.isoformat() if quote_time else None, quoteType=quote_type,
                source=f'Yahoo Finance ({symbol})', chart=chart, chartDate=chart_date, interval='15m', marketTimeZone=zone)


def compose_set(info, intraday, daily=None):
    return compose_index(info, intraday, daily)


def fetch_bitcoin_quote():
    try:
        response = requests.get('https://api.coinpaprika.com/v1/tickers/btc-bitcoin', timeout=12)
        response.raise_for_status()
        coin = response.json()
        if coin.get('id') != 'btc-bitcoin' or coin.get('symbol') != 'BTC':
            return None
        quote = coin['quotes']['USD']
        if not positive(quote.get('price')):
            return None
        return dict(value=positive(quote['price']), changePercent=number(quote.get('percent_change_24h')),
                    volume24h=number(quote.get('volume_24h')), marketCap=positive(quote.get('market_cap')),
                    rank=positive(coin.get('rank')), quoteAt=coin.get('last_updated'), source='CoinPaprika (BTC / USD)')
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        return None


def compose_bitcoin(info, intraday, quote=None, technical=None):
    base = compose_index(info, intraday, symbol='BTC-USD', name='Bitcoin', zone='UTC') if not quote else dict(quote)
    bars = intraday.copy()
    if not bars.empty and 'Close' in bars:
        bars['Close'] = pd.to_numeric(bars.Close, errors='coerce')
        bars = bars.loc[(bars.Close > 0) & bars.Close.map(math.isfinite)].sort_index()
        bars = bars.loc[~bars.index.duplicated(keep='last')]
        bars.index = pd.to_datetime(bars.index)
        bars.index = bars.index.tz_localize('UTC') if bars.index.tz is None else bars.index.tz_convert('UTC')
    chart, open_price, high, low, range_date, range_at = [], None, None, None, None, None
    if not bars.empty and 'Close' in bars:
        last = bars.index[-1]
        window = bars.loc[bars.index >= last-timedelta(hours=24)]
        chart = [dict(time=stamp.isoformat(), value=float(row.Close)) for stamp, row in window.iterrows()]
        today = bars.loc[[stamp.date() == last.date() for stamp in bars.index]]
        range_date, range_at = last.date().isoformat(), last.isoformat()
        if 'Open' in today and today.index[0].hour == 0 and today.index[0].minute == 0:
            open_price = positive(today.Open.iloc[0])
        high = positive(pd.to_numeric(today.High, errors='coerce').max()) if 'High' in today else None
        low = positive(pd.to_numeric(today.Low, errors='coerce').min()) if 'Low' in today else None
    technical = technical or {}
    base.update(symbol='BTC-USD', name='Bitcoin', currency='USD', chart=chart, chartWindow='24h', interval='15m',
                chartSource='Yahoo Finance (BTC-USD)', rangeDate=range_date, rangeAt=range_at,
                open=open_price, high=high, low=low, changeBasis='24h' if quote else 'provider-close',
                rsi=number(technical.get('rsi')) if not technical.get('historyUnavailable', True) else None,
                technicalDate=technical.get('priceDate'), technicalSource=technical.get('historySource'),
                closedPrice=positive(technical.get('techPrice')),
                closedCurrency='USDT' if 'USDT' in (technical.get('historySource') or '') else 'USD',
                technicalWarning=bool(technical.get('updateError') or technical.get('historyStale') or technical.get('historyUpdateError')))
    if not quote:
        base.update(volume24h=number(info.get('volume24Hr')), marketCap=positive(info.get('marketCap')), rank=None)
        baseline = positive(info.get('regularMarketPreviousClose'))
        reference = source_time(base.get('quoteAt'), 'UTC')
        if reference and not bars.empty:
            prior = bars.loc[[stamp.date() < reference.date() for stamp in bars.index]]
            if not prior.empty and prior.index[-1].date() == reference.date()-timedelta(days=1) and (prior.index[-1].hour,prior.index[-1].minute) == (23,45):
                baseline = positive(prior.Close.iloc[-1])
                base['changeBasis'] = 'utc-close'
        base.update(changePoints=base['value']-baseline if baseline else None,
                    changePercent=(base['value']/baseline-1)*100 if baseline else None)
    return base


def read_previous(path, key='SET'):
    try:
        data = json.loads(path.read_text(encoding='utf-8')) if path else {}
        return (data.get('bitcoin') if key == 'BTC' else data.get('indices', {}).get(key)) if isinstance(data, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def build_snapshot(output, previous_path=None, crypto_path=None):
    previous = {key:read_previous(previous_path,key) for key in ('SET','SP500','BTC')}
    technical = None
    if crypto_path:
        try:
            crypto = json.loads(crypto_path.read_text(encoding='utf-8'))
            candidates = [a for a in crypto.get('assets',[]) if a.get('symbol') == 'BTC' and a.get('id') in ('btc-bitcoin','bitcoin')]
            if len(candidates) == 1:
                technical = dict(candidates[0], updateError=candidates[0].get('updateError') or crypto.get('updateError'))
        except (OSError, ValueError, TypeError):
            pass
    published_checked = False
    result = dict(generatedAt=datetime.now(timezone.utc).isoformat(), refreshMinutes=30, indices={})
    for key, symbol, name, zone in [('SET','^SET.BK','SET Index','Asia/Bangkok'),('SP500','^GSPC','S&P 500','America/New_York'),('BTC','BTC-USD','Bitcoin','UTC')]:
        try:
            ticker = yf.Ticker(symbol)
            try:
                info = ticker.get_info() or {}
            except Exception:
                info = {}
            try:
                intraday = ticker.history(period='5d', interval='15m', auto_adjust=False, timeout=20)
            except Exception:
                intraday = pd.DataFrame()
            if key == 'BTC':
                overview = compose_bitcoin(info,intraday,fetch_bitcoin_quote(),technical)
            else:
                daily = pd.DataFrame()
                if positive(info.get('regularMarketPrice')) is None or positive(info.get('regularMarketPreviousClose')) is None:
                    try:
                        daily = ticker.history(period='5d',interval='1d',auto_adjust=False,timeout=20)
                    except Exception:
                        pass
                overview = compose_index(info,intraday,daily,symbol,name,zone)
        except Exception as error:
            if not previous[key] and not published_checked:
                published_checked = True
                try:
                    response = requests.get('https://benzsutthi.github.io/stock-crypto-scanner/data/indices.json',timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    for item in previous:
                        previous[item] = previous[item] or (data.get('bitcoin') if item == 'BTC' else data.get('indices',{}).get(item))
                except (requests.RequestException, ValueError, TypeError):
                    pass
            overview = dict(previous[key],updateError=f'Keeping previous {name} quote') if previous[key] else None
            print(f'{name} update unavailable: {error}')
        if key == 'BTC':
            result['bitcoin'] = overview
        else:
            result['indices'][key] = overview
        print(f"{name} overview: {overview['value'] if overview else 'unavailable'}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('data/indices.json'))
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--crypto', type=Path)
    args = parser.parse_args()
    build_snapshot(args.output, args.previous, args.crypto)
