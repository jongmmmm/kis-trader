# ============================================================
# cache_manager.py
# 역할: API/크롤링 결과 캐싱 — 중복 호출 방지
# 현재가 5분 / 뉴스 30분 / 재무제표 1시간
# ============================================================

import time

_cache = {}

TTL = {
    "price":   5  * 60,
    "news":    30 * 60,
    "finance": 60 * 60,
}

def _make_key(category: str, keyword: str) -> str:
    return f"{category}:{keyword}"

def get_cache(category: str, keyword: str):
    key  = _make_key(category, keyword)
    item = _cache.get(key)
    if item is None:
        return None
    if time.time() > item["expires_at"]:
        del _cache[key]
        return None
    return item["value"]

def set_cache(category: str, keyword: str, value):
    key = _make_key(category, keyword)
    _cache[key] = {
        "value":      value,
        "expires_at": time.time() + TTL.get(category, 5 * 60),
    }

def clear_cache():
    _cache.clear()