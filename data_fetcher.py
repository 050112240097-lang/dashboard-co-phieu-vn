# data_fetcher.py - Co Tran/San/TC + Bid/Ask + Phien
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from config import (
    MAX_SYMBOLS, EXCHANGES, DATA_SOURCE, LISTING_SOURCE,
    EXCEL_FILE, EXCEL_BACKUP_FILE
)


def get_all_symbols():
    print("  [Listing] Dang lay danh sach ma...")
    try:
        from vnstock import Listing
        listing = Listing(source=LISTING_SOURCE)
        df = listing.all_symbols()
        print(f"  [Listing] Tong so ma: {len(df)}")

        code_col = next((c for c in ['symbol', 'ticker', 'code'] if c in df.columns), None)
        if not code_col:
            return []

        if EXCHANGES and 'exchange' in df.columns:
            df = df[df['exchange'].isin(EXCHANGES)]

        symbols = [str(s).strip().upper() for s in df[code_col].dropna().unique()]

        if MAX_SYMBOLS > 0:
            symbols = symbols[:MAX_SYMBOLS]
            print(f"  [Listing] Gioi han: {len(symbols)} ma")

        return sorted(symbols)
    except Exception as e:
        print(f"  [LOI Listing] {e}")
        return []


def convert_time(ts):
    try:
        if ts and ts > 0:
            return datetime.fromtimestamp(ts / 1000).strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        pass
    return None


def get_current_session():
    """Xac dinh phien giao dich hien tai."""
    now = datetime.now()
    # Chu nhat = 6, thu 7 = 5
    if now.weekday() >= 5:
        return 'Đóng cửa'

    t = now.time()
    from datetime import time as dt_time
    if dt_time(8, 30) <= t < dt_time(9, 0):
        return 'Pre'         # Truoc phien
    elif dt_time(9, 0) <= t < dt_time(9, 15):
        return 'ATO'         # Mo cua
    elif dt_time(9, 15) <= t < dt_time(11, 30):
        return 'Sáng'        # Phien sang
    elif dt_time(11, 30) <= t < dt_time(13, 0):
        return 'Nghỉ trưa'
    elif dt_time(13, 0) <= t < dt_time(14, 30):
        return 'Chiều'       # Phien chieu
    elif dt_time(14, 30) <= t < dt_time(14, 45):
        return 'ATC'         # Dong cua
    elif dt_time(14, 45) <= t < dt_time(15, 0):
        return 'Sau giờ'
    else:
        return 'Đóng cửa'


def fetch_batch(symbols_batch):
    try:
        import quant_agent as qa
        import pandas as pd

        # quant_agent.price_board trả về DataFrame với dữ liệu realtime
        df = qa.price_board(symbols_batch)
        
        if df is None or df.empty:
            return None

        # Chuẩn hóa tên cột để khớp với cấu trúc code hiện tại
        # (Tên cột thực tế có thể thay đổi, cần kiểm tra lại sau khi chạy)
        column_map = {
            'symbol': 'symbol',
            'exchange': 'exchange',
            'ceiling_price': 'ceiling',
            'floor_price': 'floor',
            'reference_price': 'reference',
            'close_price': 'close',
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'volume_accumulated': 'volume',
            'price_change': 'change',
            'percent_change': 'pct',
            'foreign_buy_volume': 'foreign_buy',
            'foreign_sell_volume': 'foreign_sell',
            'foreign_net_volume': 'foreign_net',
            'time': 'time'
        }
        
        # Đổi tên cột nếu cần
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

        # Đảm bảo có đủ các cột cần thiết, nếu thiếu thì điền giá trị mặc định
        for col in ['ceiling', 'floor', 'reference', 'open', 'high', 'low', 'change', 'pct', 'foreign_buy', 'foreign_sell', 'foreign_net']:
            if col not in df.columns:
                df[col] = 0
        
        return df
        
    except Exception as e:
        print(f"    [LOI quant_agent] {str(e)[:100]}")
        # Fallback: Thử dùng vnstock nếu quant_agent lỗi (chỉ chạy được ở local)
        try:
            from vnstock import Trading
            trading = Trading(source=DATA_SOURCE)
            return trading.price_board(symbols_batch)
        except Exception as e2:
            print(f"    [LOI vnstock fallback] {str(e2)[:100]}")
            return None


def _is_data_valid_for_today(df):
    if df.empty:
        print("  [Check] DataFrame rong -> KHONG hop le")
        return False

    valid_vol = df[df['volume'] > 0]
    total = len(df)
    valid_count = len(valid_vol)
    print(f"  [Check] Co {valid_count}/{total} ma co volume > 0")

    if valid_count < total * 0.3:
        print(f"  [Check] Qua it ma co volume (>30%) -> KHONG hop le")
        return False

    times = df['time'].dropna()
    if len(times) > 0:
        sample_times = times.head(10).tolist()
        today_str = datetime.now().strftime('%d/%m/%Y')
        count_today = sum(1 for t in sample_times if today_str in str(t))
        print(f"  [Check] Co {count_today}/10 ma co thoi gian hom nay ({today_str})")

        if count_today < 3:
            print(f"  [Check] Thoi gian khong phai hom nay -> KHONG hop le")
            return False

    print("  [Check] Du lieu HOP LE")
    return True


def _load_previous_data():
    for filepath in [EXCEL_BACKUP_FILE, EXCEL_FILE]:
        if os.path.exists(filepath):
            try:
                df = pd.read_excel(filepath)
                if not df.empty:
                    print(f"  [Fallback] Doc du lieu tu {filepath} ({len(df)} dong)")
                    return df
            except Exception as e:
                print(f"  [Fallback] Loi doc {filepath}: {e}")
    return None


def _save_backup(df):
    try:
        if os.path.exists(EXCEL_FILE):
            import shutil
            shutil.copy(EXCEL_FILE, EXCEL_BACKUP_FILE)
    except Exception:
        pass


def fetch_all_data():
    symbols = get_all_symbols()
    if not symbols:
        print("  -> Khong lay duoc danh sach ma. Thu doc fallback...")
        prev = _load_previous_data()
        if prev is not None:
            return prev
        return pd.DataFrame()

    total = len(symbols)
    BATCH_SIZE = 50
    n_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"  [Fetch] {total} ma, {n_batches} batches")
    all_rows = []

    for i in range(0, total, BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        print(f"  [Fetch] Batch {i//BATCH_SIZE + 1}/{n_batches}")

        df = fetch_batch(batch)
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                try:
                    sym = str(row.get('symbol', '')).strip().upper()
                    if not sym:
                        continue

                    def clean(v, default=None):
                        if v is None:
                            return default
                        try:
                            if pd.isna(v):
                                return default
                        except Exception:
                            pass
                        return v

                    close = clean(row.get('close_price'))
                    ref = clean(row.get('reference_price'))
                    ceiling = clean(row.get('ceiling_price'))
                    floor = clean(row.get('floor_price'))
                    change = clean(row.get('price_change', 0), 0)
                    pct = clean(row.get('percent_change', 0), 0)

                    f_buy = clean(row.get('foreign_buy_volume', 0), 0) or 0
                    f_sell = clean(row.get('foreign_sell_volume', 0), 0) or 0

                    if (not change or not pct) and ref and close:
                        try:
                            change = float(close) - float(ref)
                            pct = (change / float(ref)) * 100 if float(ref) > 0 else 0
                        except Exception:
                            pass

                    # Bid/Ask levels
                    def to_num(v):
                        try:
                            if v is None or pd.isna(v):
                                return None
                            return float(v)
                        except Exception:
                            return None

                    def to_int(v):
                        try:
                            if v is None or pd.isna(v):
                                return 0
                            return int(v)
                        except Exception:
                            return 0

                    all_rows.append({
                        'symbol': sym,
                        'exchange': str(row.get('exchange', '') or ''),
                        'ceiling': to_num(ceiling),
                        'floor': to_num(floor),
                        'reference': to_num(ref),
                        'close': to_num(close),
                        'open': to_num(row.get('open_price')),
                        'high': to_num(row.get('high_price')),
                        'low': to_num(row.get('low_price')),
                        'volume': to_int(row.get('volume_accumulated')),
                        'change': round(float(change), 2) if change else 0,
                        'pct': round(float(pct), 2) if pct else 0,
                        'foreign_buy': int(f_buy),
                        'foreign_sell': int(f_sell),
                        'foreign_net': int(f_buy - f_sell),
                        # Bid/Ask 3 levels
                        'bid_price_1': to_num(row.get('bid_price_1')),
                        'bid_vol_1': to_int(row.get('bid_vol_1')),
                        'bid_price_2': to_num(row.get('bid_price_2')),
                        'bid_vol_2': to_int(row.get('bid_vol_2')),
                        'bid_price_3': to_num(row.get('bid_price_3')),
                        'bid_vol_3': to_int(row.get('bid_vol_3')),
                        'ask_price_1': to_num(row.get('ask_price_1')),
                        'ask_vol_1': to_int(row.get('ask_vol_1')),
                        'ask_price_2': to_num(row.get('ask_price_2')),
                        'ask_vol_2': to_int(row.get('ask_vol_2')),
                        'ask_price_3': to_num(row.get('ask_price_3')),
                        'ask_vol_3': to_int(row.get('ask_vol_3')),
                        'time': convert_time(clean(row.get('time'))),
                    })
                except Exception:
                    continue
        time.sleep(0.5)

    print(f"  [Fetch] Xong: {len(all_rows)} ma")
    new_df = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()

    if _is_data_valid_for_today(new_df):
        print("  [Fetch] Su dung du lieu MOI")
        _save_backup(new_df)
        return new_df
    else:
        print("  [Fetch] Du lieu hom nay CHUA HOP LE -> su dung du lieu HOM TRUOC")
        prev_df = _load_previous_data()
        if prev_df is not None and not prev_df.empty:
            print(f"  [Fallback] Da dung du lieu cu: {len(prev_df)} ma")
            if not os.path.exists(EXCEL_BACKUP_FILE):
                try:
                    prev_df.to_excel(EXCEL_BACKUP_FILE, index=False)
                    print(f"  [Backup] Da tao {EXCEL_BACKUP_FILE}")
                except Exception:
                    pass
            return prev_df
        else:
            print("  [Fallback] Khong co du lieu cu -> van dung du lieu moi")
            return new_df