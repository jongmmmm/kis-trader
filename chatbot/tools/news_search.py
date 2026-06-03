"""
뉴스 검색 모듈 — Google News RSS (국내 + 해외)
✅ 파서: lxml-xml (pip install lxml 필요)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
from urllib.parse import quote

try:
    from chatbot.cache_manager import get_cache, set_cache
    _USE_CM = True
except ImportError:
    _USE_CM = False

_mem_cache: dict = {}

def _get(key):
    return get_cache("news", key) if _USE_CM else _mem_cache.get(key)

def _set(key, val):
    if _USE_CM: set_cache("news", key, val)
    else: _mem_cache[key] = val


def _google_rss(query: str, date_str: str, lang: str = "ko", max_results: int = 5) -> list:
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        before = (target + timedelta(days=3)).strftime("%Y-%m-%d")
        after  = (target - timedelta(days=3)).strftime("%Y-%m-%d")

        if lang == "en":
            url = ("https://news.google.com/rss/search"
                   f"?q={quote(query)}+after:{after}+before:{before}"
                   f"&hl=en&gl=US&ceid=US:en")
        else:
            url = ("https://news.google.com/rss/search"
                   f"?q={quote(query)}+after:{after}+before:{before}"
                   f"&hl=ko&gl=KR&ceid=KR:ko")

        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        # ✅ xml → lxml-xml 로 변경
        soup = BeautifulSoup(resp.content, "lxml-xml")

        results = []
        for item in soup.find_all("item")[:max_results]:
            t = item.find("title")
            l = item.find("link")
            p = item.find("pubDate")
            s = item.find("source")
            if t:
                results.append({
                    "title":    t.get_text(strip=True),
                    "link":     l.get_text(strip=True) if l else "",
                    "pub_date": p.get_text(strip=True) if p else "",
                    "source":   s.get_text(strip=True) if s else "google",
                })
        return results
    except Exception:
        return []


def _dedup(news_list: list) -> list:
    seen, unique = set(), []
    for n in news_list:
        key = n["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique


def get_titles(news_list: list) -> list:
    return [n["title"] for n in news_list if n.get("title")]


def search_news(stock_code: str, stock_name: str,
                date_str: str = None, is_overseas: bool = False,
                max_results: int = 5) -> list:
    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")

    cache_key = f"{'OV' if is_overseas else 'KR'}_{stock_code}_{date_str}"
    cached = _get(cache_key)
    if cached is not None:
        return cached

    results = []
    if not is_overseas:
        query   = stock_name if stock_name else stock_code
        results = _google_rss(query, date_str, lang="ko", max_results=max_results)
        if not results and stock_name:
            results = _google_rss(stock_code, date_str, lang="ko", max_results=max_results)
    else:
        ko_query = f"{stock_name} {stock_code}" if stock_name else stock_code
        results.extend(_google_rss(ko_query, date_str, lang="ko", max_results=max_results))
        results.extend(_google_rss(stock_code, date_str, lang="en", max_results=max_results))
        results = _dedup(results)[:max_results]

    _set(cache_key, results)
    return results