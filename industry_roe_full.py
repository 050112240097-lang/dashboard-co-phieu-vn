# industry_roe_full.py - ROE toan nganh, non-blocking (tra fallback ngay, fetch background)
import time
import json
import os
import threading
from datetime import datetime

CACHE_FILE = 'industry_roe_full_cache.json'
CACHE_HOURS = 24

INDIVIDUAL_CACHE = 'industry_roe_individual_cache.json'
INDIVIDUAL_CACHE_HOURS = 24 * 7  # 7 ngay

SYMBOL_INDUSTRY_CACHE = 'symbol_industry_full_cache.json'
SYMBOL_INDUSTRY_CACHE_DAYS = 7

# Fallback median cho nganh khi chua co cache (dua tren kinh nghiem thi truong VN)
FALLBACK_MEDIAN = {
    'Tài chính': 14.0,
    'Bất động sản': 7.0,
    'Tiêu dùng thiết yếu': 14.0,
    'Tiêu dùng không thiết yếu': 10.0,
    'Công nghệ thông tin': 15.0,
    'Công nghiệp': 9.0,
    'Năng lượng': 11.0,
    'Tiện ích': 9.0,
    'Nguyên vật liệu': 12.0,
    'Y tế': 12.0,
    'Khác': 10.0,
}

# Danh sach nganh dang fetch (tranh spawn nhieu thread cung luc)
_fetching = set()
_fetching_lock = threading.Lock()


def _set_api_key():
    try:
        from config import VNSTOCK_API_KEY
        os.environ['VNSTOCK_API_KEY'] = VNSTOCK_API_KEY
    except Exception:
        pass


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _build_symbol_industry_map():
    _set_api_key()
    data = _load_json(SYMBOL_INDUSTRY_CACHE)
    if data:
        age_days = (time.time() - data.get('_ts', 0)) / 86400
        if age_days <= SYMBOL_INDUSTRY_CACHE_DAYS:
            return data.get('items', {})

    print(f"  [IndustryFull] Fetch mapping tu VCI...")
    result = {}
    try:
        from vnstock import Listing
        from industry_classifier import ICB_MAP

        l = Listing(source='vci')
        df = l.symbols_by_industries()
        if df is not None and not df.empty:
            df_lv2 = df[df['icb_level'] == 2] if 'icb_level' in df.columns else df
            for _, row in df_lv2.iterrows():
                sym = str(row.get('symbol', '')).strip().upper()
                icb = str(row.get('icb_name', '')).strip() if row.get('icb_name') else None
                if sym and icb and icb.lower() != 'nan':
                    result[sym] = ICB_MAP.get(icb, 'Khác')
    except Exception as e:
        print(f"  [IndustryFull] Loi VCI: {str(e)[:100]}")

    try:
        from industry_classifier import MANUAL_MAP
        for sym, grp in MANUAL_MAP.items():
            result[sym] = grp
    except Exception:
        pass

    if result:
        _save_json(SYMBOL_INDUSTRY_CACHE, {'_ts': time.time(), 'items': result})
    return result


def get_symbols_in_industry(industry_group):
    m = _build_symbol_industry_map()
    return sorted([s for s, g in m.items() if g == industry_group])


def _load_individual():
    data = _load_json(INDIVIDUAL_CACHE)
    if not data:
        return {}
    age_hours = (time.time() - data.get('_ts', 0)) / 3600
    if age_hours > INDIVIDUAL_CACHE_HOURS:
        return {}
    return data.get('items', {})


def _save_individual(items):
    _save_json(INDIVIDUAL_CACHE, {'_ts': time.time(), 'items': items})


def _fetch_one_roe(sym):
    from valuation_analyzer import fetch_ratio
    for attempt in range(3):
        try:
            r = fetch_ratio(sym)
            roe = r.get('roe')
            if roe and 0 < roe < 100:
                return roe
            return 0  # danh dau da fetch, khong co ROE
        except Exception as e:
            err_str = str(e).lower()
            if 'rate' in err_str or 'limit' in err_str or '429' in err_str:
                wait = 15 + attempt * 10
                time.sleep(wait)
                continue
            return 0
    return 0


def _fetch_and_cache(industry_group, max_symbols):
    """Fetch ROE toan nganh va luu cache. Chay trong thread rieng."""
    try:
        _set_api_key()
        symbols = get_symbols_in_industry(industry_group)
        if not symbols:
            return
        symbols = symbols[:max_symbols]

        individual = _load_individual()

        roes = []
        to_fetch = []
        for sym in symbols:
            cached = individual.get(sym)
            if cached is not None:
                if 0 < cached < 100:
                    roes.append(cached)
            else:
                to_fetch.append(sym)

        print(f"  [IndustryFull-bg] {industry_group}: {len(symbols)} ma, "
              f"{len(roes)} cached, {len(to_fetch)} can fetch")

        for i, sym in enumerate(to_fetch):
            roe = _fetch_one_roe(sym)
            if roe and roe > 0:
                roes.append(roe)
                individual[sym] = roe
            else:
                individual[sym] = 0
            _save_individual(individual)

            if (i + 1) % 5 == 0 or (i + 1) == len(to_fetch):
                print(f"    [bg] {i+1}/{len(to_fetch)} (co {len(roes)} ma ROE)")

            time.sleep(3.5)

        if not roes:
            return

        roes_sorted = sorted(roes)
        n = len(roes_sorted)
        result = {
            'industry': industry_group,
            'avg_roe': round(sum(roes) / n, 2),
            'median_roe': round(roes_sorted[n // 2], 2),
            'max_roe': round(max(roes), 2),
            'min_roe': round(min(roes), 2),
            'count': n,
            'total_symbols': len(symbols),
            'source': 'full',
            'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        }

        agg = _load_json(CACHE_FILE) or {}
        items = agg.get('items', {})
        items[industry_group] = result
        _save_json(CACHE_FILE, {'_ts': time.time(), 'items': items})

        print(f"  [IndustryFull-bg] XONG {industry_group}: median={result['median_roe']}%, n={n}")
    except Exception as e:
        print(f"  [IndustryFull-bg] Loi: {e}")
    finally:
        with _fetching_lock:
            _fetching.discard(industry_group)


def compute_industry_roe_full(industry_group, max_symbols=50, force_refresh=False, blocking=False):
    """
    Tra ve ROE toan nganh.
    - Co cache -> tra ngay
    - Chua cache + blocking=True -> fetch dong bo (cho test CLI)
    - Chua cache + blocking=False (default) -> tra fallback ngay + fetch background
    """
    _set_api_key()

    # Check cache
    if not force_refresh:
        cache = _load_json(CACHE_FILE) or {}
        age_hours = (time.time() - cache.get('_ts', 0)) / 3600
        if age_hours <= CACHE_HOURS:
            items = cache.get('items', {})
            if industry_group in items:
                print(f"  [IndustryFull] Cache nganh {industry_group}")
                return items[industry_group]

    # Neu blocking -> fetch dong bo
    if blocking:
        _fetch_and_cache(industry_group, max_symbols)
        cache = _load_json(CACHE_FILE) or {}
        items = cache.get('items', {})
        return items.get(industry_group)

    # Non-blocking: spawn background neu chua fetch
    with _fetching_lock:
        already_fetching = industry_group in _fetching
        if not already_fetching:
            _fetching.add(industry_group)

    if not already_fetching:
        print(f"  [IndustryFull] Bat dau fetch background: {industry_group}")
        threading.Thread(
            target=_fetch_and_cache,
            args=(industry_group, max_symbols),
            daemon=True
        ).start()
    else:
        print(f"  [IndustryFull] Dang fetch {industry_group} (khong spawn them)")

    # Tra fallback ngay
    fb = FALLBACK_MEDIAN.get(industry_group, 10.0)
    return {
        'industry': industry_group,
        'avg_roe': fb,
        'median_roe': fb,
        'max_roe': fb * 1.5,
        'min_roe': fb * 0.5,
        'count': 0,
        'total_symbols': 0,
        'source': 'fallback_pending',
        'note': 'Dang fetch background, lan sau se co so that',
        'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }