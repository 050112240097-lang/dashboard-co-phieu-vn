# portfolio_optimizer.py - Toi uu danh muc Markowitz (SLSQP + Monte Carlo)
import os
import json
import math
import base64
import io
from datetime import datetime

import numpy as np
import pandas as pd

try:
    from scipy.optimize import minimize
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False
    print("  [WARN] Chua cai scipy. Chay: pip install scipy")

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['axes.unicode_minus'] = False
    CHART_OK = True
except ImportError:
    CHART_OK = False


DEFAULT_RF = 0.033  # 3.3%/nam
TRADING_DAYS = 252
DEFAULT_DAYS = 500  # ~2 nam


def _fetch_history(symbol, days=DEFAULT_DAYS):
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
        return df[['time', 'close']].set_index('time')
    except Exception as e:
        print(f"  [Portfolio] Loi fetch {symbol}: {str(e)[:80]}")
        return None


def _build_price_matrix(symbols, days=DEFAULT_DAYS):
    """Tra ve DataFrame gia cua nhieu ma (da align theo ngay)."""
    data = {}
    for sym in symbols:
        df = _fetch_history(sym, days)
        if df is not None and len(df) > 100:
            data[sym] = df['close']
        else:
            print(f"  [Portfolio] Bo qua {sym}: khong du du lieu")
    if not data:
        return None
    prices = pd.DataFrame(data).dropna()
    return prices


def _compute_correlation_matrix(returns):
    return returns.corr()


def _portfolio_performance(weights, mean_returns, cov_matrix, rf=DEFAULT_RF):
    """Tinh return, volatility, sharpe cua danh muc."""
    weights = np.array(weights)
    ret = np.sum(mean_returns * weights) * TRADING_DAYS
    vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * TRADING_DAYS, weights)))
    sharpe = (ret - rf) / vol if vol > 0 else 0
    return ret, vol, sharpe


def _neg_sharpe(weights, mean_returns, cov_matrix, rf):
    return -_portfolio_performance(weights, mean_returns, cov_matrix, rf)[2]


def _portfolio_vol(weights, mean_returns, cov_matrix):
    return _portfolio_performance(weights, mean_returns, cov_matrix)[1]


def optimize_max_sharpe(mean_returns, cov_matrix, rf=DEFAULT_RF, bounds=None):
    """Toi uu Max Sharpe bang SLSQP."""
    if not SCIPY_OK:
        return None
    n = len(mean_returns)
    if bounds is None:
        bounds = tuple((0.0, 1.0) for _ in range(n))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    init = np.array([1.0 / n] * n)

    result = minimize(
        _neg_sharpe, init, args=(mean_returns, cov_matrix, rf),
        method='SLSQP', bounds=bounds, constraints=constraints,
        options={'maxiter': 500, 'ftol': 1e-10}
    )
    if not result.success:
        return None
    return result.x


def optimize_gmv(mean_returns, cov_matrix, bounds=None):
    """Toi uu Global Minimum Variance."""
    if not SCIPY_OK:
        return None
    n = len(mean_returns)
    if bounds is None:
        bounds = tuple((0.0, 1.0) for _ in range(n))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    init = np.array([1.0 / n] * n)

    result = minimize(
        _portfolio_vol, init, args=(mean_returns, cov_matrix),
        method='SLSQP', bounds=bounds, constraints=constraints,
        options={'maxiter': 500, 'ftol': 1e-10}
    )
    if not result.success:
        return None
    return result.x


def monte_carlo(mean_returns, cov_matrix, n_portfolios=5000, rf=DEFAULT_RF):
    """Mo phong n danh muc ngau nhien."""
    n = len(mean_returns)
    results = np.zeros((3, n_portfolios))
    weights_record = []

    for i in range(n_portfolios):
        w = np.random.random(n)
        w /= np.sum(w)
        weights_record.append(w)
        ret, vol, sharpe = _portfolio_performance(w, mean_returns, cov_matrix, rf)
        results[0, i] = ret
        results[1, i] = vol
        results[2, i] = sharpe

    return results, weights_record


def _chart_efficient_frontier(results, current_perf, max_sharpe_perf, gmv_perf):
    """Ve duong bien hieu qua."""
    if not CHART_OK:
        return None

    fig, ax = plt.subplots(figsize=(11, 7), dpi=90)

    # Scatter Monte Carlo
    sc = ax.scatter(results[1, :], results[0, :], c=results[2, :],
                    cmap='viridis', marker='o', s=10, alpha=0.6)
    plt.colorbar(sc, ax=ax, label='Sharpe Ratio')

    # Danh dau 3 danh muc
    if current_perf:
        ax.scatter(current_perf['vol'], current_perf['ret'], marker='o',
                   color='#8B5CF6', s=200, edgecolors='black', linewidth=1.5,
                   label=f"Danh mục hiện tại (Sharpe: {current_perf['sharpe']:.2f})", zorder=5)
    if max_sharpe_perf:
        ax.scatter(max_sharpe_perf['vol'], max_sharpe_perf['ret'], marker='*',
                   color='#EF4444', s=400, edgecolors='black', linewidth=1.5,
                   label=f"Max Sharpe SLSQP ({max_sharpe_perf['sharpe']:.2f})", zorder=6)
    if gmv_perf:
        ax.scatter(gmv_perf['vol'], gmv_perf['ret'], marker='D',
                   color='#3B82F6', s=200, edgecolors='black', linewidth=1.5,
                   label=f"Rủi ro tối thiểu GMV ({gmv_perf['vol']*100:.1f}%)", zorder=5)

    ax.set_xlabel('Độ lệch chuẩn / Rủi ro danh mục (σ)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Lợi nhuận kỳ vọng E(Rp)', fontsize=11, fontweight='bold')
    ax.set_title('Đường Biên Hiệu Quả Markowitz (SLSQP + Monte Carlo 5.000 danh mục)',
                 fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')
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


def optimize_portfolio(symbols_weights, rf=DEFAULT_RF, n_mc=5000, max_weight=1.0):
    """
    Ham chinh.
    Input:
      symbols_weights: list of (symbol, weight_pct) tuples. Vi du [('FPT', 35), ('HPG', 30), ('VNM', 35)]
      rf: lai suat phi rui ro
      n_mc: so danh muc Monte Carlo
      max_weight: trong so toi da moi ma (0-1)
    Output: dict ket qua hoac {'error': ...}
    """
    if not SCIPY_OK:
        return {'error': 'Chua cai scipy. Chay: pip install scipy'}

    symbols = [s.upper() for s, _ in symbols_weights]
    if len(symbols) < 2:
        return {'error': 'Can it nhat 2 ma'}
    if len(symbols) > 12:
        return {'error': 'Toi da 12 ma'}
    if len(set(symbols)) != len(symbols):
        return {'error': 'Cac ma khong duoc trung nhau'}

    # Normalize weights
    user_weights = np.array([w for _, w in symbols_weights], dtype=float)
    if user_weights.sum() <= 0:
        return {'error': 'Tong ty trong phai > 0'}
    user_weights = user_weights / user_weights.sum()

    # Fetch gia
    print(f"  [Portfolio] Dang tai du lieu {len(symbols)} ma...")
    prices = _build_price_matrix(symbols, DEFAULT_DAYS)
    if prices is None or prices.empty:
        return {'error': 'Khong lay duoc du lieu gia'}
    if len(prices) < 100:
        return {'error': f'Chi co {len(prices)} phien, can it nhat 100'}

    available_symbols = list(prices.columns)
    if len(available_symbols) != len(symbols):
        # Mot so ma bi loai, normalize lai user_weights
        idx_map = {s: i for i, s in enumerate(symbols)}
        user_weights = np.array([user_weights[idx_map[s]] for s in available_symbols])
        user_weights = user_weights / user_weights.sum()
        symbols = available_symbols

    returns = prices.pct_change().dropna()
    mean_returns = returns.mean()
    cov_matrix = returns.cov()

    # Performance hien tai
    cur_ret, cur_vol, cur_sharpe = _portfolio_performance(user_weights.values if hasattr(user_weights, 'values') else user_weights,
                                                          mean_returns, cov_matrix, rf)

    current_perf = {
        'ret': float(cur_ret),
        'vol': float(cur_vol),
        'sharpe': float(cur_sharpe),
    }

    # Bounds: cho phep 0 -> max_weight
    bounds = tuple((0.0, max_weight) for _ in range(len(symbols)))

    # Toi uu
    print(f"  [Portfolio] Toi uu Max Sharpe...")
    max_sharpe_w = optimize_max_sharpe(mean_returns, cov_matrix, rf, bounds)

    print(f"  [Portfolio] Toi uu GMV...")
    gmv_w = optimize_gmv(mean_returns, cov_matrix, bounds)

    # Monte Carlo
    print(f"  [Portfolio] Monte Carlo {n_mc} danh muc...")
    mc_results, _ = monte_carlo(mean_returns, cov_matrix, n_portfolios=n_mc, rf=rf)

    # Performance cua 2 nghiem
    max_sharpe_perf = None
    max_sharpe_weights = None
    if max_sharpe_w is not None:
        r, v, s = _portfolio_performance(max_sharpe_w, mean_returns, cov_matrix, rf)
        max_sharpe_perf = {'ret': float(r), 'vol': float(v), 'sharpe': float(s)}
        max_sharpe_weights = [round(float(w), 4) for w in max_sharpe_w]

    gmv_perf = None
    gmv_weights = None
    if gmv_w is not None:
        r, v, s = _portfolio_performance(gmv_w, mean_returns, cov_matrix, rf)
        gmv_perf = {'ret': float(r), 'vol': float(v), 'sharpe': float(s)}
        gmv_weights = [round(float(w), 4) for w in gmv_w]

    # Chart
    chart = _chart_efficient_frontier(mc_results, current_perf, max_sharpe_perf, gmv_perf)

    # Chi so da dang hoa
    # DR = 1 / sum(w_i^2) - so luong hieu qua
    sum_w2 = float(np.sum(user_weights ** 2))
    dr = 1.0 / sum_w2 if sum_w2 > 0 else 0

    # Portfolio beta (so sanh benchmark)
    beta_p = None
    try:
        bench = _fetch_history('VNINDEX', DEFAULT_DAYS)
        if bench is not None and len(bench) > 100:
            bench_ret = bench['close'].pct_change().dropna()
            common = returns.index.intersection(bench_ret.index)
            if len(common) > 50:
                port_ret = (returns.loc[common] * user_weights).sum(axis=1)
                cov_pb = np.cov(port_ret, bench_ret.loc[common])[0][1]
                var_b = bench_ret.loc[common].var()
                if var_b > 0:
                    beta_p = float(cov_pb / var_b)
    except Exception:
        pass

    # Correlation matrix
    corr = _compute_correlation_matrix(returns)
    corr_dict = {}
    for s1 in corr.columns:
        corr_dict[s1] = {}
        for s2 in corr.columns:
            corr_dict[s1][s2] = round(float(corr.loc[s1, s2]), 3)

    return {
        'symbols': symbols,
        'user_weights': [round(float(w), 4) for w in user_weights],
        'current': current_perf,
        'max_sharpe_weights': max_sharpe_weights,
        'max_sharpe': max_sharpe_perf,
        'gmv_weights': gmv_weights,
        'gmv': gmv_perf,
        'diversification_ratio': round(dr, 3),
        'beta_portfolio': round(beta_p, 2) if beta_p is not None else None,
        'correlation_matrix': corr_dict,
        'rf_rate': rf,
        'days': len(prices),
        'chart': chart,
        'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    print("Test toi uu danh muc FPT 35% - HPG 30% - VNM 35%...")
    result = optimize_portfolio([('FPT', 35), ('HPG', 30), ('VNM', 35)], n_mc=1000)
    if 'error' in result:
        print(f"LOI: {result['error']}")
    else:
        print(f"\nDanh muc hien tai:")
        print(f"  Return: {result['current']['ret']*100:.2f}%")
        print(f"  Vol: {result['current']['vol']*100:.2f}%")
        print(f"  Sharpe: {result['current']['sharpe']:.2f}")
        print(f"\nMax Sharpe SLSQP:")
        print(f"  Return: {result['max_sharpe']['ret']*100:.2f}%")
        print(f"  Vol: {result['max_sharpe']['vol']*100:.2f}%")
        print(f"  Sharpe: {result['max_sharpe']['sharpe']:.2f}")
        print(f"  Weights: {dict(zip(result['symbols'], result['max_sharpe_weights']))}")
        print(f"\nGMV:")
        print(f"  Vol: {result['gmv']['vol']*100:.2f}%")
        print(f"  Weights: {dict(zip(result['symbols'], result['gmv_weights']))}")
        print(f"\nDiversification Ratio: {result['diversification_ratio']}")
        print(f"Portfolio Beta: {result['beta_portfolio']}")
        if result['chart']:
            with open('test_portfolio.png', 'wb') as f:
                f.write(base64.b64decode(result['chart']))
            print("Da luu test_portfolio.png")