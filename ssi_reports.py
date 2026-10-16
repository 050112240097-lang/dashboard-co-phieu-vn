# ssi_reports.py - Bao cao tu nguon tong hop + RSS (khong phu thuoc CTCK SPA)
import os
import time
import re
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    from hf_compat import should_skip_playwright
    _skip_pw = should_skip_playwright()
except ImportError:
    _skip_pw = False

if _skip_pw:
    PLAYWRIGHT_OK = False
    print("  [INFO] Playwright disabled (HF mode) - bo qua scrape CTCK")
else:
    try:
        from playwright.sync_api import sync_playwright
        PLAYWRIGHT_OK = True
    except ImportError:
        PLAYWRIGHT_OK = False
        print("  [WARN] Chua cai playwright")


CACHE_FILE = 'reports_cache.json'
CACHE_MINUTES = 60
VALIDATE_URLS = True
VALIDATE_TIMEOUT = 8
MAX_REPORTS_PER_SOURCE = 20
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


# ============================================================
# NGUON 1: TRANG TONG HOP (Scrape HTML)
# ============================================================
AGGREGATOR_SOURCES = [
    {
        'name': 'Nguoi Quan Sat',
        'url': 'https://dulieu.nguoiquansat.vn/bao-cao-phan-tich',
        'base_url': 'https://dulieu.nguoiquansat.vn',
        'wait_selector': 'table tbody tr, a[href*="bao-cao"]',
    },
    {
        'name': 'Lang Tu Buon Nuoc Mam',
        'url': 'https://langtubuonnuocmam.com/category/blog/bao-cao-phan-tich/',
        'base_url': 'https://langtubuonnuocmam.com',
        'wait_selector': 'article a, h2 a, h3 a',
    },
]


# ============================================================
# NGUON 2: RSS FEED (Tin tuc tai chinh)
# ============================================================
RSS_FEEDS = [
    {
        'name': 'CafeF - Chứng khoán',
        'url': 'https://cafef.vn/thi-truong-chung-khoan.rss',
    },
    {
        'name': 'VnEconomy - Tài chính',
        'url': 'https://vneconomy.vn/tai-chinh.rss',
    },
    {
        'name': 'VnBusiness - Tài chính',
        'url': 'https://vnbusiness.vn/rss/tai-chinh.rss',
    },
    {
        'name': 'CafeF - Tài chính',
        'url': 'https://cafef.vn/tai-chinh-ngan-hang.rss',
    },
    {
        'name': 'VnEconomy - Chứng khoán',
        'url': 'https://vneconomy.vn/chung-khoan.rss',
    },
]

FALLBACK = [
    {"title": "Người Quan Sát - Báo cáo phân tích", "url": "https://dulieu.nguoiquansat.vn/bao-cao-phan-tich", "source": "Nguoi Quan Sat", "category": "Tổng hợp", "date": ""},
    {"title": "Làng Tử Buôn Nước Mắm - Báo cáo phân tích", "url": "https://langtubuonnuocmam.com/category/blog/bao-cao-phan-tich/", "source": "Lang Tu", "category": "Tổng hợp", "date": ""},
    {"title": "CafeF - Tin chứng khoán", "url": "https://cafef.vn/thi-truong-chung-khoan.rss", "source": "CafeF", "category": "Tin tức", "date": ""},
    {"title": "VietStock - Trang chủ", "url": "https://vietstock.vn/trang-chu.rss", "source": "VietStock", "category": "Tin tức", "date": ""},
    {"title": "VnEconomy - Tài chính", "url": "https://vneconomy.vn/tai-chinh.rss", "source": "VnEconomy", "category": "Tin tức", "date": ""},
]


# ============================================================
# HELPERS
# ============================================================


def _classify_type(title, source):
    """
    Phan loai bao cao:
    - 'analysis': phan tich co phieu cu the (co ticker + khuyen nghi/dinh gia)
    - 'industry': phan tich nganh / vi mo
    - 'news': tin tuc
    """
    t = title.lower()

    # 1) Co ticker (3-4 chu in hoa) -> co phieu
    import re as _re
    has_ticker = bool(_re.search(r'\b[A-Z]{3,4}\b', title))

    # 2) Tu khoa phan tich
    analysis_kw = ['khuyến nghị', 'khuyen nghi', 'định giá', 'dinh gia',
                   'giá mục tiêu', 'gia muc tieu', 'mua', 'bán', 'nắm giữ',
                   'báo cáo phân tích', 'bao cao phan tich', 'cập nhật cổ phiếu',
                   'kết quả kinh doanh', 'ket qua kinh doanh']
    has_analysis_kw = any(kw in t for kw in analysis_kw)

    # 3) Tu khoa nganh/vi mo
    industry_kw = ['ngành', 'nganh', 'vĩ mô', 'vi mo', 'triển vọng ngành',
                   'chiến lược', 'chien luoc', 'thị trường chứng khoán',
                   'vietstock', 'vn-index', 'vnindex']
    has_industry_kw = any(kw in t for kw in industry_kw)

    # 4) Tu khoa tin tuc
    news_kw = ['tin tức', 'tin tuc', 'sự kiện', 'su kien', 'công bố', 'cong bo',
               'thông báo', 'thong bao', 'biến động', 'bien dong',
               'tăng', 'giam', 'giảm', 'phiên']
    has_news_kw = any(kw in t for kw in news_kw)

    # Logic uu tien
    if has_ticker and has_analysis_kw:
        return 'analysis'
    if has_analysis_kw and not has_news_kw:
        return 'analysis'
    if has_industry_kw and not has_news_kw:
        return 'industry'
    if has_ticker and source not in ('CafeF - Chứng khoán', 'VnEconomy - Tài chính',
                                      'VnBusiness - Tài chính', 'CafeF - Tài chính',
                                      'VnEconomy - Chứng khoán'):
        return 'analysis'
    if has_news_kw:
        return 'news'
    return 'news'

def _validate_url(url, timeout=VALIDATE_TIMEOUT):
    if not VALIDATE_URLS or not url:
        return True
    try:
        req = urllib.request.Request(url, method='GET', headers={
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml,*/*',
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            ctype = resp.headers.get('Content-Type', '').lower()
            if not any(k in ctype for k in ['html', 'xml', 'rss', 'pdf', 'octet-stream']):
                return False
            body = resp.read(800)
            text = body.decode('utf-8', errors='ignore').lower()
            if 'không tìm thấy' in text or 'not found' in text or '404' in text[:200]:
                return False
            return True
    except Exception:
        return False


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = (time.time() - data.get('_ts', 0)) / 60
        if age > CACHE_MINUTES:
            print(f"  [Cache] Bao cao cu ({age:.0f} phut) -> refresh")
            return None
        print(f"  [Cache] Dung cache ({age:.1f} phut)")
        return data.get('reports', [])
    except Exception:
        return None


def save_cache(reports):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                '_ts': time.time(),
                '_updated': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'reports': reports,
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _extract_date_from_text(text):
    if not text:
        return ""
    for pattern in [r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})']:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    year, month, day = groups
                else:
                    day, month, year = groups
                d, m, y = int(day), int(month), int(year)
                if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= y <= 2100:
                    return f"{d:02d}/{m:02d}/{y}"
            except Exception:
                continue
    return ""


def _detect_category(title):
    t = title.lower()
    if 'ngành' in t or 'nganh' in t:
        return 'Ngành'
    if 'doanh nghiệp' in t or 'công ty' in t or 'ctcp' in t or 'cổ phiếu' in t:
        return 'Doanh nghiệp'
    if 'vĩ mô' in t or 'vi mo' in t or 'kinh tế' in t:
        return 'Vĩ mô'
    if 'chiến lược' in t or 'chien luoc' in t:
        return 'Chiến lược'
    if 'trái phiếu' in t or 'trai phieu' in t or 'lãi suất' in t:
        return 'Trái phiếu'
    return 'Tổng hợp'


# ============================================================
# SCRAPE NGUON TONG HOP
# ============================================================
def _scrape_aggregator(page, source):
    reports = []
    name = source['name']
    try:
        print(f"    [{name}] Dang tai trang...")
        page.goto(source['url'], timeout=30000, wait_until='domcontentloaded')
        try:
            page.wait_for_selector(source['wait_selector'], timeout=5000)
        except Exception:
            page.wait_for_timeout(3000)

        links = page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            const BAD_TITLES = ['trang chủ','giới thiệu','liên hệ','đăng nhập','đăng ký'];
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.getAttribute('href');
                const title = (a.innerText || '').trim();
                if (!href || !title || title.length < 20) return;
                if (seen.has(href)) return;
                seen.add(href);
                const tl = title.toLowerCase();
                for (const bad of BAD_TITLES) { if (tl === bad) return; }
                // Phai la bai bao cao / phan tich
                const isReport = tl.includes('báo cáo') || tl.includes('phân tích') || tl.includes('khuyến nghị')
                              || tl.includes('cập nhật') || tl.includes('dự báo') || /\\b[A-Z]{3,4}\\b/.test(title);
                if (!isReport) return;
                let dateText = '';
                const parent = a.parentElement;
                if (parent) dateText = parent.innerText || '';
                results.push({ href: href, title: title.substring(0, 180), dateText: dateText.substring(0, 200) });
            });
            return results.slice(0, 40);
        }''')

        base_url = source.get('base_url', '')
        for link in links:
            href = link['href']
            if href.startswith('//'):
                full_url = 'https:' + href
            elif href.startswith('/'):
                full_url = base_url.rstrip('/') + href
            elif not href.startswith('http'):
                full_url = base_url.rstrip('/') + '/' + href
            else:
                full_url = href

            date_str = _extract_date_from_text(link.get('dateText', '')) or _extract_date_from_text(href)
            reports.append({
                'title': link['title'],
                'url': full_url,
                'source': name,
                'category': _detect_category(link['title']),
                'type': _classify_type(link['title'], name),
                'date': date_str,
            })
        print(f"    [{name}] Tim thay {len(reports)} bai")
    except Exception as e:
        print(f"    [{name}] Loi: {str(e)[:80]}")
    return reports[:MAX_REPORTS_PER_SOURCE]


# ============================================================
# DOC RSS FEED
# ============================================================
def _fetch_rss(feed):
    reports = []
    name = feed['name']
    url = feed['url']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        items = root.findall('.//item')
        is_atom = False
        if not items:
            items = root.findall('.//atom:entry', ns)
            is_atom = True

        for item in items[:MAX_REPORTS_PER_SOURCE]:
            if is_atom:
                title_el = item.find('atom:title', ns)
                link_el = item.find('atom:link', ns)
                date_el = item.find('atom:updated', ns) or item.find('atom:published', ns)
                href = link_el.get('href') if link_el is not None else ''
            else:
                title_el = item.find('title')
                link_el = item.find('link')
                date_el = item.find('pubDate')
                href = link_el.text.strip() if (link_el is not None and link_el.text) else ''

            title = title_el.text.strip() if (title_el is not None and title_el.text) else ''
            if not title or not href:
                continue

            date_raw = date_el.text.strip() if (date_el is not None and date_el.text) else ''
            date_str = _extract_date_from_text(date_raw) or _extract_date_from_text(href)

            reports.append({
                'title': title[:180],
                'url': href,
                'source': name,
                'category': _detect_category(title),
                'type': _classify_type(title, name),
                'date': date_str,
            })
        print(f"    [{name}] {len(reports)} tin")
    except Exception as e:
        print(f"    [{name}] Loi RSS: {str(e)[:80]}")
    return reports


# ============================================================
# MAIN FETCH
# ============================================================
def fetch_ssi_reports(force_refresh=False):
    if not force_refresh:
        cached = load_cache()
        if cached:
            return cached

    print(f"  [Reports] Bat dau lay bao cao...")
    all_reports = []

    # 1) Scrape 2 nguon tong hop (can Playwright)
    if PLAYWRIGHT_OK:
        print(f"  [Reports] Scrape {len(AGGREGATOR_SOURCES)} nguon tong hop...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT, viewport={'width': 1280, 'height': 900})
                page = context.new_page()
                for source in AGGREGATOR_SOURCES:
                    reports = _scrape_aggregator(page, source)
                    all_reports.extend(reports)
                    time.sleep(1)
                browser.close()
        except Exception as e:
            print(f"  [Reports] Loi Playwright: {str(e)[:100]}")

    # 2) Doc RSS feeds (khong can Playwright)
    print(f"  [Reports] Doc {len(RSS_FEEDS)} RSS feeds...")
    for feed in RSS_FEEDS:
        reports = _fetch_rss(feed)
        all_reports.extend(reports)
        time.sleep(0.3)

    # Fallback neu khong co gi
    if len(all_reports) < 5:
        print("  [Reports] Qua it ket qua -> dung fallback")
        all_reports.extend(FALLBACK)

    # Dedup
    seen = set()
    unique = []
    for r in all_reports:
        if r['url'] not in seen:
            seen.add(r['url'])
            unique.append(r)

    # Sort: moi truoc
    def sort_key(r):
        d = r.get('date', '')
        if d:
            try:
                parts = d.split('/')
                return (0, -int(parts[2]), -int(parts[1]), -int(parts[0]))
            except Exception:
                pass
        return (1, 0, 0, 0)

    unique.sort(key=sort_key)
    save_cache(unique)
    print(f"  [Reports] Tong cong: {len(unique)} bao cao")
    return unique