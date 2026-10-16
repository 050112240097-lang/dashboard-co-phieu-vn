# fallback_provider.py - Multi-source data provider (vnstock -> Yahoo)
import os
import time
from datetime import datetime

import pandas as pd

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False
    print("  [WARN] Chua cai yfinance. Chay: pip install yfinance")


# Mapping san VN -> suffix Yahoo
YAHOO_SUFFIX = {
    'HOSE': '.VN',   # Ho Chi Minh (HSX) - Yahoo dung .VN
    'HSX': '.VN',
    'HNX': '.VN',    # Yahoo gop chung .VN
    'UPCOM': '.VN',
    '': '.VN',
}


def _fetch_vnstock(symbol, days=500):
    """Thu lay tu vnstock."""
    try:
        from vnstock import Quote
        quote = Quote(symbol=symbol, source='kbs')
        df = quote.history(length=days, interval='1D')
        if df is None or df.empty:
            return None
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['close'])
        if len(df) < 30:
            return None
        return df
    except Exception as e:
        print(f"    [vnstock] Loi {symbol}: {str(e)[:80]}")
        return None


def _fetch_yahoo(symbol, exchange='', days=500):
    """Thu lay tu Yahoo Finance."""
    if not YF_OK:
        return None
    try:
        # Yahoo suffix theo san
        suffix = YAHOO_SUFFIX.get(exchange.upper(), '.HM')
        ticker = f'{symbol.upper()}{suffix}'

        # Tinh toan khoang thoi gian (dung period thay vi days de chinh xac)
        if days <= 250:
            period = '1y'
        elif days <= 500:
            period = '2y'
        elif days <= 750:
            period = '3y'
        else:
            period = '5y'

        yt = yf.Ticker(ticker)
        hist = yt.history(period=period, auto_adjust=False)
        if hist is None or hist.empty or len(hist) < 30:
            # Thu suffix khac
            for sfx in ['.HN', '.UP']:
                if sfx == suffix:
                    continue
                ticker2 = f'{symbol.upper()}{sfx}'
                yt2 = yf.Ticker(ticker2)
                hist2 = yt2.history(period=period, auto_adjust=False)
                if hist2 is not None and len(hist2) >= 30:
                    hist = hist2
                    print(f"    [Yahoo] Dung suffix {sfx} cho {symbol}")
                    break

        if hist is None or hist.empty:
            return None

        hist = hist.reset_index()
        hist = hist.rename(columns={
            'Date': 'time', 'Open': 'open', 'High': 'high',
            'Low': 'low', 'Close': 'close', 'Volume': 'volume',
        })
        hist['time'] = pd.to_datetime(hist['time']).dt.tz_localize(None)
        hist = hist[['time', 'open', 'high', 'low', 'close', 'volume']].dropna(subset=['close'])
        if len(hist) < 30:
            return None
        return hist
    except Exception as e:
        print(f"    [Yahoo] Loi {symbol}: {str(e)[:80]}")
        return None


def get_history(symbol, days=500, exchange=''):
    """
    Lay lich su gia tu vnstock, fallback sang Yahoo neu fail.
    Tra ve DataFrame hoac None.
    """
    # 1) Thu vnstock
    df = _fetch_vnstock(symbol, days)
    if df is not None:
        df.attrs['source'] = 'vnstock'
        return df

    # 2) Fallback Yahoo
    print(f"    [Fallback] Chuyen sang Yahoo cho {symbol}...")
    df = _fetch_yahoo(symbol, exchange, days)
    if df is not None:
        df.attrs['source'] = 'yahoo'
        return df

    return None


def get_close_series(symbol, days=500, exchange=''):
    """Chi lay series close."""
    df = get_history(symbol, days, exchange)
    if df is None:
        return None
    return df.set_index('time')['close']


def get_info(symbol, exchange=''):
    """Lay thong tin cong ty tu Yahoo."""
    if not YF_OK:
        return None
    try:
        suffix = YAHOO_SUFFIX.get(exchange.upper(), '.HM')
        ticker = f'{symbol.upper()}{suffix}'
        yt = yf.Ticker(ticker)
        info = yt.info
        return {
            'name': info.get('longName') or info.get('shortName'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'market_cap': info.get('marketCap'),
            'pe': info.get('trailingPE'),
            'pb': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta'),
            'roe': info.get('returnOnEquity'),
            'roa': info.get('returnOnAssets'),
            'profit_margin': info.get('profitMargins'),
            'debt_to_equity': info.get('debtToEquity'),
        }
    except Exception as e:
        print(f"    [Yahoo Info] Loi {symbol}: {str(e)[:80]}")
        return None


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    print("Test fallback provider cho FPT, HPG, VNM...\n")
    for sym in ['FPT', 'HPG', 'VNM']:
        print(f"--- {sym} ---")
        df = get_history(sym, days=500, exchange='HOSE')
        if df is None:
            print(f"  [LOI] Khong lay duoc du lieu")
            continue
        print(f"  Source: {df.attrs.get('source', '?')}")
        print(f"  So phien: {len(df)}")
        print(f"  Close cuoi: {df['close'].iloc[-1]:,.0f}")
        print()
        time.sleep(1)

    # Test info tu Yahoo
    print("\n--- Test info FPT ---")
    info = get_info('FPT', 'HOSE')
    if info:
        for k, v in info.items():
            print(f"  {k}: {v}")