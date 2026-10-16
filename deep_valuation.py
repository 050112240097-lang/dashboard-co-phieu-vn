# deep_valuation.py - Dinh gia: Graham, P/E fair, P/B fair, DCF (co chuan hoa split)
import time
import json
import os
from datetime import datetime
from financial_utils import find_row, get_latest_periods, get_value

CACHE_FILE = 'deep_valuation_cache.json'
CACHE_HOURS = 12

DEFAULT_WACC = 0.12
DEFAULT_TERMINAL_GROWTH = 0.03
DEFAULT_YEARS = 5


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = (time.time() - data.get('_ts', 0)) / 3600
        if age > CACHE_HOURS:
            return {}
        return data.get('items', {})
    except Exception:
        return {}


def save_cache(items):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'_ts': time.time(), 'items': items}, f,
                      ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---- FCF ----
def _fetch_fcf_series(symbol):
    try:
        from vnstock import Finance
        fin = Finance(symbol=symbol, source='kbs')
        cf = fin.cash_flow(period='year', lang='vi')
    except Exception:
        return []

    if cf is None or cf.empty:
        return []

    periods = get_latest_periods(cf, n=4)
    if not periods:
        return []

    ocf_row = find_row(cf, [
        'lưu chuyển tiền tệ thuần từ hoạt động kinh doanh',
        'lưu chuyển tiền thuần từ hoạt động kinh doanh',
        'net cash from operating activities',
    ])
    capex_row = find_row(cf, [
        'tiền chi để mua sắm, xây dựng tscđ',
        'mua sắm tscđ', 'chi đầu tư tscđ',
        'capital expenditure',
    ])

    if ocf_row is None:
        return []

    fcf_list = []
    for p in periods:
        ocf = get_value(ocf_row, p)
        capex = get_value(capex_row, p) if capex_row is not None else 0
        if ocf is None:
            continue
        if capex is None:
            capex = 0
        if capex > 0:
            capex = -capex
        fcf_list.append({'period': str(p), 'fcf': ocf + capex})
    return fcf_list


def _estimate_growth(fcf_series, cap_min=0.02, cap_max=0.15):
    if len(fcf_series) < 2:
        return 0.05
    new = fcf_series[0]['fcf']
    old = fcf_series[-1]['fcf']
    n = len(fcf_series) - 1
    if old <= 0 or new <= 0:
        return 0.05
    try:
        cagr = (new / old) ** (1 / n) - 1
        return max(cap_min, min(cap_max, cagr))
    except Exception:
        return 0.05


def _dcf_price(fcf_base, growth, wacc, tg, years, shares):
    if not fcf_base or fcf_base <= 0 or not shares or shares <= 0:
        return None
    if wacc <= tg:
        return None
    pv = 0
    fcf = fcf_base
    for y in range(1, years + 1):
        fcf *= (1 + growth)
        pv += fcf / ((1 + wacc) ** y)
    tv = fcf * (1 + tg) / (wacc - tg)
    pv_tv = tv / ((1 + wacc) ** years)
    return (pv + pv_tv) / shares


def _estimate_shares_from_ratio(symbol):
    """Uoc luong shares = owners_equity / BVPS tu ratio KBS."""
    try:
        from vnstock import Finance
        fin = Finance(symbol=symbol, source='kbs')
        ratio = fin.ratio(period='Q', lang='vi')
        if ratio is None or ratio.empty or 'item_id' not in ratio.columns:
            return None
        periods = get_latest_periods(ratio, n=1)
        if not periods:
            return None
        col = periods[0]

        def _get(iid):
            rows = ratio[ratio['item_id'].astype(str).str.lower() == iid.lower()]
            if rows.empty:
                return None
            try:
                return float(rows.iloc[0][col])
            except Exception:
                return None

        equity = _get('owners_equity')
        bvps = _get('book_value_per_share_bvps')
        if equity and bvps and bvps > 0:
            shares = equity / bvps
            # Chan gia tri vo ly: shares phai > 10 trieu va < 10 ty
            if shares < 10_000_000 or shares > 10_000_000_000:
                return None
            return shares
    except Exception:
        pass
    return None


# ---- Graham / P/E fair / P/B fair ----
def graham_number(eps, bvps):
    if eps is None or bvps is None or eps <= 0 or bvps <= 0:
        return None
    return (22.5 * eps * bvps) ** 0.5


def pe_fair_price(eps, industry_pe_avg):
    if eps is None or industry_pe_avg is None or eps <= 0 or industry_pe_avg <= 0:
        return None
    return eps * industry_pe_avg


def pb_fair_price(bvps, industry_pb_avg):
    if bvps is None or industry_pb_avg is None or bvps <= 0 or industry_pb_avg <= 0:
        return None
    return bvps * industry_pb_avg


def adjust_split(valuation, close_price):
    """
    Chuan hoa EPS/BVPS tu API ve don vi gia hien tai.
    VD: PNJ chia thuong 1:4 -> EPS API (6.947) / 4.26 = 1.630
    """
    if not close_price or close_price <= 0:
        return valuation
    pe = valuation.get('pe')
    eps = valuation.get('eps')
    if not pe or not eps or pe <= 0 or eps <= 0:
        return valuation

    api_implied_price = pe * eps
    ratio = api_implied_price / close_price

    # Neu lech > 1.5 lan -> co chia thuong, can chuan hoa
    if ratio > 1.5:
        print(f"  [Split] Phat hien chia thuong {ratio:.2f}x -> dieu chinh EPS/BVPS")
        valuation = dict(valuation)
        valuation['eps'] = eps / ratio
        if valuation.get('bvps'):
            valuation['bvps'] = valuation['bvps'] / ratio
        valuation['split_ratio'] = round(ratio, 2)
        valuation['split_adjusted'] = True
    return valuation


# ============================================================
# TONG HOP
# ============================================================
def deep_valuation(symbol, close_price, valuation_api,
                   industry_pe_avg=None, industry_pb_avg=None,
                   wacc=DEFAULT_WACC, terminal_growth=DEFAULT_TERMINAL_GROWTH,
                   use_cache=True):
    cache = load_cache() if use_cache else {}
    key = f"{symbol}_{close_price}"
    if use_cache and key in cache:
        return cache[key]

    # Chuan hoa split truoc khi lay EPS/BVPS
    valuation_api = adjust_split(valuation_api, close_price)
    eps = valuation_api.get('eps')
    bvps = valuation_api.get('bvps')

    result = {
        'symbol': symbol,
        'close_price': close_price,
        'eps': eps,
        'bvps': bvps,
        'valuation_used': valuation_api,
        'split_adjusted': valuation_api.get('split_adjusted', False),
        'split_ratio': valuation_api.get('split_ratio'),
        'pe_current': valuation_api.get('pe'),
        'pb_current': valuation_api.get('pb'),
        'industry_pe_avg': industry_pe_avg,
        'industry_pb_avg': industry_pb_avg,
        'wacc': wacc,
        'terminal_growth': terminal_growth,
        'methods': {},
        'fair_range': None,
        'upside_pct': None,
        'verdict': None,
    }

    g = graham_number(eps, bvps)
    if g:
        result['methods']['graham'] = {'value': round(g, 0), 'label': 'Graham Number'}

    pe_fair = pe_fair_price(eps, industry_pe_avg)
    if pe_fair:
        result['methods']['pe_fair'] = {
            'value': round(pe_fair, 0),
            'label': f'P/E fair (P/E ngành {industry_pe_avg:.1f}x)'
        }

    pb_fair = pb_fair_price(bvps, industry_pb_avg)
    if pb_fair:
        result['methods']['pb_fair'] = {
            'value': round(pb_fair, 0),
            'label': f'P/B fair (P/B ngành {industry_pb_avg:.2f}x)'
        }

    # DCF (uoc luong shares tu ratio)
    fcf_series = _fetch_fcf_series(symbol)
    if fcf_series:
        growth = _estimate_growth(fcf_series)
        shares = _estimate_shares_from_ratio(symbol)
        result['fcf_latest'] = fcf_series[0]['fcf']
        result['fcf_history'] = fcf_series
        result['growth_assumed'] = round(growth, 4)
        result['shares_estimated'] = round(shares, 0) if shares else None
        if shares:
            dcf_price = _dcf_price(fcf_series[0]['fcf'], growth, wacc,
                                   terminal_growth, DEFAULT_YEARS, shares)
            if dcf_price:
                result['methods']['dcf'] = {
                    'value': round(dcf_price, 0),
                    'label': f'DCF {DEFAULT_YEARS} năm (g={growth:.1%}, WACC={wacc:.0%})'
                }

    # Loai bo outlier: method nao > 5x hoac < 1/5 gia hien tai thi bo
    if close_price and close_price > 0:
        filtered = {}
        for k, m in result['methods'].items():
            v = m.get('value')
            if v is None:
                continue
            ratio = v / close_price
            if 0.2 <= ratio <= 5.0:
                filtered[k] = m
            else:
                print(f"  [Valuation] Bo method {k} = {v:,.0f} (lech qua xa gia {close_price:,.0f})")
        result['methods'] = filtered

    values = [m['value'] for m in result['methods'].values() if m.get('value')]
    if values:
        result['fair_range'] = {
            'min': round(min(values), 0),
            'max': round(max(values), 0),
            'median': round(sorted(values)[len(values) // 2], 0),
            'methods_count': len(values),
        }
        if close_price and close_price > 0:
            med = result['fair_range']['median']
            result['upside_pct'] = round((med - close_price) / close_price * 100, 1)
            up = result['upside_pct']
            if up > 20:
                result['verdict'] = 'undervalued'
            elif up > 5:
                result['verdict'] = 'slightly_undervalued'
            elif up > -5:
                result['verdict'] = 'fair'
            elif up > -20:
                result['verdict'] = 'slightly_overvalued'
            else:
                result['verdict'] = 'overvalued'

    result['updated'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if use_cache:
        cache[key] = result
        save_cache(cache)

    return result