# ============================================================
# tool_registry.py
# 역할: Agent가 사용할 도구 목록 등록 (v3.4 — 전체 버그수정 완료)
# BUG FIX 목록:
#   #1  __HEADERS → _HEADERS (NameError 수정)
#   #2  DART 법인코드 인메모리 캐시 (매번 ZIP 다운로드 방지)
#   #3  DART year-1 폴백 → year-2 재시도
#   #4  네이버 finstate euc-kr 명시 디코딩
#   #5  현재가 실패 결과 캐싱 방지 (에러 캐시 버그)
#   #6  _crawl_naver_current_price 네이버 폴백 추가
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
from kis_api       import get_current_price, get_overseas_current_price, get_investor_trade
from news_search   import search_news, get_titles


# ════════════════════════════════════════════
# 공통 상수
# ════════════════════════════════════════════

# BUG FIX #1: __HEADERS → _HEADERS
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer":         "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_NAVER_INDEX_MAP = {
    "코스피":   "KOSPI",  "kospi":   "KOSPI",
    "코스닥":   "KOSDAQ", "kosdaq":  "KOSDAQ",
    "코스피200": "KPI200",
    "나스닥":   "NAS",    "nasdaq":  "NAS",
    "다우":     "DJI",    "dow":     "DJI",
    "s&p500":   "SPI",    "sp500":   "SPI",   "s&p 500": "SPI",
}

_KNOWN_CODES = {
    "삼성전자":       "005930",
    "sk하이닉스":     "000660", "하이닉스":       "000660",
    "lg에너지솔루션": "373220",
    "삼성바이오로직스":"207940", "삼바":           "207940",
    "현대차":         "005380", "현대자동차":      "005380",
    "기아":           "000270", "기아차":          "000270",
    "셀트리온":       "068270",
    "포스코홀딩스":   "005490", "포스코":          "005490",
    "카카오":         "035720", "kakao":           "035720",
    "네이버":         "035420", "naver":           "035420",
    "삼성sdi":        "006400",
    "lg화학":         "051910",
    "kb금융":         "105560",
    "신한지주":       "055550", "신한":            "055550",
    "하나금융지주":   "086790", "하나금융":        "086790",
    "카카오뱅크":     "323410",
    "sk텔레콤":       "017670", "skt":             "017670",
    "kt":             "030200",
    "lg전자":         "066570",
    "삼성생명":       "032830",
    "한화생명":       "088350",
    "삼성화재":       "000810",
    "한화에어로스페이스": "012450", "한화에어로":  "012450",
    "현대모비스":     "012330",
    "sk이노베이션":   "096770", "sk이노":          "096770",
    "삼성물산":       "028260",
    "두산에너빌리티": "034020",
    "카카오페이":     "377300",
    "크래프톤":       "259960",
    "엔씨소프트":     "036570", "엔씨":            "036570",
    "에코프로비엠":   "247540",
    "에코프로":       "086520",
    "포스코퓨처엠":   "003670",
    "lg이노텍":       "011070",
    "삼성전기":       "009150",
    "한국전력":       "015760", "한전":            "015760",
    "한미반도체":     "042700",
    "고려아연":       "010130",
    "현대건설":       "000720",
    "sk":             "034730",
    "lg":             "003550",
    "롯데케미칼":     "011170",
    "두산밥캣":       "241560",
    "넷마블":         "251270",
    "펄어비스":       "263750",
}

# BUG FIX #2: DART 법인코드 인메모리 캐시
_DART_CORP_CODE_CACHE: dict = {}


# ════════════════════════════════════════════
# 유틸리티
# ════════════════════════════════════════════

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
                sign = "▲" if float(diff_text.replace(",", "")) > 0 else (
                    "▼" if float(diff_text.replace(",", "")) < 0 else "-"
                )
            except Exception:
                sign = "-"
            return (
                f"[{name} 지수]\n"
                f"현재:   {val_text}\n"
                f"등락:   {sign} {diff_text} ({rate_text})"
            )
        return f"{name} 지수 데이터를 가져올 수 없습니다."
    except Exception as e:
        return f"{name} 지수 조회 오류: {e}"


# ════════════════════════════════════════════
# DART API — 재무제표
# ════════════════════════════════════════════

def _to_억(val_str: str) -> str:
    """원 단위 숫자 문자열 → 억원 / 조원"""
    try:
        v = int(str(val_str).replace(",", ""))
        억 = v // 100_000_000
        if abs(억) >= 10_000:
            return f"{억 / 10_000:.1f}조원"
        return f"{억:,}억원"
    except Exception:
        return val_str or "-"


def _get_dart_corp_code(stock_code: str) -> str:
    """
    BUG FIX #2: 최초 1회만 ZIP 다운로드, 이후 인메모리 캐시 사용
    """
    global _DART_CORP_CODE_CACHE

    if stock_code in _DART_CORP_CODE_CACHE:
        return _DART_CORP_CODE_CACHE[stock_code]

    dart_key = os.environ.get("DART_API_KEY", "")
    if not dart_key:
        return ""

    try:
        import zipfile
        import io
        import xml.etree.ElementTree as ET

        url  = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={dart_key}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            with z.open("CORPCODE.xml") as f:
                tree = ET.parse(f)
                for item in tree.getroot().findall("list"):
                    sc = item.findtext("stock_code", "").strip()
                    cc = item.findtext("corp_code",  "").strip()
                    if sc:
                        _DART_CORP_CODE_CACHE[sc] = cc

        return _DART_CORP_CODE_CACHE.get(stock_code, "")
    except Exception as e:
        print(f"[DART corp_code 오류] {e}")
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

        # BUG FIX #3: year-1 먼저, 실패 시 year-2 재시도
        base_year   = date.today().year - 1
        result_data = None

        for year in [base_year, base_year - 1]:
            url    = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
            params = {
                "crtfc_key":  dart_key,
                "corp_code":  corp_code,
                "bsns_year":  str(year),
                "reprt_code": "11011",  # 사업보고서(연간)
                "fs_div":     "CFS",    # 연결재무제표
            }
            resp   = requests.get(url, params=params, timeout=15)
            data   = resp.json()
            status = data.get("status", "")

            if status == "000":
                result_data = (year, data)
                break
            else:
                print(f"[DART] {name} {year}년 조회 실패 — status={status}, msg={data.get('message','')}")

        if not result_data:
            return ""

        year, data = result_data

        _WANT = {
            "ifrs-full_Revenue":           "매출액",
            "dart_OperatingIncomeLoss":    "영업이익",
            "ifrs-full_ProfitLoss":        "당기순이익",
            "ifrs-full_Assets":            "자산총계",
            "ifrs-full_Equity":            "자본총계",
            "ifrs-full_Liabilities":       "부채총계",
            "dart_cf_OperatingActivities": "영업활동현금흐름",
        }
        _ORDER = [
            "매출액", "영업이익", "당기순이익",
            "자산총계", "자본총계", "부채총계", "영업활동현금흐름",
        ]

        seen, rows = set(), []
        for item in data.get("list", []):
            key = item.get("account_id", "")
            if key in _WANT and key not in seen:
                seen.add(key)
                label   = _WANT[key]
                current = item.get("thstrm_amount", "")
                prev    = item.get("frmtrm_amount", "")
                rows.append((label, _to_억(current), _to_억(prev)))

        rows.sort(key=lambda r: _ORDER.index(r[0]) if r[0] in _ORDER else 99)

        lines = [f"[{name} ({code}) {year}년 연간 재무제표 (연결기준, DART)]"]
        lines.append(
            f"{'항목':<16} {'당기(' + str(year) + ')':>14} {'전기(' + str(year - 1) + ')':>14}"
        )
        lines.append("─" * 46)
        for label, cur, prv in rows:
            lines.append(f"{label:<16} {cur:>14} {prv:>14}")
        lines.append("\n※ 단위: 억원 / 조원  |  출처: DART 전자공시")
        return "\n".join(lines)

    except Exception as e:
        print(f"[DART 재무제표 오류] {name}: {e}")
        return ""


# ════════════════════════════════════════════
# 네이버 금융 크롤링 — 재무제표
# ════════════════════════════════════════════

def _crawl_naver_financial(name: str) -> str:
    try:
        code = _name_to_code(name)
        if not code or not code.isdigit():
            return ""

        _FINANCIAL_ITEMS = {
            "매출액", "영업수익", "보험료수익", "순이자수익", "수수료수익",
            "영업이익", "영업손익", "세전계속사업이익",
            "당기순이익", "당기순손익", "지배주주순이익",
            "자산총계", "유동자산", "비유동자산",
            "부채총계", "유동부채", "비유동부채",
            "자본총계", "자본금",
            "영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름",
        }
        _BLOCK = {
            "PER", "PBR", "EPS", "BPS", "ROE", "ROA", "EV",
            "배당", "수익률", "주당", "발행주식", "시가총액",
        }
        _ORDER = [
            "매출액", "영업수익", "보험료수익", "순이자수익",
            "영업이익", "영업손익",
            "당기순이익", "당기순손익", "지배주주순이익",
            "자산총계", "자본총계", "부채총계",
            "영업활동현금흐름",
        ]

        def _is_financial_row(label: str) -> bool:
            label_clean = label.replace(" ", "")
            if any(b in label for b in _BLOCK):
                return False
            return any(w.replace(" ", "") in label_clean for w in _FINANCIAL_ITEMS)

        def _is_year_header(cells: list) -> bool:
            return sum(1 for c in cells if len(c) >= 4 and c[:4].isdigit()) >= 2

        def _parse_soup(soup) -> tuple:
            for tbl in soup.select("table"):
                txt = tbl.get_text()
                if not any(w in txt for w in _FINANCIAL_ITEMS):
                    continue
                has_key = any(
                    w in txt for w in {
                        "영업이익", "당기순이익", "자산총계", "보험료수익", "매출액"
                    }
                )
                if not has_key:
                    continue

                years, rows = [], []
                for tr in tbl.select("tr"):
                    cells = [c.get_text(strip=True) for c in tr.select("th, td")]
                    if not cells or not cells[0]:
                        continue
                    if _is_year_header(cells) and not years:
                        years = cells
                        continue
                    if _is_financial_row(cells[0]):
                        rows.append(cells)

                if rows:
                    return years, rows
            return [], []

        years, rows = [], []

        # BUG FIX #4: euc-kr 명시 디코딩
        # ── 전략 1: finstate_all ──
        try:
            r   = requests.get(
                f"https://finance.naver.com/item/finstate_all.naver"
                f"?code={code}&fin_typ=0&freq_typ=Y",
                headers={**_HEADERS, "Accept-Encoding": "identity"},
                timeout=12,
            )
            raw = r.content.decode("euc-kr", errors="replace")
            years, rows = _parse_soup(BeautifulSoup(raw, "html.parser"))
        except Exception as e:
            print(f"[네이버 finstate_all 오류] {e}")

        # ── 전략 2: finstate 요약 ──
        if not rows:
            try:
                r2  = requests.get(
                    f"https://finance.naver.com/item/finstate.naver?code={code}",
                    headers={**_HEADERS, "Accept-Encoding": "identity"},
                    timeout=12,
                )
                raw2 = r2.content.decode("euc-kr", errors="replace")
                years, rows = _parse_soup(BeautifulSoup(raw2, "html.parser"))
            except Exception as e:
                print(f"[네이버 finstate 오류] {e}")

        # ── 전략 3: wisereport 폴백 ──
        if not rows:
            try:
                r3 = requests.get(
                    f"https://navercomp.wisereport.co.kr/v2/company/"
                    f"c1010001.aspx?cmp_cd={code}&cn=",
                    headers=_HEADERS,
                    timeout=12,
                )
                years, rows = _parse_soup(BeautifulSoup(r3.text, "html.parser"))
            except Exception as e:
                print(f"[wisereport 오류] {e}")

        if not rows:
            return ""

        yr_labels = [
            y for y in (years[1:] if years else [])
            if y and len(y) >= 4 and y[:4].isdigit()
        ]
        n_col = len(yr_labels) if yr_labels else min(4, max(len(r) - 1 for r in rows))
        LW, CW = 14, 13

        rows.sort(key=lambda r: next(
            (i for i, w in enumerate(_ORDER) if w in r[0].replace(" ", "")), 99
        ))

        seen, unique_rows = set(), []
        for r in rows:
            key = r[0].replace(" ", "")
            if key not in seen:
                seen.add(key)
                unique_rows.append(r)

        lines = [f"[{name} ({code}) 연간 재무제표]", ""]
        if yr_labels:
            lines.append(f"{'항목':<{LW}}" + "".join(f"{y:>{CW}}" for y in yr_labels))
            lines.append("─" * (LW + CW * len(yr_labels)))

        for cells in unique_rows:
            vals = cells[1:n_col + 1]
            lines.append(
                f"{cells[0]:<{LW}}" +
                "".join(f"{(v if v else '-'):>{CW}}" for v in vals)
            )

        lines.append("")
        lines.append("※ 출처: 네이버 금융  |  단위: 억원")
        return "\n".join(lines)

    except Exception as e:
        print(f"[_crawl_naver_financial 오류] {name}: {e}")
        return ""


def get_financial(name: str) -> str:
    cached = get_cache("finance", name)
    if cached:
        return cached

    # 1차: DART API
    result = _get_dart_financial(name)

    # 2차: 네이버 금융 폴백
    if not result:
        result = _crawl_naver_financial(name)

    if not result:
        code   = _name_to_code(name)
        result = (
            f"[{name} 재무제표 조회 실패]\n"
            f"DART API 오류 및 네이버 금융 크롤링 실패.\n"
            f"직접 확인: https://finance.naver.com/item/coinfo.naver?code={code}"
        )

    set_cache("finance", name, result)
    return result


# ════════════════════════════════════════════
# BUG FIX #6: 네이버 현재가 폴백 크롤러 (신규)
# ════════════════════════════════════════════

def _crawl_naver_current_price(code: str) -> dict:
    """KIS API 최종 실패 시 네이버 금융 현재가 크롤링 폴백"""
    try:
        url  = f"https://finance.naver.com/item/main.naver?code={code}"
        resp = requests.get(
            url,
            headers={**_HEADERS, "Accept-Encoding": "identity"},
            timeout=10,
        )
        raw  = resp.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")

        # 현재가
        price_el = soup.select_one("p.no_today span.blind")
        if not price_el:
            return {}
        price = int(price_el.get_text(strip=True).replace(",", ""))

        # 등락
        change_el   = soup.select_one("p.no_exday .no_up, p.no_exday .no_down")
        change_val  = 0
        change_rate = 0.0
        sign        = "-"
        if change_el:
            blinds = change_el.select("span.blind")
            sign   = "▲" if "no_up" in change_el.get("class", []) else "▼"
            try:
                change_val  = int(blinds[0].get_text(strip=True).replace(",", ""))
                change_rate = float(blinds[1].get_text(strip=True).replace(",", ""))
            except Exception:
                pass

        # 시가 / 고가 / 저가
        ohlc = {}
        for em in soup.select(
            "table.no_info em.no_color, "
            "table.no_info em.no_up, "
            "table.no_info em.no_down"
        ):
            blind = em.select_one("span.blind")
            if blind:
                label = em.find_previous("th")
                if label:
                    k = label.get_text(strip=True)
                    try:
                        ohlc[k] = int(blind.get_text(strip=True).replace(",", ""))
                    except Exception:
                        pass

        return {
            "price":       price,
            "change_val":  change_val,
            "change_rate": change_rate,
            "sign":        sign,
            "open":        ohlc.get("시가", 0),
            "high":        ohlc.get("고가", 0),
            "low":         ohlc.get("저가", 0),
        }
    except Exception as e:
        print(f"[네이버 현재가 크롤링 오류] {code}: {e}")
        return {}


# ════════════════════════════════════════════
# 수급 — 네이버 폴백
# ════════════════════════════════════════════

def _crawl_naver_investor(code: str) -> dict:
    try:
        url  = f"https://finance.naver.com/item/frgn.naver?code={code}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        raw  = resp.content.decode("euc-kr", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")

        table = soup.select_one("table.type2")
        if not table:
            return {}

        for tr in table.select("tr"):
            tds = tr.select("td")
            if len(tds) < 5:
                continue
            texts = [
                td.get_text(strip=True).replace(",", "").replace("+", "")
                for td in tds
            ]
            try:
                foreign  = int(texts[2]) if texts[2].lstrip("-").isdigit() else 0
                institut = int(texts[3]) if texts[3].lstrip("-").isdigit() else 0
                personal = -(foreign + institut)
                return {
                    "foreign_net_buy":     foreign,
                    "institution_net_buy": institut,
                    "personal_net_buy":    personal,
                    "date":                texts[0] if texts[0] else "당일",
                    "source":              "naver",
                }
            except Exception:
                continue
        return {}
    except Exception as e:
        print(f"[_crawl_naver_investor 오류] {e}")
        return {}


# ════════════════════════════════════════════
# 도구 함수
# ════════════════════════════════════════════

def get_stock_price(query: str) -> str:
    cached = get_cache("price", query)
    if cached:
        return cached

    is_overseas = any(c.isupper() and c.isascii() for c in query.replace(" ", ""))
    code        = _name_to_code(query)
    result      = None  # BUG FIX #5: None 초기화 → 성공 시에만 캐싱

    # ── 1차: KIS API (내부에서 401복구 + retry 자동처리) ──
    try:
        if is_overseas:
            data = get_overseas_current_price(query, excd="NAS")
            sign = "▲" if data["change_rate"] > 0 else ("▼" if data["change_rate"] < 0 else "-")
            result = (
                f"[{query} 현재가]\n"
                f"현재가: {data['price']:,.2f} {data['currency']}\n"
                f"등락:   {sign} {abs(data['change_val']):.2f} ({data['change_rate']:+.2f}%)\n"
                f"시가: {data['open']:,.2f} / 고가: {data['high']:,.2f} / 저가: {data['low']:,.2f}\n"
                f"거래량: {data['volume']:,}"
            )
        else:
            data = get_current_price(code)
            sign = {"1": "▲", "2": "▲", "3": "-", "4": "▼", "5": "▼"}.get(
                data["change_sign"], "-"
            )
            result = (
                f"[{query} ({code}) 현재가]  ※출처: KIS API\n"
                f"현재가:   {data['price']:,}원\n"
                f"등락:     {sign} {abs(data['change_val']):,}원 ({data['change_rate']:+.2f}%)\n"
                f"시가: {data['open']:,} / 고가: {data['high']:,} / 저가: {data['low']:,}\n"
                f"거래량:   {data['volume']:,}\n"
                f"시가총액: {data['market_cap']:,}억원 | PER: {data['per']} | PBR: {data['pbr']}"
            )
    except Exception as e:
        print(f"[KIS API 최종 실패] {query}: {e}")

    # BUG FIX #6: ── 2차: 네이버 현재가 폴백 (국내주만) ──
    if result is None and not is_overseas and code.isdigit():
        print(f"[네이버 폴백 시도] {query} ({code})")
        nv = _crawl_naver_current_price(code)
        if nv:
            result = (
                f"[{query} ({code}) 현재가]  ※출처: 네이버 금융(KIS 불가)\n"
                f"현재가:   {nv['price']:,}원\n"
                f"등락:     {nv['sign']} {nv['change_val']:,}원 ({nv['change_rate']:+.2f}%)\n"
                f"시가: {nv['open']:,} / 고가: {nv['high']:,} / 저가: {nv['low']:,}"
            )

    # ── 최종 실패 — 에러는 캐싱 안 함 ──
    if result is None:
        return (
            f"{query} 현재가 조회 실패 (KIS API + 네이버 모두 실패)\n"
            f"직접 확인: https://finance.naver.com/item/main.naver?code={code}"
        )

    set_cache("price", query, result)  # ✅ 성공 결과만 캐싱
    return result


def get_market_index(name: str) -> str:
    cached = get_cache("price", f"index_{name}")
    if cached:
        return cached
    result = _crawl_index(name)
    set_cache("price", f"index_{name}", result)
    return result


def get_stock_news(query: str) -> str:
    cached = get_cache("news", query)
    if cached:
        return cached

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


def get_stock_investor_trade(query: str) -> str:
    code = _name_to_code(query)
    f_net, i_net, p_net, date_str, source = 0, 0, 0, "당일", "KIS API"

    kis_ok = False
    try:
        data = get_investor_trade(code)
        if "error" not in data:
            f_net    = data.get("foreign_net_buy", 0)
            i_net    = data.get("institution_net_buy", 0)
            p_net    = data.get("personal_net_buy", 0)
            date_str = data.get("date", "당일") or "당일"
            kis_ok   = True
    except Exception:
        pass

    if not kis_ok:
        nv = _crawl_naver_investor(code)
        if nv:
            f_net    = nv.get("foreign_net_buy", 0)
            i_net    = nv.get("institution_net_buy", 0)
            p_net    = nv.get("personal_net_buy", 0)
            date_str = nv.get("date", "당일")
            source   = "네이버 금융"
        else:
            return (
                f"📊 [{query}] 수급 현황\n"
                f"- KIS API 및 네이버 금융 모두 수급 데이터를 가져오지 못했습니다.\n"
                f"  직접 확인: https://finance.naver.com/item/frgn.naver?code={code}"
            )

    smart_total = f_net + i_net
    smart_label = "순매수" if smart_total > 0 else "순매도"
    f_label = ("▲ 순매수" if f_net > 0 else "▼ 순매도") if f_net != 0 else "- 보합"
    i_label = ("▲ 순매수" if i_net > 0 else "▼ 순매도") if i_net != 0 else "- 보합"
    p_label = ("▲ 순매수" if p_net > 0 else "▼ 순매도") if p_net != 0 else "- 보합"

    return (
        f"📊 [{query} ({code})] 수급 현황 ({date_str})  ※출처: {source}\n"
        f"- 외국인: {f_label}  {f_net:+,}주\n"
        f"- 기관:   {i_label}  {i_net:+,}주\n"
        f"- 개인:   {p_label}  {p_net:+,}주\n"
        f"────────────────────────────\n"
        f"★ 큰손(외인+기관) 합산: {smart_total:+,}주 → {smart_label}세"
    )


# ════════════════════════════════════════════
# Agent 도구 목록
# ════════════════════════════════════════════

def get_tools() -> list:
    return [
        Tool(
            name="Stock_Price",
            func=get_stock_price,
            description="주식 현재가를 조회합니다. 종목명/코드/해외티커 가능.",
        ),
        Tool(
            name="Market_Index",
            func=get_market_index,
            description="시장 지수(코스피, 나스닥 등)를 조회합니다.",
        ),
        Tool(
            name="Stock_News",
            func=get_stock_news,
            description="최신 뉴스를 조회합니다. 주가 변동 분석 시 수급 데이터와 함께 사용하세요.",
        ),
        Tool(
            name="Financial_Statement",
            func=get_financial,
            description="DART API로 기업의 연간 재무제표를 조회합니다.",
        ),
        Tool(
            name="Stock_Investor_Trade",
            func=get_stock_investor_trade,
            description="기관/외국인 수급(매매동향)을 조회합니다.",
        ),
    ]
