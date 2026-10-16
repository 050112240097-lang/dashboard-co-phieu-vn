# technical_analyzer.py - Chi bao ky thuat MA, RSI, MACD + Ke hoach giao dich
import pandas as pd
import numpy as np
import time


def compute_ma_rsi(symbol):
    """
    Tinh MA20, MA50, RSI14, MACD + high/low 20 phien + ke hoach giao dich.
    """
    result = {
        'symbol': symbol,
        'ma20': None,
        'ma50': None,
        'ema20': None,
        'rsi14': None,
        'macd': None,
        'macd_signal': None,
        'macd_hist': None,
        'signal': None,
        'close': None,
        'high_20': None,
        'low_20': None,
        'trade_plan': None,
    }

    try:
        # Uu tien fallback_provider (vnstock -> Yahoo)
        try:
            from fallback_provider import get_history
            df = get_history(symbol, days=100)
        except ImportError:
            from vnstock import Quote
            quote = Quote(symbol=symbol, source='kbs')
            df = quote.history(length=100, interval='1D')

        if df is None or df.empty or len(df) < 20:
            return result

        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df = df.dropna(subset=['close'])

        # MA20, MA50
        df['MA20'] = df['close'].rolling(20).mean()
        df['MA50'] = df['close'].rolling(50).mean()

        # EMA20
        df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()

        # RSI14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI14'] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']

        last = df.iloc[-1]
        close = float(last['close'])

        result['close'] = round(close, 2)
        result['ma20'] = round(float(last['MA20']), 2) if pd.notna(last['MA20']) else None
        result['ma50'] = round(float(last['MA50']), 2) if pd.notna(last['MA50']) else None
        result['ema20'] = round(float(last['EMA20']), 2) if pd.notna(last['EMA20']) else None
        result['rsi14'] = round(float(last['RSI14']), 2) if pd.notna(last['RSI14']) else None
        result['macd'] = round(float(last['MACD']), 3) if pd.notna(last['MACD']) else None
        result['macd_signal'] = round(float(last['MACD_signal']), 3) if pd.notna(last['MACD_signal']) else None
        result['macd_hist'] = round(float(last['MACD_hist']), 3) if pd.notna(last['MACD_hist']) else None

        # High/Low 20 phien gan nhat
        df_20 = df.tail(20)
        result['high_20'] = round(float(df_20['high'].max()), 2) if not df_20['high'].isna().all() else None
        result['low_20'] = round(float(df_20['low'].min()), 2) if not df_20['low'].isna().all() else None

        # Tin hieu
        if result['ma20'] and result['ma50']:
            if close > result['ma20'] > result['ma50']:
                result['signal'] = 'Tăng'
            elif close < result['ma20'] < result['ma50']:
                result['signal'] = 'Giảm'
            else:
                result['signal'] = 'Trung tính'

        # Ke hoach giao dich
        result['trade_plan'] = compute_trade_plan(
            close=close,
            ma20=result['ma20'],
            ma50=result['ma50'],
            rsi14=result['rsi14'],
            high_20=result['high_20'],
            low_20=result['low_20'],
            signal=result['signal'],
        )

        return result

    except Exception as e:
        print(f"    [LOI] {symbol}: {str(e)[:80]}")
        return result


def compute_trade_plan(close, ma20, ma50, rsi14, high_20, low_20, signal):
    """
    Tinh ke hoach giao dich tham khao:
    - Vung vao lenh (entry)
    - Muc tieu (target)
    - Cat lo (stop)
    - Ty le R:R
    - Do tin cay + khuyen nghi
    """
    if not close or not ma20:
        return None

    plan = {
        'entry_low': None,
        'entry_high': None,
        'target': None,
        'stop': None,
        'rr_ratio': None,
        'confidence': 'Thấp',
        'advice': 'Chưa đủ dữ liệu',
        'upside_pct': None,
        'downside_pct': None,
        'reasons': [],
    }

    # Vung vao lenh = MA20 +- 1%
    entry_low = round(ma20 * 0.99, 0)
    entry_high = round(ma20 * 1.01, 0)
    plan['entry_low'] = entry_low
    plan['entry_high'] = entry_high

    # Muc tieu: uu tien dinh 20 phien, neu qua xa (>25%) thi dung MA20 + 15%
    if high_20 and high_20 > close:
        target = high_20
        upside = (target - close) / close * 100
        if upside > 25:
            target = round(ma20 * 1.15, 0)
            plan['reasons'].append('Đỉnh 20 phiên quá xa, dùng mục tiêu thận trọng')
    else:
        target = round(close * 1.15, 0)
        plan['reasons'].append('Không có đỉnh 20 phiên rõ ràng, dùng +15%')

    plan['target'] = target
    plan['upside_pct'] = round((target - close) / close * 100, 1)

    # Cat lo: MA50 * 0.98 hoac low_20 neu cao hon
    stop = None
    if ma50 and ma50 > 0:
        stop = round(ma50 * 0.98, 0)
    if low_20 and low_20 > 0:
        stop_candidate = round(low_20 * 0.98, 0)
        if stop is None or stop_candidate > stop:
            stop = stop_candidate

    if stop is None:
        stop = round(close * 0.92, 0)
        plan['reasons'].append('Không có MA50, dùng stop -8%')

    plan['stop'] = stop
    plan['downside_pct'] = round((stop - close) / close * 100, 1)

    # R:R
    entry_mid = (entry_low + entry_high) / 2
    reward = target - entry_mid
    risk = entry_mid - stop
    if risk > 0:
        plan['rr_ratio'] = round(reward / risk, 2)

    # Do tin cay
    confidence_pts = 0
    if signal == 'Tăng':
        confidence_pts += 2
    elif signal == 'Trung tính':
        confidence_pts += 1
    if rsi14:
        if 40 <= rsi14 <= 65:
            confidence_pts += 2
        elif 30 <= rsi14 < 40 or 65 < rsi14 <= 75:
            confidence_pts += 1
        elif rsi14 > 75:
            confidence_pts -= 1
        elif rsi14 < 30:
            confidence_pts += 1
    if plan['rr_ratio']:
        if plan['rr_ratio'] >= 2:
            confidence_pts += 2
        elif plan['rr_ratio'] >= 1.5:
            confidence_pts += 1
        elif plan['rr_ratio'] < 1:
            confidence_pts -= 1

    if confidence_pts >= 5:
        plan['confidence'] = 'Cao'
    elif confidence_pts >= 3:
        plan['confidence'] = 'Trung bình'
    else:
        plan['confidence'] = 'Thấp'

    # Khuyen nghi
    if rsi14 and rsi14 > 75:
        plan['advice'] = 'KHÔNG MUA — RSI quá mua, chờ điều chỉnh'
    elif plan['rr_ratio'] and plan['rr_ratio'] >= 2 and signal == 'Tăng':
        plan['advice'] = 'CÂN NHẮC MUA — R:R tốt, xu hướng tăng'
    elif plan['rr_ratio'] and plan['rr_ratio'] >= 1.5:
        plan['advice'] = 'THEO DÕI — Chờ giá về vùng vào lệnh'
    elif signal == 'Giảm':
        plan['advice'] = 'HẠN CHẾ GIẢI NGÂN — Xu hướng giảm'
    elif rsi14 and rsi14 < 30:
        plan['advice'] = 'CÂN NHẮC BẮT ĐÁY — RSI quá bán, rủi ro cao'
    else:
        plan['advice'] = 'TRUNG LẬP — Chờ tín hiệu rõ hơn'

    return plan


def fetch_all_technical(symbols):
    """Lay MA, RSI cho danh sach ma."""
    results = {}
    print(f"  [TA] Dang tinh MA, RSI cho {len(symbols)} ma...")

    for i, sym in enumerate(symbols):
        if i > 0:
            time.sleep(0.5)
        if i % 10 == 0:
            print(f"    Tien do: {i+1}/{len(symbols)}")
        results[sym] = compute_ma_rsi(sym)

    print(f"  [TA] Xong: {len(results)} ma")
    return results


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    for sym in ['FPT', 'HPG', 'VNM', 'VCB', 'PNJ']:
        r = compute_ma_rsi(sym)
        print(f"\n=== {sym} ===")
        print(f"  Close: {r.get('close')}  |  MA20: {r.get('ma20')}  |  MA50: {r.get('ma50')}")
        print(f"  RSI14: {r.get('rsi14')}  |  Signal: {r.get('signal')}")
        tp = r.get('trade_plan')
        if tp:
            print(f"  Ke hoach: entry {tp['entry_low']:.0f}-{tp['entry_high']:.0f} | "
                  f"target {tp['target']:.0f} ({tp['upside_pct']:+.1f}%) | "
                  f"stop {tp['stop']:.0f} ({tp['downside_pct']:+.1f}%)")
            print(f"  R:R: {tp['rr_ratio']} | Confidence: {tp['confidence']}")
            print(f"  Advice: {tp['advice']}")
        time.sleep(1)