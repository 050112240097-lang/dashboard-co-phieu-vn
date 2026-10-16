# config.example.py - Mau cau hinh. Doi ten thanh config.py va dien key.

# ============================================================
# API KEYS
# ============================================================
# Groq API (mien phi): https://console.groq.com/keys
GROQ_API_KEY = 'gsk_...'

# VNStock API (mien phi): https://vnstocks.com/login
# Sau khi lay key, chay: vnstock register
VNSTOCK_API_KEY = 'vnstock_...'

# Telegram (tuy chon)
# TELEGRAM_BOT_TOKEN = ''
# TELEGRAM_CHAT_ID = ''

# ============================================================
# CAU HINH LAY DU LIEU
# ============================================================
DATA_SOURCE = 'kbs'
LISTING_SOURCE = 'kbs'
VALUATION_SOURCE = 'kbs'

MAX_SYMBOLS = 0
VALUATION_LIMIT = 100
EXCHANGES = []

# ============================================================
# THOI GIAN
# ============================================================
UPDATE_INTERVAL_MINUTES = 15
REQUEST_DELAY_SECONDS = 1.2

# ============================================================
# FILE OUTPUT
# ============================================================
EXCEL_FILE = 'stock_data.xlsx'
EXCEL_BACKUP_FILE = 'stock_data_backup.xlsx'
HTML_FILE = 'index.html'
VALUATION_CACHE = 'valuation_cache.json'
INDUSTRY_CACHE = 'industries_cache.json'