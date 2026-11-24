"""Daily 08:00 Bangkok LINE Flex Message report for the Google Sheets portfolio."""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

SITE = 'https://benzsutthi.github.io/stock-crypto-scanner'
DEFAULT_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4/edit?gid=146811986#gid=146811986'
BANGKOK = ZoneInfo('Asia/Bangkok')


def parse_sheet_csv_url(url: str) -> str:
    raw = (url or '').strip()
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', raw)
    if not m:
        raise ValueError('Invalid Google Sheets URL')
    sheet_id = m.group(1)
    gid_match = re.search(r'[?#&]gid=(\d+)', raw)
    default_gid = '146811986' if sheet_id == '1XJjMCBopfrYrxYYQLa7AxXb6-vAFL3VnlcC7T9VxrD4' else '0'
    gid = gid_match.group(1) if gid_match else default_gid
    return f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}'


def _num(val) -> float | None:
    if val is None:
        return None
    cleaned = re.sub(r'[,$\s฿%]', '', str(val)).strip()
    if not cleaned:
        return None
    try:
        n = float(cleaned)
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def parse_portfolio_csv(csv_text: str) -> dict:
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise ValueError('Portfolio CSV is empty')

    headers = [h.strip().lower() for h in rows[0]]
    def find_col(*needles):
        for i, h in enumerate(headers):
            if any(n in h for n in needles):
                return i
        return -1

    idx_ticker = find_col('ticker', 'symbol')
    idx_class = find_col('asset class', 'market')
    idx_qty = find_col('shares', 'units', 'qty', 'quantity')
    idx_cost = find_col('avg invest', 'cost')
    idx_price = find_col('current price', 'price')
    idx_val_thb = find_col('current value thb')
    idx_cost_thb = find_col('total invest costthb', 'costthb')
    idx_pnl_pct = find_col('profit/loss (%)')

    if idx_ticker == -1 or idx_qty == -1 or idx_cost == -1:
        raise ValueError('Required columns (Ticker, Shares/Units, avg invest) not found')

    items = []
    inferred_rates = []
    for cols in rows[1:]:
        if idx_ticker >= len(cols):
            continue
        raw_ticker = cols[idx_ticker].strip()
        if not raw_ticker:
            continue
        qty = _num(cols[idx_qty]) if idx_qty < len(cols) else None
        cost = _num(cols[idx_cost]) if idx_cost < len(cols) else None
        if qty is None or qty <= 0 or cost is None or cost <= 0:
            continue

        asset_class = cols[idx_class].strip() if 0 <= idx_class < len(cols) else ''
        price = _num(cols[idx_price]) if 0 <= idx_price < len(cols) else None
        val_thb = _num(cols[idx_val_thb]) if 0 <= idx_val_thb < len(cols) else None
        cost_thb = _num(cols[idx_cost_thb]) if 0 <= idx_cost_thb < len(cols) else None
        pnl_pct = _num(cols[idx_pnl_pct]) if 0 <= idx_pnl_pct < len(cols) else None

        symbol = raw_ticker.upper()
        currency = 'THB'
        if re.search(r'us', asset_class, re.I) or re.search(r'\s+US$', raw_ticker, re.I):
            currency = 'USD'
            symbol = re.sub(r'\s+US$', '', symbol).strip()
        elif re.search(r'crypto', asset_class, re.I):
            if not (symbol.endswith('THB') and len(symbol) > 3):
                if val_thb and price and price > 0 and (val_thb / (qty * price)) > 15:
                    currency = 'USD'
                elif cost_thb and (cost_thb / (qty * cost)) > 15:
                    currency = 'USD'

        if currency == 'USD' and cost_thb and cost_thb > 0:
            rate = cost_thb / (qty * cost)
            if 20 < rate < 60:
                inferred_rates.append(rate)

        items.append({
            'symbol': symbol,
            'asset_class': asset_class or 'Other',
            'currency': currency,
            'qty': qty,
            'cost': cost,
            'price': price,
            'val_thb': val_thb,
            'cost_thb': cost_thb,
            'pnl_pct': pnl_pct,
        })

    usd_thb = sum(inferred_rates) / len(inferred_rates) if inferred_rates else 34.5
    enriched = []
    for it in items:
        cost_thb = it['cost_thb']
        if cost_thb is None or cost_thb <= 0:
            cost_thb = it['qty'] * it['cost'] * (usd_thb if it['currency'] == 'USD' else 1.0)
        val_thb = it['val_thb']
        if val_thb is None or val_thb <= 0:
            unit_val = it['price'] if (it['price'] and it['price'] > 0) else it['cost']
            val_thb = it['qty'] * unit_val * (usd_thb if it['currency'] == 'USD' else 1.0)
        pnl_thb = val_thb - cost_thb
        pnl_pct = it['pnl_pct'] if it['pnl_pct'] is not None else (pnl_thb / cost_thb * 100 if cost_thb > 0 else 0.0)
        enriched.append({
            **it,
            'cost_thb': cost_thb,
            'val_thb': val_thb,
            'pnl_thb': pnl_thb,
            'pnl_pct': pnl_pct,
        })

    total_cost = sum(x['cost_thb'] for x in enriched)
    total_value = sum(x['val_thb'] for x in enriched)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    for x in enriched:
        x['alloc_pct'] = (x['val_thb'] / total_value * 100) if total_value > 0 else 0.0
    enriched.sort(key=lambda x: x['alloc_pct'], reverse=True)

    return {
        'items': enriched,
        'total_cost_thb': total_cost,
        'total_value_thb': total_value,
        'total_pnl_thb': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'usd_thb': round(usd_thb, 2),
    }


def build_portfolio_flex(summary: dict, now: datetime | None = None) -> dict:
    local = (now or datetime.now(timezone.utc)).astimezone(BANGKOK)
    date_str = local.strftime('%d/%m/%Y · %H:%M น.')
    total_val = summary['total_value_thb']
    total_cost = summary['total_cost_thb']
    total_pnl = summary['total_pnl_thb']
    total_pct = summary['total_pnl_pct']
    pnl_color = '#00E676' if total_pnl >= 0 else '#FF5252'
    pnl_sign = '+' if total_pnl >= 0 else ''

    items = summary['items']
    top_items = items[:10]
    rest_count = max(0, len(items) - len(top_items))
    rest_pct = sum(x['alloc_pct'] for x in items[10:])

    rows = []
    for item in top_items:
        c = '#00E676' if item['pnl_pct'] >= 0 else '#FF5252'
        sign = '+' if item['pnl_pct'] >= 0 else ''
        bar_w = f"{min(100, max(3, round(item['alloc_pct'])))}%"
        rows.append({
            'type': 'box',
            'layout': 'vertical',
            'margin': 'sm',
            'contents': [
                {
                    'type': 'box',
                    'layout': 'horizontal',
                    'contents': [
                        {'type': 'text', 'text': item['symbol'], 'weight': 'bold', 'size': 'sm', 'color': '#F3F4F6', 'flex': 3},
                        {'type': 'text', 'text': f"{item['alloc_pct']:.1f}%", 'weight': 'bold', 'size': 'sm', 'color': '#A8F05F', 'align': 'end', 'flex': 2},
                        {'type': 'text', 'text': f"฿{item['val_thb']:,.0f}", 'size': 'xs', 'color': '#D1D5DB', 'align': 'end', 'flex': 3},
                        {'type': 'text', 'text': f"{sign}{item['pnl_pct']:.1f}%", 'size': 'xs', 'color': c, 'align': 'end', 'flex': 2},
                    ],
                },
                {
                    'type': 'box',
                    'layout': 'vertical',
                    'height': '4px',
                    'backgroundColor': '#111827',
                    'cornerRadius': '2px',
                    'margin': 'xs',
                    'contents': [
                        {
                            'type': 'box',
                            'layout': 'vertical',
                            'width': bar_w,
                            'height': '4px',
                            'backgroundColor': '#A8F05F',
                            'cornerRadius': '2px',
                            'contents': [],
                        }
                    ],
                },
            ],
        })

    if rest_count > 0:
        rows.append({
            'type': 'text',
            'text': f"และอีก {rest_count} สินทรัพย์ (รวม {rest_pct:.1f}%)",
            'size': 'xs',
            'color': '#9CA3AF',
            'margin': 'sm',
        })

    bubble = {
        'type': 'bubble',
        'size': 'mega',
        'styles': {
            'header': {'backgroundColor': '#0F172A'},
            'body': {'backgroundColor': '#111827'},
            'footer': {'backgroundColor': '#0F172A'},
        },
        'header': {
            'type': 'box',
            'layout': 'vertical',
            'paddingAll': '16px',
            'contents': [
                {'type': 'text', 'text': 'MARKETSCOPE PORTFOLIO', 'size': 'xxs', 'weight': 'bold', 'color': '#A8F05F'},
                {'type': 'text', 'text': '📊 สรุปพอร์ตการลงทุนประจำวัน', 'size': 'md', 'weight': 'bold', 'color': '#FFFFFF', 'margin': 'xs'},
                {'type': 'text', 'text': f"อัปเดต {date_str} · {len(items)} สินทรัพย์", 'size': 'xs', 'color': '#9CA3AF', 'margin': 'xs'},
            ],
        },
        'body': {
            'type': 'box',
            'layout': 'vertical',
            'paddingAll': '16px',
            'contents': [
                {
                    'type': 'box',
                    'layout': 'vertical',
                    'backgroundColor': '#1F2937',
                    'cornerRadius': '10px',
                    'paddingAll': '14px',
                    'contents': [
                        {'type': 'text', 'text': 'มูลค่าพอร์ตปัจจุบัน', 'size': 'xs', 'color': '#9CA3AF'},
                        {'type': 'text', 'text': f"฿{total_val:,.2f}", 'size': 'xl', 'weight': 'bold', 'color': '#FFFFFF', 'margin': 'xs'},
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'margin': 'sm',
                            'contents': [
                                {'type': 'text', 'text': f"ทุน ฿{total_cost:,.0f}", 'size': 'xs', 'color': '#9CA3AF', 'flex': 1},
                                {'type': 'text', 'text': f"{pnl_sign}฿{total_pnl:,.0f} ({pnl_sign}{total_pct:.2f}%)", 'size': 'xs', 'weight': 'bold', 'color': pnl_color, 'align': 'end', 'flex': 1},
                            ],
                        },
                    ],
                },
                {'type': 'text', 'text': 'สัดส่วนสินทรัพย์ (Top 10)', 'size': 'xs', 'weight': 'bold', 'color': '#9CA3AF', 'margin': 'lg'},
                *rows,
            ],
        },
        'footer': {
            'type': 'box',
            'layout': 'vertical',
            'paddingAll': '12px',
            'contents': [
                {
                    'type': 'button',
                    'style': 'primary',
                    'color': '#A8F05F',
                    'action': {'type': 'uri', 'label': 'เปิดดูพอร์ตเต็มๆ บนเว็บ', 'uri': f'{SITE}/portfolio.html'},
                }
            ],
        },
    }

    return {
        'type': 'flex',
        'altText': f"📊 สรุปพอร์ต {local:%d/%m}: ฿{total_val:,.0f} ({pnl_sign}{total_pct:.2f}%)",
        'contents': bubble,
    }


def send_once(state_path: Path, token: str, flex_msg: dict, report_date: str):
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    if state.get('sentDate') == report_date:
        print('Daily portfolio report already sent today; skipped.')
        return False

    retry_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f'{SITE}/daily-portfolio/{report_date}'))
    payload = {'messages': [flex_msg]}
    headers = {'Authorization': f'Bearer {token}', 'X-Line-Retry-Key': retry_key}
    for attempt in range(3):
        try:
            resp = requests.post('https://api.line.me/v2/bot/message/broadcast', headers=headers, json=payload, timeout=30)
            if resp.status_code == 409 and resp.headers.get('x-line-accepted-request-id'):
                break
            if resp.status_code >= 500 and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            resp.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({'sentDate': report_date}, ensure_ascii=False), encoding='utf-8')
    print(f'Daily portfolio Flex report accepted: {report_date}')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--state', type=Path, default=Path('.daily-portfolio-state/state.json'))
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    report_date = now.astimezone(BANGKOK).date().isoformat()
    dry = args.dry_run or os.getenv('DRY_RUN', 'false').lower() == 'true'

    sheet_url = os.getenv('PORTFOLIO_SHEET_URL') or DEFAULT_SHEET_URL
    csv_url = parse_sheet_csv_url(sheet_url)
    resp = requests.get(csv_url, timeout=30)
    resp.raise_for_status()
    summary = parse_portfolio_csv(resp.text)
    flex_msg = build_portfolio_flex(summary, now=now)

    if dry:
        print(json.dumps(flex_msg, ensure_ascii=False, indent=2))
        print('DRY RUN: no LINE message sent.')
        return

    token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
    if not token:
        raise RuntimeError('LINE_CHANNEL_ACCESS_TOKEN secret is required')
    send_once(args.state, token, flex_msg, report_date)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
