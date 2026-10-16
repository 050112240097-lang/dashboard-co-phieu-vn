# ctck_analyzer.py - Trich xuat khuyen nghi CTCK tu tieu de bao cao (co validate ticker)
import re
import json
import os
try:
    from hf_compat import get_path as _hf_path
except ImportError:
    _hf_path = lambda x: x
from datetime import datetime

CACHE_FILE = _hf_path('ctck_analyzer_cache.json')
VALID_SYMBOLS_FILE = _hf_path('valid_symbols.json')


SOURCE_SHORT = {
    'SSI Research': 'SSI', 'VNDIRECT': 'VND', 'MBS': 'MBS', 'VCBS': 'VCBS',
    'BSC': 'BSC', 'Vietcap': 'VCI', 'HSC': 'HSC', 'FPTS': 'FPTS',
    'VDSC': 'VDSC', 'SHS': 'SHS', 'Nguoi Quan Sat': 'NQS', 'Lang Tu': 'LT',
}

RECO_PATTERNS = [
    (r'\b(?:khuyến nghị|khuyen nghi|recommend(?:ation)?)[:\s]+(mua mạnh|mua|tích cực|nắm giữ|trung lập|giảm tỷ trọng|bán|tiêu cực)\b', 'explicit'),
    (r'\b(mua mạnh|strong buy)\b', 'strong_buy'),
    (r'\b(mua|buy)\b', 'buy'),
    (r'\b(nắm giữ|hold|trung lập)\b', 'hold'),
    (r'\b(giảm tỷ trọng|bán|sell|reduce)\b', 'sell'),
]

TARGET_PATTERNS = [
    r'(?:giá mục tiêu|gia muc tieu|target(?:\s*price)?|mục tiêu)[:\s]+([0-9][0-9\.,]+)\s*(?:đồng|đ|vnd|VND|nghìn|nghin|k|K)?',
    r'(?:lên|tăng lên|về|tới)\s+([0-9][0-9\.,]+)\s*(?:đồng|đ|vnd|VND)',
    r'(?:giá mục tiêu mới|target mới)[:\s]+([0-9][0-9\.,]+)',
]

TICKER_PATTERN = r'\b([A-Z]{3,4})\b'


def _load_valid_symbols():
    """Lay danh sach ma co phieu that tu stock_data.xlsx."""
    if os.path.exists(VALID_SYMBOLS_FILE):
        try:
            with open(VALID_SYMBOLS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('items'):
                return set(data['items'])
        except Exception:
            pass
    # Fallback: doc tu Excel
    try:
        import pandas as pd
        df = pd.read_excel('stock_data.xlsx')
        if 'symbol' in df.columns:
            symbols = set(str(s).strip().upper() for s in df['symbol'].dropna().unique())
            try:
                with open(VALID_SYMBOLS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({'items': list(symbols), '_ts': datetime.now().isoformat()}, f, ensure_ascii=False)
            except Exception:
                pass
            return symbols
    except Exception:
        pass
    return set()


_VALID_SYMBOLS = None


def _get_valid_symbols():
    global _VALID_SYMBOLS
    if _VALID_SYMBOLS is None:
        _VALID_SYMBOLS = _load_valid_symbols()
        print(f"  [CTCK] Load {len(_VALID_SYMBOLS)} ma hop le")
    return _VALID_SYMBOLS


def _parse_price(s):
    if not s:
        return None
    s = s.strip().replace(' ', '')
    s = re.sub(r'(đồng|đ|vnd|VND|nghìn|nghin|k|K)$', '', s)
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        if len(s.split(',')[-1]) == 3:
            s = s.replace(',', '')
        else:
            s = s.replace(',', '.')
    elif '.' in s:
        if len(s.split('.')[-1]) == 3:
            s = s.replace('.', '')
    try:
        v = float(s)
        if 0 < v < 1000:
            v = v * 1000
        return int(v)
    except Exception:
        return None


def _extract_recommendation(text):
    t = text.lower()
    for pattern, kind in RECO_PATTERNS:
        m = re.search(pattern, t)
        if m:
            if kind == 'explicit':
                reco = m.group(1)
            else:
                reco = kind
            reco_lower = reco.lower()
            if 'mua mạnh' in reco_lower or 'strong_buy' in reco_lower or reco_lower == 'strong buy':
                return 'MUA MẠNH', 2
            if 'mua' in reco_lower or reco_lower == 'buy' or 'tích cực' in reco_lower:
                return 'MUA', 1
            if 'nắm giữ' in reco_lower or 'hold' in reco_lower or 'trung lập' in reco_lower:
                return 'NẮM GIỮ', 0
            if 'giảm tỷ trọng' in reco_lower or 'bán' in reco_lower or 'sell' in reco_lower or 'reduce' in reco_lower or 'tiêu cực' in reco_lower:
                return 'BÁN', -1
    return None, None


def _extract_target_price(text):
    for pattern in TARGET_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            price = _parse_price(m.group(1))
            if price and 1000 <= price <= 10_000_000:
                return price
    return None


def _extract_tickers(text):
    """Tim ticker va CHI tra ve ma co trong danh sach hop le."""
    valid = _get_valid_symbols()
    tickers = []
    for m in re.finditer(TICKER_PATTERN, text):
        t = m.group(1)
        # Chi accept neu la ma that
        if valid and t not in valid:
            continue
        if not valid:
            # Fallback: loc thu cong
            NON = {'SSI','MBS','BSC','HSC','VND','VCI','VCBS','FPTS','VDSC','SHS',
                   'NQS','LT','VN','USD','GDP','CPI','FED','ETF','IPO','Q1','Q2','Q3','Q4',
                   'HNX','HSX','HOSE','UPCOM','VNINDEX','VNI','ROE','ROA','PE','PB','EPS',
                   'MUA','BAN','QUAN','THEO','DOI','VAO','RA','LEN','XUONG','TANG','GIAM',
                   'CAO','THAP','VUA','MOI','CUC','SIEU','HOT','TOP','SO','CO','TAI','CUA'}
            if t in NON:
                continue
        if t not in tickers:
            tickers.append(t)
    return tickers[:3]


def analyze_reports(reports):
    result = {}

    for r in reports:
        title = r.get('title', '')
        source_raw = r.get('source', '')
        source = SOURCE_SHORT.get(source_raw, source_raw)
        date = r.get('date', '')
        url = r.get('url', '')

        tickers = _extract_tickers(title)
        reco, reco_score = _extract_recommendation(title)
        target = _extract_target_price(title)

        if not tickers or (reco is None and target is None):
            continue

        for ticker in tickers:
            if ticker not in result:
                result[ticker] = {
                    'symbol': ticker,
                    'recommendations': [],
                    'avg_target': None, 'max_target': None, 'min_target': None,
                    'buy_count': 0, 'hold_count': 0, 'sell_count': 0,
                    'total_reports': 0,
                    'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                }
            entry = {
                'source': source, 'source_full': source_raw,
                'reco': reco, 'target': target, 'date': date,
                'title': title, 'url': url,
            }
            result[ticker]['recommendations'].append(entry)
            result[ticker]['total_reports'] += 1

            if reco in ('MUA MẠNH', 'MUA'):
                result[ticker]['buy_count'] += 1
            elif reco == 'NẮM GIỮ':
                result[ticker]['hold_count'] += 1
            elif reco == 'BÁN':
                result[ticker]['sell_count'] += 1

    for sym, info in result.items():
        targets = [r['target'] for r in info['recommendations'] if r['target']]
        if targets:
            info['avg_target'] = int(sum(targets) / len(targets))
            info['max_target'] = max(targets)
            info['min_target'] = min(targets)
        info['recommendations'].sort(
            key=lambda x: (x.get('date') or '', x.get('source') or ''),
            reverse=True
        )

    return result


def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'_ts': datetime.now().isoformat(), 'items': data}, f,
                      ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [CTCK] Loi save cache: {e}")


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('items', {})
    except Exception:
        return {}


if __name__ == '__main__':
    test_reports = [
        {'title': 'PNJ - Khuyến nghị MUA, giá mục tiêu 95.000 đồng', 'source': 'SSI Research', 'date': '15/10/2026', 'url': '#'},
        {'title': 'Cập nhật PNJ: Nắm giữ, target 89.000', 'source': 'MBS', 'date': '14/10/2026', 'url': '#'},
        {'title': 'HPG - Khuyến nghị BÁN, giá mục tiêu 22.500', 'source': 'BSC', 'date': '12/10/2026', 'url': '#'},
        {'title': 'Doanh nghiệp bất động sản hút vốn', 'source': 'CafeF', 'date': '10/10/2026', 'url': '#'},
    ]
    result = analyze_reports(test_reports)
    print(f"\n=== {len(result)} ma ===\n")
    for sym, info in result.items():
        print(f"--- {sym} ---")
        print(f"  Total: {info['total_reports']} | Buy: {info['buy_count']} | Hold: {info['hold_count']} | Sell: {info['sell_count']}")
        if info['avg_target']:
            print(f"  Target TB: {info['avg_target']:,}")
        for r in info['recommendations']:
            print(f"    [{r['source']}] {r['reco'] or '?'} | {r['target'] or '?'} | {r['title'][:60]}")