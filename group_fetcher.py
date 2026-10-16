# group_fetcher.py - Lay danh sach ma theo nhom (co fallback)
import pandas as pd


# ============================================================
# FALLBACK LISTS (public, co the verify tren SSI/Fireant)
# ============================================================

# VN30 - 30 ma von hoa lon nhat HOSE
VN30_FALLBACK = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR",
    "HDB", "HPG", "MBB", "MSN", "MWG", "PLX", "POW", "SAB",
    "SHB", "SSB", "SSI", "STB", "TCB", "TPB", "VCB", "VIB",
    "VIC", "VHM", "VJC", "VNM", "VPB", "VRE"
]

# VN100 - Top 100 ma von hoa lon nhat HOSE (VN30 + 70 ma midcap)
VN100_FALLBACK = VN30_FALLBACK + [
    "AAA", "ANV", "ASM", "BCG", "BHN", "BWE", "CII", "CMG",
    "CTR", "CTS", "DBC", "DCM", "DGC", "DGW", "DHC", "DIG",
    "DPM", "DPR", "DXG", "EIB", "EVF", "FRT", "FTS", "GEX",
    "GMD", "HAG", "HCM", "HDG", "HHV", "HT1", "IMP", "KBC",
    "KDH", "KOS", "LPB", "MSB", "NKG", "NLG", "NT2", "NVL",
    "OCB", "PAN", "PC1", "PDR", "PET", "PHR", "PNJ", "PVD",
    "PVT", "REE", "SBT", "SCR", "SJS", "SZC", "TCH", "VCI",
    "VHC", "VND", "VPI", "VSC", "VSH", "BMP", "BMI", "BTP",
    "C47", "CKG", "CRC", "CSV", "FMC", "GIL", "HTN", "IDI",
]

# VNDIAMOND - 18-22 ma chat luong cao nhat (co thanh khoan + co ban tot)
VNDIAMOND_FALLBACK = [
    "ACB", "BID", "CTG", "FPT", "GAS", "HDB", "HPG", "MBB",
    "MSB", "MWG", "PNJ", "REE", "SSI", "STB", "TCB", "TPB",
    "VCB", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]


def fetch_symbol_groups():
    """
    Lay danh sach ma theo cac nhom quan trong.
    Thu API truoc, neu that bai thi dung fallback.
    """
    groups = {}

    try:
        from vnstock import Listing
        listing = Listing(source='vci')

        print("  [Group] Thu lay tu API vnstock...")

        # ==== VN30 ====
        try:
            df = listing.symbols_by_group('VN30')
            if df is not None and not df.empty:
                code_col = next(
                    (c for c in ['symbol', 'ticker', 'code'] if c in df.columns),
                    df.columns[0]
                )
                groups['VN30'] = sorted([str(s).strip().upper() for s in df[code_col].dropna().unique()])
                print(f"  [Group] VN30 tu API: {len(groups['VN30'])} ma")
            else:
                groups['VN30'] = VN30_FALLBACK.copy()
                print(f"  [Group] VN30 fallback: {len(groups['VN30'])} ma")
        except Exception as e:
            groups['VN30'] = VN30_FALLBACK.copy()
            print(f"  [Group] VN30 fallback (API loi: {str(e)[:40]}): {len(groups['VN30'])} ma")

        # ==== VN100 ====
        try:
            df = listing.symbols_by_group('VN100')
            if df is not None and not df.empty:
                code_col = next(
                    (c for c in ['symbol', 'ticker', 'code'] if c in df.columns),
                    df.columns[0]
                )
                groups['VN100'] = sorted([str(s).strip().upper() for s in df[code_col].dropna().unique()])
                print(f"  [Group] VN100 tu API: {len(groups['VN100'])} ma")
            else:
                groups['VN100'] = VN100_FALLBACK.copy()
                print(f"  [Group] VN100 fallback: {len(groups['VN100'])} ma")
        except Exception as e:
            groups['VN100'] = VN100_FALLBACK.copy()
            print(f"  [Group] VN100 fallback (API loi: {str(e)[:40]}): {len(groups['VN100'])} ma")

        # ==== VNDIAMOND ====
        try:
            df = listing.symbols_by_group('VNDIAMOND')
            if df is not None and not df.empty:
                code_col = next(
                    (c for c in ['symbol', 'ticker', 'code'] if c in df.columns),
                    df.columns[0]
                )
                groups['VNDIAMOND'] = sorted([str(s).strip().upper() for s in df[code_col].dropna().unique()])
                print(f"  [Group] VNDIAMOND tu API: {len(groups['VNDIAMOND'])} ma")
            else:
                groups['VNDIAMOND'] = VNDIAMOND_FALLBACK.copy()
                print(f"  [Group] VNDIAMOND fallback: {len(groups['VNDIAMOND'])} ma")
        except Exception as e:
            groups['VNDIAMOND'] = VNDIAMOND_FALLBACK.copy()
            print(f"  [Group] VNDIAMOND fallback (API loi: {str(e)[:40]}): {len(groups['VNDIAMOND'])} ma")

        # ==== NHOM THEO SAN (HOSE, HNX, UPCOM) ====
        try:
            df_ex = listing.symbols_by_exchange()
            if df_ex is not None and not df_ex.empty:
                sym_col = next(
                    (c for c in ['symbol', 'ticker', 'code'] if c in df_ex.columns),
                    'symbol'
                )
                exch_col = next(
                    (c for c in ['exchange', 'san', 'board'] if c in df_ex.columns),
                    'exchange'
                )
                for exch in ['HOSE', 'HNX', 'UPCOM']:
                    sub = df_ex[df_ex[exch_col].astype(str).str.upper() == exch]
                    if not sub.empty:
                        symbols = [str(s).strip().upper() for s in sub[sym_col].dropna().unique()]
                        groups[exch] = sorted(symbols)
                        print(f"  [Group] {exch}: {len(symbols)} ma")
        except Exception as e:
            print(f"  [Group] Exchange API loi: {str(e)[:60]}")

    except Exception as e:
        print(f"  [Group] Loi tong: {str(e)[:80]}")
        # Neu import vnstock loi, dung tat ca fallback
        groups['VN30'] = VN30_FALLBACK.copy()
        groups['VN100'] = VN100_FALLBACK.copy()
        groups['VNDIAMOND'] = VNDIAMOND_FALLBACK.copy()

    # Dam bao co 3 nhom chinh
    if 'VN30' not in groups or not groups['VN30']:
        groups['VN30'] = VN30_FALLBACK.copy()
    if 'VN100' not in groups or not groups['VN100']:
        groups['VN100'] = VN100_FALLBACK.copy()
    if 'VNDIAMOND' not in groups or not groups['VNDIAMOND']:
        groups['VNDIAMOND'] = VNDIAMOND_FALLBACK.copy()

    print(f"  [Group] Tong cong {len(groups)} nhom")
    return groups