# financial_utils.py - Helper chung cho phan tich BCTC KBS/VCI
import re


def normalize_item(s):
    """Bo prefix so/la ma, lowercase, strip. VD: '3. Doanh thu thuan' -> 'doanh thu thuan'"""
    if s is None:
        return ''
    s = str(s).strip().lower()
    s = re.sub(r'^\d+\s*[\.\)]\s*', '', s)       # '3.' '18.'
    s = re.sub(r'^[ivx]+\s*[\.\)]\s*', '', s)    # 'I.' 'IV.'
    s = re.sub(r'^[a-z]\s*[\)\.]\s*', '', s)     # 'a)'
    s = re.sub(r'^[-*]\s*', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _get_name_col(df):
    for c in ['item', 'item_vi', 'name', 'Chỉ tiêu', 'chi_tieu']:
        if c in df.columns:
            return c
    return None


def find_row(df, aliases):
    """
    Tim dong trong df khop alias.
    Uu tien: exact match sau normalize -> substring -> index.
    """
    if df is None or df.empty:
        return None

    name_col = _get_name_col(df)
    norm_aliases = [normalize_item(a) for a in aliases]

    if name_col:
        # Pass 1: exact match
        for _, row in df.iterrows():
            name = normalize_item(row[name_col])
            for na in norm_aliases:
                if name == na:
                    return row
        # Pass 2: substring match (alias la substring cua ten dong)
        for _, row in df.iterrows():
            name = normalize_item(row[name_col])
            for na in norm_aliases:
                if na and na in name:
                    return row

    # Pass 3: fallback theo index
    try:
        for alias in aliases:
            if alias in df.index:
                return df.loc[alias]
    except Exception:
        pass

    return None


def get_latest_periods(df, n=5):
    """
    Tra ve list ten cot ky (moi -> cu).
    Ho tro: '2025-Năm', '2024-Q4', '2024', '2025-Nam', '2025-Q4_1'.
    Uu tien Nam > Q4 > Q3 > Q2 > Q1.
    """
    if df is None or df.empty:
        return []

    skip = {'item', 'item_id', 'item_vi', 'name', 'Chỉ tiêu', 'chi_tieu'}
    cols = [c for c in df.columns if c not in skip]
    period_cols = [c for c in cols if any(ch.isdigit() for ch in str(c))]
    if not period_cols:
        return []

    def sort_key(c):
        s = str(c).lower()
        m = re.search(r'(\d{4})', s)
        year = int(m.group(1)) if m else 0
        if 'năm' in s or 'nam' in s or 'year' in s:
            q = 5
        else:
            mq = re.search(r'q(\d)', s)
            q = int(mq.group(1)) if mq else 0
        # Cot co hau to '_1' la ban duplicate -> xep sau
        if '_' in str(c):
            q -= 0.1
        return (-year, -q)

    return sorted(period_cols, key=sort_key)[:n]


def get_value(row, col):
    """Lay gia tri tu row[col] -> float hoac None."""
    if row is None or col is None:
        return None
    try:
        v = row[col] if col in row.index else None
        if v is None:
            return None
        f = float(v)
        return None if f != f else f
    except Exception:
        return None