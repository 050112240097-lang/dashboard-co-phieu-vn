# scoring.py - Cham diem tong hop 4 nhom (giong bao cao tham khao)
import os
try:
    from hf_compat import get_path as _hf_path
except ImportError:
    _hf_path = lambda x: x
import json
from datetime import datetime

CACHE_FILE = _hf_path('scoring_cache.json')


def _safe_get(d, key, default=None):
    if not d:
        return default
    v = d.get(key)
    return v if v is not None else default


def _score_technical(ta):
    """
    Ky thuat: gia vs MA50 + slope MA20.
    Tra ve (score, ly_do)
    """
    if not ta:
        return 0, 'Không có dữ liệu kỹ thuật'
    close = ta.get('close')
    ma50 = ta.get('ma50')
    signal = ta.get('signal')

    if not close or not ma50:
        return 0, 'Thiếu giá hoặc MA50'

    if close > ma50 and signal == 'Tăng':
        return 1, f'Giá {close:,.0f} > MA50 {ma50:,.0f}, xu hướng tăng'
    elif close < ma50 and signal == 'Giảm':
        return -1, f'Giá {close:,.0f} < MA50 {ma50:,.0f}, xu hướng giảm'
    else:
        return 0, 'Xu hướng trung tính'


def _score_fundamental(valuation, industry_roe_data, industry_group):
    """
    Co ban: ROE so voi trung vi nganh.
    """
    roe = _safe_get(valuation, 'roe')
    if not roe:
        return 0, 'Không có dữ liệu ROE'

    ind = (industry_roe_data or {}).get(industry_group)
    if not ind:
        return 0, f'Không có ROE ngành {industry_group}'

    ind_median = ind.get('median_roe') or ind.get('avg_roe')
    if not ind_median:
        return 0, 'Không có ROE trung vị ngành'

    diff = roe - ind_median
    if diff > 5:
        return 1, f'ROE {roe:.1f}% > trung vị ngành {ind_median:.1f}% (chênh +{diff:.1f}%)'
    elif diff < -3:
        return -1, f'ROE {roe:.1f}% < trung vị ngành {ind_median:.1f}% (chênh {diff:.1f}%)'
    else:
        return 0, f'ROE {roe:.1f}% tương đương ngành {ind_median:.1f}%'


def _score_valuation(valuation, close_price, ctck_data, industry_pe_median=None):
    """
    Dinh gia: P/E vs nganh + CTCK target vs gia.
    """
    pe = _safe_get(valuation, 'pe')
    target = None
    if ctck_data:
        target = ctck_data.get('avg_target')

    reasons = []
    score = 0

    # 1) So P/E voi nganh
    if pe and industry_pe_median:
        if pe < industry_pe_median * 0.8:
            score += 1
            reasons.append(f'P/E {pe:.1f}x rẻ hơn ngành {industry_pe_median:.1f}x')
        elif pe > industry_pe_median * 1.3:
            score -= 1
            reasons.append(f'P/E {pe:.1f}x đắt hơn ngành {industry_pe_median:.1f}x')

    # 2) So CTCK target voi gia
    if target and close_price and close_price > 0:
        upside = (target - close_price) / close_price * 100
        if upside > 15:
            score += 1
            reasons.append(f'CTCK target {target:,.0f} cao hơn giá {upside:.1f}%')
        elif upside < -10:
            score -= 1
            reasons.append(f'CTCK target {target:,.0f} thấp hơn giá {upside:.1f}%')

    if not reasons:
        return 0, 'Không đủ dữ liệu định giá'

    # Clamp
    score = max(-1, min(1, score))
    return score, ' | '.join(reasons)


def _score_news(rss_news, symbol):
    """
    Tin tuc: positive >= 2x negative -> +1, nguoc lai -> -1.
    """
    if not rss_news:
        return 0, 'Không có dữ liệu tin tức'

    symbol_upper = symbol.upper()
    matched = []
    for n in rss_news:
        title = (n.get('title') or '').upper()
        if symbol_upper in title:
            matched.append(n)

    if not matched:
        return 0, 'Không có tin về mã này'

    pos = sum(1 for n in matched if n.get('sentiment_label') == 'positive')
    neg = sum(1 for n in matched if n.get('sentiment_label') == 'negative')
    neutral = len(matched) - pos - neg

    if pos >= 2 * max(neg, 1) and pos > 0:
        return 1, f'{pos} tin tích cực / {neg} tiêu cực / {neutral} trung lập'
    elif neg >= 2 * max(pos, 1) and neg > 0:
        return -1, f'{pos} tin tích cực / {neg} tiêu cực / {neutral} trung lập'
    else:
        return 0, f'{pos} tin tích cực / {neg} tiêu cực / {neutral} trung lập'


def compute_score(symbol, valuation, ta, industry_group, industry_roe_data,
                  ctck_data, rss_news, close_price, industry_pe_median=None):
    """
    Tinh diem tong hop cho 1 ma.
    Tra ve dict:
      - total: tong diem (-4 to +4)
      - label: 'positive' / 'neutral' / 'negative'
      - label_vn: 'Tích cực' / 'Trung lập' / 'Tiêu cực'
      - parts: chi tiet tung nhom
    """
    s_tech, r_tech = _score_technical(ta)
    s_fund, r_fund = _score_fundamental(valuation, industry_roe_data, industry_group)
    s_val, r_val = _score_valuation(valuation, close_price, ctck_data, industry_pe_median)
    s_news, r_news = _score_news(rss_news, symbol)

    total = s_tech + s_fund + s_val + s_news

    if total >= 2:
        label = 'positive'
        label_vn = 'Tích cực'
    elif total <= -2:
        label = 'negative'
        label_vn = 'Tiêu cực'
    else:
        label = 'neutral'
        label_vn = 'Trung lập'

    return {
        'symbol': symbol,
        'total': total,
        'label': label,
        'label_vn': label_vn,
        'parts': {
            'technical': {'score': s_tech, 'reason': r_tech},
            'fundamental': {'score': s_fund, 'reason': r_fund},
            'valuation': {'score': s_val, 'reason': r_val},
            'news': {'score': s_news, 'reason': r_news},
        },
        'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }


def compute_all_scores(stock_data_map, valuation_map, technical_map,
                      industry_map, industry_roe_data, ctck_map, rss_news):
    """
    Tinh diem cho TAT CA cac ma.
    Tra ve dict: {symbol: score_result}
    """
    print(f"  [Scoring] Dang cham diem cho {len(stock_data_map)} ma...")

    # Tinh trung vi P/E theo nganh
    industry_pe_values = {}
    for sym, v in valuation_map.items():
        ind = (industry_map.get(sym) or {}).get('group')
        pe = v.get('pe') if v else None
        if ind and pe and 0 < pe < 100:
            industry_pe_values.setdefault(ind, []).append(pe)

    industry_pe_median = {}
    for ind, values in industry_pe_values.items():
        if values:
            sorted_v = sorted(values)
            industry_pe_median[ind] = sorted_v[len(sorted_v) // 2]

    results = {}
    for sym in stock_data_map.keys():
        v = valuation_map.get(sym) or {}
        ta = technical_map.get(sym) or {}
        ind = (industry_map.get(sym) or {}).get('group') or 'Khác'
        ctck = ctck_map.get(sym) if ctck_map else None
        stock = stock_data_map.get(sym) or {}
        close = stock.get('close') or ta.get('close') or 0

        results[sym] = compute_score(
            sym, v, ta, ind, industry_roe_data, ctck, rss_news,
            close, industry_pe_median.get(ind)
        )

    # Thong ke
    pos = sum(1 for r in results.values() if r['label'] == 'positive')
    neg = sum(1 for r in results.values() if r['label'] == 'negative')
    neu = len(results) - pos - neg
    print(f"  [Scoring] +{pos} tích cực | {neu} trung lập | -{neg} tiêu cực")

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
            return json.load(f).get('items', {})
    except Exception:
        return {}


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    # Test voi du lieu gia lap
    valuation = {'pe': 13.1, 'pb': 2.83, 'roe': 27.1}
    ta = {'close': 60200, 'ma50': 64543, 'signal': 'Giảm'}
    ind_roe = {'Công nghệ thông tin': {'median_roe': 12.3}}
    ctck = {'avg_target': 95000}
    rss = [
        {'title': 'FPT tăng mạnh sau khi công bố lợi nhuận', 'sentiment_label': 'positive'},
        {'title': 'FPT mở rộng thị trường AI', 'sentiment_label': 'positive'},
        {'title': 'FPT điều chỉnh nhẹ', 'sentiment_label': 'neutral'},
    ]
    result = compute_score('FPT', valuation, ta, 'Công nghệ thông tin', ind_roe, ctck, rss, 60200, 13.19)
    print(json.dumps(result, ensure_ascii=False, indent=2))