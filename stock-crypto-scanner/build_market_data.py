"""Build a daily stock quote/technical snapshot consumed by the static screener."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
import requests

from config import THAI_STOCKS, US_STOCKS
from technicals import analyze
from zoneinfo import ZoneInfo
from refresh_policy import read_previous, stock_session, market_open, reusable, overlay_quote


def extract_ticker_frame(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded.empty:
        return pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        for level in range(downloaded.columns.nlevels):
            if symbol in downloaded.columns.get_level_values(level):
                return downloaded.xs(symbol, axis=1, level=level, drop_level=True)
        return pd.DataFrame()
    return downloaded


def build_snapshot(output: Path, previous_path=None) -> dict:
    symbols = list(dict.fromkeys([*US_STOCKS, *THAI_STOCKS]))
    previous = read_previous(previous_path)
    cached = {(a['market'], a['symbol']): a for a in previous.get('assets', [])}
    now_utc = datetime.now(timezone.utc)
    targets = {market: stock_session(market, now_utc) for market in ('Thai', 'US')}
    thai_set = set(THAI_STOCKS)
    needed = [s for s in symbols if not reusable(cached.get(('Thai' if s in thai_set else 'US', s.removesuffix('.BK'))), targets['Thai' if s in thai_set else 'US'], now_utc)]
    print(f"Refreshing {len(needed)} daily histories; reusing {len(symbols)-len(needed)}.")
    downloaded = yf.download(
        tickers=needed,
        period="1y",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=8,
        progress=False,
        timeout=30,
    ) if needed else pd.DataFrame()

    assets = []
    failed = []
    for symbol in symbols:
        market = "Thai" if symbol in thai_set else "US"
        old = cached.get((market, symbol.removesuffix('.BK')))
        if symbol not in needed:
            assets.append(dict(old))
            continue
        frame = extract_ticker_frame(downloaded, symbol)
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(-1)
        required = ["Close", "High", "Low", "Volume"]
        if frame.empty or any(column not in frame.columns for column in required):
            failed.append(symbol)
            if old:
                assets.append(dict(old))
            continue
        frame = frame.copy()
        for column in required:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame.dropna(subset=required)
        market = "Thai" if symbol in thai_set else "US"
        now = datetime.now(ZoneInfo("Asia/Bangkok" if market == "Thai" else "America/New_York"))
        # Exclude today's bar until the exchange close plus a publication buffer.
        close_hour, close_minute = (17, 15) if market == "Thai" else (16, 30)
        if (now.hour, now.minute) < (close_hour, close_minute):
            frame = frame.loc[[stamp.date() < now.date() for stamp in frame.index]]
        if len(frame) < 50:
            failed.append(symbol)
            if old:
                assets.append(dict(old))
            continue

        market = "Thai" if symbol in thai_set else "US"
        result = analyze(frame)
        if not result:
            failed.append(symbol)
            continue
        assets.append({
            "market": market,
            "symbol": symbol.removesuffix(".BK"),
            "name": symbol.removesuffix(".BK"),
            "currency": "THB" if market == "Thai" else "USD",
            **result,
            "techPrice": result['price'],
            "previousClose": float(frame.Close.iloc[-2]),
            "priceDate": frame.index[-1].date().isoformat(),
            "historyCheckedAt": now_utc.isoformat(),
            "historyTarget": targets[market],
            "quoteAt": None,
            "quoteDate": frame.index[-1].date().isoformat(),
            "quoteType": "daily-close",
        })

    if not assets or not all(any(asset['market'] == market for asset in assets) for market in ('US', 'Thai')):
        raise RuntimeError("No stock data was returned by Yahoo Finance; refusing to publish an empty snapshot.")

    active = [a for a in assets if market_open(a['market'], now_utc) and 'previousClose' in a]
    quote_tickers = [a['symbol']+'.BK' if a['market']=='Thai' else a['symbol'] for a in active]
    quote_data = yf.download(quote_tickers, period='5d', interval='15m', group_by='ticker',
                             auto_adjust=True, threads=8, progress=False, timeout=20) if quote_tickers else pd.DataFrame()
    missing_quotes = []
    for i, asset in enumerate(assets):
        if asset not in active:
            continue
        ticker = asset['symbol']+'.BK' if asset['market']=='Thai' else asset['symbol']
        frame = extract_ticker_frame(quote_data, ticker)
        if not frame.empty:
            frame = frame.copy()
            zone = ZoneInfo('Asia/Bangkok' if asset['market']=='Thai' else 'America/New_York')
            frame.index = frame.index.tz_localize(timezone.utc).tz_convert(zone) if frame.index.tz is None else frame.index.tz_convert(zone)
        updated = overlay_quote(asset, frame)
        if frame.empty or updated.get('quoteType') != '15m':
            missing_quotes.append(ticker)
        assets[i] = updated

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance via yfinance",
        "markets": {"US": len([asset for asset in assets if asset["market"] == "US"]),
                    "Thai": len([asset for asset in assets if asset["market"] == "Thai"])},
        "assets": assets,
        "failedSymbols": failed,
        "missingQuoteSymbols": missing_quotes,
        "marketRefresh": {market: {"failedHistory": sum((s in thai_set) == (market == 'Thai') for s in failed),
                                    "failedQuotes": sum(s.endswith('.BK') == (market == 'Thai') for s in missing_quotes)} for market in ('Thai','US')},
        "refreshMinutes": 30,
        "quoteDescription": "Yahoo Finance 15-minute bars during market hours; may be delayed. Signals use confirmed daily bars.",
        "updateError": "Some daily histories could not be refreshed; retaining previous data where available." if failed else None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"Saved {len(assets)} stocks ({snapshot['markets']['US']} US, {snapshot['markets']['Thai']} Thai); {len(failed)} unavailable.")
    print(f"Stocks with 15-minute reference quotes: {sum(a.get('quoteType')=='15m' for a in assets)}; missing quote responses: {len(missing_quotes)}.")
    if failed:
        print("Unavailable symbols: " + ", ".join(failed))
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/stocks.json"))
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        build_snapshot(args.output, args.previous)
    except Exception as error:
        previous = read_previous(args.previous)
        if not previous.get('assets'):
            response = requests.get('https://benzsutthi.github.io/stock-crypto-scanner/data/stocks.json', timeout=15)
            response.raise_for_status()
            previous = response.json()
        if not previous.get('assets'):
            raise RuntimeError('No usable previous stock snapshot') from error
        previous['updateError'] = 'Latest stock update failed; displaying previous snapshot.'
        previous['keptPreviousSnapshot'] = True
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(previous, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        print(f'Keeping previous stock snapshot: {error}')
