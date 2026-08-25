# main.py
import sys
import os

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import (
    LINE_CHANNEL_ACCESS_TOKEN, US_STOCKS, THAI_STOCKS, CRYPTO_LIST,
    MAX_PICKS_PER_CATEGORY, USE_DYNAMIC_BINANCE, BINANCE_MIN_VOL_USD, BINANCE_TOP_LIMIT
)
from scanner import scan_all
from line_notifier import format_text_report, send_line_broadcast

def main():
    print("=" * 50)
    print("🚀 เริ่มต้นระบบสแกนหุ้นและคริปโตประจำวัน (Dynamic All-Market)")
    print("=" * 50)
    
    results = scan_all(
        us_stocks=US_STOCKS,
        thai_stocks=THAI_STOCKS,
        crypto_list=CRYPTO_LIST,
        use_dynamic_binance=USE_DYNAMIC_BINANCE,
        min_vol_usd=BINANCE_MIN_VOL_USD,
        top_crypto_limit=BINANCE_TOP_LIMIT,
        max_picks=MAX_PICKS_PER_CATEGORY
    )
    
    report_text = format_text_report(results)
    print("\n" + "=" * 50)
    print("📝 สรุปรายงานตลาด:")
    print("=" * 50)
    print(report_text)
    print("=" * 50)
    
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ ไม่พบ LINE_CHANNEL_ACCESS_TOKEN")
        return
        
    print("\n📲 กำลังส่งข้อความไปยัง LINE (Flex Message)...")
    send_line_broadcast(results, LINE_CHANNEL_ACCESS_TOKEN)

if __name__ == "__main__":
    main()
