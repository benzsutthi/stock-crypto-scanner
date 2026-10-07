"""Aligned benchmark returns and market-specific liquidity filters."""
import math

LIQUIDITY_LIMITS = {'Thai': 20_000_000, 'US': 10_000_000, 'Crypto': 5_000_000}


def return_history(frame, limit=100):
    if frame.empty or 'Close' not in frame:
        return []
    return [dict(date=stamp.date().isoformat(), close=float(value))
            for stamp, value in frame.Close.iloc[-limit:].items()
            if hasattr(stamp, 'date') and math.isfinite(float(value)) and value > 0]


def relative_returns(asset_history, benchmark_history, periods=(20,60)):
    asset = {p['date']:p['close'] for p in asset_history if p.get('close',0)>0 and math.isfinite(p['close'])}
    benchmark = {p['date']:p['close'] for p in benchmark_history if p.get('close',0)>0 and math.isfinite(p['close'])}
    result = {str(period):None for period in periods}
    if not asset:
        return result
    end = max(asset)
    if end not in benchmark:
        return result
    dates = sorted(day for day in benchmark if day <= end)
    for period in periods:
        window = dates[-(period+1):]
        # No forward-fill, missing sessions or future benchmark bars.
        if len(window)!=period+1 or any(day not in asset for day in window):
            continue
        start = window[0]
        asset_return = (asset[end]/asset[start]-1)*100
        benchmark_return = (benchmark[end]/benchmark[start]-1)*100
        result[str(period)] = dict(assetReturn=round(asset_return,2), benchmarkReturn=round(benchmark_return,2),
                                  difference=round(asset_return-benchmark_return,2), startDate=start, endDate=end)
    return result


def attach_quality(asset, benchmark=None):
    asset['baseScore'] = asset.get('baseScore', asset.get('score',0))
    asset['signals'] = [s for s in asset.get('signals',[]) if s['type'] not in ('relative-strength','liquidity')]
    benchmark = benchmark or {}
    windows = relative_returns(asset.get('returnHistory',[]), benchmark.get('history',[]))
    asset.update(rsWindows=windows, rsBenchmark=benchmark.get('name'), rsSource=benchmark.get('source'),
                 rsAsOf=asset.get('priceDate'), relativeStrength20=windows['20']['difference'] if windows['20'] else None,
                 relativeStrength60=windows['60']['difference'] if windows['60'] else None)
    stronger = all(asset.get(field) is not None and asset[field]>0 for field in ('relativeStrength20','relativeStrength60'))
    asset['relativeStrengthLeader'] = stronger
    if stronger:
        text=f"แข็งกว่า {asset['rsBenchmark']} · 20/60D"
        asset['signals'].append(dict(type='relative-strength',label=text,description='ผลตอบแทนส่วนต่าง 20 และ 60 แท่งปิดสูงกว่าตลาด บนวันเดียวกัน หน่วยจุดเปอร์เซ็นต์'))
    currency = asset.get('liquidityCurrency')
    threshold = LIQUIDITY_LIMITS.get(asset.get('market'))
    turnover = asset.get('avgTurnover20')
    passed = currency in ('THB','USD','USDT') and threshold is not None and turnover is not None and math.isfinite(turnover) and turnover>=threshold
    asset.update(liquidityThreshold=threshold, liquidityPassed=bool(passed))
    if passed:
        label=f"Liquidity ≥{threshold/1_000_000:g}M {currency}"
        asset['signals'].append(dict(type='liquidity',label=label,description=f"มูลค่าซื้อขายเฉลี่ย 20 แท่งปิด {turnover:,.0f} {currency} · {asset.get('liquidityBasis','')}; เป็นตัวกรองสภาพคล่อง ไม่ใช่สัญญาณทิศทาง"))
    asset['score'] = asset['baseScore']+(10 if stronger else 0)
    return asset
