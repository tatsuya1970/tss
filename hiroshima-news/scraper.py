import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

BASE_URL_HIROSHIMA     = "https://www.city.hiroshima.lg.jp"
BASE_URL_FUKUYAMA      = "https://www.city.fukuyama.hiroshima.jp"
BASE_URL_KURE          = "https://www.city.kure.lg.jp"
BASE_URL_HATSUKA       = "https://www.city.hatsukaichi.hiroshima.jp"
BASE_URL_ONOMICHI      = "https://www.city.onomichi.hiroshima.jp"
BASE_URL_HIGASHI       = "https://www.city.higashihiroshima.lg.jp"
BASE_URL_TAKEHARA      = "https://www.city.takehara.lg.jp"
BASE_URL_MIHARA        = "https://www.city.mihara.hiroshima.jp"
BASE_URL_FUCHU_CITY    = "https://www.city.fuchu.hiroshima.jp"
BASE_URL_MIYOSHI       = "https://www.city.miyoshi.hiroshima.jp"
BASE_URL_SHOBARA       = "https://www.city.shobara.hiroshima.jp"
BASE_URL_OTAKE         = "https://www.city.otake.hiroshima.jp"
BASE_URL_AKITAKATA     = "https://www.akitakata.jp"
BASE_URL_ETAJIMA       = "https://www.city.etajima.hiroshima.jp"
BASE_URL_FUCHU_TOWN    = "https://www.town.fuchu.hiroshima.jp"
BASE_URL_KAITA         = "https://www.town.kaita.lg.jp"
BASE_URL_KUMANO        = "https://www.town.kumano.hiroshima.jp"
BASE_URL_SAKA          = "https://www.town.saka.lg.jp"
BASE_URL_AKIOTA        = "https://www.akiota.jp"
BASE_URL_KITAHIROSHIMA = "https://www.town.kitahiroshima.lg.jp"
BASE_URL_OSAKIKAMIJIMA = "https://www.town.osakikamijima.hiroshima.jp"
BASE_URL_SERA          = "https://www.town.sera.hiroshima.jp"
BASE_URL_JINSEKI       = "https://www.jinsekigun.jp"


def get(url: str) -> BeautifulSoup | None:
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = res.apparent_encoding
        return BeautifulSoup(res.text, "html.parser")
    except Exception:
        return None


# ── 広島市 ─────────────────────────────────────────────
def scrape_hiroshima() -> list[dict]:
    """広島市: 年別→月別→記事一覧の階層構造"""
    import re

    # 年ページを取得（URLを明示的に保持）
    year_index_url = f"{BASE_URL_HIROSHIMA}/shisei/kouhou/1004010/index.html"
    year_index_page = get(year_index_url)
    if not year_index_page:
        return []

    # 年ページリンク: /1004010/XXXXXX/index.html パターン
    year_pattern = re.compile(r"/shisei/kouhou/1004010/(\d+)/index\.html$")
    year_links = [a for a in year_index_page.select("a[href]")
                  if year_pattern.search(urljoin(year_index_url, a["href"]))]
    if not year_links:
        return []
    year_url = urljoin(year_index_url, year_links[0]["href"])

    # 月ページリンク: 年ID/月ID/index.html パターン
    year_id = year_pattern.search(year_url).group(1)
    month_pattern = re.compile(rf"/shisei/kouhou/1004010/{year_id}/(\d+)/index\.html$")
    month_page = get(year_url)
    if not month_page:
        return []
    month_links = [a for a in month_page.select("a[href]")
                   if month_pattern.search(urljoin(year_url, a["href"]))]
    if not month_links:
        return []
    month_url = urljoin(year_url, month_links[0]["href"])

    # 記事一覧: 月ID以下の数字ID.html パターン
    month_id = month_pattern.search(month_url).group(1)
    article_pattern = re.compile(rf"/shisei/kouhou/1004010/{year_id}/{month_id}/\d+\.html$")
    article_page = get(month_url)
    if not article_page:
        return []

    articles = []
    for li in article_page.select("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        full_url = urljoin(month_url, href)
        if not article_pattern.search(full_url):
            continue
        title = a.get_text(strip=True)
        if len(title) < 10 or title.isascii():
            continue
        # 日付: <span class="date">2026年3月23日</span>
        date_span = li.find("span", class_="date")
        published_at = date_span.get_text(strip=True) if date_span else ""
        articles.append({
            "city": "広島市",
            "title": title,
            "url": full_url,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 共通CMS（list1-1.html）を使う市 ───────────────────
def scrape_list_cms(city_name: str, base_url: str) -> list[dict]:
    """福山市・廿日市市・尾道市などが使う共通CMS形式"""
    import re
    url = f"{base_url}/soshiki/list1-1.html"
    soup = get(url)
    if not soup:
        return []

    articles = []
    # 記事URLは /soshiki/部門名/数字.html の形式
    article_url_pattern = re.compile(r"/soshiki/[^/]+/\d+\.html$")
    for li in soup.select("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a["href"]
        # 記事URLパターンに合致するもののみ
        if not article_url_pattern.search(href):
            continue
        # 短すぎる・ASCII（英語ナビ）・ナビゲーション系を除外
        if len(title) < 10 or title.isascii():
            continue
        nav_words = ("ページの先頭", "メニュー", "トップへ", "サイトマップ", "問い合わせ", "language", "Language")
        if any(w in title for w in nav_words):
            continue
        # 日付: span_a or span_b のどちらかに「YYYY年M月D日」が入る（市によって異なる）
        published_at = ""
        date_m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", li.get_text())
        if date_m:
            published_at = date_m.group(0)
        articles.append({
            "city": city_name,
            "title": title,
            "url": urljoin(base_url, href),
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 呉市 ───────────────────────────────────────────────
def reiwa_to_seireki(text: str) -> str:
    """令和X年M月D日 → YYYY年M月D日 に変換"""
    import re
    m = re.search(r"令和(\d+)年(\d{1,2})月(\d{1,2})日", text)
    if m:
        year = 2018 + int(m.group(1))
        return f"{year}年{m.group(2)}月{m.group(3)}日"
    # 既に西暦の場合はそのまま返す
    m2 = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text)
    return m2.group(0) if m2 else ""


def scrape_kure() -> list[dict]:
    """呉市: /site/press-releases/YYYYMM.html
    構造: 日付見出し要素 → <ul><li><a href=".pdf">タイトル</a></li></ul>
    """
    import re
    now = datetime.now()
    url = f"{BASE_URL_KURE}/site/press-releases/{now.year}{now.month:02d}.html"
    soup = get(url)
    if not soup:
        m = now.month - 1 or 12
        y = now.year if now.month > 1 else now.year - 1
        url = f"{BASE_URL_KURE}/site/press-releases/{y}{m:02d}.html"
        soup = get(url)
    if not soup:
        return []

    nav_words = ("メニュー", "トップへ", "先頭へ", "免責事項", "著作権", "サイトマップ",
                 "問い合わせ", "リンク集", "プライバシー", "カレンダー", "過去の")
    articles = []
    for a in soup.select("a[href]"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if len(title) < 15 or title.isascii():
            continue
        if any(w in title for w in nav_words):
            continue
        if href.startswith("#") or href.startswith("javascript"):
            continue

        # 日付: <ul>の直前の兄弟要素に「令和X年M月D日」が入る
        published_at = ""
        ul = a.parent.parent  # li → ul
        if ul:
            prev = ul.find_previous_sibling()
            if prev:
                published_at = reiwa_to_seireki(prev.get_text(strip=True))

        # PDFファイルのサイズ表記を除去
        title = re.sub(r"\s*\[PDFファイル[^\]]*\]", "", title).strip()
        if len(title) < 10:
            continue
        articles.append({
            "city": "呉市",
            "title": title,
            "url": urljoin(BASE_URL_KURE, href),
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 東広島市 ───────────────────────────────────────────
def scrape_higashihiroshima() -> list[dict]:
    """東広島市: 報道提供資料ページ"""
    import re
    url = f"{BASE_URL_HIGASHI}/soshiki/somu/1_1/4/25693.html"
    soup = get(url)
    if not soup:
        return []

    # 記事URLパターン: /soshiki/somu/以下の数字IDページ
    article_pattern = re.compile(r"/soshiki/.+/\d+\.html$")
    skip_titles = {"Foreign Language", "ご意見・お問い合わせ", "開庁日・開庁時間", "ページの先頭へ"}
    articles = []
    seen = set()
    for a in soup.select("a[href]"):
        title = a.get_text(strip=True)
        href = a.get("href", "")
        if title in skip_titles or len(title) < 15 or title in seen:
            continue
        if not article_pattern.search(href):
            continue
        seen.add(title)
        articles.append({
            "city": "東広島市",
            "title": title,
            "url": urljoin(BASE_URL_HIGASHI, href),
            "published_at": "",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 竹原市 ─────────────────────────────────────────────
def scrape_takehara() -> list[dict]:
    """竹原市: RSSフィード（RSS 1.0/RDF）"""
    import re
    import xml.etree.ElementTree as ET
    rss_url = f"{BASE_URL_TAKEHARA}/cgi-bin/feed.php?siteNew=1"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        root = ET.fromstring(res.text)
    except Exception:
        return []
    ns = {
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    articles = []
    seen = set()
    for item in root.findall("rss:item", ns):
        title = item.findtext("rss:title", namespaces=ns) or ""
        link = item.findtext("rss:link", namespaces=ns) or ""
        dc_date = item.findtext("dc:date", namespaces=ns) or ""
        if not title or not link or link in seen or title in seen:
            continue
        seen.add(link)
        seen.add(title)
        published_at = ""
        date_m = re.search(r"(\d{4})-(\d{2})-(\d{2})", dc_date)
        if date_m:
            published_at = f"{date_m.group(1)}年{int(date_m.group(2))}月{int(date_m.group(3))}日"
        articles.append({
            "city": "竹原市", "title": title,
            "url": link,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 府中市 ─────────────────────────────────────────────
def scrape_fuchu_city() -> list[dict]:
    """府中市（広島県）: 新着情報一覧"""
    import re
    url = f"{BASE_URL_FUCHU_CITY}/shinchakulist.html"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    article_pattern = re.compile(r"/soshiki/.+/\d+\.html$|/site/.+/\d+\.html$")
    nav_words = ("ページの先頭", "メニュー", "トップへ", "サイトマップ", "問い合わせ")
    for li in soup.select("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        title = a.get_text(strip=True)
        if not article_pattern.search(href):
            continue
        if len(title) < 10 or title.isascii() or title in seen:
            continue
        if any(w in title for w in nav_words):
            continue
        seen.add(title)
        date_m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", li.get_text())
        articles.append({
            "city": "府中市", "title": title,
            "url": urljoin(BASE_URL_FUCHU_CITY, href),
            "published_at": date_m.group(0) if date_m else "",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 三次市 ─────────────────────────────────────────────
def scrape_miyoshi() -> list[dict]:
    """三次市: 報道発表資料"""
    import re
    url = f"{BASE_URL_MIYOSHI}/site/houdousiryou/"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    article_pattern = re.compile(r"/site/houdousiryou/\d+\.html$")
    for li in soup.select("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        title = a.get_text(strip=True)
        if not article_pattern.search(href):
            continue
        if len(title) < 10 or title.isascii() or title in seen:
            continue
        seen.add(title)
        date_m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日", li.get_text())
        articles.append({
            "city": "三次市", "title": title,
            "url": urljoin(BASE_URL_MIYOSHI, href),
            "published_at": date_m.group(0) if date_m else "",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 庄原市 ─────────────────────────────────────────────
def scrape_shobara() -> list[dict]:
    """庄原市: Atomフィード"""
    import re
    import xml.etree.ElementTree as ET
    atom_url = f"{BASE_URL_SHOBARA}/info/atom.xml"
    try:
        res = requests.get(atom_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        root = ET.fromstring(res.text)
    except Exception:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    base = "https://cms.city.shobara.hiroshima.jp/info/"
    articles = []
    seen = set()
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", namespaces=ns) or ""
        link_el = next((l for l in entry.findall("atom:link", ns) if l.get("rel") == "alternate"), None)
        published = entry.findtext("atom:published", namespaces=ns) or ""
        if not title or link_el is None:
            continue
        href = link_el.get("href", "")
        url = href if href.startswith("http") else urljoin(base, href)
        if title in seen or url in seen:
            continue
        seen.add(title)
        seen.add(url)
        published_at = ""
        date_m = re.search(r"(\d{4})-(\d{2})-(\d{2})", published)
        if date_m:
            published_at = f"{date_m.group(1)}年{int(date_m.group(2))}月{int(date_m.group(3))}日"
        articles.append({
            "city": "庄原市", "title": title,
            "url": url,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 大竹市 ─────────────────────────────────────────────
def scrape_otake() -> list[dict]:
    """大竹市: RSSフィード（RSS 1.0/RDF）"""
    import re
    import xml.etree.ElementTree as ET
    rss_url = f"{BASE_URL_OTAKE}/cgi-bin/feed.php?siteNew=1&displayRange=90&includeShortcut=1"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        root = ET.fromstring(res.text)
    except Exception:
        return []
    ns = {
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    articles = []
    seen = set()
    for item in root.findall("rss:item", ns):
        title = item.findtext("rss:title", namespaces=ns) or ""
        link = item.findtext("rss:link", namespaces=ns) or ""
        dc_date = item.findtext("dc:date", namespaces=ns) or ""
        if not title or not link or link in seen or title in seen:
            continue
        seen.add(link)
        seen.add(title)
        published_at = ""
        date_m = re.search(r"(\d{4})-(\d{2})-(\d{2})", dc_date)
        if date_m:
            published_at = f"{date_m.group(1)}年{int(date_m.group(2))}月{int(date_m.group(3))}日"
        articles.append({
            "city": "大竹市", "title": title,
            "url": link,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 安芸高田市 ──────────────────────────────────────────
def scrape_akitakata() -> list[dict]:
    """安芸高田市: トピックス一覧"""
    url = f"{BASE_URL_AKITAKATA}/ja/topics/"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    for box in soup.select("div.border_box"):
        a = box.parent
        if not a or a.name != "a":
            continue
        href = a.get("href", "")
        title_el = box.select_one("p.title")
        time_el = box.select_one("time")
        if not title_el or not href:
            continue
        title = title_el.get_text(strip=True)
        if len(title) < 5 or title in seen:
            continue
        seen.add(title)
        published_at = time_el.get_text(strip=True) if time_el else ""
        articles.append({
            "city": "安芸高田市", "title": title,
            "url": urljoin(BASE_URL_AKITAKATA, href),
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 江田島市 ────────────────────────────────────────────
def scrape_etajima() -> list[dict]:
    """江田島市: 新着情報"""
    import re
    url = f"{BASE_URL_ETAJIMA}/cms/details/news"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    article_pattern = re.compile(r"/cms/articles/show/\d+")
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not article_pattern.search(href):
            continue
        if len(title) < 10 or title.isascii() or title in seen:
            continue
        seen.add(title)
        article_url = urljoin(BASE_URL_ETAJIMA, href)
        # 記事個別ページから「公開日」を取得
        published_at = ""
        detail = get(article_url)
        if detail:
            date_m = re.search(r"公開日\s*[：:]?\s*(\d{4}年\d{1,2}月\d{1,2}日)", detail.get_text())
            if date_m:
                published_at = date_m.group(1)
        articles.append({
            "city": "江田島市", "title": title,
            "url": article_url,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 海田町 ──────────────────────────────────────────────
def scrape_kaita() -> list[dict]:
    """海田町: 新着情報"""
    import re
    url = f"{BASE_URL_KAITA}/soshiki/list6-1.html"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    article_pattern = re.compile(r"/soshiki/[^/]+/\d+\.html$|/site/[^/]+/\d+\.html$")
    nav_words = ("ページの先頭", "メニュー", "トップへ", "サイトマップ", "問い合わせ")
    for li in soup.select("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        title = a.get_text(strip=True)
        if not article_pattern.search(href):
            continue
        if len(title) < 10 or title.isascii() or title in seen:
            continue
        if any(w in title for w in nav_words):
            continue
        seen.add(title)
        date_m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", li.get_text())
        articles.append({
            "city": "海田町", "title": title,
            "url": urljoin(BASE_URL_KAITA, href),
            "published_at": date_m.group(0) if date_m else "",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 熊野町 ──────────────────────────────────────────────
def scrape_kumano() -> list[dict]:
    """熊野町: RSSフィード（RSS 1.0/RDF）"""
    import re
    import xml.etree.ElementTree as ET
    rss_url = f"{BASE_URL_KUMANO}/www/rss/news.rdf"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        root = ET.fromstring(res.text)
    except Exception:
        return []
    ns = {
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    articles = []
    seen = set()
    for item in root.findall("rss:item", ns):
        title = item.findtext("rss:title", namespaces=ns) or ""
        link = item.findtext("rss:link", namespaces=ns) or ""
        dc_date = item.findtext("dc:date", namespaces=ns) or ""
        if not title or not link or link in seen or title in seen:
            continue
        seen.add(link)
        seen.add(title)
        published_at = ""
        date_m = re.search(r"(\d{4})-(\d{2})-(\d{2})", dc_date)
        if date_m:
            published_at = f"{date_m.group(1)}年{int(date_m.group(2))}月{int(date_m.group(3))}日"
        articles.append({
            "city": "熊野町", "title": title,
            "url": link,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 坂町 ────────────────────────────────────────────────
def scrape_saka() -> list[dict]:
    """坂町: 新着情報（WordPress）"""
    import re
    url = f"{BASE_URL_SAKA}/"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    article_pattern = re.compile(r"/\d{4}/\d{2}/\d{2}/.+/")
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not article_pattern.search(href):
            continue
        if len(title) < 10 or title.isascii() or title in seen:
            continue
        seen.add(title)
        date_m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", href)
        published_at = f"{date_m.group(1)}年{int(date_m.group(2))}月{int(date_m.group(3))}日" if date_m else ""
        articles.append({
            "city": "坂町", "title": title,
            "url": href if href.startswith("http") else urljoin(BASE_URL_SAKA, href),
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 大崎上島町 ──────────────────────────────────────────
def scrape_osakikamijima() -> list[dict]:
    """大崎上島町: RSSフィード（RSS 1.0/RDF）"""
    import re
    import xml.etree.ElementTree as ET
    rss_url = f"{BASE_URL_OSAKIKAMIJIMA}/cgi-bin/feed.php?siteNew=1"
    try:
        res = requests.get(rss_url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        root = ET.fromstring(res.text)
    except Exception:
        return []
    ns = {
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    articles = []
    seen = set()
    for item in root.findall("rss:item", ns):
        title = item.findtext("rss:title", namespaces=ns) or ""
        link = item.findtext("rss:link", namespaces=ns) or ""
        dc_date = item.findtext("dc:date", namespaces=ns) or ""
        if not title or not link or link in seen or title in seen:
            continue
        seen.add(link)
        seen.add(title)
        published_at = ""
        date_m = re.search(r"(\d{4})-(\d{2})-(\d{2})", dc_date)
        if date_m:
            published_at = f"{date_m.group(1)}年{int(date_m.group(2))}月{int(date_m.group(3))}日"
        articles.append({
            "city": "大崎上島町", "title": title,
            "url": link,
            "published_at": published_at,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 神石高原町 ──────────────────────────────────────────
def scrape_jinseki() -> list[dict]:
    """神石高原町: お知らせ"""
    import re
    url = f"{BASE_URL_JINSEKI}/town/news/"
    soup = get(url)
    if not soup:
        return []
    articles = []
    seen = set()
    article_pattern = re.compile(r"/town/[\w-]+/[\w-]+/[\w-]+/")
    nav_words = ("メニュー", "トップ", "サイトマップ", "お問い合わせ", "ページの先頭")
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not article_pattern.search(href):
            continue
        if len(title) < 10 or title.isascii() or title in seen:
            continue
        if any(w in title for w in nav_words):
            continue
        seen.add(title)
        parent_text = a.parent.get_text() if a.parent else ""
        date_m = re.search(r"\d{4}年\d{1,2}月\d{1,2}日", parent_text)
        articles.append({
            "city": "神石高原町", "title": title,
            "url": urljoin(BASE_URL_JINSEKI, href),
            "published_at": date_m.group(0) if date_m else "",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if len(articles) >= 10:
            break
    return articles


# ── 全市取得 ───────────────────────────────────────────
def fetch_all() -> list[dict]:
    all_articles = []
    # 既存5市
    all_articles.extend(scrape_hiroshima())
    all_articles.extend(scrape_list_cms("福山市", BASE_URL_FUKUYAMA))
    all_articles.extend(scrape_kure())
    all_articles.extend(scrape_list_cms("廿日市市", BASE_URL_HATSUKA))
    all_articles.extend(scrape_list_cms("尾道市", BASE_URL_ONOMICHI))
    all_articles.extend(scrape_higashihiroshima())
    # 新規追加（カスタムスクレイパー）
    all_articles.extend(scrape_takehara())
    all_articles.extend(scrape_fuchu_city())
    all_articles.extend(scrape_miyoshi())
    all_articles.extend(scrape_shobara())
    all_articles.extend(scrape_otake())
    all_articles.extend(scrape_akitakata())
    all_articles.extend(scrape_etajima())
    all_articles.extend(scrape_kaita())
    all_articles.extend(scrape_kumano())
    all_articles.extend(scrape_saka())
    all_articles.extend(scrape_osakikamijima())
    all_articles.extend(scrape_jinseki())
    # 新規追加（list1-1.html CMS）
    all_articles.extend(scrape_list_cms("三原市", BASE_URL_MIHARA))
    all_articles.extend(scrape_list_cms("府中町", BASE_URL_FUCHU_TOWN))
    all_articles.extend(scrape_list_cms("安芸太田町", BASE_URL_AKIOTA))
    all_articles.extend(scrape_list_cms("北広島町", BASE_URL_KITAHIROSHIMA))
    all_articles.extend(scrape_list_cms("世羅町", BASE_URL_SERA))
    return all_articles
