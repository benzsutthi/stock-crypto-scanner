# scanner.py
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime

def analyze_ticker(symbol: str, asset_type: str = "US"):
    """
    ดึงข้อมูลและคำนวณ Indicator ทางเทคนิคของสินทรัพย์แต่ละตัว
    """
    try:
        # ดึงข้อมูลย้อนหลัง 1 ปี (Daily timeframe)
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None
        
        # จัดการกรณี MultiIndex column ของ yfinance เวอร์ชั่นใหม่
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # ตรวจสอบคอลัมน์ที่จำเป็น
        required_cols = ['Close', 'High', 'Low', 'Volume']
        for col in required_cols:
            if col not in df.columns:
                return None
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df = df.dropna(subset=['Close'])
        if len(df) < 50:
            return None

        # คำนวณ Indicators
        close_series = df['Close']
        high_series = df['High']
        vol_series = df['Volume']

        df['EMA20'] = ta.trend.ema_indicator(close_series, window=20)
        df['EMA50'] = ta.trend.ema_indicator(close_series, window=50)
        if len(df) >= 200:
            df['EMA200'] = ta.trend.ema_indicator(close_series, window=200)
        else:
            df['EMA200'] = None

        df['RSI'] = ta.momentum.rsi(close_series, window=14)
        
        macd = ta.trend.MACD(close_series)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Diff'] = macd.macd_diff()
        
        df['Vol_SMA20'] = ta.trend.sma_indicator(vol_series, window=20)
        df['High_20'] = high_series.rolling(window=20).max()

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        curr_close = float(curr['Close'])
        prev_close = float(prev['Close'])
        change_pct = ((curr_close - prev_close) / prev_close) * 100
        
        curr_vol = float(curr['Volume']) if curr['Volume'] > 0 else 0
        vol_sma20 = float(curr['Vol_SMA20']) if curr['Vol_SMA20'] > 0 else 1
        vol_ratio = curr_vol / vol_sma20 if vol_sma20 > 0 else 1.0

        rsi = float(curr['RSI']) if pd.notna(curr['RSI']) else 50.0
        ema20 = float(curr['EMA20']) if pd.notna(curr['EMA20']) else 0
        ema50 = float(curr['EMA50']) if pd.notna(curr['EMA50']) else 0
        ema200 = float(curr['EMA200']) if pd.notna(curr['EMA200']) else None
        
        signals = []

        # 1. เงื่อนไข Momentum / Breakout (มีแรงส่ง+โวลุ่มเข้า)
        is_breakout = (curr_close >= float(prev['High_20']) * 0.99)
        is_uptrend = (curr_close > ema20 > ema50)
        if (is_uptrend or is_breakout) and vol_ratio >= 1.3 and (50 <= rsi <= 72):
            signals.append("🚀 Strong Momentum (โวลุ่มเข้า+ทรงขาขึ้น)")

        # 2. เงื่อนไข MACD Bullish Crossover (จุดตัดกลับตัวขึ้น)
        if prev['MACD'] <= prev['MACD_Signal'] and curr['MACD'] > curr['MACD_Signal'] and curr_close > ema20:
            signals.append("🎯 MACD Bullish Cross (เริ่มกลับตัวขึ้น)")

        # 3. เงื่อนไข Oversold Bounce (โซนล่างน่าสะสม)
        if (float(prev['RSI']) < 32 and rsi >= 32) or (rsi < 30):
            signals.append("💎 Oversold Zone (โซนขายมากเกินไป/เริ่มฟื้น)")

        # จัดชื่อให้สวยงาม (ตัด .BK ออก หรือแสดงคู่เหรียญ)
        display_name = symbol.replace(".BK", " (SET)").replace("-USD", "")

        result = {
            "symbol": symbol,
            "display_name": display_name,
            "asset_type": asset_type,
            "price": curr_close,
            "change_pct": round(change_pct, 2),
            "rsi": round(rsi, 1),
            "vol_ratio": round(vol_ratio, 2),
            "signals": signals
        }
        return result
    except Exception as e:
        # print(f"Error {symbol}: {e}")
        return None

def scan_all(us_stocks, thai_stocks, crypto_list):
    """สแกนสินทรัพย์ทั้งหมดและคัดกรองตัวที่มีสัญญาณน่าสนใจ"""
    results = {
        "crypto": [],
        "us_stocks": [],
        "thai_stocks": []
    }
    
    print("🔍 กำลังสแกนคริปโต (Crypto)...")
    for s in crypto_list:
        data = analyze_ticker(s, asset_type="Crypto")
        if data and len(data['signals']) > 0:
            results["crypto"].append(data)
            
    print("🔍 กำลังสแกนหุ้นสหรัฐฯ (US Stocks)...")
    for s in us_stocks:
        data = analyze_ticker(s, asset_type="US Stock")
        if data and len(data['signals']) > 0:
            results["us_stocks"].append(data)

    print("🔍 กำลังสแกนหุ้นไทย (Thai Stocks)...")
    for s in thai_stocks:
        data = analyze_ticker(s, asset_type="Thai Stock")
        if data and len(data['signals']) > 0:
            results["thai_stocks"].append(data)

    return results
