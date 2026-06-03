# ============================================================
# tool_registry.py
# 역할: Agent가 사용할 도구 목록 등록
# ============================================================

import os
import sys
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import Tool

_THIS_DIR  = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(_THIS_DIR, "tools")

for _p in [_THIS_DIR, _TOOLS_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cache_manager import get_cache, set_cache
from kis_api       import get_current_price, get_overseas_current_price
from news_search   import search_news, get_titles

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

_NAVER_INDEX_MAP = {
    "코스피": "KOSPI", "kospi": "KOSPI",
    "코스닥": "KOSDAQ", "kosdaq": "KOSDAQ",
    "코스피200": "KPI200",
    "나스닥": "NAS", "nasdaq": "NAS",
    "다우": "DJI", "dow": "DJI",
    "s&p500": "SPI", "sp500": "SPI", "s&p 500": "SPI",
}

_KNOWN_CODES = {
    "삼성전자": "005930", "sk하이닉스": "000660", "lg에너지솔루션": "373220",
    "삼성바이오로직스": "207940", "현대차": "005380", "기아": "000270",
    "셀트리온": "068270", "포스코홀딩스": "005490", "카카오": "035720",
    "네이버": "035420", "naver": "035420", "kakao": "035720",
    "삼성sdi": "006400", "lg화학": "051910", "kb금융": "105560",
    "신한지주": "055550", "하나금융지주": "086790", "카카오뱅크": "323410",
    "sk텔레콤": "017670", "kt": "030200", "lg전자": "066570",
}


def _name_to_code(query: str) -> str:
    query = query.strip()
    if query.isdigit() and len(query) == 6:
        return query
    lower = query.lower().replace(" ", "")
    for name, code in _KNOWN_CODES.items():
        if name.replace(" ", "") in lower or lower in name.replace(" ", ""):
            return code
    try:
        url  = f"https://ac.finance.naver.com/nameSearch.nhn?query={query}"
        resp = requests.get(url, headers=_HEADERS, timeout=5)
        data = resp.json()
        items = data.get("items", [[]])[0]
        if items:
            return items[0].get("code", query)
    except Exception:
        pass
    return query


def _crawl_index(name: str) -> str:
    try:
        name_lower = name.lower().strip()
        naver_code = None
        for k, v in _NAVER_INDEX_MAP.items():
            if k in name_lower or name_lower in k:
                naver_code = v
                break
        if not naver_code:
            return f"{name} 지수를 찾을 수 없습니다."

        url  = f"https://finance.naver.com/sise/sise_index.naver?code={naver_code}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        value = soup.select_one("#now_value")
        diff  = soup.select_one("#change_value")
        rate  = soup.select_one("#change_rate")

        if value:
            val_text  = value.get_text(strip=True)
            diff_text = diff.get_text(strip=True) if diff else "0"
            rate_text = rate.get_text(strip=True) if rate else "0"
            try:
                sign = "▲" if float(diff_text.replace(",", "")) > 0 else ("▼" if float(diff_text.replace(",", "")) < 0 else "-")
            except Exception:
                sign = "-"
            return f"[{name} 지수]\n현재:   {val_text}\n등락:   {sign} {diff_text} ({rate_text})"
        return f"{name} 지수 데이터를 가져올 수 없습니다."
    except Exception as e:
        return f"{name} 지수 조회 오류: {e}"


def _crawl_financial(name: str) -> str:
    try:
        code = _name_to_code(name)
        if not code or not code.isdigit():
            return f"{name}의 종목코드를 찾을 수 없습니다."

        lines = [f"[{name} ({code}) 연간 재무제표]"]

        # ✅ 네이버 금융 재무제표 전용 페이지
        url  = f"https://finance.naver.com/item/finstate.naver?code={code}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 연간 재무제표 테이블 찾기
        for table in soup.select("table.tb_type1, table.tb_type1_s"):
            ths = " ".join(th.get_text(strip=True) for th in table.select("th"))
            if any(k in ths for k in ["매출액", "영업이익", "당기순이익"]):
                # 헤더
                headers = [th.get_text(strip=True) for th in table.select("thead th")]
                if headers:
                    lines.append(" | ".join(headers))
                    lines.append("-" * 70)
                # 데이터
                for row in table.select("tbody tr"):
                    cells = [td.get_text(strip=True) for td in row.select("td")]
                    if cells and cells[0]:
                        lines.append(" | ".join(cells))
                break

        if len(lines) == 1:
            # 대안: wisefn 재무제표
            url2  = f"https://finance.naver.com/item/coinfo.naver?code={code}&target=finsum_more"
            resp2 = requests.get(url2, headers=_HEADERS, timeout=10)
            resp2.encoding = "euc-kr"
            soup2 = BeautifulSoup(resp2.text, "html.parser")

            for table in soup2.select("table"):
                ths = " ".join(th.get_text(strip=True) for th in table.select("th"))
                if any(k in ths for k in ["매출액", "영업이익", "EPS", "ROE"]):
                    headers = [th.get_text(strip=True) for th in table.select("th")][:6]
                    if headers:
                        lines.append(" | ".join(headers))
                        lines.append("-" * 70)
                    for row in table.select("tr")[1:10]:
                        cells = [td.get_text(strip=True) for td in row.select("td")]
                        if cells and cells[0]:
                            lines.append(" | ".join(cells))
                    break

        if len(lines) == 1:
            lines.append("재무제표를 가져올 수 없습니다. 네이버 금융(finance.naver.com)에서 직접 확인해주세요.")

        return "\n".join(lines)

    except Exception as e:
        return f"재무제표 조회 오류: {e}"


# ═══════════════════════════════════════════════
# 도구 함수
# ═══════════════════════════════════════════════

def get_stock_price(query: str) -> str:
    cached = get_cache("price", query)
    if cached: return cached
    try:
        is_overseas = any(c.isupper() and c.isascii() for c in query.replace(" ", ""))
        if is_overseas:
            data  = get_overseas_current_price(query, excd="NAS")
            sign  = "▲" if data["change_rate"] > 0 else ("▼" if data["change_rate"] < 0 else "-")
            result = (
                f"[{query} 현재가]\n"
                f"현재가: {data['price']:,.2f} {data['currency']}\n"
                f"등락:   {sign} {abs(data['change_val']):.2f} ({data['change_rate']:+.2f}%)\n"
                f"시가: {data['open']:,.2f} / 고가: {data['high']:,.2f} / 저가: {data['low']:,.2f}\n"
                f"거래량: {data['volume']:,}"
            )
        else:
            code = _name_to_code(query)
            data = get_current_price(code)
            sign = {"1": "▲", "2": "▲", "3": "-", "4": "▼", "5": "▼"}.get(data["change_sign"], "-")
            result = (
                f"[{query} ({code}) 현재가]\n"
                f"현재가:   {data['price']:,}원\n"
                f"등락:     {sign} {abs(data['change_val']):,}원 ({data['change_rate']:+.2f}%)\n"
                f"시가: {data['open']:,} / 고가: {data['high']:,} / 저가: {data['low']:,}\n"
                f"거래량:   {data['volume']:,}\n"
                f"시가총액: {data['market_cap']:,}억원 | PER: {data['per']} | PBR: {data['pbr']}"
            )
    except Exception as e:
        result = f"{query} 현재가 조회 실패: {e}"
    set_cache("price", query, result)
    return result


def get_market_index(name: str) -> str:
    cached = get_cache("price", f"index_{name}")
    if cached: return cached
    result = _crawl_index(name)
    set_cache("price", f"index_{name}", result)
    return result


def get_stock_news(query: str) -> str:
    cached = get_cache("news", query)
    if cached: return cached
    is_overseas = any(c.isupper() and c.isascii() for c in query.replace(" ", ""))
    news_list   = search_news(
        stock_code=query, stock_name=query,
        is_overseas=is_overseas, max_results=5,
    )
    titles = get_titles(news_list)
    if not titles:
        result = f"'{query}' 관련 뉴스를 찾을 수 없습니다."
    else:
        label  = "🌍 해외" if is_overseas else "🇰🇷 국내"
        result = f"[{label} 뉴스 — {query}]\n" + "\n".join(
            f"{i+1}. {t}" for i, t in enumerate(titles)
        )
    set_cache("news", query, result)
    return result


def get_financial(name: str) -> str:
    cached = get_cache("finance", name)
    if cached: return cached
    result = _crawl_financial(name)
    set_cache("finance", name, result)
    return result


# ═══════════════════════════════════════════════
# Agent 도구 목록
# ═══════════════════════════════════════════════

def get_tools() -> list:
    return [
        Tool(name="Stock_Price", func=get_stock_price,
             description="주식 현재가 조회. 종목명(삼성전자), 종목코드(005930), 해외티커(AAPL) 가능. 예: Stock_Price('삼성전자')"),
        Tool(name="Market_Index", func=get_market_index,
             description="시장 지수 조회. 코스피, 코스닥, 나스닥, 다우, S&P500. 예: Market_Index('코스피')"),
        Tool(name="Stock_News", func=get_stock_news,
             description="최신 뉴스 검색. 주가 하락/상승 원인 분석. 예: Stock_News('삼성전자'), Stock_News('NVDA')"),
        Tool(name="Financial_Statement", func=get_financial,
             description="재무제표 조회. 매출액, 영업이익, 당기순이익, PER, PBR, ROE 등. 예: Financial_Statement('삼성전자')"),
    ]