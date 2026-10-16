# watchlist_db.py - Quan ly danh muc theo doi (SQLite)
import os
import sqlite3
from datetime import datetime

try:
    from hf_compat import get_path
    DB_FILE = get_path('watchlist.db')
except ImportError:
    DB_FILE = 'watchlist.db'


def _get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Tao bang neu chua co."""
    conn = _get_conn()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                note TEXT DEFAULT '',
                added_at TEXT NOT NULL,
                target_price REAL,
                stop_price REAL
            )
        ''')
        conn.commit()
        print(f"  [Watchlist] DB ready ({DB_FILE})")
    finally:
        conn.close()


def get_all():
    """Lay tat ca ma dang theo doi."""
    conn = _get_conn()
    try:
        rows = conn.execute('SELECT * FROM watchlist ORDER BY added_at DESC').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add(symbol, note='', target_price=None, stop_price=None):
    """Them ma vao watchlist. Neu da co thi update."""
    symbol = symbol.upper().strip()
    if not symbol:
        return {'error': 'Ma khong hop le'}
    conn = _get_conn()
    try:
        conn.execute('''
            INSERT INTO watchlist (symbol, note, added_at, target_price, stop_price)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                note = excluded.note,
                target_price = excluded.target_price,
                stop_price = excluded.stop_price
        ''', (symbol, note, datetime.now().strftime('%d/%m/%Y %H:%M:%S'), target_price, stop_price))
        conn.commit()
        return {'ok': True, 'symbol': symbol}
    finally:
        conn.close()


def remove(symbol):
    """Xoa ma khoi watchlist."""
    symbol = symbol.upper().strip()
    conn = _get_conn()
    try:
        conn.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
        conn.commit()
        return {'ok': True, 'symbol': symbol}
    finally:
        conn.close()


def is_in_watchlist(symbol):
    """Kiem tra 1 ma co trong watchlist khong."""
    symbol = symbol.upper().strip()
    conn = _get_conn()
    try:
        row = conn.execute('SELECT 1 FROM watchlist WHERE symbol = ?', (symbol,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_symbols():
    """Tra ve list cac ma dang theo doi."""
    conn = _get_conn()
    try:
        rows = conn.execute('SELECT symbol FROM watchlist').fetchall()
        return [r['symbol'] for r in rows]
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    add('FPT', 'Cong nghe hang dau', target_price=150000, stop_price=120000)
    add('VNM', 'Sua')
    add('HPG', 'Thep')
    print('Watchlist:', get_all())
    remove('VNM')
    print('Sau khi xoa VNM:', get_symbols())