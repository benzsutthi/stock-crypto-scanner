"""Send confirmed daily watchlist signals; update state only after LINE accepts."""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
from technicals import analyze


def select_new(asset, state):
    key = f"{asset['market']}:{asset['symbol']}"
    previous = state.get(key, {})
    if asset['priceDate'] <= previous.get('date', ''):
        return []
    active = {s['type'] for s in asset['signals']}
    return [s for s in asset['signals'] if s['type'] not in previous.get('active', [])]


def main():
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
    watch = json.loads(os.environ.get('WATCHLIST_JSON') or '[]')
    market_filter = os.environ.get('ALERT_MARKET', 'All')
    path = Path(os.environ.get('ALERT_STATE_PATH', '.alert-state/state.json'))
    if not watch:
        print('Watchlist empty; no alerts requested.')
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text('{}', encoding='utf-8')
        return
    if not token:
        raise RuntimeError('LINE_CHANNEL_ACCESS_TOKEN secret is required')
    state = json.loads(path.read_text()) if path.exists() else {}
    updated = dict(state)
    messages = []
    for key in dict.fromkeys(watch):
        market, symbol = key.split(':', 1)
        if market not in ('Thai', 'US', 'Crypto'):
            raise ValueError(f'Invalid market: {market}')
        if market_filter != 'All' and market not in (market_filter, 'Crypto'):
            continue
        ticker = symbol+'.BK' if market == 'Thai' else symbol+'-USD' if market == 'Crypto' else symbol
        frame = yf.Ticker(ticker).history(period='1y', interval='1d', auto_adjust=True)
        if frame.empty:
            print(f'Unavailable: {ticker}'); continue
        tz = 'Asia/Bangkok' if market == 'Thai' else 'America/New_York' if market == 'US' else 'UTC'
        now = datetime.now(ZoneInfo(tz))
        cutoff = (17, 15) if market == 'Thai' else (16, 30) if market == 'US' else (24, 0)
        if (now.hour, now.minute) < cutoff:
            frame = frame.loc[[stamp.date() < now.date() for stamp in frame.index]]
        frame = frame.dropna(subset=['Close', 'High', 'Low', 'Volume'])
        if len(frame) < 50:
            continue
        if (now.date() - frame.index[-1].date()).days > 4:
            print(f'Skipping stale daily quote: {ticker}')
            continue
        asset = dict(market=market, symbol=symbol, priceDate=frame.index[-1].date().isoformat(), **analyze(frame,volume_basis='quote' if market=='Crypto' else 'base'))
        if asset['priceDate'] <= state.get(key, {}).get('date', ''):
            continue
        signals = select_new(asset, state)
        if signals:
            messages.append(f"{market} {symbol} · ปิด {asset['priceDate']}\nราคา {asset['price']:.2f} · RSI {asset['rsi']}\n" + ' / '.join(s['label'] for s in signals))
        updated[key] = {'date': asset['priceDate'], 'active': [s['type'] for s in asset['signals']]}
    # Single request prevents partially sent batches from being replayed.
    if messages:
        text = 'MarketScope · สัญญาณใหม่ใน Watchlist\n\n' + '\n\n'.join(messages)
        if len(text) > 4900:
            raise RuntimeError('Watchlist report exceeds LINE limit; reduce watchlist size.')
        response = requests.post('https://api.line.me/v2/bot/message/broadcast',
            headers={'Authorization': f'Bearer {token}'},
            json={'messages': [{'type': 'text', 'text': text}]}, timeout=30)
        response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(updated, ensure_ascii=False), encoding='utf-8')
    print(f'Sent {len(messages)} watchlist notifications.')


if __name__ == '__main__':
    main()
