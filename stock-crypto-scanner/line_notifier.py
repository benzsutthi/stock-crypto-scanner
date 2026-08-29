from datetime import datetime, timezone, timedelta

# กำหนด Timezone เวลาประเทศไทย (UTC+7)
try:
    import zoneinfo
    THAI_TZ = zoneinfo.ZoneInfo("Asia/Bangkok")
except Exception:
    THAI_TZ = timezone(timedelta(hours=7))

def get_thai_now() -> datetime:
    """ดึงเวลาปัจจุบันใน Timezone ประเทศไทย (UTC+7) เสมอ แม้รันบน GitHub Actions/Server UTC"""
    return datetime.now(THAI_TZ)

def format_price(price: float, currency: str = "$") -> str:
    if price >= 1000:
        return f"{currency}{price:,.2f}"
    elif price >= 1:
        return f"{currency}{price:,.2f}"
    elif price >= 0.01:
        return f"{currency}{price:.4f}"
    else:
        return f"{currency}{price:.6f}"

def get_tradingview_url(symbol: str, asset_type: str) -> str:
    if asset_type == "Crypto":
        clean_coin = symbol.replace("-USD", "").replace("USDT", "")
        return f"https://www.tradingview.com/symbols/{clean_coin}USDT/"
    elif asset_type == "Thai Stock":
        clean_stock = symbol.replace(".BK", "")
        return f"https://www.tradingview.com/symbols/SET-{clean_stock}/"
    else:
        return f"https://www.tradingview.com/symbols/{symbol}/"

def build_asset_box(item: dict, rank: int) -> dict:
    change_pct = item['change_pct']
    is_positive = change_pct >= 0
    change_str = f"+{change_pct}%" if is_positive else f"{change_pct}%"
    change_color = "#00C853" if is_positive else "#FF3D00"
    
    currency = "฿" if item['asset_type'] == "Thai Stock" else "$"
    price_str = format_price(item['price'], currency)
    tv_url = get_tradingview_url(item['symbol'], item['asset_type'])
    signals_summary = " • ".join([s.split(" (")[0] for s in item['signals']])

    return {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#1F2937",
        "cornerRadius": "10px",
        "paddingAll": "12px",
        "margin": "md",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#374151",
                        "cornerRadius": "4px",
                        "width": "24px",
                        "height": "24px",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "contents": [
                            {
                                "type": "text",
                                "text": str(rank),
                                "color": "#F9FAFB",
                                "size": "xs",
                                "weight": "bold"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": item['display_name'],
                        "weight": "bold",
                        "size": "md",
                        "color": "#FFFFFF",
                        "margin": "sm",
                        "flex": 4
                    },
                    {
                        "type": "text",
                        "text": change_str,
                        "weight": "bold",
                        "size": "sm",
                        "color": change_color,
                        "align": "end",
                        "flex": 3
                    }
                ]
            },
            {
                "type": "box",
                "layout": "horizontal",
                "margin": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": f"ราคา: {price_str}",
                        "size": "xs",
                        "color": "#D1D5DB",
                        "flex": 4
                    },
                    {
                        "type": "text",
                        "text": f"Vol {item['vol_ratio']}x | RSI {item['rsi']}",
                        "size": "xs",
                        "color": "#9CA3AF",
                        "align": "end",
                        "flex": 4
                    }
                ]
            },
            {
                "type": "text",
                "text": signals_summary,
                "size": "xxs",
                "color": "#FBBF24",
                "margin": "sm",
                "wrap": True
            },
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "margin": "sm",
                "color": "#374151",
                "action": {
                    "type": "uri",
                    "label": "📈 ดูกราฟ TradingView",
                    "uri": tv_url
                }
            }
        ]
    }

def build_category_bubble(title: str, subtitle: str, header_color: str, items: list) -> dict:
    body_contents = [
        {
            "type": "text",
            "text": subtitle,
            "size": "xs",
            "color": "#9CA3AF",
            "margin": "xs"
        }
    ]

    if items:
        for i, item in enumerate(items[:3], 1):
            body_contents.append(build_asset_box(item, i))
    else:
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "margin": "lg",
            "paddingAll": "16px",
            "backgroundColor": "#1F2937",
            "cornerRadius": "8px",
            "contents": [
                {
                    "type": "text",
                    "text": "😴 ยังไม่พบสัญญาณที่เข้าเกณฑ์ในหมวดนี้",
                    "size": "xs",
                    "color": "#9CA3AF",
                    "align": "center"
                }
            ]
        })

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "horizontal",
            "backgroundColor": header_color,
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                    "flex": 4
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#111827",
            "paddingAll": "16px",
            "contents": body_contents
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#111827",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "text",
                    "text": "⚠️ สัญญาณเทคนิคอลเบื้องต้น โปรดตั้ง Stop Loss เสมอ",
                    "size": "xxs",
                    "color": "#6B7280",
                    "align": "center",
                    "wrap": True
                }
            ]
        }
    }

def create_flex_message(scan_results: dict) -> dict:
    now_str = get_thai_now().strftime("%d/%m/%Y %H:%M น.")
    bubbles = [
        build_category_bubble(
            title="🪙 CRYPTO TOP PICKS",
            subtitle=f"อัปเดต {now_str} • สแกนจาก Binance",
            header_color="#B45309",
            items=scan_results.get('crypto', [])
        ),
        build_category_bubble(
            title="🇺🇸 US STOCKS TOP PICKS",
            subtitle=f"อัปเดต {now_str} • สแกนจาก US Top 100",
            header_color="#1E40AF",
            items=scan_results.get('us_stocks', [])
        ),
        build_category_bubble(
            title="🇹🇭 THAI SET TOP PICKS",
            subtitle=f"อัปเดต {now_str} • สแกนจาก SET100",
            header_color="#065F46",
            items=scan_results.get('thai_stocks', [])
        )
    ]

    return {
        "type": "flex",
        "altText": f"📊 รายงานสแกนหุ้นและคริปโตเด่นประจำวัน ({now_str})",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }

def format_text_report(scan_results):
    now_str = get_thai_now().strftime("%d/%m/%Y %H:%M น.")
    total_found = len(scan_results['crypto']) + len(scan_results['us_stocks']) + len(scan_results['thai_stocks'])
    
    msg_lines = [
        f"📊 【 สรุปสัญญาณตลาดเด่นประจำวัน Top 3 】",
        f"🕒 {now_str}",
        ""
    ]
    
    if scan_results['crypto']:
        msg_lines.append("🪙 【 CRYPTO TOP 3 】")
        for i, item in enumerate(scan_results['crypto'][:3], 1):
            sign_str = "+" if item['change_pct'] >= 0 else ""
            msg_lines.append(f"{i}. {item['display_name']}: ${item['price']:,.2f} ({sign_str}{item['change_pct']}%) | Vol {item['vol_ratio']}x | RSI {item['rsi']}")
            msg_lines.append(f"   ↳ {' • '.join([s.split(' (')[0] for s in item['signals']])}")
        msg_lines.append("")

    if scan_results['us_stocks']:
        msg_lines.append("🇺🇸 【 US STOCKS TOP 3 】")
        for i, item in enumerate(scan_results['us_stocks'][:3], 1):
            sign_str = "+" if item['change_pct'] >= 0 else ""
            msg_lines.append(f"{i}. {item['display_name']}: ${item['price']:,.2f} ({sign_str}{item['change_pct']}%) | Vol {item['vol_ratio']}x | RSI {item['rsi']}")
            msg_lines.append(f"   ↳ {' • '.join([s.split(' (')[0] for s in item['signals']])}")
        msg_lines.append("")

    if scan_results['thai_stocks']:
        msg_lines.append("🇹🇭 【 THAI SET TOP 3 】")
        for i, item in enumerate(scan_results['thai_stocks'][:3], 1):
            sign_str = "+" if item['change_pct'] >= 0 else ""
            msg_lines.append(f"{i}. {item['display_name']}: ฿{item['price']:,.2f} ({sign_str}{item['change_pct']}%) | Vol {item['vol_ratio']}x | RSI {item['rsi']}")
            msg_lines.append(f"   ↳ {' • '.join([s.split(' (')[0] for s in item['signals']])}")
        msg_lines.append("")

    if total_found == 0:
        msg_lines.append("😴 วันนี้ตลาดค่อนข้างนิ่ง ยังไม่พบสินทรัพย์ที่เข้าเกณฑ์สำคัญ")
    else:
        msg_lines.append("⚠️ ข้อมูลคัดกรองทางเทคนิคอลเบื้องต้น โปรดตั้ง Stop Loss เสมอ")

    return "\n".join(msg_lines)

def send_line_broadcast(scan_results, token):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    flex_msg = create_flex_message(scan_results)
    payload = {"messages": [flex_msg]}
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("✅ ส่งแจ้งเตือนแบบ LINE Flex Message สำเร็จเรียบร้อยแล้ว!")
        return True
    else:
        print(f"⚠️ Flex Message ไม่ผ่าน ({res.status_code}): {res.text} -> สลับไปส่ง Text Message")
        text_payload = {
            "messages": [{"type": "text", "text": format_text_report(scan_results)}]
        }
        res_text = requests.post(url, headers=headers, json=text_payload)
        return res_text.status_code == 200
