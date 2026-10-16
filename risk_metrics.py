# risk_metrics.py - Chi so rui ro: Beta, sigma, Sharpe, CAGR, Max Drawdown
import os
try:
    from hf_compat import get_path as _hf_path
except ImportError:
    _hf_path = lambda x: x
import json
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

CACHE_FILE = _hf_path('risk_metrics_cache.json')
CACHE_HOURS = 6

# Lai suat phi rui ro mac dinh (VN 10Y bond ~ 3.3%/nam)
DEFAULT_RF = 0.033

# Ma VNINDEX de tinh beta
BENCHMARK_SYMBOLS = ['VNINDEX', 'VNI', 'VN30']


def _set_api_key():
    try:
        from config import VNSTOCK_API_KEY
        # Khong dung env de tranh conflict voi vnstock 5.x
    except Exception:
        pass


def _fetch_history(symbol, days=500):
    """Lay lich su gia 1 ma - dung fallback_provider."""
    try:
        try:
            from fallback_provider import get_history
            df = get_history(symbol, days=days)
        except ImportError:
            from vnstock import Quote
            quote = Quote(symbol=symbol, source='kbs')
            df = quote.history(length=days, interval='1D')

        if df is None or df.empty:
            return None
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        return df[['time', 'close']]
    except Exception as e:
        print(f"  [Risk] Loi fetch {symbol}: {str(e)[:80]}")
        return None


def _fetch_benchmark(days=500):
    """Lay VNINDEX lam benchmark."""
    for sym in BENCHMARK_SYMBOLS:
        df = _fetch_history(sym, days=days)
        if df is not None and len(df) > 100:
            print(f"  [Risk] Dung benchmark: {sym}")
            return df
    print(f"  [Risk] Khong lay duoc benchmark -> beta = 1.0 mac dinh")
    return None


def _max_drawdown(prices):
    """Tinh Max Drawdown tu chuoi gia."""
    if prices is None or len(prices) < 2:
        return None
    prices = np.array(prices, dtype=float)
    cum_max = np.maximum.accumulate(prices)
    drawdown = (prices - cum_max) / cum_max
    return float(drawdown.min())


def compute_risk(symbol, benchmark_df=None, days=500, rf=DEFAULT_RF):
    """
    Tinh cac chi so rui ro cho 1 ma.
    Tra ve dict hoac {'error': ...}
    """
    df = _fetch_history(symbol, days=days)
    if df is None or len(df) < 30:
        return {'error': f'Khong du du lieu cho {symbol}'}

    # Tinh toan
    closes = df['close'].values
    returns = np.diff(closes) / closes[:-1]

    # 1) CAGR 1 nam, 2 nam
    cagr_1y = cagr_2y = None
    n = len(closes)
    if n >= 250:
        try:
            cagr_1y = (closes[-1] / closes[-250]) - 1
        except Exception:
            pass
    if n >= 500:
        try:
            cagr_2y = ((closes[-1] / closes[-500]) ** 0.5) - 1
        except Exception:
            pass

    # 2) Do lech chuan nam (~252 phien)
    sigma_annual = float(np.std(returns) * math.sqrt(252)) if len(returns) > 20 else None

    # 3) Max drawdown
    mdd = _max_drawdown(closes)

    # 4) Beta so voi benchmark
    beta = None
    if benchmark_df is not None and len(benchmark_df) >= 30:
        bench = benchmark_df.set_index('time')['close']
        stock = df.set_index('time')['close']
        joined = pd.concat([stock, bench], axis=1, join='inner').dropna()
        joined.columns = ['stock', 'bench']
        if len(joined) >= 30:
            sr = joined['stock'].pct_change().dropna()
            br = joined['bench'].pct_change().dropna()
            common = sr.index.intersection(br.index)
            sr = sr.loc[common]
            br = br.loc[common]
            if len(sr) >= 20 and br.var() > 0:
                cov = np.cov(sr, br)[0][1]
                beta = float(cov / br.var())

    # 5) Sharpe Ratio
    sharpe = None
    if sigma_annual and sigma_annual > 0:
        # Dung return trung binh nam
        mean_return_annual = float(np.mean(returns) * 252) if len(returns) > 0 else 0
        sharpe = (mean_return_annual - rf) / sigma_annual

    # 6) Total return 1y (giu nguyen)
    total_1y = None
    if n >= 250:
        total_1y = float(closes[-1] / closes[-250] - 1)

    result = {
        'symbol': symbol,
        'close': float(closes[-1]),
        'beta': round(beta, 2) if beta is not None else None,
        'sigma_annual': round(sigma_annual, 4) if sigma_annual else None,
        'cagr_1y': round(cagr_1y, 4) if cagr_1y is not None else None,
        'cagr_2y': round(cagr_2y, 4) if cagr_2y is not None else None,
        'total_1y': round(total_1y, 4) if total_1y is not None else None,
        'sharpe': round(sharpe, 2) if sharpe is not None else None,
        'max_drawdown': round(mdd, 4) if mdd is not None else None,
        'rf_rate': rf,
        'days': len(closes),
        'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }
    return result


def correlation(sym1, sym2, days=500):
    """Tinh he so tuong quan giua 2 ma."""
    df1 = _fetch_history(sym1, days=days)
    df2 = _fetch_history(sym2, days=days)
    if df1 is None or df2 is None:
        return None

    s1 = df1.set_index('time')['close']
    s2 = df2.set_index('time')['close']
    joined = pd.concat([s1, s2], axis=1, join='inner').dropna()
    joined.columns = ['s1', 's2']
    if len(joined) < 30:
        return None
    r1 = joined['s1'].pct_change().dropna()
    r2 = joined['s2'].pct_change().dropna()
    common = r1.index.intersection(r2.index)
    if len(common) < 20:
        return None
    corr = np.corrcoef(r1.loc[common], r2.loc[common])[0, 1]
    return round(float(corr), 3)


def compute_all_risk(symbols, days=500):
    """
    Tinh rui ro cho danh sach ma.
    Cache 6h de tranh fetch lai.
    """
    cache = load_cache()
    benchmark_df = _fetch_benchmark(days=days)

    results = {}
    to_fetch = []
    for s in symbols:
        if s in cache:
            results[s] = cache[s]
        else:
            to_fetch.append(s)

    print(f"  [Risk] {len(results)} ma tu cache, can fetch {len(to_fetch)} ma")

    for i, sym in enumerate(to_fetch):
        if i > 0:
            import time
            time.sleep(0.8)
        r = compute_risk(sym, benchmark_df, days=days)
        results[sym] = r
        if (i + 1) % 10 == 0:
            print(f"    [Risk] Tien do: {i+1}/{len(to_fetch)}")

    save_cache(results)
    return results


def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'_ts': datetime.now().isoformat(), 'items': data}, f,
                      ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
        # Kiem tra tuoi cache
        ts = d.get('_ts')
        if ts:
            try:
                age_hours = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
                if age_hours > CACHE_HOURS:
                    return {}
            except Exception:
                pass
        return d.get('items', {})
    except Exception:
        return {}


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    print("Test risk metrics cho FPT, HPG, VNM...")
    bench = _fetch_benchmark()
    print()
    for sym in ['FPT', 'HPG', 'VNM', 'VCB']:
        r = compute_risk(sym, bench)
        if 'error' in r:
            print(f"[{sym}] LOI: {r['error']}")
            continue
        print(f"[{sym}]")
        print(f"  Close: {r['close']:,.0f}")
        print(f"  Beta: {r['beta']}")
        print(f"  Sigma: {r['sigma_annual']}")
        print(f"  CAGR 1y: {r['cagr_1y']}, CAGR 2y: {r['cagr_2y']}")
        print(f"  Sharpe: {r['sharpe']}")
        print(f"  Max DD: {r['max_drawdown']}")
        print()

    # Test correlation
    print("Correlation FPT - HPG:", correlation('FPT', 'HPG'))
    print("Correlation FPT - VNM:", correlation('FPT', 'VNM'))