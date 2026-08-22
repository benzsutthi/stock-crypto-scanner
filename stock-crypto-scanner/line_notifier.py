# line_notifier.py
import requests
import json
from datetime import datetime

def format_price(price: float, currency: str = "$") -> str:
    """จัดรูปแบบราคาให้สวยงาม รองรับทั้งเหรียญทศนิยมเยอะและหุ้นปกติ"""
    if price >= 1000:
        return f"{currency}{price:,.2f}"
    elif price >= 1:
        return f"{currency}{price:,.2f}"
    elif price >= 0.01:
        return f"{currency}{price:.4f}"
    else:
        return f"{currency}{price:.6f}"

def format_report(scan_results):
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    stats = scan_results.get("universe_stats", {})
    total_scanned = stats.get("total_count", 0)
    
    total_found = len(scan_results['crypto']) + len(scan_results['us_stocks']) + len(scan_results['thai_stocks'])
    
    msg_lines = []
    msg_lines.append("📊 【 สรุปสัญญาณตลาดเด่นประจำวัน Top 3 】")
    if total_scanned > 0:
        msg_lines.append(f"🕒 {now_str} (สแกน {total_scanned} สินทรัพย์ทั่วโลก)")
    else:
        msg_lines.append(f"🕒 {now_str}")
    msg_lines.append("")
    
    # หมวดคริปโต
    if scan_results['crypto']:
        msg_lines.append("🪙 【 CRYPTO TOP 3 】")
        for i, item in enumerate(scan_results['crypto'][:3], 1):
            sign_str = "+" if item['change_pct'] >= 0 else ""
            formatted_price = format_price(item['price'], "$")
            signals_str = " + ".join([s.split(" (")[0] for s in item['signals']])
            msg_lines.append(f"{i}. {item['display_name']}: {formatted_price} ({sign_str}{item['change_pct']}%) | Vol {item['vol_ratio']}x | RSI {item['rsi']}")
            msg_lines.append(f"   ↳ {signals_str}")
        msg_lines.append("")

    # หมวดหุ้นสหรัฐฯ
    if scan_results['us_stocks']:
        msg_lines.append("🇺🇸 【 US STOCKS TOP 3 】")
        for i, item in enumerate(scan_results['us_stocks'][:3], 1):
            sign_str = "+" if item['change_pct'] >= 0 else ""
            formatted_price = format_price(item['price'], "$")
            signals_str = " + ".join([s.split(" (")[0] for s in item['signals']])
            msg_lines.append(f"{i}. {item['display_name']}: {formatted_price} ({sign_str}{item['change_pct']}%) | Vol {item['vol_ratio']}x | RSI {item['rsi']}")
            msg_lines.append(f"   ↳ {signals_str}")
        msg_lines.append("")

    # หมวดหุ้นไทย
    if scan_results['thai_stocks']:
        msg_lines.append("🇹🇭 【 THAI SET TOP 3 】")
        for i, item in enumerate(scan_results['thai_stocks'][:3], 1):
            sign_str = "+" if item['change_pct'] >= 0 else ""
            formatted_price = format_price(item['price'], "฿")
            signals_str = " + ".join([s.split(" (")[0] for s in item['signals']])
            msg_lines.append(f"{i}. {item['display_name']}: {formatted_price} ({sign_str}{item['change_pct']}%) | Vol {item['vol_ratio']}x | RSI {item['rsi']}")
            msg_lines.append(f"   ↳ {signals_str}")
        msg_lines.append("")

    if total_found == 0:
        msg_lines.append("😴 วันนี้ตลาดค่อนข้างนิ่ง ยังไม่พบสินทรัพย์ที่เข้าเกณฑ์เทคนิคอลสำคัญ")
    else:
        msg_lines.append("⚠️ ข้อมูลคัดกรองทางเทคนิคอลเบื้องต้น โปรดตั้ง Stop Loss เสมอ")

    return "\n".join(msg_lines)

def send_line_broadcast(message_text, token):
    """ส่ง Broadcast ข้อความผ่าน LINE Messaging API"""
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # ตัดความยาวไม่ให้เกิน 5000 อักษร (ลิมิตของ LINE ต่อ 1 บล็อก)
    if len(message_text) > 4900:
        message_text = message_text[:4900] + "\n...(ข้อความยาวเกินไป)"

    payload = {
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("✅ ส่งแจ้งเตือนทาง LINE สำเร็จเรียบร้อยแล้ว!")
        return True
    else:
        print(f"❌ ส่ง LINE ไม่สำเร็จ ({response.status_code}): {response.text}")
        return False
