# ai_reporter.py - Chi dung Groq
import time
import os

from company_names import get_company_name

try:
    from config import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')


GROQ_MODELS = [
    'openai/gpt-oss-120b',
    'qwen/qwen3-32b',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'openai/gpt-oss-20b',
]

DEFAULT_SYSTEM = "Ban la chuyen gia phan tich chung khoan Viet Nam. Tra loi bang tieng Viet, chuyen nghiep, suc tich."


def _call(prompt, system_msg=None, max_tokens=2500):
    if not GROQ_API_KEY or len(GROQ_API_KEY) < 20:
        return None, 'Chua co GROQ_API_KEY. Lay tai https://console.groq.com/keys'
    if system_msg is None:
        system_msg = DEFAULT_SYSTEM

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
    except ImportError:
        return None, 'Chua cai groq. Chay: pip install groq'
    except Exception as e:
        return None, f'Loi client Groq: {str(e)[:150]}'

    start = time.time()
    last_err = None
    for model in GROQ_MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                text = response.choices[0].message.content
                if text:
                    print(f"  [AI] Groq OK - {model} ({time.time()-start:.1f}s, {len(text)} ky tu)")
                    return text, None
            except Exception as e:
                err = str(e)[:200]
                last_err = f'{model}: {err}'
                err_lower = err.lower()
                if any(k in err_lower for k in ['429', 'rate', '503', 'unavailable', 'timeout']):
                    if attempt < 1:
                        time.sleep(2)
                        continue
                break

    print(f"  [AI] Groq that bai: {str(last_err)[:120]}")
    return None, f'Groq: {last_err}'


# ============================================================
# PUBLIC FUNCTIONS
# ============================================================
def generate_market_overview(top_up, top_down, valuation_data):
    up = ', '.join([f"{s['symbol']} (+{s['pct']:.2f}%)" for s in top_up[:5]])
    down = ', '.join([f"{s['symbol']} ({s['pct']:.2f}%)" for s in top_down[:5]])

    prompt = f"""Ban la chuyen gia phan tich chung khoan Viet Nam.
Viet nhan dinh thi truong ngan (200-250 tu) dua tren du lieu THUC TE. KHONG bia so lieu.

## Du lieu:
- Top tang manh: {up}
- Top giam manh: {down}
- So ma co du lieu: {len(valuation_data)}

## Cau truc:
1. Nhan dinh chung phien giao dich
2. Nhom nganh dan dat / yeu nhat
3. Dong tien
4. Rui ro ngan han

Viet bang tieng Viet, chuyen nghiep."""

    text, err = _call(prompt, max_tokens=800)
    if err:
        return {'error': err, 'report': None}
    return {'error': None, 'report': text}


def generate_stock_report(stock, valuation, industry, question=None):
    sym = stock.get('symbol', '')
    company = get_company_name(sym) or 'KHONG CO DU LIEU'
    extra = ""
    if question:
        extra = f"\n\n## Cau hoi cu the cua nguoi dung:\n{question}\n\nHay tra loi cau hoi nay dua tren du lieu ben tren."

    prompt = f"""Ban la chuyen gia phan tich chung khoan Viet Nam.
Viet bao cao 300-400 tu cho co phieu {sym} dua CHINH XAC tren du lieu. KHONG bia.

⚠️ QUY TAC NGHIEM NGAT:
- KHONG duoc bia ten cong ty, linh vuc kinh doanh, san pham, ban lanh dao.
- Chi su dung thong tin trong "DU LIEU" duoi day.
- Neu khong biet ten cong ty, chi ghi ma {sym}, KHONG tu doan.

## Du lieu:
- Ma: {sym} | San: {stock.get('exchange', 'N/A')}
- Ten cong ty day du: {company}
- Gia: {stock.get('close', 0):,.0f} VND
- Thay doi: {stock.get('pct', 0):+.2f}%
- KL: {stock.get('volume', 0):,}
- Ngoai rong: {stock.get('foreign_net', 0):+,}
- Nganh: {industry.get('group', 'N/A') if industry else 'N/A'}
- P/E: {valuation.get('pe') or 'N/A'}
- P/B: {valuation.get('pb') or 'N/A'}
- ROE: {valuation.get('roe') or 'N/A'}%

## Cau truc: 1.Tong quan 2.Dinh gia 3.Dong tien 4.Rui ro 5.Ket luan
Viet bang tieng Viet.{extra}"""

    text, err = _call(prompt, max_tokens=1200)
    if err:
        return {'error': err, 'report': None}
    return {'error': None, 'report': text, 'symbol': sym}


def generate_deep_analysis_report(symbol, stock, valuation, industry,
                                   roe_analysis, deep_val, question=None):
    company = get_company_name(symbol) or 'KHONG CO DU LIEU'

    dup = roe_analysis.get('dupont', {}) if roe_analysis else {}
    cmp = roe_analysis.get('compare', {}) if roe_analysis else {}
    methods = deep_val.get('methods', {}) if deep_val else {}
    fair_range = deep_val.get('fair_range', {}) if deep_val else {}
    upside = deep_val.get('upside_pct') if deep_val else None

    verdict_map = {
        'undervalued': 'DINH GIA THAP (hap dan)',
        'slightly_undervalued': 'Hoi duoi gia tri hop ly',
        'fair': 'Dung gia tri',
        'slightly_overvalued': 'Hoi cao hon gia tri',
        'overvalued': 'DINH GIA CAO (can than trong)',
    }
    verdict_text = verdict_map.get(deep_val.get('verdict'), 'Khong xac dinh') if deep_val else 'N/A'

    split_note = ''
    if deep_val and deep_val.get('split_adjusted'):
        split_note = f" (da dieu chinh ty le chia thuong {deep_val.get('split_ratio')}x)"

    def _f(v, unit=''):
        if v is None:
            return 'N/A'
        try:
            return f"{float(v):,.1f}{unit}"
        except Exception:
            return 'N/A'

    prompt = f"""Ban la chuyen gia phan tich dau tu co phieu Viet Nam 15 nam kinh nghiem.
Viet bao cao PHAN TICH CHUYEN SAU cho {symbol}, 500-700 tu, dua CHINH XAC tren du lieu. KHONG bia.

⚠️ QUY TAC NGHIEM NGAT:
- TIEU DE PHAI LA: "Bao cao phan tich chuyen sau" (KHONG viet "chuyen sang", "chuyen doi"...)
- KHONG duoc bia ten cong ty, linh vuc kinh doanh, san pham, ban lanh dao.
- KHONG duoc noi "thieu du lieu gia" hay "khong co du lieu nganh" neu 
  thong tin do DA CO trong phan DU LIEU ben duoi.
- Chi su dung thong tin trong "DU LIEU" duoi day.
- Neu mot chi tieu ghi "N/A" thi bo qua, KHONG nhac toi.
- Neu khong biet ten cong ty, chi ghi ma {symbol}, KHONG tu doan.

# DU LIEU CO PHIEU
- Ma: {symbol} | San: {stock.get('exchange', 'N/A')}
- Ten cong ty day du: {company}
- Gia hien tai: {_f(stock.get('close'))} VND ({stock.get('pct', 0):+.2f}%)
- Nganh: {industry.get('group', 'N/A')}

# DINH GIA
- EPS{split_note}: {_f(valuation.get('eps'))} VND
- BVPS{split_note}: {_f(valuation.get('bvps'))} VND
- P/E hien tai: {_f(valuation.get('pe'), 'x')}
- P/B hien tai: {_f(valuation.get('pb'), 'x')}
- Graham Number: {_f(methods.get('graham', {}).get('value'))} VND
- P/E fair: {_f(methods.get('pe_fair', {}).get('value'))} VND
- P/B fair: {_f(methods.get('pb_fair', {}).get('value'))} VND
- Vung gia hop ly: {_f(fair_range.get('min'))} - {_f(fair_range.get('max'))} VND
- Trung vi: {_f(fair_range.get('median'))} VND
- Upside: {_f(upside, '%')}
- Ket luan dinh gia: {verdict_text}

# ROE & DUPONT
- ROE hien tai: {_f(valuation.get('roe'), '%')}
- Ky BCTC: {dup.get('period', 'N/A')}
- Bien LN rong: {_f(dup.get('net_margin') and dup.get('net_margin')*100, '%')}
- Vong quay tai san: {_f(dup.get('asset_turnover'), 'x')}
- Don bay: {_f(dup.get('equity_multiplier'), 'x')}
- ROE Dupont 3 lop: {_f(dup.get('roe_3layer') and dup.get('roe_3layer')*100, '%')}
- ROE Dupont 5 lop: {_f(dup.get('roe_5layer') and dup.get('roe_5layer')*100, '%')}

# SO SANH NGANH
- Nganh: {cmp.get('industry_group', 'N/A')}
- ROE trung vi nganh: {_f(cmp.get('industry_avg_roe'), '%')}
- ROE cao nhat: {_f(cmp.get('industry_max_roe'), '%')}
- ROE thap nhat: {_f(cmp.get('industry_min_roe'), '%')}
- Chenh lech vs trung vi: {_f(cmp.get('diff_vs_avg'), '%')}
- So ma so sanh: {cmp.get('industry_count', 0)}

# CAU TRUC BAO CAO
## 1. Tong quan & luan diem dau tu (2-3 cau)
## 2. Dinh gia — co hap dan khong?
## 3. Chat luong sinh loi ROE (boc tach Dupont)
## 4. Vi the canh tranh (ROE so voi nganh)
## 5. Rui ro chinh (2-3 rui ro cu the)
## 6. Ket luan & khuyen nghi (MUA / NAM GIU / THEO DOI / TRANH)

Viet bang tieng Viet, chuyen nghiep, co so lieu cu the."""

    if question:
        prompt += f"\n\n## Cau hoi cu the:\n{question}\n\nLong ghep cau tra loi vao bao cao."

    text, err = _call(prompt, max_tokens=2500)
    if err:
        return {'error': err, 'report': None}
    return {'error': None, 'report': text, 'symbol': symbol}