# debug_val.py - Kiem tra du lieu thuc te tu API
import os
from config import VNSTOCK_API_KEY
os.environ['VNSTOCK_API_KEY'] = VNSTOCK_API_KEY

import warnings
warnings.filterwarnings('ignore')

from valuation_analyzer import fetch_ratio
from industry_classifier import fetch_industry

# Test 3 ma thanh khoan cao
symbols = ['HPG', 'SHB', 'TCB']

print("=" * 70)
print("  DEBUG VALUATION & INDUSTRY")
print("=" * 70)

for sym in symbols:
    print(f"\n{'─' * 70}")
    print(f"  MA: {sym}")
    print(f"{'─' * 70}")

    # Test valuation
    print("\n[1] VALUATION - Finance.ratio():")
    try:
        from vnstock import Finance
        fin = Finance(symbol=sym, source='kbs')
        df = fin.ratio(period='Q', lang='vi')
        if df is not None and not df.empty:
            print(f"    Cot: {list(df.columns)}")
            print(f"    Dong 0:")
            for c in df.columns:
                v = df.iloc[0][c]
                print(f"      {c} = {v}")
        else:
            print("    -> EMPTY")
    except Exception as e:
        print(f"    -> LOI: {e}")

    # Test Company.overview
    print("\n[2] VALUATION - Company.overview():")
    try:
        from vnstock import Company
        comp = Company(symbol=sym, source='kbs')
        ov = comp.overview()
        if ov is not None and not ov.empty:
            print(f"    Cot: {list(ov.columns)}")
            for c in ov.columns:
                v = ov.iloc[0][c]
                print(f"      {c} = {v}")
        else:
            print("    -> EMPTY")
    except Exception as e:
        print(f"    -> LOI: {e}")

    # Test industry
    print("\n[3] INDUSTRY:")
    try:
        info = fetch_industry(sym)
        print(f"    {info}")
    except Exception as e:
        print(f"    -> LOI: {e}")

print("\n" + "=" * 70)
print("  KET THUC DEBUG")
print("=" * 70)