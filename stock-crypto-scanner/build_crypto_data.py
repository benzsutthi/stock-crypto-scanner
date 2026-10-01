"""Publish ranked crypto quotes and confirmed daily technical analysis."""
import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from build_market_data import extract_ticker_frame
from technicals import analyze


def fetch_universe():
    errors = []
    try:
        response = requests.get('https://api.coinpaprika.com/v1/tickers', timeout=20)
        response.raise_for_status()
        coins = sorted((c for c in response.json() if c.get('rank', 0) > 0), key=lambda c: c['rank'])[:100]
        if not coins:
            raise ValueError('Empty ranking')
        return [dict(id=c['id'], symbol=c['symbol'].upper(), name=c['name'], rank=c['rank'],
                     price=c['quotes']['USD'].get('price'), change=c['quotes']['USD'].get('percent_change_24h')) for c in coins], 'CoinPaprika'
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
                     price=c['current_price'], change=c['price_change_percentage_24h']) for c in coins], 'CoinGecko'
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


def build_snapshot(output):
    coins, source = fetch_universe()
    symbols = Counter(c['symbol'] for c in coins)
    tickers = [c['symbol']+'-USD' for c in coins if symbols[c['symbol']] == 1]
    downloaded = yf.download(tickers, period='1y', interval='1d', group_by='ticker',
                             auto_adjust=True, threads=8, progress=False, timeout=15)
    def worker(coin):
        if symbols[coin['symbol']] != 1:
            return enrich(coin, pd.DataFrame(), None)  # Never guess identities from duplicate tickers.
        frame = confirmed(extract_ticker_frame(downloaded, coin['symbol']+'-USD'))
        history_source = 'Yahoo Finance (USD)'
        if len(frame) < 50 or (datetime.now(timezone.utc).date()-frame.index[-1].date()).days > 4:
            try:
                frame = confirmed(exchange_history(coin['symbol']))
                history_source = 'Binance market data (USDT)'
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
                frame = pd.DataFrame()
        return enrich(coin, frame, history_source)
    with ThreadPoolExecutor(max_workers=5) as executor:
        assets = list(executor.map(worker, coins))
    analyzed = sum(not a['historyUnavailable'] for a in assets)
    if not analyzed:
        raise RuntimeError('No historical crypto data; refusing to replace a working snapshot.')
    result = dict(generatedAt=datetime.now(timezone.utc).isoformat(), source=source,
                  assets=assets, analyzedCount=analyzed,
                  unavailableSymbols=[a['symbol'] for a in assets if a['historyUnavailable']])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f'Crypto: {len(assets)} ranked assets; {analyzed} analyzed; quotes from {source}.')
    print('History unavailable: ' + ', '.join(result['unavailableSymbols']))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('data/crypto.json'))
    args = parser.parse_args()
    try:
        build_snapshot(args.output)
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
