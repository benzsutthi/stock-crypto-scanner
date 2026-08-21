# line_notifier.py
import requests
import json
from datetime import datetime

def format_report(scan_results):
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    total_found = len(scan_results['crypto']) + len(scan_results['us_stocks']) + len(scan_results['thai_stocks'])
    
    msg_lines = []
    msg_lines.append(f"📊 [รายงานสแกนหุ้น & คริปโตเด่น]")
    msg_lines.append(f"🕒 อัปเดต: {now_str}")
    msg_lines.append(f"🎯 พบสินทรัพย์น่าสนใจทั้งหมด: {total_found} ตัว\n")
    
    # หมวดคริปโต
    if scan_results['crypto']:
        msg_lines.append("🪙 【 CRYPTO PICKS 】")
        for item in scan_results['crypto']:
            sign_str = " + " if item['change_pct'] >= 0 else " "
            msg_lines.append(f"• {item['display_name']}: ${item['price']:,.2f} ({sign_str}{item['change_pct']}%)")
            msg_lines.append(f"   RSI: {item['rsi']} | Vol: {item['vol_ratio']}x")
            for sig in item['signals']:
                msg_lines.append(f"   ↳ {sig}")
        msg_lines.append("")

    # หมวดหุ้นสหรัฐฯ
    if scan_results['us_stocks']:
        msg_lines.append("🇺🇸 【 US STOCKS PICKS 】")
        for item in scan_results['us_stocks']:
            sign_str = " + " if item['change_pct'] >= 0 else " "
            msg_lines.append(f"• {item['display_name']}: ${item['price']:,.2f} ({sign_str}{item['change_pct']}%)")
            msg_lines.append(f"   RSI: {item['rsi']} | Vol: {item['vol_ratio']}x")
            for sig in item['signals']:
                msg_lines.append(f"   ↳ {sig}")
        msg_lines.append("")

    # หมวดหุ้นไทย
    if scan_results['thai_stocks']:
        msg_lines.append("🇹🇭 【 THAI STOCKS (SET) 】")
        for item in scan_results['thai_stocks']:
            sign_str = " + " if item['change_pct'] >= 0 else " "
            msg_lines.append(f"• {item['display_name']}: ฿{item['price']:,.2f} ({sign_str}{item['change_pct']}%)")
            msg_lines.append(f"   RSI: {item['rsi']} | Vol: {item['vol_ratio']}x")
            for sig in item['signals']:
                msg_lines.append(f"   ↳ {sig}")
        msg_lines.append("")

    if total_found == 0:
        msg_lines.append("😴 วันนี้ตลาดค่อนข้างนิ่ง ยังไม่พบสินทรัพย์ที่เข้าเกณฑ์เทคนิคอลสำคัญ")
    else:
        msg_lines.append("⚠️ ข้อมูลนี้เป็นการคัดกรองทางเทคนิคอลเบื้องต้น ไม่ใช่คำแนะนำทางการเงิน โปรดบริหารความเสี่ยง (Stop Loss) เสมอ")

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
