"""
한국투자증권 Open API — AI Agent 독립 실행 버전
Flask / db / models 의존성 제거
config모의투자.yaml 에서 키 로드
토큰 메모리 캐시
"""

import os
import yaml
import requests
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────
# 설정 로드
# ─────────────────────────────────────────────
_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_THIS_DIR, "..", "config모의투자.yaml")

def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("hantu", {})
    except Exception:
        return {}

_CFG = _load_config()

_PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"
_REAL_BASE_URL  = "https://openapi.koreainvestment.com:9443"

# 토큰 메모리 캐시
_token_cache: dict = {}


def _base_url(mode: str) -> str:
    return _PAPER_BASE_URL if mode == "paper" else _REAL_BASE_URL


def _credentials(mode: str) -> tuple:
    return (
        _CFG.get("api_key", ""),
        _CFG.get("secret_key", ""),
        _CFG.get("account_id", ""),
    )


def get_token(mode: str) -> str:
    now    = datetime.utcnow()
    cached = _token_cache.get(mode)
    if cached and cached.get("expires_at") and \
            cached["expires_at"] > now + timedelta(minutes=5):
        return cached["access_token"]

    app_key, app_secret, _ = _credentials(mode)
    resp = requests.post(
        f"{_base_url(mode)}/oauth2/tokenP",
        json={"grant_type": "client_credentials",
              "appkey": app_key, "appsecret": app_secret},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache[mode] = {
        "access_token": data["access_token"],
        "expires_at":   now + timedelta(seconds=int(data.get("expires_in", 86400))),
    }
    return _token_cache[mode]["access_token"]


def _headers(mode: str, tr_id: str) -> dict:
    app_key, app_secret, _ = _credentials(mode)
    return {
        "authorization": f"Bearer {get_token(mode)}",
        "appkey":        app_key,
        "appsecret":     app_secret,
        "tr_id":         tr_id,
        "custtype":      "P",
        "Content-Type":  "application/json; charset=utf-8",
    }


def _today() -> str:
    return date.today().strftime("%Y%m%d")


# ═══════════════════════════════════════════════════════════
# 국내주식
# ═══════════════════════════════════════════════════════════

def get_current_price(stock_code: str, mode: str = "paper") -> dict:
    url    = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
    resp   = requests.get(url, headers=_headers(mode, "FHKST01010100"), params=params, timeout=10)
    resp.raise_for_status()
    o = resp.json().get("output", {})
    return {
        "stock_code":  stock_code,
        "price":       int(o.get("stck_prpr", 0)),
        "change_val":  int(o.get("prdy_vrss", 0)),
        "change_rate": float(o.get("prdy_ctrt", 0)),
        "change_sign": o.get("prdy_vrss_sign", "3"),
        "volume":      int(o.get("acml_vol", 0)),
        "open":        int(o.get("stck_oprc", 0)),
        "high":        int(o.get("stck_hgpr", 0)),
        "low":         int(o.get("stck_lwpr", 0)),
        "high_52w":    int(o.get("w52_hgpr", 0)),
        "low_52w":     int(o.get("w52_lwpr", 0)),
        "per":         float(o.get("per", 0)),
        "pbr":         float(o.get("pbr", 0)),
        "market_cap":  int(o.get("hts_avls", 0)),
    }


def get_daily_ohlcv(stock_code: str, mode: str = "paper",
                    count: int = 100, period_code: str = "D",
                    start_date: str = "19000101") -> list:
    url    = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD":         stock_code,
        "FID_INPUT_DATE_1":       start_date,
        "FID_INPUT_DATE_2":       _today(),
        "FID_PERIOD_DIV_CODE":    period_code,
        "FID_ORG_ADJ_PRC":        "0",
    }
    resp = requests.get(url, headers=_headers(mode, "FHKST03010100"), params=params, timeout=15)
    resp.raise_for_status()
    return [
        {"date": r.get("stck_bsop_date", ""), "open": int(r.get("stck_oprc", 0)),
         "high": int(r.get("stck_hgpr", 0)), "low": int(r.get("stck_lwpr", 0)),
         "close": int(r.get("stck_clpr", 0)), "volume": int(r.get("acml_vol", 0))}
        for r in resp.json().get("output2", [])[:count]
    ]


def place_order(stock_code: str, order_type: str, price: int,
                quantity: int, mode: str = "paper") -> dict:
    _, _, account_no   = _credentials(mode)
    account_suffix     = _CFG.get("account_suffix", "01")
    tr_id = ("VTTC0802U" if mode == "paper" else "TTTC0802U") if order_type == "buy" \
            else ("VTTC0801U" if mode == "paper" else "TTTC0801U")
    resp = requests.post(
        f"{_base_url(mode)}/uapi/domestic-stock/v1/trading/order-cash",
        headers=_headers(mode, tr_id),
        json={"CANO": account_no, "ACNT_PRDT_CD": account_suffix, "PDNO": stock_code,
              "ORD_DVSN": "00" if price > 0 else "01",
              "ORD_QTY": str(quantity), "ORD_UNPR": str(price)},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"success": data.get("rt_cd") == "0",
            "order_no": data.get("output", {}).get("ODNO", ""),
            "message": data.get("msg1", "")}


def get_balance(mode: str = "paper") -> list:
    _, _, account_no = _credentials(mode)
    account_suffix   = _CFG.get("account_suffix", "01")
    tr_id = "VTTC8434R" if mode == "paper" else "TTTC8434R"
    resp  = requests.get(
        f"{_base_url(mode)}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers=_headers(mode, tr_id),
        params={"CANO": account_no, "ACNT_PRDT_CD": account_suffix,
                "AFHR_FLPR_YN": "N", "OFL_YN": "N", "INQR_DVSN": "02",
                "UNPR_DVSN": "01", "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00",
                "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""},
        timeout=10,
    )
    resp.raise_for_status()
    return [
        {"stock_code": r.get("pdno", ""), "stock_name": r.get("prdt_name", ""),
         "quantity": int(r.get("hldg_qty", 0)), "avg_price": float(r.get("pchs_avg_pric", 0)),
         "current_price": int(r.get("prpr", 0)), "eval_profit_loss": float(r.get("evlu_pfls_amt", 0)),
         "profit_loss_rate": float(r.get("evlu_pfls_rt", 0))}
        for r in resp.json().get("output1", []) if int(r.get("hldg_qty", 0)) > 0
    ]


def get_index_price(index_code: str, mode: str = "paper") -> dict:
    """코스피=0001, 코스닥=1001, 코스피200=2001"""
    url    = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-index-price"
    params = {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": index_code}
    resp   = requests.get(url, headers=_headers(mode, "FHPUP02100000"), params=params, timeout=10)
    resp.raise_for_status()
    o = resp.json().get("output", {})
    return {
        "index_code":  index_code,
        "index":       float(o.get("bstp_nmix_prpr", 0)),
        "change_val":  float(o.get("bstp_nmix_prdy_vrss", 0)),
        "change_rate": float(o.get("bstp_nmix_prdy_ctrt", 0)),
        "open":        float(o.get("bstp_nmix_oprc", 0)),
        "high":        float(o.get("bstp_nmix_hgpr", 0)),
        "low":         float(o.get("bstp_nmix_lwpr", 0)),
        "volume":      int(o.get("acml_vol", 0)),
    }


def get_volume_rank(mode: str = "paper") -> list:
    url    = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/volume-rank"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000", "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0", "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000", "FID_INPUT_PRICE_1": "0",
        "FID_INPUT_PRICE_2": "0", "FID_VOL_CNT": "0", "FID_INPUT_DATE_1": "",
    }
    resp = requests.get(url, headers=_headers(mode, "FHPST01710000"), params=params, timeout=10)
    resp.raise_for_status()
    return [
        {"rank": int(r.get("data_rank", 0)), "stock_code": r.get("mksc_shrn_iscd", ""),
         "stock_name": r.get("hts_kor_isnm", ""), "price": int(r.get("stck_prpr", 0)),
         "change_rate": float(r.get("prdy_ctrt", 0)), "volume": int(r.get("acml_vol", 0))}
        for r in resp.json().get("output", [])[:30]
    ]


# ═══════════════════════════════════════════════════════════
# 해외주식
# ═══════════════════════════════════════════════════════════

def get_overseas_current_price(stock_code: str, excd: str = "NAS",
                                mode: str = "paper") -> dict:
    url    = f"{_base_url(mode)}/uapi/overseas-price/v1/quotations/price"
    params = {"AUTH": "", "EXCD": excd, "SYMB": stock_code}
    resp   = requests.get(url, headers=_headers(mode, "HHDFS00000300"), params=params, timeout=10)
    resp.raise_for_status()
    o = resp.json().get("output", {})
    return {
        "stock_code":  stock_code, "exchange": excd,
        "price":       float(o.get("last", 0)),
        "change_val":  float(o.get("diff", 0)),
        "change_rate": float(o.get("rate", 0)),
        "volume":      int(float(o.get("tvol", 0))),
        "open":        float(o.get("open", 0)),
        "high":        float(o.get("high", 0)),
        "low":         float(o.get("low", 0)),
        "name":        o.get("name", ""),
        "currency":    o.get("curr", "USD"),
    }


# ═══════════════════════════════════════════════════════════
# 환율
# ═══════════════════════════════════════════════════════════

def get_fx_rate(fx_code: str = "FX@KRW", mode: str = "paper") -> dict:
    """FX@KRW=달러/원, FX@EUR=유로/원, FX@JPY=엔/원"""
    url    = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {"FID_COND_MRKT_DIV_CODE": "FX", "FID_INPUT_ISCD": fx_code}
    resp   = requests.get(url, headers=_headers(mode, "FHKST01010100"), params=params, timeout=10)
    resp.raise_for_status()
    o = resp.json().get("output", {})
    return {
        "fx_code":     fx_code,
        "rate":        float(o.get("stck_prpr", 0)),
        "change_val":  float(o.get("prdy_vrss", 0)),
        "change_rate": float(o.get("prdy_ctrt", 0)),
        "high":        float(o.get("stck_hgpr", 0)),
        "low":         float(o.get("stck_lwpr", 0)),
    }