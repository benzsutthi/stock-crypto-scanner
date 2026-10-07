"""Market-aware refresh rules; all timestamps are timezone-aware."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ANALYSIS_VERSION = 'confirmed-quality-rs-v1'


def read_previous(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
        return data if isinstance(data, dict) and isinstance(data.get('assets'), list) else {}
    except (OSError, ValueError, TypeError):
        return {}


def stock_session(market, now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Asia/Bangkok' if market == 'Thai' else 'America/New_York'))
    cutoff = (17, 15) if market == 'Thai' else (16, 30)
    day = local.date()
    if (local.hour, local.minute) < cutoff:
        day -= timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    return day.isoformat()


def market_open(market, now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Asia/Bangkok' if market == 'Thai' else 'America/New_York'))
    clock = (local.hour, local.minute)
    # Include a publication buffer after closing. Holidays are identified from quote timestamps.
    return local.weekday() < 5 and ((9, 45) <= clock <= (17, 15) if market == 'Thai' else (9, 30) <= clock <= (16, 30))


def reusable(asset, session, now=None):
    if not asset or asset.get('historyTarget') != session or not asset.get('historyCheckedAt'):
        return False
    try:
        age = (now or datetime.now(timezone.utc)) - datetime.fromisoformat(asset['historyCheckedAt'])
        # Retry a lagging provider next cycle; complete session histories can be cached longer.
        ttl = timedelta(minutes=30) if asset.get('priceDate', '') < session else timedelta(hours=6)
        return timedelta(0) <= age < ttl
    except (ValueError, TypeError):
        return False


def overlay_quote(asset, frame):
    """Intraday change is versus the previous session close, never the intraday daily bar."""
    if frame.empty or 'Close' not in frame:
        return asset
    frame = frame.dropna(subset=['Close'])
    if frame.empty:
        return asset
    last = frame.index[-1]
    quote_day = last.date().isoformat()
    if quote_day < asset['priceDate']:
        return asset
    baseline = asset['previousClose'] if quote_day == asset['priceDate'] else asset['techPrice']
    earlier = frame.loc[[stamp.date() < last.date() for stamp in frame.index]]
    if not earlier.empty:
        baseline = float(earlier.Close.iloc[-1])
    price = float(frame.Close.iloc[-1])
    if price <= 0 or baseline <= 0:
        return asset
    return dict(asset, price=price, change=round((price / baseline - 1)*100, 2),
                quoteAt=last.isoformat(), quoteDate=quote_day, quoteType='15m',
                historySource=asset.get('historySource') or 'Yahoo Finance adjusted daily close',
                priceSource='Yahoo Finance adjusted 15-minute reference', priceBasis='adjusted-intraday')
