import re
from datetime import datetime
from loguru import logger

from crawler.rss import RSSCrawler
from crawler.article import extract_article


# ============================================================
# Sumber RSS - CTI (bilingual ID + EN)
# ============================================================
RSS_SOURCES = [
    # English - international CTI
    ("https://feeds.feedburner.com/TheHackersNews", "the-hacker-news", "en"),
    ("https://www.bleepingcomputer.com/feed/", "bleepingcomputer", "en"),
    ("https://krebsonsecurity.com/feed/", "krebsonsecurity", "en"),
    ("https://www.darkreading.com/rss.xml", "darkreading", "en"),
    ("https://www.securityweek.com/feed/", "securityweek", "en"),
    ("https://threatpost.com/feed/", "threatpost", "en"),
    # Indonesia - kanal teknologi/keamanan
    ("https://www.antaranews.com/rss/tekno.xml", "antara-tekno", "id"),
    ("https://www.cnnindonesia.com/teknologi/rss", "cnn-teknologi", "id"),
]


# ============================================================
# Deteksi bahasa sederhana
# ============================================================
ID_MARKERS = [
    "dan", "yang", "di", "ke", "dari", "untuk", "dengan", "pada",
    "adalah", "ini", "itu", "akan", "tidak", "bisa", "telah",
    "kata", "ujar", "menurut", "pemerintah", "indonesia",
]

EN_MARKERS = [
    "the", "and", "of", "to", "in", "for", "with", "on", "is",
    "are", "was", "were", "this", "that", "will", "not", "can",
    "said", "according", "researchers", "security", "attack",
]


def detect_language(text: str) -> str:
    """Return 'id' atau 'en' berdasarkan frekuensi kata kunci."""
    t = " " + text.lower() + " "
    id_score = sum(1 for m in ID_MARKERS if f" {m} " in t)
    en_score = sum(1 for m in EN_MARKERS if f" {m} " in t)
    return "id" if id_score > en_score else "en"


# ============================================================
# Keyword matching
# ============================================================
def match_keyword(text: str, keywords: list[str]) -> str | None:
    """Kembalikan keyword pertama yang cocok (substring), atau None."""
    t = text.lower()
    for kw in keywords:
        if kw.lower() in t:
            return kw
    return None


# ============================================================
# Fetch satu artikel
# ============================================================
def _fetch_one(item: dict, category: str, keyword: str, language: str) -> dict | None:
    try:
        c = RSSCrawler(item["url"], item["source"])
        html = c.fetch(item["url"])
        art = extract_article(html, item["url"], item["source"])
        if not art.content or len(art.content) < 200:
            logger.debug(f"Skip (konten pendek): {item['url']}")
            return None
        return {
            "source": item["source"],
            "category": category,
            "keyword": keyword,
            "url": item["url"],
            "title": art.title or item["title"],
            "author": art.author,
            "date": art.date or item["date"],
            "content": art.content,
            "language": language,
            "crawled_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Skip {item['url']}: {e}")
        return None


# ============================================================
# Pipeline utama
# ============================================================
def crawl_by_categories(
    categories: list[dict],
    per_keyword_limit: int = 5,
    lain_lain_limit: int = 3,
):
    """
    1. Ambil item dari semua RSS.
    2. Untuk setiap kategori, match keyword.
    3. Fetch isi artikel lengkap.
    """
    all_items = []
    for rss_url, name, lang in RSS_SOURCES:
        try:
            crawler = RSSCrawler(rss_url, name)
            items = crawler.fetch_items()
            for it in items:
                it["lang_hint"] = lang
            logger.info(f"[{name}] {len(items)} item dari RSS ({lang})")
            all_items.extend(items)
        except Exception as e:
            logger.error(f"Gagal RSS {name}: {e}")

    logger.info(f"Total item dari RSS: {len(all_items)}")

    results = []
    fetched_urls = set()

    for cat in categories:
        cat_name = cat["name"]
        cat_keywords = cat["keywords"]
        matched = 0
        limit = per_keyword_limit * len(cat_keywords)

        for item in all_items:
            if matched >= limit:
                break
            if item["url"] in fetched_urls:
                continue

            text = f"{item['title']} {item.get('summary', '')}"
            kw = match_keyword(text, cat_keywords)
            if not kw:
                continue

            # Deteksi bahasa: pakai hint dari RSS, validasi dengan konten judul+summary
            lang = item.get("lang_hint") or detect_language(text)

            art = _fetch_one(item, cat_name, kw, lang)
            if art:
                results.append(art)
                fetched_urls.add(item["url"])
                matched += 1

        logger.info(f"[{cat_name}] match & fetch {matched} artikel")

    # Lain-lain: sisa item yang belum ke-fetch
    lain_matched = 0
    for item in all_items:
        if lain_matched >= lain_lain_limit:
            break
        if item["url"] in fetched_urls:
            continue

        text = f"{item['title']} {item.get('summary', '')}"
        lang = item.get("lang_hint") or detect_language(text)
        art = _fetch_one(item, "lain-lain", "-", lang)
        if art:
            results.append(art)
            fetched_urls.add(item["url"])
            lain_matched += 1

    logger.info(f"[lain-lain] match & fetch {lain_matched} artikel")

    return results