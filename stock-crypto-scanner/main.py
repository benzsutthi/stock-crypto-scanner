# main.py
import sys
import os

# บังคับให้ Console ของ Windows รองรับภาษาไทยและ Emoji (UTF-8)
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import LINE_CHANNEL_ACCESS_TOKEN, US_STOCKS, THAI_STOCKS, CRYPTO_LIST
from scanner import scan_all
from line_notifier import format_report, send_line_broadcast

def main():
    print("=" * 50)
    print("🚀 เริ่มต้นระบบสแกนหุ้นและคริปโตประจำวัน")
    print("=" * 50)
    
    # 1. สแกนสินทรัพย์ทั้งหมด
    results = scan_all(US_STOCKS, THAI_STOCKS, CRYPTO_LIST)
    
    # 2. จัดรูปแบบข้อความ
    report_text = format_report(results)
    
    print("\n" + "=" * 50)
    print("📝 ตัวอย่างข้อความที่จะส่ง:")
    print("=" * 50)
    print(report_text)
    print("=" * 50)
    
    # 3. ส่งเข้า LINE
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ ไม่พบ LINE_CHANNEL_ACCESS_TOKEN กรุณาตรวจสอบ config.py")
        return
        
    print("\n📲 กำลังส่งข้อความไปยัง LINE...")
    send_line_broadcast(report_text, LINE_CHANNEL_ACCESS_TOKEN)

if __name__ == "__main__":
    main()
