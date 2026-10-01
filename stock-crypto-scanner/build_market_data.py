"""Build a daily stock quote/technical snapshot consumed by the static screener."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import THAI_STOCKS, US_STOCKS
from technicals import analyze
from zoneinfo import ZoneInfo


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

    assets = []
    failed = []
    thai_set = set(THAI_STOCKS)
    for symbol in symbols:
        frame = extract_ticker_frame(downloaded, symbol)
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(-1)
        required = ["Close", "High", "Low", "Volume"]
        if frame.empty or any(column not in frame.columns for column in required):
            failed.append(symbol)
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
            "priceDate": frame.index[-1].date().isoformat(),
        })

    if not assets or not all(any(asset['market'] == market for asset in assets) for market in ('US', 'Thai')):
        raise RuntimeError("No stock data was returned by Yahoo Finance; refusing to publish an empty snapshot.")

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance via yfinance",
        "markets": {"US": len([asset for asset in assets if asset["market"] == "US"]),
                    "Thai": len([asset for asset in assets if asset["market"] == "Thai"])},
        "assets": assets,
        "failedSymbols": failed,
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
