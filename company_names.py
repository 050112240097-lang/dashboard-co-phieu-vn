# company_names.py - Tra cuu ten cong ty tu KBS Listing, co cache
import os
import json
import time

CACHE_FILE = 'company_names_cache.json'
CACHE_DAYS = 30

_cache = None


def _load_from_file():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age_days = (time.time() - data.get('_ts', 0)) / 86400
        if age_days > CACHE_DAYS:
            return None
        return data.get('items', {})
    except Exception:
        return None


def _save_to_file(items):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'_ts': time.time(), 'items': items}, f,
                      ensure_ascii=False, indent=2)
    except Exception:
        pass


def _fetch_from_kbs():
    try:
        from vnstock import Listing
        l = Listing(source='kbs')
        df = l.all_symbols()
        if df is None or df.empty:
            return {}
        if 'symbol' not in df.columns or 'organ_name' not in df.columns:
            return {}
        items = {}
        for _, row in df.iterrows():
            sym = str(row['symbol']).strip().upper()
            name = str(row['organ_name']).strip()
            if sym and name and name.lower() != 'nan':
                items[sym] = name
        return items
    except Exception as e:
        print(f"  [CompanyNames] Loi KBS: {str(e)[:100]}")
        return {}


def _ensure_loaded():
    global _cache
    if _cache is not None:
        return _cache

    items = _load_from_file()
    if items:
        print(f"  [CompanyNames] Dung cache ({len(items)} ma)")
        _cache = items
        return _cache

    print(f"  [CompanyNames] Tai lan dau tu KBS...")
    items = _fetch_from_kbs()
    if items:
        _save_to_file(items)
        print(f"  [CompanyNames] Da luu {len(items)} ma vao cache")
    _cache = items
    return _cache


def get_company_name(symbol):
    """Tra cuu ten cong ty. Tra ve None neu khong tim thay."""
    if not symbol:
        return None
    items = _ensure_loaded()
    return items.get(str(symbol).strip().upper())


def get_all():
    return dict(_ensure_loaded())