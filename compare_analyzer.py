# compare_analyzer.py - So sanh 2 ma cung nganh
import os
try:
    from hf_compat import get_path as _hf_path
except ImportError:
    _hf_path = lambda x: x
import json
import base64
import io
from datetime import datetime

import numpy as np
import pandas as pd

CACHE_FILE = _hf_path('compare_cache.json')

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    plt.rcParams['axes.unicode_minus'] = False
    CHART_OK = True
except ImportError:
    CHART_OK = False


def _fetch_history(symbol, days=500):
    """Lay lich su gia - dung fallback_provider."""
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
        return df
    except Exception as e:
        print(f"  [Compare] Loi fetch {symbol}: {str(e)[:80]}")
        return None


def _compute_metrics(df, sym):
    """Tinh cac chi so tu chuoi gia."""
    closes = df['close'].values
    returns = np.diff(closes) / closes[:-1]
    n = len(closes)

    sigma = float(np.std(returns) * np.sqrt(252)) if len(returns) > 20 else None

    # CAGR
    cagr_1y = cagr_2y = None
    if n >= 250:
        try:
            cagr_1y = closes[-1] / closes[-250] - 1
        except Exception:
            pass
    if n >= 500:
        try:
            cagr_2y = (closes[-1] / closes[-500]) ** 0.5 - 1
        except Exception:
            pass

    # Max DD
    cum_max = np.maximum.accumulate(closes)
    dd = (closes - cum_max) / cum_max
    mdd = float(dd.min())

    # Sharpe (Rf = 3.3%)
    rf = 0.033
    mean_ret = float(np.mean(returns) * 252) if len(returns) > 0 else 0
    sharpe = (mean_ret - rf) / sigma if sigma and sigma > 0 else None

    # Total return 2y
    total_2y = None
    if n >= 500:
        total_2y = closes[-1] / closes[-500] - 1

    return {
        'symbol': sym,
        'close': float(closes[-1]),
        'sigma': round(sigma, 4) if sigma else None,
        'cagr_1y': round(cagr_1y, 4) if cagr_1y is not None else None,
        'cagr_2y': round(cagr_2y, 4) if cagr_2y is not None else None,
        'total_2y': round(total_2y, 4) if total_2y is not None else None,
        'sharpe': round(sharpe, 2) if sharpe is not None else None,
        'max_drawdown': round(mdd, 4),
        'days': n,
    }


def _compute_correlation(df1, df2):
    """Tinh correlation 2 chuoi gia."""
    s1 = df1.set_index('time')['close']
    s2 = df2.set_index('time')['close']
    joined = pd.concat([s1, s2], axis=1, join='inner').dropna()
    if len(joined) < 30:
        return None
    joined.columns = ['s1', 's2']
    r1 = joined['s1'].pct_change().dropna()
    r2 = joined['s2'].pct_change().dropna()
    common = r1.index.intersection(r2.index)
    if len(common) < 20:
        return None
    return round(float(np.corrcoef(r1.loc[common], r2.loc[common])[0, 1]), 3)


def _chart_normalized(df1, df2, sym1, sym2):
    """Ve bieu do tang truong chuan hoa goc 100."""
    if not CHART_OK:
        return None
    s1 = df1.set_index('time')['close'].tail(500)
    s2 = df2.set_index('time')['close'].tail(500)

    joined = pd.concat([s1, s2], axis=1, join='inner').dropna()
    if len(joined) < 30:
        return None
    joined.columns = ['s1', 's2']

    # Chuan hoa goc 100
    base1 = joined['s1'].iloc[0]
    base2 = joined['s2'].iloc[0]
    norm1 = joined['s1'] / base1 * 100
    norm2 = joined['s2'] / base2 * 100

    fig, ax = plt.subplots(figsize=(11, 5), dpi=90)
    ax.plot(joined.index, norm1, label=f'{sym1} ({(norm1.iloc[-1]-100):+.1f}%)',
            color='#3B82F6', linewidth=1.8)
    ax.plot(joined.index, norm2, label=f'{sym2} ({(norm2.iloc[-1]-100):+.1f}%)',
            color='#EF4444', linewidth=1.8)
    ax.axhline(100, color='#94A3B8', linewidth=0.8, linestyle='--')
    ax.set_ylabel('Hiệu suất chuẩn hóa (gốc 100)', fontsize=10, fontweight='bold')
    ax.set_title(f'So sánh tăng trưởng 2 năm: {sym1} vs {sym2}', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#FAFAFA')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def compare_two(sym1, sym2):
    """
    So sanh 2 ma.
    Tra ve dict:
      - sym1, sym2
      - metrics1, metrics2: chi so rui ro
      - correlation: he so tuong quan
      - chart: base64 PNG
    """
    sym1 = sym1.upper().strip()
    sym2 = sym2.upper().strip()

    if sym1 == sym2:
        return {'error': 'Hai mã không được trùng nhau'}

    df1 = _fetch_history(sym1, 500)
    if df1 is None or len(df1) < 30:
        return {'error': f'Không đủ dữ liệu cho {sym1}'}

    df2 = _fetch_history(sym2, 500)
    if df2 is None or len(df2) < 30:
        return {'error': f'Không đủ dữ liệu cho {sym2}'}

    m1 = _compute_metrics(df1, sym1)
    m2 = _compute_metrics(df2, sym2)
    corr = _compute_correlation(df1, df2)
    chart = _chart_normalized(df1, df2, sym1, sym2)

    return {
        'sym1': sym1,
        'sym2': sym2,
        'metrics1': m1,
        'metrics2': m2,
        'correlation': corr,
        'chart': chart,
        'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    print("So sanh FPT va CMG...")
    r = compare_two('FPT', 'CMG')
    if 'error' in r:
        print(f"LOI: {r['error']}")
    else:
        print(f"\n{r['sym1']} vs {r['sym2']}")
        print(f"Correlation: {r['correlation']}")
        print(f"\n{r['sym1']}:")
        for k, v in r['metrics1'].items():
            print(f"  {k}: {v}")
        print(f"\n{r['sym2']}:")
        for k, v in r['metrics2'].items():
            print(f"  {k}: {v}")
        print(f"\nChart base64 length: {len(r['chart']) if r['chart'] else 0}")
        if r['chart']:
            with open('test_compare.png', 'wb') as f:
                f.write(base64.b64decode(r['chart']))
            print("Da luu test_compare.png")