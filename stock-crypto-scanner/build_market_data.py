"""Build a daily stock quote/technical snapshot consumed by the static screener."""
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf
import requests

from config import THAI_STOCKS, US_STOCKS
from technicals import analyze
from zoneinfo import ZoneInfo
from market_history import clean_history


def confirmed_stock(frame, market, now=None):
    now = now or datetime.now(ZoneInfo('Asia/Bangkok' if market == 'Thai' else 'America/New_York'))
    frame = clean_history(frame)
    if frame.empty:
        return frame
    cutoff = now.date()
    close_time = (17, 15) if market == 'Thai' else (16, 30)
    if (now.hour, now.minute) < close_time:
        cutoff -= timedelta(days=1)
    return frame.loc[[stamp.date() <= cutoff for stamp in frame.index]]


def stock_history_stale(price_date, market, now=None):
    # Conservative weekday check: exchange holidays may be marked delayed.
    now = now or datetime.now(ZoneInfo('Asia/Bangkok' if market == 'Thai' else 'America/New_York'))
    expected = now.date()
    if (now.hour, now.minute) < ((17, 15) if market == 'Thai' else (16, 30)):
        expected -= timedelta(days=1)
    while expected.weekday() >= 5:
        expected -= timedelta(days=1)
    return price_date < expected


def extract_ticker_frame(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded.empty:
        return pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        for level in range(downloaded.columns.nlevels):
            if symbol in downloaded.columns.get_level_values(level):
                return downloaded.xs(symbol, axis=1, level=level, drop_level=True)
        return pd.DataFrame()
    return downloaded


def build_snapshot(output: Path) -> dict:
    symbols = list(dict.fromkeys([*US_STOCKS, *THAI_STOCKS]))
    print(f"Downloading daily history for {len(symbols)} US/Thai tickers...")
    try:
        downloaded = yf.download(
            tickers=symbols,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=8,
            progress=False,
            timeout=30,
        )
    except Exception as error:
        print(f'Batch download failed; retrying individually: {error}')
        downloaded = pd.DataFrame()

    assets = []
    failed = []
    thai_set = set(THAI_STOCKS)
    for symbol in symbols:
        market = 'Thai' if symbol in thai_set else 'US'
        frame = extract_ticker_frame(downloaded, symbol)
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(-1)
        frame = confirmed_stock(frame, market)
        if len(frame) < 50 or stock_history_stale(frame.index[-1].date(), market):
            try:
                retry = confirmed_stock(yf.Ticker(symbol).history(period='1y', interval='1d', auto_adjust=True, timeout=20), market)
                if len(retry) >= 50 and (frame.empty or retry.index[-1].date() >= frame.index[-1].date()):
                    frame = retry
            except Exception as error:
                print(f'{symbol}: retry failed: {error}')
        if len(frame) < 50:
            failed.append(symbol)
            continue

        market = "Thai" if symbol in thai_set else "US"
        result = analyze(frame)
        if not result:
            failed.append(symbol)
            continue
        stale = stock_history_stale(frame.index[-1].date(), market)
        if stale:
            result['earlyCycle'] = False
            result['signals'] = [s for s in result['signals'] if s['type'] != 'early-cycle']
        assets.append({
            "market": market,
            "symbol": symbol.removesuffix(".BK"),
            "name": symbol.removesuffix(".BK"),
            "currency": "THB" if market == "Thai" else "USD",
            **result,
            "priceDate": frame.index[-1].date().isoformat(),
            "historyStale": stale,
            "priceSource": "Yahoo Finance adjusted daily close",
            "priceBasis": "adjusted-close",
        })

    # A partial provider outage must not silently remove previously listed stocks.
    if failed:
        try:
            response = requests.get('https://benzsutthi.github.io/stock-crypto-scanner/data/stocks.json', timeout=15)
            response.raise_for_status()
            previous = {(a['market'], a['symbol']): a for a in response.json()['assets']}
            for symbol in failed:
                key = ('Thai' if symbol in thai_set else 'US', symbol.removesuffix('.BK'))
                if key in previous:
                    asset = dict(previous[key], updateError='Using previously published data', historyStale=True, earlyCycle=False)
                    asset['signals'] = [s for s in asset.get('signals', []) if s['type'] != 'early-cycle']
                    assets.append(asset)
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            print(f'Previous stock snapshot unavailable: {error}')

    if not assets or not all(any(asset['market'] == market for asset in assets) for market in ('US', 'Thai')):
        raise RuntimeError("No stock data was returned by Yahoo Finance; refusing to publish an empty snapshot.")

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance via yfinance",
        "markets": {"US": len([asset for asset in assets if asset["market"] == "US"]),
                    "Thai": len([asset for asset in assets if asset["market"] == "Thai"])},
        "assets": assets,
        "failedSymbols": failed,
        "staleSymbols": [a['symbol'] for a in assets if a.get('historyStale')],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"Saved {len(assets)} stocks ({snapshot['markets']['US']} US, {snapshot['markets']['Thai']} Thai); {len(failed)} unavailable.")
    if failed:
        print("Unavailable symbols: " + ", ".join(failed))
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/stocks.json"))
    args = parser.parse_args()
    build_snapshot(args.output)
