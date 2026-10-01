# scanner.py
import urllib.request
import json
import concurrent.futures
import yfinance as yf
import pandas as pd
from datetime import datetime
from technicals import analyze
from zoneinfo import ZoneInfo

# รายชื่อเหรียญ Stablecoins และเหรียญ Leveraged ที่ต้องตัดออก
EXCLUDE_CRYPTO = {
    "USDC", "USDT", "FDUSD", "TUSD", "DAI", "BUSD", "USDE", "USD1", "RLUSD", "USTC",
    "EUR", "GBP", "TRY", "AUD", "BRL", "WBTC", "WETH", "WSTETH", "STETH"
}

def fetch_dynamic_binance_crypto(min_vol_usd: float = 8000000, limit: int = 60, fallback_list: list = None):
    """
    ดึงรายชื่อเหรียญคริปโตคู่ USDT จาก Binance API แบบ Real-time
    กรองเฉพาะเหรียญที่มี Volume สูงสุด และตัด Stablecoin ออก
    """
    try:
        url = "https://data-api.binance.vision/api/v3/ticker/24hr"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        candidates = []
        for item in data:
            sym = item.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            # ตัด Leveraged tokens (UP, DOWN, BEAR, BULL)
            if any(sym.endswith(x) for x in ["UPUSDT", "DOWNUSDT", "BEARUSDT", "BULLUSDT"]):
                continue
            
            base_coin = sym[:-4] # ตัด USDT ออก
            if base_coin in EXCLUDE_CRYPTO:
                continue
            
            quote_vol = float(item.get("quoteVolume", 0))
            if quote_vol >= min_vol_usd:
                candidates.append((base_coin, quote_vol))
        
        # เรียงตาม Volume ซื้อขาย 24 ชั่วโมงจากมากไปน้อย
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_coins = [f"{coin}-USD" for coin, _ in candidates[:limit]]
        
        if top_coins:
            print(f"🌐 [Dynamic Discovery] ดึงเหรียญยอดนิยมจาก Binance สำเร็จ: {len(top_coins)} เหรียญ")
            return top_coins
    except Exception as e:
        print(f"⚠️ ไม่สามารถเชื่อมต่อ Binance API ได้ ({e}) -> สลับไปใช้รายชื่อสำรอง")
    
    return fallback_list if fallback_list else ["BTC-USD", "ETH-USD", "SOL-USD"]

def analyze_binance_crypto(coin_name: str):
    """
    ดึงแท่งเทียนย้อนหลัง 100 วันของเหรียญจาก Binance Klines API โดยตรง (เร็วและแม่นยำ 100%)
    """
    try:
        pair = f"{coin_name}USDT"
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={pair}&interval=1d&limit=250"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
        
        if not raw or len(raw) < 50:
            return None
            
        raw = [bar for bar in raw if int(bar[6]) < datetime.now().timestamp() * 1000]
        df = pd.DataFrame(raw, columns=['open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        return evaluate_dataframe(df, symbol=f"{coin_name}-USD", display_name=coin_name, asset_type="Crypto")
    except Exception:
        return None

def evaluate_dataframe(df: pd.DataFrame, symbol: str, display_name: str, asset_type: str, include_no_signal: bool = False):
    """คำนวณ Indicator ทางเทคนิคและตัดเกรดสัญญาณ"""
    try:
        df = df.dropna(subset=['Close', 'High', 'Low', 'Volume'])
        if len(df) < 50:
            return None
        result = analyze(df)
        if not result['signals'] and not include_no_signal:
            return None

        return {
            "symbol": symbol,
            "display_name": display_name,
            "asset_type": asset_type,
            "price": result['price'],
            "change_pct": result['change'],
            "rsi": result['rsi'],
            "vol_ratio": result['volumeRatio'],
            "ema20": result['ema20'],
            "ema50": result['ema50'],
            "high20": result['high20'],
            "signals": [s['label'] for s in result['signals']],
            "score": result['score']
        }
    except Exception:
        return None
        
def analyze_ticker(symbol: str, asset_type: str = "US", include_no_signal: bool = False):
    """
    ดึงข้อมูลหุ้นผ่าน yfinance และคำนวณ Indicator
    """
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        now = datetime.now(ZoneInfo('Asia/Bangkok' if symbol.endswith('.BK') else 'America/New_York'))
        cutoff = (17, 15) if symbol.endswith('.BK') else (16, 30)
        if (now.hour, now.minute) < cutoff:
            df = df.loc[[stamp.date() < now.date() for stamp in df.index]]
            
        required_cols = ['Close', 'High', 'Low', 'Volume']
        for col in required_cols:
            if col not in df.columns:
                return None
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df = df.dropna(subset=['Close'])
        if len(df) < 50:
            return None

        display_name = symbol.replace(".BK", " (SET)").replace("-USD", "")
        return evaluate_dataframe(df, symbol=symbol, display_name=display_name, asset_type=asset_type, include_no_signal=include_no_signal)
    except Exception:
        return None

def scan_symbol_list_parallel(symbols: list, asset_type: str, max_workers: int = 12) -> list:
    """สแกนรายชื่อสินทรัพย์พร้อมกันแบบ Parallel Concurrency"""
    results = []
    
    def worker_func(s):
        if asset_type == "Crypto":
            clean_name = s.replace("-USD", "").replace("USDT", "")
            return analyze_binance_crypto(clean_name)
        else:
            return analyze_ticker(s, asset_type=asset_type)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_func, s): s for s in symbols}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res and len(res.get('signals', [])) > 0:
                results.append(res)
                
    # จัดเรียงตามคะแนนความแรงของสัญญาณ (Score) และ Volume Ratio
    results.sort(key=lambda x: (x.get('score', 0), x.get('vol_ratio', 0)), reverse=True)
    return results

def scan_all(us_stocks, thai_stocks, crypto_list, use_dynamic_binance=True, min_vol_usd=8000000, top_crypto_limit=60, max_picks=6):
    """
    สแกนตลาดทั้งหมด (Dynamic Discovery + Multi-threading)
    """
    results = {
        "crypto": [],
        "us_stocks": [],
        "thai_stocks": [],
        "universe_stats": {}
    }
    
    # 1. จัดเตรียมรายชื่อ Crypto
    if use_dynamic_binance:
        active_crypto = fetch_dynamic_binance_crypto(min_vol_usd, top_crypto_limit, fallback_list=crypto_list)
    else:
        active_crypto = crypto_list

    results["universe_stats"] = {
        "crypto_count": len(active_crypto),
        "us_count": len(us_stocks),
        "thai_count": len(thai_stocks),
        "total_count": len(active_crypto) + len(us_stocks) + len(thai_stocks)
    }

    print(f"🔍 เริ่มสแกน {results['universe_stats']['total_count']} สินทรัพย์ (Crypto: {len(active_crypto)}, US: {len(us_stocks)}, SET: {len(thai_stocks)})...")

    # 2. สแกน Crypto
    print("⏳ กำลังสแกนคริปโต (Crypto)...")
    crypto_matches = scan_symbol_list_parallel(active_crypto, asset_type="Crypto", max_workers=12)
    results["crypto"] = crypto_matches[:max_picks]
    print(f"   -> พบสัญญาณคริปโต {len(crypto_matches)} ตัว (คัดเลือก Top {len(results['crypto'])} ตัวเด่น)")

    # 3. สแกน US Stocks
    print("⏳ กำลังสแกนหุ้นสหรัฐฯ (US Stocks)...")
    us_matches = scan_symbol_list_parallel(us_stocks, asset_type="US Stock", max_workers=12)
    results["us_stocks"] = us_matches[:max_picks]
    print(f"   -> พบสัญญาณหุ้น US {len(us_matches)} ตัว (คัดเลือก Top {len(results['us_stocks'])} ตัวเด่น)")

    # 4. สแกน Thai SET Stocks
    print("⏳ กำลังสแกนหุ้นไทย (Thai SET)...")
    thai_matches = scan_symbol_list_parallel(thai_stocks, asset_type="Thai Stock", max_workers=12)
    results["thai_stocks"] = thai_matches[:max_picks]
    print(f"   -> พบสัญญาณหุ้นไทย {len(thai_matches)} ตัว (คัดเลือก Top {len(results['thai_stocks'])} ตัวเด่น)")

    return results

