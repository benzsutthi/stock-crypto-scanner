"""Publish ranked crypto quotes and confirmed daily technical analysis."""
import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from build_market_data import extract_ticker_frame
from technicals import analyze
from refresh_policy import read_previous, reusable


def fetch_universe():
    errors = []
    try:
        response = requests.get('https://api.coinpaprika.com/v1/tickers', timeout=20)
        response.raise_for_status()
        coins = sorted((c for c in response.json() if c.get('rank', 0) > 0), key=lambda c: c['rank'])[:100]
        if not coins:
            raise ValueError('Empty ranking')
        return [dict(id=c['id'], symbol=c['symbol'].upper(), name=c['name'], rank=c['rank'],
                     price=c['quotes']['USD'].get('price'), change=c['quotes']['USD'].get('percent_change_24h'), quoteAt=c.get('last_updated')) for c in coins], 'CoinPaprika'
    except (requests.RequestException, ValueError, KeyError) as error:
        errors.append(str(error))
    try:
        response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
            'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 100, 'page': 1}, timeout=20)
        response.raise_for_status()
        coins = response.json()
        if not isinstance(coins, list) or not coins:
            raise ValueError('Empty ranking')
        return [dict(id=c['id'], symbol=c['symbol'].upper(), name=c['name'], rank=c['market_cap_rank'],
                     price=c['current_price'], change=c['price_change_percentage_24h'], quoteAt=c.get('last_updated')) for c in coins], 'CoinGecko'
    except (requests.RequestException, ValueError, KeyError) as error:
        errors.append(str(error))
    raise RuntimeError('Crypto rankings unavailable: ' + '; '.join(errors))


def confirmed(frame, today=None):
    today = today or datetime.now(timezone.utc).date()
    required = ['Close', 'High', 'Low', 'Volume']
    if frame.empty or any(c not in frame.columns for c in required):
        return pd.DataFrame()
    frame = frame.copy()
    for col in required:
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
    frame = frame.dropna(subset=required)
    return frame.loc[[stamp.date() < today for stamp in frame.index]]


def exchange_history(symbol):
    # Binance's market-data-only endpoint also works where api.binance.com is restricted.
    response = requests.get('https://data-api.binance.vision/api/v3/klines', params={
        'symbol': symbol+'USDT', 'interval': '1d', 'limit': 250}, timeout=8)
    response.raise_for_status()
    bars = [b for b in response.json() if int(b[6]) < datetime.now(timezone.utc).timestamp()*1000]
    return pd.DataFrame({'Close': [float(b[4]) for b in bars], 'High': [float(b[2]) for b in bars],
                         'Low': [float(b[3]) for b in bars], 'Volume': [float(b[5]) for b in bars]},
                        index=pd.to_datetime([b[0] for b in bars], unit='ms', utc=True))


def enrich(coin, frame, history_source):
    asset = dict(coin, market='Crypto', currency='USD', rsi=None, signals=[], score=0,
                 historyUnavailable=True, historySource=None, priceDate=None)
    if len(frame) >= 50 and (datetime.now(timezone.utc).date()-frame.index[-1].date()).days <= 4:
        result = analyze(frame)
        asset.update(result)
        asset.update(price=coin['price'], change=coin['change'], techPrice=result['price'],
                     priceDate=frame.index[-1].date().isoformat(), historySource=history_source,
                     historyUnavailable=False)
    return asset


def build_snapshot(output, previous_path=None):
    coins, source = fetch_universe()
    now = datetime.now(timezone.utc)
    target = (now.date()-timedelta(days=1)).isoformat()
    previous = read_previous(previous_path)
    cached = {a['id']:a for a in previous.get('assets', [])}
    symbols = Counter(c['symbol'] for c in coins)
    reuse = {c['id'] for c in coins if not cached.get(c['id'], {}).get('historyUnavailable', True) and not cached.get(c['id'], {}).get('historyUpdateError') and reusable(cached.get(c['id']), target, now)}
    tickers = [c['symbol']+'-USD' for c in coins if symbols[c['symbol']] == 1 and c['id'] not in reuse]
    print(f'Refreshing crypto quotes; reusing {len(reuse)} confirmed histories.')
    downloaded = yf.download(tickers, period='1y', interval='1d', group_by='ticker',
                             auto_adjust=True, threads=8, progress=False, timeout=15) if tickers else pd.DataFrame()
    def worker(coin):
        if symbols[coin['symbol']] != 1:
            return enrich(coin, pd.DataFrame(), None)  # Never guess identities from duplicate tickers.
        if coin['id'] in reuse:
            return dict(cached[coin['id']], **coin)
        frame = confirmed(extract_ticker_frame(downloaded, coin['symbol']+'-USD'))
        history_source = 'Yahoo Finance (USD)'
        if len(frame) < 50 or (datetime.now(timezone.utc).date()-frame.index[-1].date()).days > 4:
            try:
                frame = confirmed(exchange_history(coin['symbol']))
                history_source = 'Binance market data (USDT)'
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
                frame = pd.DataFrame()
        asset = enrich(coin, frame, history_source)
        old = cached.get(coin['id'])
        if asset['historyUnavailable'] and old and not old.get('historyUnavailable') and old.get('priceDate') and (now.date()-datetime.fromisoformat(old['priceDate']).date()).days <= 4:
            return dict(old, **coin, historyUpdateError='Using previous confirmed history')
        asset.update(historyTarget=target, historyCheckedAt=now.isoformat())
        return asset
    with ThreadPoolExecutor(max_workers=5) as executor:
        assets = list(executor.map(worker, coins))
    analyzed = sum(not a['historyUnavailable'] for a in assets)
    if not analyzed:
        raise RuntimeError('No historical crypto data; refusing to replace a working snapshot.')
    result = dict(generatedAt=datetime.now(timezone.utc).isoformat(), source=source,
                  assets=assets, analyzedCount=analyzed,
                  unavailableSymbols=[a['symbol'] for a in assets if a['historyUnavailable']],
                  refreshMinutes=30, quoteDescription='Provider quotes refreshed every 30 minutes; confirmed UTC daily bars for signals.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f'Crypto: {len(assets)} ranked assets; {analyzed} analyzed; quotes from {source}.')
    print('History unavailable: ' + ', '.join(result['unavailableSymbols']))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('data/crypto.json'))
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    try:
        build_snapshot(args.output, args.previous)
    except Exception as error:
        # Preserve the previously published data when upstream providers fail.
        response = requests.get('https://benzsutthi.github.io/stock-crypto-scanner/data/crypto.json', timeout=15)
        response.raise_for_status()
        previous = response.json()
        if not previous.get('assets') or not previous.get('analyzedCount'):
            raise RuntimeError('No usable previous crypto snapshot') from error
        previous['updateError'] = 'Latest update failed; displaying previous snapshot.'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(previous, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        print(f'Keeping previous crypto snapshot: {error}')
