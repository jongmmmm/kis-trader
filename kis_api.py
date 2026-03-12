"""
한국투자증권 Open API 래퍼
- 토큰 자동 갱신 (DB 캐시)
- 모의/실전 URL·키 자동 전환
- 현재가, 일봉, 주문(매수/매도), 잔고, 지수 조회
"""
import requests
from datetime import datetime, timedelta
from flask import current_app
from db import db
from models import KisToken


def _base_url(mode: str) -> str:
    cfg = current_app.config
    return cfg["PAPER_BASE_URL"] if mode == "paper" else cfg["REAL_BASE_URL"]


def _credentials(mode: str) -> tuple:
    """모드에 맞는 (app_key, app_secret, account_no) 반환"""
    cfg = current_app.config
    if mode == "paper":
        return cfg["KIS_PAPER_APP_KEY"], cfg["KIS_PAPER_APP_SECRET"], cfg["KIS_PAPER_ACCOUNT_NO"]
    return cfg["KIS_REAL_APP_KEY"], cfg["KIS_REAL_APP_SECRET"], cfg["KIS_REAL_ACCOUNT_NO"]


def get_token(mode: str) -> str:
    """액세스 토큰 반환 (캐시 유효하면 재사용)"""
    app_key, app_secret, _ = _credentials(mode)
    token_row = KisToken.query.filter_by(mode=mode).first()
    now = datetime.utcnow()

    if token_row and token_row.expires_at and token_row.expires_at > now + timedelta(minutes=5):
        return token_row.access_token

    url = f"{_base_url(mode)}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    resp = requests.post(url, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    new_token = data["access_token"]
    expires_in = int(data.get("expires_in", 86400))

    if not token_row:
        token_row = KisToken(mode=mode)
        db.session.add(token_row)
    token_row.access_token = new_token
    token_row.expires_at = now + timedelta(seconds=expires_in)
    token_row.updated_at = now
    db.session.commit()
    return new_token


def _headers(mode: str, tr_id: str) -> dict:
    app_key, app_secret, _ = _credentials(mode)
    return {
        "authorization": f"Bearer {get_token(mode)}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
        "Content-Type": "application/json; charset=utf-8",
    }


def get_current_price(stock_code: str, mode: str = "paper") -> dict:
    """현재가 조회 → {"price": 70000, "change_rate": 1.23, "volume": ...}"""
    url = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    resp = requests.get(url, headers=_headers(mode, "FHKST01010100"), params=params, timeout=10)
    resp.raise_for_status()
    output = resp.json().get("output", {})
    return {
        "price": int(output.get("stck_prpr", 0)),
        "change_rate": float(output.get("prdy_ctrt", 0)),
        "volume": int(output.get("acml_vol", 0)),
        "high": int(output.get("stck_hgpr", 0)),
        "low": int(output.get("stck_lwpr", 0)),
        "open": int(output.get("stck_oprc", 0)),
    }


def get_daily_ohlcv(stock_code: str, mode: str = "paper", count: int = 100,
                     period_code: str = "D", start_date: str = "19000101") -> list:
    """일봉/주봉/월봉 데이터 조회 (period_code: D=일, W=주, M=월)"""
    from datetime import date
    url = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    today = date.today().strftime("%Y%m%d")
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_INPUT_DATE_1": start_date,
        "FID_INPUT_DATE_2": today,
        "FID_PERIOD_DIV_CODE": period_code,
        "FID_ORG_ADJ_PRC": "0",
    }
    resp = requests.get(url, headers=_headers(mode, "FHKST03010100"), params=params, timeout=15)
    resp.raise_for_status()
    output2 = resp.json().get("output2", [])
    result = []
    for row in output2[:count]:
        result.append({
            "date": row.get("stck_bsop_date", ""),
            "open": int(row.get("stck_oprc", 0)),
            "high": int(row.get("stck_hgpr", 0)),
            "low": int(row.get("stck_lwpr", 0)),
            "close": int(row.get("stck_clpr", 0)),
            "volume": int(row.get("acml_vol", 0)),
        })
    return result


def place_order(stock_code: str, order_type: str, price: int,
                quantity: int, mode: str = "paper") -> dict:
    """주문 실행 → {"order_no": "...", "success": True}"""
    cfg = current_app.config
    _, _, account_no = _credentials(mode)
    if order_type == "buy":
        tr_id = "VTTC0802U" if mode == "paper" else "TTTC0802U"
    else:
        tr_id = "VTTC0801U" if mode == "paper" else "TTTC0801U"

    url = f"{_base_url(mode)}/uapi/domestic-stock/v1/trading/order-cash"
    body = {
        "CANO": account_no,
        "ACNT_PRDT_CD": cfg["KIS_ACCOUNT_SUFFIX"],
        "PDNO": stock_code,
        "ORD_DVSN": "00" if price > 0 else "01",
        "ORD_QTY": str(quantity),
        "ORD_UNPR": str(price),
    }
    resp = requests.post(url, headers=_headers(mode, tr_id), json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    output = data.get("output", {})
    return {
        "success": data.get("rt_cd") == "0",
        "order_no": output.get("ODNO", ""),
        "message": data.get("msg1", ""),
    }


def get_index_price(index_code: str, mode: str = "paper") -> dict:
    """업종 지수 현재가 조회 (0001=코스피, 1001=코스닥)"""
    url = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-index-price"
    params = {
        "FID_COND_MRKT_DIV_CODE": "U",
        "FID_INPUT_ISCD": index_code,
    }
    resp = requests.get(
        url, headers=_headers(mode, "FHPUP02100000"), params=params, timeout=10
    )
    resp.raise_for_status()
    output = resp.json().get("output", {})
    return {
        "index": float(output.get("bstp_nmix_prpr", 0)),
        "change_val": float(output.get("bstp_nmix_prdy_vrss", 0)),
        "change_rate": float(output.get("bstp_nmix_prdy_ctrt", 0)),
        "open": float(output.get("bstp_nmix_oprc", 0)),
        "high": float(output.get("bstp_nmix_hgpr", 0)),
        "low": float(output.get("bstp_nmix_lwpr", 0)),
        "volume": int(output.get("acml_vol", 0)),
    }


def get_volume_rank(mode: str = "paper") -> list:
    """거래량 상위 종목 조회"""
    url = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/volume-rank"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0",
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1": "0",
        "FID_INPUT_PRICE_2": "0",
        "FID_VOL_CNT": "0",
        "FID_INPUT_DATE_1": "",
    }
    resp = requests.get(url, headers=_headers(mode, "FHPST01710000"), params=params, timeout=10)
    resp.raise_for_status()
    output = resp.json().get("output", [])
    result = []
    for row in output[:30]:
        result.append({
            "rank": int(row.get("data_rank", 0)),
            "stock_code": row.get("mksc_shrn_iscd", ""),
            "stock_name": row.get("hts_kor_isnm", ""),
            "price": int(row.get("stck_prpr", 0)),
            "change_rate": float(row.get("prdy_ctrt", 0)),
            "change_val": int(row.get("prdy_vrss", 0)),
            "volume": int(row.get("acml_vol", 0)),
            "change_sign": row.get("prdy_vrss_sign", "3"),
        })
    return result


def get_overseas_volume_rank(mode: str = "paper", excd: str = "NAS") -> list:
    """해외주식 거래량 상위 종목 조회 — 주요 종목 시세를 가져와 거래량순 정렬"""
    MAJOR_STOCKS = {
        "NAS": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
                "NFLX", "AVGO", "COST", "AMD", "QCOM", "INTC", "PYPL",
                "ADBE", "CSCO", "PEP", "CMCSA", "TMUS", "INTU",
                "AMAT", "ISRG", "MU", "LRCX", "MRVL", "PLTR", "COIN",
                "MSTR", "SMCI", "ARM"],
        "NYS": ["BRK.B", "JPM", "V", "UNH", "MA", "JNJ", "WMT", "PG",
                "XOM", "HD", "BAC", "CVX", "KO", "MRK", "PFE",
                "ABBV", "DIS", "NKE", "T", "VZ", "GM", "F", "BA",
                "GS", "MS", "C", "WFC", "IBM", "GE", "CAT"],
        "AMS": ["SPY", "QQQ", "IWM", "SOXL", "TQQQ", "SQQQ", "UVXY",
                "XLF", "XLE", "XLK", "GLD", "SLV", "EEM", "VXX",
                "ARKK"],
    }
    symbols = MAJOR_STOCKS.get(excd, MAJOR_STOCKS["NAS"])
    result = []
    for sym in symbols:
        try:
            data = get_overseas_current_price(sym, excd, mode)
            if data["price"] > 0 and data["volume"] > 0:
                data["stock_code"] = sym
                data["stock_name"] = data.get("name", sym)
                result.append(data)
        except Exception:
            continue
    result.sort(key=lambda x: x["volume"], reverse=True)
    return result[:30]


# ─── 해외주식 API ────────────────────────────────────────────

# 거래소 코드 매핑
EXCHANGE_MAP = {
    "NAS": "NASD",   # 나스닥
    "NYS": "NYSE",   # 뉴욕
    "AMS": "AMEX",   # 아멕스
    "HKS": "SEHK",   # 홍콩
    "SHS": "SHAA",   # 상해
    "SZS": "SZAA",   # 심천
    "TSE": "TKSE",   # 도쿄
    "HNX": "HASE",   # 하노이
    "HSX": "VNSE",   # 호치민
}

# 거래소별 tr_id (모의투자는 해외주식 미지원이므로 실전만)
def _overseas_exchange_code(excd: str) -> str:
    """거래소 약어를 KIS API 파라미터용으로 변환"""
    return EXCHANGE_MAP.get(excd, excd)


def get_overseas_current_price(stock_code: str, excd: str = "NAS", mode: str = "paper") -> dict:
    """해외 현재가 조회"""
    url = f"{_base_url(mode)}/uapi/overseas-price/v1/quotations/price"
    params = {
        "AUTH": "",
        "EXCD": excd,
        "SYMB": stock_code,
    }
    resp = requests.get(url, headers=_headers(mode, "HHDFS00000300"), params=params, timeout=10)
    resp.raise_for_status()
    output = resp.json().get("output", {})
    return {
        "price": float(output.get("last", 0)),
        "change_rate": float(output.get("rate", 0)),
        "change_val": float(output.get("diff", 0)),
        "volume": int(float(output.get("tvol", 0))),
        "high": float(output.get("high", 0)),
        "low": float(output.get("low", 0)),
        "open": float(output.get("open", 0)),
        "name": output.get("name", ""),
        "currency": output.get("curr", "USD"),
        "exchange": excd,
    }


def get_overseas_daily_ohlcv(stock_code: str, excd: str = "NAS",
                              mode: str = "paper", count: int = 100,
                              period_code: str = "0") -> list:
    """해외 일봉 조회 (period_code: 0=일, 1=주, 2=월)"""
    url = f"{_base_url(mode)}/uapi/overseas-price/v1/quotations/dailyprice"
    params = {
        "AUTH": "",
        "EXCD": excd,
        "SYMB": stock_code,
        "GUBN": period_code,
        "BYMD": "",
        "MODP": "1",
    }
    resp = requests.get(url, headers=_headers(mode, "HHDFS76240000"), params=params, timeout=15)
    resp.raise_for_status()
    output2 = resp.json().get("output2", [])
    result = []
    for row in output2[:count]:
        if not row.get("xymd"):
            continue
        result.append({
            "date": row.get("xymd", ""),
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "close": float(row.get("clos", 0)),
            "volume": int(float(row.get("tvol", 0))),
        })
    return result


def get_overseas_balance(mode: str = "paper") -> list:
    """해외 잔고 조회"""
    cfg = current_app.config
    _, _, account_no = _credentials(mode)
    tr_id = "TTTS3012R" if mode == "real" else "VTTS3012R"
    url = f"{_base_url(mode)}/uapi/overseas-stock/v1/trading/inquire-balance"
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": cfg["KIS_ACCOUNT_SUFFIX"],
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": "",
    }
    resp = requests.get(url, headers=_headers(mode, tr_id), params=params, timeout=10)
    resp.raise_for_status()
    output1 = resp.json().get("output1", [])
    result = []
    for row in output1:
        qty = int(float(row.get("ovrs_cblc_qty", 0)))
        if qty > 0:
            result.append({
                "stock_code": row.get("ovrs_pdno", ""),
                "stock_name": row.get("ovrs_item_name", ""),
                "exchange": row.get("ovrs_excg_cd", ""),
                "quantity": qty,
                "avg_price": float(row.get("pchs_avg_pric", 0)),
                "current_price": float(row.get("now_pric2", 0)),
                "eval_profit_loss": float(row.get("frcr_evlu_pfls_amt", 0)),
                "profit_loss_rate": float(row.get("evlu_pfls_rt", 0)),
                "currency": row.get("tr_crcy_cd", "USD"),
            })
    return result


def place_overseas_order(stock_code: str, excd: str, order_type: str,
                          price: float, quantity: int, mode: str = "paper") -> dict:
    """해외 주문 실행"""
    cfg = current_app.config
    _, _, account_no = _credentials(mode)
    ovrs_excg_cd = _overseas_exchange_code(excd)

    if order_type == "buy":
        tr_id = "VTTT1002U" if mode == "paper" else "TTTT1002U"
    else:
        tr_id = "VTTT1001U" if mode == "paper" else "TTTT1001U"

    url = f"{_base_url(mode)}/uapi/overseas-stock/v1/trading/order"
    body = {
        "CANO": account_no,
        "ACNT_PRDT_CD": cfg["KIS_ACCOUNT_SUFFIX"],
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "PDNO": stock_code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(quantity),
        "OVRS_ORD_UNPR": str(price),
    }
    resp = requests.post(url, headers=_headers(mode, tr_id), json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    output = data.get("output", {})
    return {
        "success": data.get("rt_cd") == "0",
        "order_no": output.get("ODNO", ""),
        "message": data.get("msg1", ""),
    }


def get_balance(mode: str = "paper") -> list:
    """잔고 조회"""
    cfg = current_app.config
    _, _, account_no = _credentials(mode)
    tr_id = "VTTC8434R" if mode == "paper" else "TTTC8434R"
    url = f"{_base_url(mode)}/uapi/domestic-stock/v1/trading/inquire-balance"
    params = {
        "CANO": account_no,
        "ACNT_PRDT_CD": cfg["KIS_ACCOUNT_SUFFIX"],
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    resp = requests.get(url, headers=_headers(mode, tr_id), params=params, timeout=10)
    resp.raise_for_status()
    output1 = resp.json().get("output1", [])
    result = []
    for row in output1:
        qty = int(row.get("hldg_qty", 0))
        if qty > 0:
            result.append({
                "stock_code": row.get("pdno", ""),
                "stock_name": row.get("prdt_name", ""),
                "quantity": qty,
                "avg_price": float(row.get("pchs_avg_pric", 0)),
                "current_price": int(row.get("prpr", 0)),
                "eval_profit_loss": float(row.get("evlu_pfls_amt", 0)),
                "profit_loss_rate": float(row.get("evlu_pfls_rt", 0)),
            })
    return result
