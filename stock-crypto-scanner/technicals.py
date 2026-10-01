"""Daily confirmed-bar indicators shared by the snapshot and watchlist alerts."""
def ema(values, period):
    out = [None] * len(values)
    if len(values) < period:
        return out
    value = sum(values[:period]) / period
    out[period - 1] = value
    for i in range(period, len(values)):
        value += (values[i] - value) * 2 / (period + 1)
        out[i] = value
    return out


def analyze(frame):
    closes = frame.Close.tolist()
    gain = sum(max(closes[i] - closes[i-1], 0) for i in range(1, 15)) / 14
    loss = sum(max(closes[i-1] - closes[i], 0) for i in range(1, 15)) / 14
    for i in range(15, len(closes)):
        gain = (gain * 13 + max(closes[i] - closes[i-1], 0)) / 14
        loss = (loss * 13 + max(closes[i-1] - closes[i], 0)) / 14
    rsi = 50 if gain == loss == 0 else 100 if loss == 0 else 100 - 100 / (1 + gain / loss)
    e20, e50 = ema(closes, 20)[-1], ema(closes, 50)[-1]
    fast, slow = ema(closes, 12), ema(closes, 26)
    macd = [a-b for a, b in zip(fast, slow) if a is not None and b is not None]
    signal = ema(macd, 9)
    high = float(frame.High.iloc[-21:-1].max())
    avg = float(frame.Volume.iloc[-21:-1].mean())
    ratio = float(frame.Volume.iloc[-1]) / avg if avg > 0 else 0
    labels = []
    score = 0
    def add(kind, label, points):
        nonlocal score
        labels.append(dict(type=kind, label=label, description=label))
        score += points
    if closes[-1] > high:
        add('breakout', '20D Breakout', 35)
    if rsi >= 70:
        add('rsi-high', 'RSI สูง · ร้อนแรง', 0)
    elif rsi >= 55:
        add('rsi-momentum', 'RSI โมเมนตัม', 15)
    elif rsi < 30:
        add('rsi-low', 'RSI Oversold', 10)
    if ratio >= 1.5:
        add('volume', f'Volume {ratio:.1f}×', 20)
    if len(signal) >= 2 and signal[-2] is not None and macd[-2] <= signal[-2] and macd[-1] > signal[-1]:
        add('macd', 'MACD Golden Cross', 20)
    if e50 and closes[-1] > e20 > e50:
        add('trend', 'ขาขึ้น EMA20/50', 10)
    return dict(price=float(closes[-1]), change=round((closes[-1]/closes[-2]-1)*100, 2),
                rsi=round(rsi, 1), volumeRatio=round(ratio, 2), ema20=e20, ema50=e50,
                high20=high, breakoutDistance=round((closes[-1]/high-1)*100, 2),
                signals=labels, score=score)
