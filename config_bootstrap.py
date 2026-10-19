import os

CONFIG_FILE = 'config.py'

def _ensure_config():
    if os.path.exists(CONFIG_FILE):
        return

    print("  [Bootstrap] config.py khong ton tai, tao tu env vars...")

    groq = os.environ.get('GROQ_API_KEY', '')
    vnstock = os.environ.get('VNSTOCK_API_KEY', '')
    
    content = f'''# Auto-generated
import os
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '{groq}')
VNSTOCK_API_KEY = os.environ.get('VNSTOCK_API_KEY', '{vnstock}')
DATA_SOURCE = 'kbs'
LISTING_SOURCE = 'kbs'
VALUATION_SOURCE = 'kbs'
MAX_SYMBOLS = 0
VALUATION_LIMIT = 100
EXCHANGES = []
UPDATE_INTERVAL_MINUTES = 15
REQUEST_DELAY_SECONDS = 1.2
EXCEL_FILE = 'stock_data.xlsx'
EXCEL_BACKUP_FILE = 'stock_data_backup.xlsx'
HTML_FILE = 'index.html'
VALUATION_CACHE = 'valuation_cache.json'
INDUSTRY_CACHE = 'industries_cache.json'
'''
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [Bootstrap] Da tao {CONFIG_FILE}")
    except Exception as e:
        print(f"  [Bootstrap] Loi tao config: {e}")

_ensure_config()