# rss_fetcher.py - Lay tin tuc RSS CafeF + gan sentiment
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
from bs4 import BeautifulSoup

try:
    from sentiment_analyzer import analyze_sentiment, sentiment_summary
    SENTIMENT_OK = True
except ImportError:
    SENTIMENT_OK = False
    print("  [WARN] Chua co sentiment_analyzer.py")


RSS_FEEDS = {
    'Thị trường chứng khoán': 'https://cafef.vn/thi-truong-chung-khoan.rss',
    'Tài chính - Ngân hàng': 'https://cafef.vn/tai-chinh-ngan-hang.rss',
    'Doanh nghiệp': 'https://cafef.vn/doanh-nghiep.rss',
    'Vĩ mô - Đầu tư': 'https://cafef.vn/vi-mo-dau-tu.rss',
    'Bất động sản': 'https://cafef.vn/bat-dong-san.rss',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}


def fetch_rss(feed_url, category, max_items=10):
    items = []
    try:
        r = requests.get(feed_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"    [{category}] HTTP {r.status_code}")
            return items

        root = ET.fromstring(r.content)

        for item in root.iter('item'):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            pub_date_el = item.find('pubDate')

            title = title_el.text.strip() if title_el is not None and title_el.text else ''
            link = link_el.text.strip() if link_el is not None and link_el.text else ''
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ''
            pub_date = pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else ''

            if desc:
                try:
                    desc = BeautifulSoup(desc, 'html.parser').get_text(strip=True)
                except Exception:
                    pass

            if title and link:
                # Phan tich sentiment
                sentiment_label = 'neutral'
                sentiment_score = 0
                if SENTIMENT_OK:
                    try:
                        s = analyze_sentiment(title + ' ' + desc[:200])
                        sentiment_label = s['label']
                        sentiment_score = s['score']
                    except Exception:
                        pass

                items.append({
                    'title': title,
                    'link': link,
                    'description': desc[:300],
                    'pub_date': pub_date,
                    'category': category,
                    'source': 'CafeF',
                    'sentiment_label': sentiment_label,
                    'sentiment_score': sentiment_score,
                })

            if len(items) >= max_items:
                break

        print(f"    [{category}] {len(items)} tin")

    except Exception as e:
        print(f"    [{category}] Loi: {str(e)[:80]}")

    return items


def fetch_all_news(max_per_feed=8):
    print(f"  [RSS] Bat dau lay tin tu {len(RSS_FEEDS)} feeds...")
    all_news = []

    for cat, url in RSS_FEEDS.items():
        news = fetch_rss(url, cat, max_items=max_per_feed)
        all_news.extend(news)

    def parse_date(item):
        try:
            return datetime.strptime(item['pub_date'][:25], '%a, %d %b %Y %H:%M:%S')
        except Exception:
            return datetime.min

    all_news.sort(key=parse_date, reverse=True)
    result = all_news[:50]

    # In summary
    if SENTIMENT_OK and result:
        summary = sentiment_summary(result)
        print(f"  [RSS] Sentiment: +{summary['positive']} tich cuc, "
              f"{summary['neutral']} trung lap, -{summary['negative']} tieu cuc")

    print(f"  [RSS] Tong cong: {len(result)} tin")
    return result


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    news = fetch_all_news(max_per_feed=5)
    print()
    for n in news[:8]:
        label = n.get('sentiment_label', '?')
        score = n.get('sentiment_score', 0)
        icon = {'positive': '[+]', 'negative': '[-]', 'neutral': '[ ]'}.get(label, '[?]')
        print(f"  {icon} {score:>3} | {n['title'][:70]}")