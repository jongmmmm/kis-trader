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

from chatbot.cache_manager import get_cache, set_cache
from chatbot.tools.kis_api import (
    get_current_price, get_overseas_current_price,
    get_balance as _kis_get_balance, place_order as _kis_place_order,
    get_volume_rank as _kis_get_volume_rank, get_fx_rate as _kis_get_fx_rate,
)
from chatbot.tools.news_search import search_news, get_titles

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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


# ═══════════════════════════════════════════════
# ✅ DART API — 재무제표 (중복제거 + 억원 변환)
# ═══════════════════════════════════════════════

def _to_억(val_str: str) -> str:
    """원 → 억원 변환"""
    try:
        v = int(val_str.replace(",", ""))
        억 = v // 100_000_000
        if abs(억) >= 10000:
            return f"{억/10000:.1f}조원"
        return f"{억:,}억원"
    except Exception:
        return val_str or "-"


def _get_dart_corp_code(stock_code: str) -> str:
    dart_key = os.environ.get("DART_API_KEY", "")
    if not dart_key:
        return ""
    try:
        import zipfile, io
        import xml.etree.ElementTree as ET
        url  = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={dart_key}"
        resp = requests.get(url, timeout=20)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            with z.open("CORPCODE.xml") as f:
                tree = ET.parse(f)
                for item in tree.getroot().findall("list"):
                    if item.findtext("stock_code") == stock_code:
                        return item.findtext("corp_code", "")
    except Exception:
        pass
    return ""


def _get_dart_financial(name: str) -> str:
    dart_key = os.environ.get("DART_API_KEY", "")
    if not dart_key:
        return ""
    try:
        from datetime import date
        code      = _name_to_code(name)
        corp_code = _get_dart_corp_code(code)
        if not corp_code:
            return ""

        year   = date.today().year - 1
        url    = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
        params = {
            "crtfc_key": dart_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div":    "CFS",
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "000":
            return ""

        # 원하는 항목 + 순서
        _WANT = {
            "ifrs-full_Revenue":           "매출액",
            "dart_OperatingIncomeLoss":    "영업이익",
            "ifrs-full_ProfitLoss":        "당기순이익",
            "ifrs-full_Assets":            "자산총계",
            "ifrs-full_Equity":            "자본총계",
            "ifrs-full_Liabilities":       "부채총계",
            "dart_cf_OperatingActivities": "영업활동현금흐름",
        }
        _ORDER = ["매출액", "영업이익", "당기순이익", "자산총계", "자본총계", "부채총계", "영업활동현금흐름"]

        # 중복 제거: 처음 나오는 항목만 사용
        seen = set()
        rows = []
        for item in data.get("list", []):
            key = item.get("account_id", "")
            if key in _WANT and key not in seen:
                seen.add(key)
                label   = _WANT[key]
                current = item.get("thstrm_amount", "")
                prev    = item.get("frmtrm_amount", "")
                rows.append((label, _to_억(current), _to_억(prev)))

        # 원하는 순서로 정렬
        rows.sort(key=lambda r: _ORDER.index(r[0]) if r[0] in _ORDER else 99)

        lines = [f"[{name} ({code}) {year}년 연간 재무제표 (연결기준)]"]
        lines.append(f"{'항목':<16} {'당기(' + str(year) + ')':>14} {'전기(' + str(year-1) + ')':>14}")
        lines.append("─" * 46)
        for label, cur, prv in rows:
            lines.append(f"{label:<16} {cur:>14} {prv:>14}")
        lines.append("\n※ 단위: 억원 / 조원")
        return "\n".join(lines)

    except Exception:
        return ""


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
    result = _get_dart_financial(name)
    if not result:
        code   = _name_to_code(name)
        result = (
            f"[{name} 재무제표 조회 실패]\n"
            f"DART API 키를 확인하거나 잠시 후 다시 시도해주세요.\n"
            f"직접 확인: https://finance.naver.com/item/coinfo.naver?code={code}"
        )
    set_cache("finance", name, result)
    return result


# ═══════════════════════════════════════════════
# 잔고 / 매수·매도 / 거래량 / 환율
# ═══════════════════════════════════════════════

def get_check_balance(mode: str = "paper") -> str:
    """모의투자 계좌 잔고를 조회합니다."""
    try:
        mode = mode.strip().lower() if mode else "paper"
        if mode not in ("paper", "real"):
            mode = "paper"
        holdings = _kis_get_balance(mode)
        if not holdings:
            return "보유 종목이 없습니다."
        lines = [f"[{'모의' if mode == 'paper' else '실전'}투자 보유 종목]"]
        total_profit = 0
        for h in holdings:
            lines.append(
                f"  {h['stock_name']}({h['stock_code']}) "
                f"{h['quantity']}주 | 평단가 {h['avg_price']:,.0f}원 | "
                f"현재가 {h['current_price']:,}원 | "
                f"손익 {h['eval_profit_loss']:+,.0f}원 ({h['profit_loss_rate']:+.2f}%)"
            )
            total_profit += h["eval_profit_loss"]
        lines.append(f"\n  총 평가손익: {total_profit:+,.0f}원")
        return "\n".join(lines)
    except Exception as e:
        return f"잔고 조회 오류: {e}"


def do_buy_stock(args_json: str) -> str:
    """주식 매수. 입력: 'stock_code,price,quantity' (예: '005930,70000,10')"""
    try:
        parts = [p.strip() for p in args_json.split(",")]
        stock_code, price, quantity = parts[0], int(parts[1]), int(parts[2])
        result = _kis_place_order(stock_code, "buy", price, quantity)
        if result["success"]:
            return f"매수 주문 성공! 주문번호: {result['order_no']}"
        return f"매수 주문 실패: {result['message']}"
    except Exception as e:
        return f"매수 오류: {e}"


def do_sell_stock(args_json: str) -> str:
    """주식 매도. 입력: 'stock_code,price,quantity' (예: '005930,75000,5')"""
    try:
        parts = [p.strip() for p in args_json.split(",")]
        stock_code, price, quantity = parts[0], int(parts[1]), int(parts[2])
        result = _kis_place_order(stock_code, "sell", price, quantity)
        if result["success"]:
            return f"매도 주문 성공! 주문번호: {result['order_no']}"
        return f"매도 주문 실패: {result['message']}"
    except Exception as e:
        return f"매도 오류: {e}"


def get_volume_ranking(_input: str = "") -> str:
    """거래량 상위 종목 순위를 조회합니다."""
    try:
        ranks = _kis_get_volume_rank()
        lines = ["[거래량 TOP 10]"]
        for r in ranks[:10]:
            sign = "+" if r["change_rate"] > 0 else ""
            lines.append(
                f"  {r['rank']:2d}. {r['stock_name']:<10s} "
                f"{r['price']:>10,}원 ({sign}{r['change_rate']:.2f}%) "
                f"거래량 {r['volume']:>12,}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"거래량 순위 조회 오류: {e}"


def get_exchange_rate(currency: str = "달러") -> str:
    """환율을 조회합니다. 달러, 유로, 엔을 지원합니다. (네이버 크롤링)"""
    try:
        currency = currency.strip() if currency else "달러"
        fx_map = {"달러": "USD", "유로": "EUR", "엔": "JPY", "위안": "CNY"}
        code = fx_map.get(currency, "USD")
        url = f"https://finance.naver.com/marketindex/exchangeDailyQuote.naver?marketindexCd=FX_{code}KRW"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        row = soup.select_one("table.tbl_exchange tbody tr")
        if row:
            cols = row.select("td")
            rate = cols[1].get_text(strip=True) if len(cols) > 1 else "N/A"
            diff = cols[2].get_text(strip=True) if len(cols) > 2 else "0"
            return f"[{currency}/원 환율]\n현재: {rate}원 (전일대비 {diff}원)"
        return f"{currency} 환율 정보를 가져올 수 없습니다."
    except Exception as e:
        return f"환율 조회 오류: {e}"


# ═══════════════════════════════════════════════
# Agent 도구 목록
# ═══════════════════════════════════════════════

def get_tools() -> list:
    return [
        Tool(
            name="Stock_Price",
            func=get_stock_price,
            description=(
                "주식 현재가를 조회합니다. "
                "종목명(삼성전자), 종목코드(005930), 해외티커(AAPL) 모두 가능합니다. "
                "예: '삼성전자 현재가' → Stock_Price('삼성전자'), '애플 주가' → Stock_Price('AAPL')"
            ),
        ),
        Tool(
            name="Market_Index",
            func=get_market_index,
            description=(
                "시장 지수를 조회합니다. 국내: 코스피, 코스닥, 코스피200. 해외: 나스닥, 다우, S&P500. "
                "예: '코스피 지수' → Market_Index('코스피'), '나스닥' → Market_Index('나스닥')"
            ),
        ),
        Tool(
            name="Stock_News",
            func=get_stock_news,
            description=(
                "종목명 또는 키워드로 최신 뉴스를 검색합니다. "
                "주가 하락/상승 원인, 시장 동향 파악에 사용하세요. "
                "예: '삼성전자 왜 떨어졌어?' → Stock_News('삼성전자'), 'NVDA 뉴스' → Stock_News('NVDA')"
            ),
        ),
        Tool(
            name="Financial_Statement",
            func=get_financial,
            description=(
                "DART API로 연간 재무제표를 조회합니다. "
                "매출액, 영업이익, 당기순이익, 자산총계, 자본총계, 부채총계 등. "
                "예: '삼성전자 재무제표' → Financial_Statement('삼성전자'), "
                "'SK하이닉스 재무정보' → Financial_Statement('SK하이닉스')"
            ),
        ),
        Tool(
            name="Check_Balance",
            func=get_check_balance,
            description=(
                "모의투자 계좌의 보유 종목과 잔고를 조회합니다. "
                "예: '내 잔고', '보유종목', '포트폴리오' → Check_Balance('paper')"
            ),
        ),
        Tool(
            name="Buy_Stock",
            func=do_buy_stock,
            description=(
                "주식을 매수합니다. 반드시 사용자 확인 후 호출하세요. "
                "입력 형식: 'stock_code,price,quantity'. "
                "예: 삼성전자 10주 70000원 매수 → Buy_Stock('005930,70000,10')"
            ),
        ),
        Tool(
            name="Sell_Stock",
            func=do_sell_stock,
            description=(
                "주식을 매도합니다. 반드시 사용자 확인 후 호출하세요. "
                "입력 형식: 'stock_code,price,quantity'. "
                "예: 삼성전자 5주 75000원 매도 → Sell_Stock('005930,75000,5')"
            ),
        ),
        Tool(
            name="Volume_Rank",
            func=get_volume_ranking,
            description=(
                "거래량 상위 종목 순위를 조회합니다. "
                "예: '거래량 순위', '많이 거래된 종목' → Volume_Rank('')"
            ),
        ),
        Tool(
            name="Exchange_Rate",
            func=get_exchange_rate,
            description=(
                "환율을 조회합니다. 달러, 유로, 엔을 지원합니다. "
                "예: '달러 환율' → Exchange_Rate('달러'), '엔화' → Exchange_Rate('엔')"
            ),
        ),
    ]