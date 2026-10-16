# roe_analyzer.py - Dupont 3 & 5 lop + so sanh ROE nganh (da ho tro ngan hang/CK/BH)
import time
import json
import os
from datetime import datetime
from financial_utils import find_row, get_latest_periods, get_value

CACHE_FILE = 'roe_analysis_cache.json'
CACHE_HOURS = 12


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


# ---- Alias mo rong: san xuat + ngan hang + chung khoan + bao hiem + BDS ----
INCOME_ALIASES = {
    'revenue': [
        # San xuat / thuong mai
        'doanh thu thuần về bán hàng và cung cấp dịch vụ',
        'doanh thu thuần về bán hàng',
        'doanh thu thuần hoạt động kinh doanh',
        'doanh thu thuần',
        # Ngan hang
        'tổng thu nhập hoạt động',
        'thu nhập lãi thuần',
        'tổng thu nhập lãi thuần',
        # Chung khoan
        'doanh thu hoạt động kinh doanh',
        'tổng doanh thu hoạt động',
        # Bao hiem
        'doanh thu thuần hoạt động kinh doanh bảo hiểm',
        'tổng doanh thu',
    ],
    'operating_profit': [
        'lợi nhuận thuần từ hoạt động kinh doanh',
        'lợi nhuận thuần hđkd',
        'lợi nhuận thuần từ hoạt động kinh doanh trước chi phí dự phòng',
        'lợi nhuận thuần hđkd trước chi phí dự phòng rủi ro tín dụng',
        'lợi nhuận từ hoạt động kinh doanh',
    ],
    'ebt': [
        'tổng lợi nhuận kế toán trước thuế',
        'lợi nhuận trước thuế',
        'lợi nhuận trước thuế và chi phí dự phòng',
    ],
    'interest_expense': [
        'trong đó: chi phí đi vay',
        'chi phí lãi vay',
        'chi phí lãi và các chi phí tương tự',
        'chi phí trả lãi và các khoản tương tự',
    ],
    'net_profit': [
        'lợi nhuận sau thuế thu nhập doanh nghiệp',
        'lợi nhuận sau thuế tndn',
        'lợi nhuận sau thuế của cổ đông của công ty mẹ',
        'lợi nhuận sau thuế',
    ],
}

BALANCE_ALIASES = {
    'total_assets': [
        'tổng cộng tài sản',
        'tổng tài sản',
    ],
    'equity': [
        'vốn chủ sở hữu',
        'vốn và các quỹ',
        'vốn chủ sở hữu của cổ đông công ty mẹ',
        'owners equity',
    ],
}


# ============================================================
# DUPONT
# ============================================================
def compute_dupont(symbol, period='year'):
    try:
        from vnstock import Finance
        fin = Finance(symbol=symbol, source='kbs')
        income = fin.income_statement(period=period, lang='vi')
        balance = fin.balance_sheet(period=period, lang='vi')
    except Exception as e:
        return {'error': f'Khong lay duoc BCTC: {str(e)[:120]}'}

    if income is None or income.empty or balance is None or balance.empty:
        return {'error': 'BCTC rong'}

    inc_periods = get_latest_periods(income, n=2)
    bal_periods = get_latest_periods(balance, n=1)
    if not inc_periods or not bal_periods:
        return {'error': 'Khong tim thay cot ky'}

    latest_col = inc_periods[0]
    bal_col = bal_periods[0]

    rev_row = find_row(income, INCOME_ALIASES['revenue'])
    op_row = find_row(income, INCOME_ALIASES['operating_profit'])
    ebt_row = find_row(income, INCOME_ALIASES['ebt'])
    int_row = find_row(income, INCOME_ALIASES['interest_expense'])
    np_row = find_row(income, INCOME_ALIASES['net_profit'])

    ta_row = find_row(balance, BALANCE_ALIASES['total_assets'])
    eq_row = find_row(balance, BALANCE_ALIASES['equity'])

    missing = []
    if rev_row is None: missing.append('revenue')
    if ebt_row is None: missing.append('ebt')
    if np_row is None: missing.append('net_profit')
    if ta_row is None: missing.append('total_assets')
    if eq_row is None: missing.append('equity')

    if missing:
        return {
            'error': f'Thieu chi tieu: {missing}',
            'partial': True,
            'missing': missing,
        }

    revenue = get_value(rev_row, latest_col)
    ebt = get_value(ebt_row, latest_col)
    net_profit = get_value(np_row, latest_col)
    total_assets = get_value(ta_row, bal_col)
    equity = get_value(eq_row, bal_col)

    if not all([revenue, ebt, net_profit, total_assets, equity]):
        return {'error': 'Du lieu khong day du', 'partial': True}
    if revenue == 0 or equity == 0 or total_assets == 0:
        return {'error': 'Chia cho 0', 'partial': True}

    net_margin = net_profit / revenue
    asset_turnover = revenue / total_assets
    equity_multiplier = total_assets / equity
    roe_3 = net_margin * asset_turnover * equity_multiplier

    result = {
        'period': str(latest_col),
        'revenue': revenue,
        'ebt': ebt,
        'net_profit': net_profit,
        'total_assets': total_assets,
        'equity': equity,
        'net_margin': round(net_margin, 4),
        'asset_turnover': round(asset_turnover, 4),
        'equity_multiplier': round(equity_multiplier, 4),
        'roe_3layer': round(roe_3, 4),
        'partial': False,
    }

    op_profit = get_value(op_row, latest_col) if op_row is not None else None
    interest = get_value(int_row, latest_col) if int_row is not None else 0
    ebit = (op_profit + interest) if (op_profit is not None and interest) else op_profit

    if ebit and ebit != 0 and ebt and ebt != 0:
        result['tax_burden'] = round(net_profit / ebt, 4)
        result['interest_burden'] = round(ebt / ebit, 4)
        result['operating_margin'] = round(ebit / revenue, 4)
        roe_5 = (result['tax_burden'] * result['interest_burden'] *
                 result['operating_margin'] * asset_turnover * equity_multiplier)
        result['roe_5layer'] = round(roe_5, 4)

    return result


# ============================================================
# SO SANH NGANH
# ============================================================
def compare_roe_vs_industry(symbol, stock_roe, industry_group, industry_roe_data):
    if stock_roe is None or industry_group is None:
        return {'error': 'Thieu du lieu so sanh'}

    ind = industry_roe_data.get(industry_group)
    if not ind:
        return {'error': f'Khong co du lieu ROE nganh {industry_group}'}

    avg = ind.get('avg_roe')
    mx = ind.get('max_roe')
    mn = ind.get('min_roe')
    cnt = ind.get('count', 0)

    diff = stock_roe - avg if avg is not None else None

    rank_pct = None
    if mx is not None and mn is not None and mx != mn:
        raw = (stock_roe - mn) / (mx - mn) * 100
        rank_pct = round(max(0.0, min(100.0, raw)), 1)

    if diff is None:
        verdict = 'unknown'
    elif diff > 5:
        verdict = 'outperform'
    elif diff > 0:
        verdict = 'above_avg'
    elif diff > -3:
        verdict = 'slightly_below'
    else:
        verdict = 'underperform'

    return {
        'stock_roe': stock_roe,
        'industry_group': industry_group,
        'industry_avg_roe': avg,
        'industry_max_roe': mx,
        'industry_min_roe': mn,
        'industry_count': cnt,
        'industry_source': ind.get('source', 'unknown'),
        'diff_vs_avg': round(diff, 2) if diff is not None else None,
        'rank_pct_in_range': rank_pct,
        'verdict': verdict,
    }


# ============================================================
# TONG HOP
# ============================================================
def analyze_roe_full(symbol, stock_roe, industry_group, industry_roe_data, use_cache=True):
    cache = load_cache() if use_cache else {}
    if use_cache and symbol in cache:
        return cache[symbol]

    dupont = compute_dupont(symbol)
    compare = compare_roe_vs_industry(symbol, stock_roe, industry_group, industry_roe_data)
    commentary = _build_commentary(symbol, dupont, compare)

    result = {
        'symbol': symbol,
        'dupont': dupont,
        'compare': compare,
        'commentary': commentary,
        'updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }

    if use_cache:
        cache[symbol] = result
        save_cache(cache)

    return result


def _build_commentary(symbol, dupont, compare):
    lines = []

    if 'error' in dupont:
        err = dupont['error']
        if 'Thieu chi tieu' in err:
            lines.append(
                f"⚠️ Không thể phân tích Dupont đầy đủ cho {symbol} "
                f"(BCTC có cấu trúc đặc thù — thường gặp ở ngân hàng, chứng khoán, bảo hiểm). "
                f"Vui lòng dùng chỉ số ROE tổng hợp ở phần so sánh ngành."
            )
        else:
            lines.append(f"⚠️ Không thể phân tích Dupont: {err}")
    else:
        nm = dupont.get('net_margin', 0)
        at = dupont.get('asset_turnover', 0)
        em = dupont.get('equity_multiplier', 0)
        roe = dupont.get('roe_3layer', 0)

        drivers = []
        if nm > 0.20:
            drivers.append(f"biên LN ròng rất cao ({nm:.1%})")
        elif nm > 0.12:
            drivers.append(f"biên LN ròng tốt ({nm:.1%})")
        elif nm < 0.05:
            drivers.append(f"biên LN ròng mỏng ({nm:.1%})")

        if at > 1.5:
            drivers.append(f"vòng quay tài sản nhanh ({at:.2f}x)")
        elif at > 0.5:
            drivers.append(f"vòng quay tài sản trung bình ({at:.2f}x)")
        else:
            drivers.append(f"vòng quay tài sản chậm ({at:.2f}x)")

        if em > 4:
            drivers.append(f"đòn bẩy cao ({em:.2f}x)")
        elif em > 2.5:
            drivers.append(f"đòn bẩy trung bình ({em:.2f}x)")
        elif em < 1.5:
            drivers.append(f"đòn bẩy thấp ({em:.2f}x)")

        if drivers:
            lines.append(f"ROE {roe:.1%} đến từ: " + ", ".join(drivers) + ".")

        if em > 4:
            lines.append("⚠️ ROE phần lớn được đẩy lên bởi đòn bẩy tài chính — cần kiểm tra khả năng trả lãi và cấu trúc nợ.")
        if nm < 0.02 and at > 1.5:
            lines.append("📌 Mô hình kinh doanh biên mỏng nhưng quay vòng nhanh (đặc trưng bán lẻ / phân phối).")
        if nm > 0.25 and em < 2:
            lines.append("💎 Biên LN ròng cao + đòn bẩy thấp = mô hình kinh doanh chất lượng cao, ít rủi ro.")

    if 'error' not in compare:
        diff = compare['diff_vs_avg']
        avg = compare['industry_avg_roe']
        verdict = compare['verdict']
        src = compare.get('industry_source', 'unknown')
        vmap = {
            'outperform': f"vượt trội so với trung bình ngành ({avg}%)",
            'above_avg': f"cao hơn trung bình ngành ({avg}%)",
            'slightly_below': f"thấp hơn nhẹ so với trung bình ngành ({avg}%)",
            'underperform': f"thua kém trung bình ngành ({avg}%)",
        }
        lines.append(
            f"Xếp hạng ROE trong ngành {compare['industry_group']}: "
            f"{vmap.get(verdict, 'không xác định')} — chênh lệch {diff:+.2f}%."
        )

        rp = compare.get('rank_pct_in_range')
        if rp is not None:
            if rp >= 100:
                pos = "dẫn đầu ngành"
            elif rp >= 75:
                pos = f"top {100 - rp:.0f}% ngành"
            elif rp >= 50:
                pos = "trên trung vị ngành"
            elif rp >= 25:
                pos = "dưới trung vị ngành"
            else:
                pos = "nhóm thấp nhất ngành"
            lines.append(f"Vị trí trong ngành ({compare['industry_count']} mã): {pos}.")

        if src == 'fallback_pending':
            lines.append(
                "ℹ️ Số liệu ngành đang dùng giá trị mặc định. Hệ thống đang tải dữ liệu thật "
                "(mất 3-5 phút) — các lần phân tích sau sẽ chính xác hơn."
            )

    return "\n".join(lines)