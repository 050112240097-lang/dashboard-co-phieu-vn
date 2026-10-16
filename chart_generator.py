# chart_generator.py - Render bieu do gia + SMA/RSI/MACD bang matplotlib
import io
import base64
import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Khong can display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

# Font cho tieng Viet
try:
    plt.rcParams['font.family'] = 'DejaVu Sans'
except Exception:
    pass
plt.rcParams['axes.unicode_minus'] = False


def _fetch_ohlcv(symbol, length=90):
    """Lay du lieu OHLCV tu vnstock."""
    try:
        try:
            from fallback_provider import get_history
            df = get_history(symbol, days=length)
        except ImportError:
            from vnstock import Quote
            quote = Quote(symbol=symbol, source='kbs')
            df = quote.history(length=length, interval='1D')
        if df is None or df.empty:
            return None
        # Chuan hoa
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['close'])
        return df
    except Exception as e:
        print(f"  [Chart] Loi fetch {symbol}: {str(e)[:80]}")
        return None


def _compute_indicators(df):
    """Tinh SMA20, SMA50, EMA20, RSI14, MACD."""
    df = df.copy()
    df['SMA20'] = df['close'].rolling(20).mean()
    df['SMA50'] = df['close'].rolling(50).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI14'] = 100 - (100 / (1 + rs))

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    return df


def generate_chart_base64(symbol, length=90):
    """
    Tra ve (base64_png, info_dict) hoac (None, error).
    """
    df = _fetch_ohlcv(symbol, length=length)
    if df is None or len(df) < 20:
        return None, {'error': f'Khong du du lieu cho {symbol}'}

    df = _compute_indicators(df)
    df = df.dropna(subset=['SMA20']).reset_index(drop=True)
    if len(df) < 5:
        return None, {'error': 'Du lieu qua it'}

    # Setup figure: 3 subplot
    fig = plt.figure(figsize=(11, 7), dpi=90)
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.15)
    ax_price = fig.add_subplot(gs[0])
    ax_vol = fig.add_subplot(gs[1], sharex=ax_price)
    ax_rsi = fig.add_subplot(gs[2], sharex=ax_price)
    ax_macd = fig.add_subplot(gs[3], sharex=ax_price)

    # --- Subplot 1: Gia + SMA/EMA ---
    ax_price.plot(df['time'], df['close'], color='#0F172A', linewidth=1.5, label='Close')
    ax_price.plot(df['time'], df['SMA20'], color='#3B82F6', linewidth=1.2, label='SMA20')
    ax_price.plot(df['time'], df['SMA50'], color='#F59E0B', linewidth=1.2, label='SMA50')
    ax_price.plot(df['time'], df['EMA20'], color='#8B5CF6', linewidth=1, linestyle='--', label='EMA20')
    ax_price.fill_between(df['time'], df['close'], alpha=0.05, color='#0F172A')

    # Danh dau diem cuoi
    last = df.iloc[-1]
    ax_price.scatter([last['time']], [last['close']], color='#EF4444', s=40, zorder=5)
    ax_price.annotate(
        f"{last['close']:,.0f}",
        xy=(last['time'], last['close']),
        xytext=(5, 5), textcoords='offset points',
        color='#EF4444', fontweight='bold', fontsize=10,
    )

    ax_price.set_ylabel('Giá (VND)', fontsize=10, fontweight='bold')
    ax_price.set_title(f'Biểu đồ {symbol} — {len(df)} phiên', fontsize=13, fontweight='bold', pad=12)
    ax_price.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax_price.grid(True, alpha=0.3, linestyle='--')
    ax_price.tick_params(labelbottom=False)

    # --- Subplot 2: Volume ---
    colors = ['#10B981' if df['close'].iloc[i] >= df['open'].iloc[i] else '#EF4444'
              for i in range(len(df))]
    ax_vol.bar(df['time'], df['volume'], color=colors, alpha=0.6, width=0.8)
    ax_vol.set_ylabel('KL', fontsize=9, fontweight='bold')
    ax_vol.grid(True, alpha=0.3, linestyle='--')
    ax_vol.tick_params(labelbottom=False)
    # Format volume
    ax_vol.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'{x/1e6:.0f}M' if x >= 1e6 else f'{x/1e3:.0f}K')
    )

    # --- Subplot 3: RSI ---
    ax_rsi.plot(df['time'], df['RSI14'], color='#8B5CF6', linewidth=1.3)
    ax_rsi.axhline(70, color='#EF4444', linestyle='--', linewidth=0.8, alpha=0.7)
    ax_rsi.axhline(30, color='#10B981', linestyle='--', linewidth=0.8, alpha=0.7)
    ax_rsi.fill_between(df['time'], 70, 100, color='#EF4444', alpha=0.08)
    ax_rsi.fill_between(df['time'], 0, 30, color='#10B981', alpha=0.08)
    ax_rsi.set_ylabel('RSI', fontsize=9, fontweight='bold')
    ax_rsi.set_ylim(0, 100)
    ax_rsi.grid(True, alpha=0.3, linestyle='--')
    ax_rsi.tick_params(labelbottom=False)
    # Marker RSI cuoi
    if pd.notna(last.get('RSI14')):
        ax_rsi.scatter([last['time']], [last['RSI14']], color='#8B5CF6', s=30, zorder=5)

    # --- Subplot 4: MACD ---
    ax_macd.plot(df['time'], df['MACD'], color='#3B82F6', linewidth=1.2, label='MACD')
    ax_macd.plot(df['time'], df['MACD_signal'], color='#F59E0B', linewidth=1.2, label='Signal')
    colors_hist = ['#10B981' if v >= 0 else '#EF4444' for v in df['MACD_hist']]
    ax_macd.bar(df['time'], df['MACD_hist'], color=colors_hist, alpha=0.5, width=0.8)
    ax_macd.axhline(0, color='#94A3B8', linewidth=0.8)
    ax_macd.set_ylabel('MACD', fontsize=9, fontweight='bold')
    ax_macd.grid(True, alpha=0.3, linestyle='--')
    ax_macd.legend(loc='upper left', fontsize=8, framealpha=0.9)
    ax_macd.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax_macd.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
    plt.setp(ax_macd.get_xticklabels(), rotation=0, fontsize=8)

    # Toi uu
    fig.patch.set_facecolor('#FFFFFF')
    for ax in [ax_price, ax_vol, ax_rsi, ax_macd]:
        ax.set_facecolor('#FAFAFA')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)

    plt.tight_layout()

    # Luu vao buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)

    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    info = {
        'symbol': symbol,
        'close': round(float(last['close']), 2),
        'sma20': round(float(last['SMA20']), 2) if pd.notna(last['SMA20']) else None,
        'sma50': round(float(last['SMA50']), 2) if pd.notna(last['SMA50']) else None,
        'rsi14': round(float(last['RSI14']), 2) if pd.notna(last['RSI14']) else None,
        'macd': round(float(last['MACD']), 3) if pd.notna(last['MACD']) else None,
        'signal': None,
    }

    # Signal
    if info['sma20'] and info['sma50']:
        c = info['close']
        if c > info['sma20'] > info['sma50']:
            info['signal'] = 'Tăng'
        elif c < info['sma20'] < info['sma50']:
            info['signal'] = 'Giảm'
        else:
            info['signal'] = 'Trung tính'

    return b64, info


def save_chart_file(symbol, out_path=None):
    """Luu chart ra file PNG (neu can)."""
    b64, info = generate_chart_base64(symbol)
    if not b64:
        return None, info
    if out_path is None:
        out_path = f'chart_{symbol}.png'
    with open(out_path, 'wb') as f:
        f.write(base64.b64decode(b64))
    return out_path, info


if __name__ == '__main__':
    print("Test render chart FPT...")
    b64, info = generate_chart_base64('FPT')
    if b64:
        path = 'test_chart_FPT.png'
        with open(path, 'wb') as f:
            f.write(base64.b64decode(b64))
        print(f"  [OK] Da luu {path} ({len(b64)} bytes base64)")
        print(f"  Info: {info}")
    else:
        print(f"  [LOI] {info}")