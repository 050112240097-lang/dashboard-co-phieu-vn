# valuation_analyzer.py - Doc dung format long cua Finance.ratio()
import time
import json
import os
from datetime import datetime

CACHE_FILE = 'valuation_cache.json'
CACHE_HOURS = 6


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = (time.time() - data.get('_ts', 0)) / 3600
        if age > CACHE_HOURS:
            return {}
        print(f"  [Cache] Valuation ({age:.1f}h)")
        return data.get('ratios', {})
    except Exception:
        return {}


def save_cache(ratios):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                '_ts': time.time(),
                'ratios': ratios,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _to_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else round(f, 2)
    except Exception:
        return None


def fetch_ratio(symbol, close_price=None):
    """
    Lay EPS tu Finance.ratio() (format long: item_id + cac cot quy).
    Tinh P/E tu gia / EPS.
    """
    empty = {
        'symbol': symbol, 'pe': None, 'pb': None, 'roe': None,
        'roa': None, 'eps': None, 'bvps': None, 'source': 'kbs',
    }

    try:
        from vnstock import Finance
        fin = Finance(symbol=symbol, source='kbs')
        df = fin.ratio(period='Q', lang='vi')

        if df is None or df.empty:
            return empty

        # Format: ['item', 'item_id', '2026-Q2', '2025-Q4', ...]
        # item_id chua trailing_eps, pe, pb, roe, roa...
        # Lay cot quy moi nhat (cot thu 3, index 2)
        cols = list(df.columns)
        if len(cols) < 3:
            return empty

        latest_col = cols[2]  # VD: 2026-Q2

        # Tim dong co item_id tuong ung
        def find_value(item_ids):
            if 'item_id' not in df.columns:
                return None
            for iid in item_ids:
                rows = df[df['item_id'].astype(str).str.lower() == iid.lower()]
                if not rows.empty:
                    v = rows.iloc[0][latest_col]
                    f = _to_float(v)
                    if f is not None:
                        return f
            return None

        # EPS
        eps = find_value(['trailing_eps', 'eps', 'eps_quarter'])
        empty['eps'] = eps

        # ROE, ROA
        empty['roe'] = find_value(['roe_trailling', 'roe_trailing', 'roe', 'return_on_equity'])
        empty['roa'] = find_value(['roa_trailling', 'roa_trailing', 'roa', 'return_on_asset'])
        empty['bvps'] = find_value(['book_value_per_share_bvps', 'bvps', 'book_value_per_share'])

        # P/E: tinh tu gia / EPS
        if eps and eps > 0 and close_price and close_price > 0:
            empty['pe'] = round(close_price / eps, 2)

        # P/B: tinh tu gia / BVPS
        if empty['bvps'] and empty['bvps'] > 0 and close_price and close_price > 0:
            empty['pb'] = round(close_price / empty['bvps'], 2)

        # Neu ratio co san pe/pb thi dung luon
        pe_api = find_value(['pe', 'pe_ratio', 'p_e'])
        if pe_api:
            empty['pe'] = pe_api
        pb_api = find_value(['pb', 'pb_ratio', 'p_b'])
        if pb_api:
            empty['pb'] = pb_api

    except Exception as e:
        pass

    return empty


def fetch_all_valuations(symbols_with_price):
    """
    symbols_with_price: dict {symbol: close_price} hoac list symbols
    """
    cache = load_cache()
    result = dict(cache)

    # Chuyen ve dict
    if isinstance(symbols_with_price, dict):
        price_map = symbols_with_price
    else:
        price_map = {s: None for s in symbols_with_price}

    to_fetch = [s for s in price_map.keys() if s not in cache]
    if not to_fetch:
        return {s: result[s] for s in price_map.keys() if s in result}

    print(f"  [Valuation] Lay {len(to_fetch)} ma moi")
    for i, sym in enumerate(to_fetch):
        if i > 0:
            time.sleep(1.2)
        if i % 5 == 0:
            print(f"    Tien do: {i+1}/{len(to_fetch)}")
        result[sym] = fetch_ratio(sym, price_map.get(sym))

    save_cache(result)
    return {s: result[s] for s in price_map.keys() if s in result}


def compute_industry_roe(valuations, industries, min_count=5):
    """
    Tinh ROE trung binh theo nganh.
    - Neu nganh co >= min_count ma -> dung gia tri thuc.
    - Neu nganh co < min_count ma -> dung gia tri mac dinh (fallback).
    """
    # Gia tri fallback cho nganh it ma (dua tren kinh nghiem thi truong VN)
    FALLBACK_ROE = {
        'Tài chính': 15.0,
        'Bất động sản': 8.0,
        'Tiêu dùng thiết yếu': 16.0,
        'Tiêu dùng không thiết yếu': 12.0,
        'Công nghệ thông tin': 18.0,
        'Công nghiệp': 10.0,
        'Năng lượng': 12.0,
        'Tiện ích': 10.0,
        'Nguyên vật liệu': 14.0,
        'Y tế': 14.0,
        'Khác': 10.0,
    }

    groups = {}
    for sym, r in valuations.items():
        roe = r.get('roe')
        if not roe or roe <= 0:
            continue
        ind = industries.get(sym, {}).get('group', 'Khác')
        groups.setdefault(ind, []).append(roe)

    result = {}
    for ind, roes in groups.items():
        if len(roes) >= min_count:
            # Du ma -> dung so thuc
            result[ind] = {
                'avg_roe': round(sum(roes) / len(roes), 2),
                'count': len(roes),
                'max_roe': round(max(roes), 2),
                'min_roe': round(min(roes), 2),
                'source': 'actual',
            }
        else:
            # It ma -> dung fallback
            fb = FALLBACK_ROE.get(ind, 10.0)
            result[ind] = {
                'avg_roe': fb,
                'count': len(roes),
                'max_roe': fb * 1.5,
                'min_roe': fb * 0.5,
                'source': 'fallback',
            }
    return result