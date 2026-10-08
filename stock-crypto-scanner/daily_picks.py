"""One daily LINE digest, up to three eligible assets across all markets."""
import argparse
import json
import math
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from refresh_policy import stock_session

SITE = 'https://benzsutthi.github.io/stock-crypto-scanner'
ACTIONABLE = {'early-cycle','breakout','macd','strong-close','trend','rsi-momentum'}


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def fresh_snapshot(snapshot, now):
    try:
        age = now-datetime.fromisoformat(snapshot['generatedAt'].replace('Z','+00:00'))
        return timedelta(0)<=age<=timedelta(hours=3) and not snapshot.get('keptPreviousSnapshot')
    except (ValueError, TypeError, KeyError):
        return False


def select_daily_picks(stocks, crypto, now=None, limit=3):
    now = now or datetime.now(timezone.utc)
    candidates = {}
    for snapshot in (stocks,crypto):
        if not fresh_snapshot(snapshot,now) or (snapshot is crypto and snapshot.get('updateError')):
            continue
        for asset in snapshot.get('assets',[]):
            market = asset.get('market')
            if not isinstance(asset.get('symbol'),str) or not asset['symbol'] or not finite(asset.get('volumeRatio')):
                continue
            if market not in ('Thai','US','Crypto') or any(asset.get(k) for k in ('historyUnavailable','historyStale','historyUpdateError','updateError','quoteStale')):
                continue
            expected = stock_session(market,now) if market!='Crypto' else (now.date()-timedelta(days=1)).isoformat()
            if asset.get('priceDate')!=expected or not asset.get('liquidityPassed'):
                continue
            if not finite(asset.get('techPrice')) or asset['techPrice']<=0 or not finite(asset.get('rsi')) or not 40<=asset['rsi']<=75:
                continue
            if not finite(asset.get('ema20')) or asset['techPrice']<=asset['ema20']:
                continue
            score = asset.get('score',0)
            if not finite(score) or (score<30 and not asset.get('earlyCycle')):
                continue
            types = {s['type'] for s in asset.get('signals',[])}
            if not types.intersection(ACTIONABLE):
                continue
            ranked = dict(asset, dailyRankScore=score+(15 if asset.get('earlyCycle') else 0), snapshotAt=snapshot['generatedAt'])
            key = (market,asset.get('symbol'))
            if key not in candidates or ranked['dailyRankScore']>candidates[key]['dailyRankScore']:
                candidates[key]=ranked
    ordered = sorted(candidates.values(), key=lambda a:(-a['dailyRankScore'], -(a.get('relativeStrength20') if finite(a.get('relativeStrength20')) else -1e9), -a.get('volumeRatio',0), a['market'],a['symbol']))
    return ordered[:limit]


def make_report(picks, now):
    local=now.astimezone(ZoneInfo('Asia/Bangkok'))
    lines=[f"📌 MarketScope · สินทรัพย์น่าจับตาประจำวัน",f"วันที่ {local:%d/%m/%Y} · คัด {len(picks)}/3 รายการจากทุกตลาด",'']
    markets={'Thai':'หุ้นไทย','US':'หุ้น/ETF สหรัฐ','Crypto':'คริปโท'}
    for rank,asset in enumerate(picks,1):
        currency=asset.get('liquidityCurrency') or asset.get('currency') or 'USD'
        decimals=6 if asset['techPrice']<1 else 2
        reasons=[s['label'] for s in asset.get('signals',[]) if s['type'] in ACTIONABLE|{'relative-strength'}][:4]
        lines.extend([f"{rank}. {asset['symbol']} · {markets[asset['market']]}",
                      f"ราคาวิเคราะห์ {asset['techPrice']:,.{decimals}f} {currency} · ปิด {asset['priceDate']}",
                      f"คะแนนจัดอันดับ {asset.get('dailyRankScore',asset['score'])} · RSI {asset['rsi']:.1f} · Volume {asset.get('volumeRatio',0):.2f}×",
                      'เหตุผล: '+' / '.join(reasons)])
        if finite(asset.get('relativeStrength20')):
            lines.append(f"RS20 {asset['relativeStrength20']:+.2f} pp เทียบ {asset.get('rsBenchmark','ตลาด')}")
        lines.append('')
    if not picks:
        lines.append('วันนี้ยังไม่มีรายการที่ผ่านเกณฑ์พร้อมข้อมูลแท่งปิดล่าสุด จะไม่เติมรายการจากข้อมูลเก่าหรือสมมติ')
    elif len(picks)<3:
        lines.append('ผู้ผ่านเกณฑ์ไม่ครบ 3 รายการ แสดงเฉพาะที่ผ่าน')
    lines.extend(['รายการเพื่อศึกษาต่อจากแท่งปิด ไม่ใช่คำสั่งซื้อหรือราคาเรียลไทม์',SITE])
    return '\n'.join(lines)


def send_once(path, token, report, report_date, symbols):
    state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if state.get('sentDate')==report_date:
        print('Daily digest already accepted today; skipped.')
        return False
    # Persist the original payload before transport, including failures/timeouts.
    if state.get('pendingDate')!=report_date:
        state.update(pendingDate=report_date,pendingReport=report,pendingSymbols=symbols)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    retry_key=str(uuid.uuid5(uuid.NAMESPACE_URL,SITE+'/daily-picks/'+report_date))
    payload={'messages':[{'type':'text','text':state['pendingReport']}]}
    if len(state['pendingReport'])>4900:
        raise ValueError('Daily report exceeds LINE text limit')
    for attempt in range(3):
        try:
            response=requests.post('https://api.line.me/v2/bot/message/broadcast',
                                   headers={'Authorization':'Bearer '+token,'X-Line-Retry-Key':retry_key},json=payload,timeout=30)
            if response.status_code==409 and response.headers.get('x-line-accepted-request-id'):
                break
            if response.status_code>=500 and attempt<2:
                time.sleep(2**(attempt+1));continue
            response.raise_for_status()
            break
        except (requests.Timeout,requests.ConnectionError):
            if attempt==2:raise
            time.sleep(2**(attempt+1))
    state.update(sentDate=report_date,sentSymbols=state['pendingSymbols'])
    for key in ('pendingDate','pendingReport','pendingSymbols'):state.pop(key,None)
    path.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    print(f"Daily digest accepted: {report_date}, {len(state['sentSymbols'])} selections.")
    return True


def fetch_snapshot(name):
    response=requests.get(f'{SITE}/data/{name}.json',params={'daily':int(time.time())},timeout=30)
    response.raise_for_status()
    return response.json()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--state',type=Path,default=Path('.daily-picks-state/state.json'))
    parser.add_argument('--stocks',type=Path,help='Freshly prepared stock snapshot')
    parser.add_argument('--crypto',type=Path,help='Freshly prepared crypto snapshot')
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    date=now.astimezone(ZoneInfo('Asia/Bangkok')).date().isoformat()
    dry=args.dry_run or os.getenv('DRY_RUN','false').lower()=='true'
    if not dry and args.state.exists() and json.loads(args.state.read_text(encoding='utf-8')).get('sentDate')==date:
        print('Daily report already sent; no new request.');return
    snapshots=[]
    for name,path in (('stocks',args.stocks),('crypto',args.crypto)):
        try:snapshots.append(json.loads(path.read_text(encoding='utf-8')) if path else fetch_snapshot(name))
        except (requests.RequestException, OSError, ValueError) as error:
            print(f'{name} snapshot unavailable: {error}');snapshots.append({})
    picks=select_daily_picks(*snapshots,now=now)
    report=make_report(picks,now)
    if dry:
        print(report);print('DRY RUN: no LINE message sent.');return
    token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN','')
    if not token:raise RuntimeError('LINE_CHANNEL_ACCESS_TOKEN secret is required')
    if now.astimezone(ZoneInfo('Asia/Bangkok')).hour<9:
        print('Before 09:00 Bangkok; skipped live send.');return
    send_once(args.state,token,report,date,[f"{a['market']}:{a['symbol']}" for a in picks])


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    main()
