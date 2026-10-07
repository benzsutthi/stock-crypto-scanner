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
from refresh_policy import ANALYSIS_VERSION, read_previous, reusable
from market_history import clean_history
from quality_metrics import return_history, attach_quality
from benchmarks import fetch_benchmark
from config import CRYPTO_TOP_LIMIT

# Provider IDs, not ticker spelling, establish identity. Unmapped coins retain
# their market quote but never receive technical signals from a guessed ticker.
HISTORY_IDENTITIES = {
    'BTC': ('btc-bitcoin', 'bitcoin'), 'ETH': ('eth-ethereum', 'ethereum'),
    'SOL': ('sol-solana', 'solana'), 'XRP': ('xrp-xrp', 'ripple'),
    'BNB': ('bnb-binance-coin', 'binancecoin'), 'DOGE': ('doge-dogecoin', 'dogecoin'),
    'ADA': ('ada-cardano', 'cardano'), 'TRX': ('trx-tron', 'tron'),
    'LINK': ('link-chainlink', 'chainlink'), 'AVAX': ('avax-avalanche', 'avalanche-2'),
    'LTC': ('ltc-litecoin', 'litecoin'), 'BCH': ('bch-bitcoin-cash', 'bitcoin-cash'),
    'DOT': ('dot-polkadot', 'polkadot'), 'XLM': ('xlm-stellar', 'stellar'),
    'SHIB': ('shib-shiba-inu', 'shiba-inu'), 'UNI': ('uni-uniswap', 'uniswap'),
    'ATOM': ('atom-cosmos', 'cosmos'), 'NEAR': ('near-near-protocol', 'near'),
    'AAVE': ('aave-new', 'aave'), 'ETC': ('etc-ethereum-classic', 'ethereum-classic'),
    'ZEC': ('zec-zcash', 'zcash'), 'XMR': ('xmr-monero', 'monero'),
    'HBAR': ('hbar-hedera-hashgraph', 'hedera-hashgraph'), 'SUI': ('sui-sui', 'sui'),
    'CRO': ('cro-cryptocom-chain', 'crypto-com-chain'), 'QNT': ('qnt-quant', 'quant-network'),
    'TAO': ('tao-bittensor', 'bittensor'), 'ENA': ('ena-ethena', 'ethena'),
    'ONDO': ('ondo-ondo', 'ondo-finance'), 'MNT': ('mnt-mantle', 'mantle'),
    'WLD': ('wld-worldcoin', 'worldcoin-wld'), 'PEPE': ('pepe-pepe', 'pepe'),
    'ICP': ('icp-internet-computer', 'internet-computer'), 'PAXG': ('paxg-pax-gold', 'pax-gold'),
    'ARB': ('arb-arbitrum', 'arbitrum'), 'KAS': ('kas-kaspa', 'kaspa'),
    'POL': ('pol-polygon-ecosystem-token', 'polygon-ecosystem-token'),
    'ALGO': ('algo-algorand', 'algorand'), 'CAKE': ('cake-pancakeswap', 'pancakeswap-token'),
    'FIL': ('fil-filecoin', 'filecoin'), 'DASH': ('dash-dash', 'dash'),
    'VET': ('vet-vechain', 'vechain'), 'INJ': ('inj-injective-protocol', 'injective-protocol'),
}


def history_ticker(coin):
    return coin['symbol'] + '-USD' if coin.get('id') in HISTORY_IDENTITIES.get(coin['symbol'], ()) else None


def fetch_universe():
    errors = []
    try:
        response = requests.get('https://api.coinpaprika.com/v1/tickers', timeout=20)
        response.raise_for_status()
        coins = sorted((c for c in response.json() if c.get('rank', 0) > 0), key=lambda c: c['rank'])[:CRYPTO_TOP_LIMIT]
        if not coins:
            raise ValueError('Empty ranking')
        return [dict(id=c['id'], symbol=c['symbol'].upper(), name=c['name'], rank=c['rank'],
                     quoteUpdatedAt=c.get('last_updated'), quoteAt=c.get('last_updated'),
                     price=c['quotes']['USD'].get('price'), change=c['quotes']['USD'].get('percent_change_24h')) for c in coins], 'CoinPaprika'
    except (requests.RequestException, ValueError, KeyError) as error:
        errors.append(str(error))
    try:
        response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
            'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': CRYPTO_TOP_LIMIT, 'page': 1}, timeout=20)
        response.raise_for_status()
        coins = response.json()
        if not isinstance(coins, list) or not coins:
            raise ValueError('Empty ranking')
        return [dict(id=c['id'], symbol=c['symbol'].upper(), name=c['name'], rank=c['market_cap_rank'],
                     quoteUpdatedAt=c.get('last_updated'), quoteAt=c.get('last_updated'),
                     price=c['current_price'], change=c['price_change_percentage_24h']) for c in coins], 'CoinGecko'
    except (requests.RequestException, ValueError, KeyError) as error:
        errors.append(str(error))
    raise RuntimeError('Crypto rankings unavailable: ' + '; '.join(errors))


def confirmed(frame, today=None):
    today = today or datetime.now(timezone.utc).date()
    frame = clean_history(frame)
    if frame.empty:
        return pd.DataFrame()
    return frame.loc[[stamp.date() < today for stamp in frame.index]]


def exchange_history(symbol):
    # Binance's market-data-only endpoint also works where api.binance.com is restricted.
    response = requests.get('https://data-api.binance.vision/api/v3/klines', params={
        'symbol': symbol+'USDT', 'interval': '1d', 'limit': 250}, timeout=8)
    response.raise_for_status()
    bars = [b for b in response.json() if int(b[6]) < datetime.now(timezone.utc).timestamp()*1000]
    return pd.DataFrame({'Close': [float(b[4]) for b in bars], 'High': [float(b[2]) for b in bars],
                          'Low': [float(b[3]) for b in bars], 'Volume': [float(b[5]) for b in bars], 'QuoteVolume':[float(b[7]) for b in bars]},
                        index=pd.to_datetime([b[0] for b in bars], unit='ms', utc=True))


def apply_quote_freshness(asset):
    try:
        quote_time = datetime.fromisoformat(asset['quoteUpdatedAt'].replace('Z', '+00:00'))
        age = (datetime.now(timezone.utc)-quote_time).total_seconds()
        asset['quoteStale'] = not 0 <= age <= 2*3600
    except (KeyError, ValueError, TypeError, AttributeError):
        asset['quoteStale'] = True
    conditions = asset.get('earlyConditions', {})
    target = (datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
    eligible = bool(conditions) and all(conditions.values()) and asset.get('priceDate') == target and not any(asset.get(k) for k in ('quoteStale', 'historyStale', 'historyUnavailable', 'historyUpdateError', 'updateError'))
    asset['earlyCycle'] = eligible
    asset['signals'] = [s for s in asset.get('signals', []) if s['type'] != 'early-cycle']
    if eligible:
        label = 'ต้นรอบ · ฐานแน่นและเริ่มกลับตัว'
        asset['signals'].append(dict(type='early-cycle', label=label, description=label))
    return asset


def enrich(coin, frame, history_source):
    asset = dict(coin, market='Crypto', currency='USD', rsi=None, signals=[], score=0,
                 historyUnavailable=True, historySource=None, priceDate=None,
                 earlyCycle=False, earlyScore=0)
    if len(frame) >= 50 and (datetime.now(timezone.utc).date()-frame.index[-1].date()).days == 1:
        result = analyze(frame,volume_basis='quote' if history_source and history_source.startswith('Yahoo') else 'base')
        asset.update(result)
        asset.update(price=coin['price'], change=coin['change'], techPrice=result['price'],
                     priceDate=frame.index[-1].date().isoformat(), historySource=history_source,
                      historyUnavailable=False, returnHistory=return_history(frame),
                      liquidityCurrency='USD' if history_source and history_source.startswith('Yahoo') else 'USDT' if history_source and 'Binance' in history_source else None)
    return apply_quote_freshness(asset)


def build_snapshot(output, previous_path=None):
    coins, source = fetch_universe()
    now = datetime.now(timezone.utc)
    target = (now.date()-timedelta(days=1)).isoformat()
    previous = read_previous(previous_path)
    benchmarks = {currency:fetch_benchmark(symbol,name,'Crypto',previous.get('benchmarks',{}).get(currency))
                  for currency,symbol,name in [('USD','BTC-USD','BTC/USD'),('USDT','BTCUSDT','BTC/USDT')]}
    cached = {a['id']:a for a in previous.get('assets', [])}
    symbols = Counter(c['symbol'] for c in coins)
    reuse = {c['id'] for c in coins if symbols[c['symbol']] == 1 and history_ticker(c) and cached.get(c['id'], {}).get('analysisVersion') == ANALYSIS_VERSION and cached.get(c['id'], {}).get('priceDate') == target and not cached.get(c['id'], {}).get('historyUnavailable', True) and not cached.get(c['id'], {}).get('historyUpdateError') and reusable(cached.get(c['id']), target, now)}
    tickers = [history_ticker(c) for c in coins if symbols[c['symbol']] == 1 and history_ticker(c) and c['id'] not in reuse]
    print(f'Refreshing crypto quotes; reusing {len(reuse)} confirmed histories.')
    try:
        downloaded = yf.download(tickers, period='1y', interval='1d', group_by='ticker',
                                 auto_adjust=True, threads=8, progress=False, timeout=15) if tickers else pd.DataFrame()
    except Exception as error:
        print(f'Yahoo crypto history unavailable; trying verified Binance pairs: {error}')
        downloaded = pd.DataFrame()
    def worker(coin):
        if symbols[coin['symbol']] != 1 or not history_ticker(coin):
            asset = enrich(coin, pd.DataFrame(), None)
            asset['historyUnavailableReason'] = 'Asset identity not verified or duplicate ticker'
            return asset
        if coin['id'] in reuse:
            return apply_quote_freshness(dict(cached[coin['id']], **coin))
        frame = confirmed(extract_ticker_frame(downloaded, history_ticker(coin)))
        history_source = 'Yahoo Finance (USD)'
        if len(frame) < 50 or (datetime.now(timezone.utc).date()-frame.index[-1].date()).days != 1:
            try:
                frame = confirmed(exchange_history(coin['symbol']))
                history_source = 'Binance market data (USDT)'
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
                frame = pd.DataFrame()
        asset = enrich(coin, frame, history_source)
        old = cached.get(coin['id'])
        if asset['historyUnavailable'] and old and not old.get('historyUnavailable') and old.get('priceDate') and (now.date()-datetime.fromisoformat(old['priceDate']).date()).days <= 4:
            retained = dict(old, **coin, historyUpdateError='Using previous confirmed history', historyStale=True, earlyCycle=False)
            retained['signals'] = [s for s in retained.get('signals', []) if s['type'] != 'early-cycle']
            return apply_quote_freshness(retained)
        asset.update(historyTarget=target, historyCheckedAt=now.isoformat(), analysisVersion=ANALYSIS_VERSION)
        return asset
    with ThreadPoolExecutor(max_workers=5) as executor:
        assets = list(executor.map(worker, coins))
    for asset in assets:
        benchmark=benchmarks.get(asset.get('liquidityCurrency'))
        if asset.get('symbol') == 'BTC' and benchmark:
            benchmark=dict(benchmark,history=asset.get('returnHistory',[]),source=asset.get('historySource'))
        attach_quality(asset,benchmark)
    analyzed = sum(not a['historyUnavailable'] for a in assets)
    if not analyzed:
        raise RuntimeError('No historical crypto data; refusing to replace a working snapshot.')
    result = dict(generatedAt=datetime.now(timezone.utc).isoformat(), source=source,
                  assets=assets, analyzedCount=analyzed,
                  unavailableSymbols=[a['symbol'] for a in assets if a['historyUnavailable']],
                  refreshMinutes=30, benchmarks=benchmarks, quoteDescription='Provider quotes refreshed every 30 minutes; confirmed UTC daily bars for signals.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f'Crypto: {len(assets)} ranked assets; {analyzed} analyzed; quotes from {source}.')
    print(f"Quality: RS20 available {sum(a.get('relativeStrength20') is not None for a in assets)}, RS60 available {sum(a.get('relativeStrength60') is not None for a in assets)}, liquid {sum(a.get('liquidityPassed',False) for a in assets)}, strong close {sum(a.get('strongClose',False) for a in assets)}.")
    unavailable_text=', '.join(result['unavailableSymbols']).encode('ascii',errors='backslashreplace').decode('ascii')
    print('History unavailable: ' + unavailable_text)
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
