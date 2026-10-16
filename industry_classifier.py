# industry_classifier.py - Fix: Filter icb_level == 2
import time
import json
import os
from datetime import datetime

CACHE_FILE = 'industries_cache.json'
CACHE_DAYS = 7

# Mapping ICB cap 2 -> nhom tong quat
ICB_MAP = {
    # Tai chinh
    "Ngân hàng": "Tài chính",
    "Dịch vụ tài chính": "Tài chính",
    "Bảo hiểm": "Tài chính",
    "Quỹ đầu tư": "Tài chính",
    "Chứng khoán": "Tài chính",

    # Bat dong san
    "Bất động sản": "Bất động sản",

    # Tieu dung
    "Thực phẩm và đồ uống": "Tiêu dùng thiết yếu",
    "Hàng cá nhân & Gia dụng": "Tiêu dùng thiết yếu",
    "Hàng gia dụng": "Tiêu dùng thiết yếu",
    "Bán lẻ": "Tiêu dùng không thiết yếu",
    "Du lịch và Giải trí": "Tiêu dùng không thiết yếu",
    "Phương tiện truyền thông": "Tiêu dùng không thiết yếu",
    "Ô tô và Phụ tùng": "Tiêu dùng không thiết yếu",

    # Cong nghe
    "Công nghệ Thông tin": "Công nghệ thông tin",
    "Viễn thông": "Công nghệ thông tin",
    "Truyền thông": "Công nghệ thông tin",

    # Cong nghiep
    "Hàng & Dịch vụ Công nghiệp": "Công nghiệp",
    "Xây dựng và Vật liệu": "Công nghiệp",
    "Xây dựng & Vật liệu": "Công nghiệp",
    "Vận tải": "Công nghiệp",

    # Nang luong
    "Dầu khí": "Năng lượng",

    # Tien ich
    "Điện, nước & xăng dầu khí đốt": "Tiện ích",

    # Nguyen lieu
    "Tài nguyên Cơ bản": "Nguyên vật liệu",
    "Hóa chất": "Nguyên vật liệu",

    # Y te
    "Y tế": "Y tế",
    "Dược phẩm và Công nghệ sinh học": "Y tế",
    "Thiết bị và Dịch vụ Y tế": "Y tế",
}

# Mapping thu cong cho cac ma quan trong (fallback)
MANUAL_MAP = {
    "VCB": "Tài chính", "BID": "Tài chính", "CTG": "Tài chính",
    "TCB": "Tài chính", "VPB": "Tài chính", "MBB": "Tài chính",
    "ACB": "Tài chính", "STB": "Tài chính", "HDB": "Tài chính",
    "SHB": "Tài chính", "VIB": "Tài chính", "TPB": "Tài chính",
    "OCB": "Tài chính", "MSB": "Tài chính", "LPB": "Tài chính",
    "SSB": "Tài chính", "NAB": "Tài chính", "EIB": "Tài chính",
    "SSI": "Tài chính", "VND": "Tài chính", "VCI": "Tài chính",
    "HCM": "Tài chính", "MBS": "Tài chính", "SHS": "Tài chính",
    "VDS": "Tài chính", "FTS": "Tài chính", "BVS": "Tài chính",
    "CTS": "Tài chính", "VIX": "Tài chính", "BVH": "Tài chính",

    "VIC": "Bất động sản", "VHM": "Bất động sản", "VRE": "Bất động sản",
    "NVL": "Bất động sản", "KDH": "Bất động sản", "NLG": "Bất động sản",
    "DXG": "Bất động sản", "PDR": "Bất động sản", "DIG": "Bất động sản",
    "HDG": "Bất động sản", "CEO": "Bất động sản", "KBC": "Bất động sản",
    "IDC": "Bất động sản", "SZC": "Bất động sản", "BCM": "Bất động sản",

    "HPG": "Nguyên vật liệu", "HSG": "Nguyên vật liệu", "NKG": "Nguyên vật liệu",
    "DGC": "Nguyên vật liệu", "DPM": "Nguyên vật liệu", "DCM": "Nguyên vật liệu",
    "GVR": "Nguyên vật liệu", "PHR": "Nguyên vật liệu",

    "FPT": "Công nghệ thông tin", "CMG": "Công nghệ thông tin",
    "CTR": "Công nghệ thông tin", "ELC": "Công nghệ thông tin",

    "VNM": "Tiêu dùng thiết yếu", "MSN": "Tiêu dùng thiết yếu",
    "SAB": "Tiêu dùng thiết yếu", "KDC": "Tiêu dùng thiết yếu",
    "QNS": "Tiêu dùng thiết yếu", "MCH": "Tiêu dùng thiết yếu",
    "VHC": "Tiêu dùng thiết yếu", "ANV": "Tiêu dùng thiết yếu",

    "MWG": "Tiêu dùng không thiết yếu", "PNJ": "Tiêu dùng không thiết yếu",
    "DGW": "Tiêu dùng không thiết yếu", "FRT": "Tiêu dùng không thiết yếu",

    "GAS": "Năng lượng", "PLX": "Năng lượng", "PVD": "Năng lượng",
    "PVS": "Năng lượng", "PVT": "Năng lượng", "BSR": "Năng lượng",
    "OIL": "Năng lượng", "PVC": "Năng lượng",

    "POW": "Tiện ích", "NT2": "Tiện ích", "PPC": "Tiện ích",
    "REE": "Tiện ích", "GEG": "Tiện ích", "PC1": "Tiện ích",

    "HVN": "Công nghiệp", "VJC": "Công nghiệp", "GMD": "Công nghiệp",
    "HAH": "Công nghiệp", "VSC": "Công nghiệp", "CII": "Công nghiệp",
    "HHV": "Công nghiệp", "VCG": "Công nghiệp", "CTD": "Công nghiệp",

    "DHG": "Y tế", "IMP": "Y tế", "TRA": "Y tế", "DBD": "Y tế",
}


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = (time.time() - data.get('_ts', 0)) / 86400
        if age > CACHE_DAYS:
            return {}
        print(f"  [Cache] Industry ({age:.1f} ngay)")
        return data.get('items', {})
    except Exception:
        return {}


def save_cache(items):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                '_ts': time.time(),
                '_updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'items': items,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fetch_all_industries_via_listing():
    """
    Lay mapping symbol -> industry tu VCI Listing.
    QUAN TRONG: Filter icb_level == 2 de lay cap trung binh.
    """
    try:
        from vnstock import Listing
        listing = Listing(source='vci')
        df = listing.symbols_by_industries()
        if df is None or df.empty:
            return {}

        print(f"  [Industry] Lay duoc {len(df)} dong tu VCI")

        # QUAN TRONG: Chi lay icb_level == 2
        df_lv2 = df[df['icb_level'] == 2]
        print(f"  [Industry] Sau filter level 2: {len(df_lv2)} dong")

        result = {}
        for _, row in df_lv2.iterrows():
            sym = str(row['symbol']).strip().upper()
            icb = str(row['icb_name']).strip() if row['icb_name'] else None
            if not sym:
                continue
            result[sym] = {
                'symbol': sym,
                'icb': icb,
                'group': ICB_MAP.get(icb, 'Khác') if icb else 'Khác',
            }

        # Thong ke
        from collections import Counter
        groups = Counter(v['group'] for v in result.values())
        print(f"  [Industry] Phan bo: {dict(groups)}")

        return result
    except Exception as e:
        print(f"  [Industry] Loi: {str(e)[:100]}")
        return {}


def fetch_industry(symbol):
    """Fallback: dung manual mapping."""
    group = MANUAL_MAP.get(symbol, 'Khác')
    return {'symbol': symbol, 'icb': None, 'group': group}


def fetch_all_industries(symbols):
    """Lay nganh cho danh sach ma, uu tien manual map truoc."""
    result = {}
    for s in symbols:
        # Uu tien manual map cho cac ma quan trong
        if s in MANUAL_MAP:
            result[s] = {'symbol': s, 'icb': None, 'group': MANUAL_MAP[s]}
        else:
            result[s] = fetch_industry(s)
    return result


def group_by_industry(industries):
    groups = {}
    for sym, info in industries.items():
        g = info.get('group', 'Khác')
        groups.setdefault(g, []).append(sym)
    return groups