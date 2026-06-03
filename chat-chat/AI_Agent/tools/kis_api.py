"""
한국투자증권 Open API — AI Agent 독립 실행 버전
Flask / db / models 의존성 제거
config모의투자.yaml 에서 키 로드
토큰 메모리 캐시 + 자동 재발급 + 재시도 로직
"""

import os
import time
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


# ─────────────────────────────────────────────
# ✅ [수정] 토큰 강제 재발급 지원
# ─────────────────────────────────────────────
def get_token(mode: str, force_refresh: bool = False) -> str:
    """
    force_refresh=True  → 캐시 무시하고 새 토큰 발급 (401 발생 시 호출)
    force_refresh=False → 캐시 유효하면 그대로 사용
    """
    now    = datetime.utcnow()
    cached = _token_cache.get(mode)

    # 강제 갱신이 아니고, 캐시가 유효하면 그대로 반환
    if not force_refresh and cached and cached.get("expires_at") and \
            cached["expires_at"] > now + timedelta(minutes=5):
        return cached["access_token"]

    # 신규 발급
    app_key, app_secret, _ = _credentials(mode)
    resp = requests.post(
        f"{_base_url(mode)}/oauth2/tokenP",
        json={
            "grant_type": "client_credentials",
            "appkey":     app_key,
            "appsecret":  app_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    _token_cache[mode] = {
        "access_token": data["access_token"],
        "expires_at":   now + timedelta(seconds=int(data.get("expires_in", 86400))),
    }
    print(f"[KIS] 토큰 {'강제 ' if force_refresh else ''}발급 완료 (mode={mode})")
    return _token_cache[mode]["access_token"]


def _headers(mode: str, tr_id: str, force_refresh: bool = False) -> dict:
    app_key, app_secret, _ = _credentials(mode)
    return {
        "authorization": f"Bearer {get_token(mode, force_refresh=force_refresh)}",
        "appkey":         app_key,
        "appsecret":      app_secret,
        "tr_id":          tr_id,
        "custtype":       "P",
        "Content-Type":   "application/json; charset=utf-8",
    }


def _today() -> str:
    return date.today().strftime("%Y%m%d")


# ─────────────────────────────────────────────
# ✅ [신규] 공통 HTTP 요청 래퍼 — 재시도 + 401 자동 복구
# ─────────────────────────────────────────────
def _api_get(
    url: str,
    mode: str,
    tr_id: str,
    params: dict,
    *,
    max_retries: int = 2,
    retry_delay: float = 0.5,
) -> dict:
    """
    GET 요청 공통 처리
    - 401 Unauthorized → 토큰 강제 재발급 후 1회 재시도
    - 일시적 오류(5xx, 연결 오류) → max_retries 횟수만큼 재시도
    - 최종 실패 → 예외 raise
    """
    last_exc = None
    force_refresh = False

    for attempt in range(max_retries + 1):
        try:
            hdrs = _headers(mode, tr_id, force_refresh=force_refresh)
            resp = requests.get(url, headers=hdrs, params=params, timeout=10)

            # 401: 토큰 만료 → 강제 재발급 후 즉시 재시도
            if resp.status_code == 401:
                print(f"[KIS] 401 감지 → 토큰 강제 재발급 후 재시도 (attempt={attempt+1})")
                force_refresh = True
                time.sleep(0.3)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            last_exc = e
            print(f"[KIS] API 요청 실패 (attempt={attempt+1}/{max_retries+1}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay * (attempt + 1))  # 0.5s, 1.0s, ...
            force_refresh = False  # 401이 아닌 일반 오류 → 토큰 재발급 불필요

    raise last_exc or RuntimeError("KIS API 요청 최종 실패")


def _api_post(
    url: str,
    mode: str,
    tr_id: str,
    body: dict,
    *,
    max_retries: int = 2,
    retry_delay: float = 0.5,
) -> dict:
    """POST 요청 공통 처리 (주문 등)"""
    last_exc = None
    force_refresh = False

    for attempt in range(max_retries + 1):
        try:
            hdrs = _headers(mode, tr_id, force_refresh=force_refresh)
            resp = requests.post(url, headers=hdrs, json=body, timeout=10)

            if resp.status_code == 401:
                print(f"[KIS] 401 감지 → 토큰 강제 재발급 후 재시도 (attempt={attempt+1})")
                force_refresh = True
                time.sleep(0.3)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            last_exc = e
            print(f"[KIS] API POST 실패 (attempt={attempt+1}/{max_retries+1}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay * (attempt + 1))
            force_refresh = False

    raise last_exc or RuntimeError("KIS API POST 최종 실패")


# ═══════════════════════════════════════════════════════════
# 국내주식
# ═══════════════════════════════════════════════════════════

def get_current_price(stock_code: str, mode: str = "paper") -> dict:
    url  = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-price"
    data = _api_get(url, mode, "FHKST01010100", {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    })
    o = data.get("output", {})
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
    url  = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    data = _api_get(url, mode, "FHKST03010100", {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD":          stock_code,
        "FID_INPUT_DATE_1":        start_date,
        "FID_INPUT_DATE_2":        _today(),
        "FID_PERIOD_DIV_CODE":     period_code,
        "FID_ORG_ADJ_PRC":         "0",
    })
    return [
        {
            "date":   r.get("stck_bsop_date", ""),
            "open":   int(r.get("stck_oprc", 0)),
            "high":   int(r.get("stck_hgpr", 0)),
            "low":    int(r.get("stck_lwpr", 0)),
            "close":  int(r.get("stck_clpr", 0)),
            "volume": int(r.get("acml_vol", 0)),
        }
        for r in data.get("output2", [])[:count]
    ]


def place_order(stock_code: str, order_type: str, price: int,
                quantity: int, mode: str = "paper") -> dict:
    _, _, account_no = _credentials(mode)
    account_suffix   = _CFG.get("account_suffix", "01")

    if order_type == "buy":
        tr_id = "VTTC0802U" if mode == "paper" else "TTTC0802U"
    else:
        tr_id = "VTTC0801U" if mode == "paper" else "TTTC0801U"

    data = _api_post(
        f"{_base_url(mode)}/uapi/domestic-stock/v1/trading/order-cash",
        mode, tr_id,
        {
            "CANO":        account_no,
            "ACNT_PRDT_CD": account_suffix,
            "PDNO":        stock_code,
            "ORD_DVSN":    "00" if price > 0 else "01",
            "ORD_QTY":     str(quantity),
            "ORD_UNPR":    str(price),
        },
    )
    return {
        "success":  data.get("rt_cd") == "0",
        "order_no": data.get("output", {}).get("ODNO", ""),
        "message":  data.get("msg1", ""),
    }


def get_balance(mode: str = "paper") -> list:
    _, _, account_no = _credentials(mode)
    account_suffix   = _CFG.get("account_suffix", "01")
    tr_id = "VTTC8434R" if mode == "paper" else "TTTC8434R"
    data  = _api_get(
        f"{_base_url(mode)}/uapi/domestic-stock/v1/trading/inquire-balance",
        mode, tr_id,
        {
            "CANO":               account_no,
            "ACNT_PRDT_CD":       account_suffix,
            "AFHR_FLPR_YN":       "N",
            "OFL_YN":             "N",
            "INQR_DVSN":          "02",
            "UNPR_DVSN":          "01",
            "FUND_STTL_ICLD_YN":  "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN":          "00",
            "CTX_AREA_FK100":     "",
            "CTX_AREA_NK100":     "",
        },
    )
    return [
        {
            "stock_code":        r.get("pdno", ""),
            "stock_name":        r.get("prdt_name", ""),
            "quantity":          int(r.get("hldg_qty", 0)),
            "avg_price":         float(r.get("pchs_avg_pric", 0)),
            "current_price":     int(r.get("prpr", 0)),
            "eval_profit_loss":  float(r.get("evlu_pfls_amt", 0)),
            "profit_loss_rate":  float(r.get("evlu_pfls_rt", 0)),
        }
        for r in data.get("output1", [])
        if int(r.get("hldg_qty", 0)) > 0
    ]


def get_index_price(index_code: str, mode: str = "paper") -> dict:
    """코스피=0001 / 코스닥=1001 / 코스피200=2001"""
    url  = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-index-price"
    data = _api_get(url, mode, "FHPUP02100000", {
        "FID_COND_MRKT_DIV_CODE": "U",
        "FID_INPUT_ISCD":         index_code,
    })
    o = data.get("output", {})
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
    url  = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/volume-rank"
    data = _api_get(url, mode, "FHPST01710000", {
        "FID_COND_MRKT_DIV_CODE":    "J",
        "FID_COND_SCR_DIV_CODE":     "20171",
        "FID_INPUT_ISCD":            "0000",
        "FID_DIV_CLS_CODE":          "0",
        "FID_BLNG_CLS_CODE":         "0",
        "FID_TRGT_CLS_CODE":         "111111111",
        "FID_TRGT_EXLS_CLS_CODE":    "000000",
        "FID_INPUT_PRICE_1":         "0",
        "FID_INPUT_PRICE_2":         "0",
        "FID_VOL_CNT":               "0",
        "FID_INPUT_DATE_1":          "",
    })
    return [
        {
            "rank":        int(r.get("data_rank", 0)),
            "stock_code":  r.get("mksc_shrn_iscd", ""),
            "stock_name":  r.get("hts_kor_isnm", ""),
            "price":       int(r.get("stck_prpr", 0)),
            "change_rate": float(r.get("prdy_ctrt", 0)),
            "volume":      int(r.get("acml_vol", 0)),
        }
        for r in data.get("output", [])[:30]
    ]


def get_investor_trade(stock_code: str, mode: str = "paper") -> dict:
    """주식 투자자별 매매동향 (기관·외국인 순매수량 등)"""
    url  = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-investor"
    data = _api_get(url, mode, "FHKST01010900", {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD":         stock_code,
    })
    outputs = data.get("output", [])
    if not outputs:
        return {"error": "수급 데이터를 찾을 수 없습니다."}

    d = outputs[0]
    return {
        "stock_code":          stock_code,
        "date":                d.get("stck_bsop_date", ""),
        "personal_net_buy":    int(d.get("prsn_ntby_qty", 0)),
        "institution_net_buy": int(d.get("orgn_ntby_qty", 0)),
        "foreign_net_buy":     int(d.get("frgn_ntby_qty", 0)),
        "total_buy_volume":    int(d.get("acml_vol", 0)),
    }


# ═══════════════════════════════════════════════════════════
# 해외주식
# ═══════════════════════════════════════════════════════════

def get_overseas_current_price(stock_code: str, excd: str = "NAS",
                                mode: str = "paper") -> dict:
    url  = f"{_base_url(mode)}/uapi/overseas-price/v1/quotations/price"
    data = _api_get(url, mode, "HHDFS00000300", {
        "AUTH": "",
        "EXCD": excd,
        "SYMB": stock_code,
    })
    o = data.get("output", {})
    return {
        "stock_code":  stock_code,
        "exchange":    excd,
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
    """FX@KRW=달러/원  FX@EUR=유로/원  FX@JPY=엔/원"""
    url  = f"{_base_url(mode)}/uapi/domestic-stock/v1/quotations/inquire-price"
    data = _api_get(url, mode, "FHKST01010100", {
        "FID_COND_MRKT_DIV_CODE": "FX",
        "FID_INPUT_ISCD":         fx_code,
    })
    o = data.get("output", {})
    return {
        "fx_code":     fx_code,
        "rate":        float(o.get("stck_prpr", 0)),
        "change_val":  float(o.get("prdy_vrss", 0)),
        "change_rate": float(o.get("prdy_ctrt", 0)),
        "high":        float(o.get("stck_hgpr", 0)),
        "low":         float(o.get("stck_lwpr", 0)),
    }
