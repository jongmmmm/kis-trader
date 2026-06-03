import pandas as pd
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from db import db
from models import Strategy, AuctionAlert
from kis_api import (
    get_daily_ohlcv, get_current_price,
    get_overseas_daily_ohlcv, get_overseas_current_price,
)
from strategies.ai_analyzer import analyze_stock

bp = Blueprint("strategies", __name__, url_prefix="/strategies")

@bp.route("/")
@login_required
def index():
    return render_template("strategies.html")

@bp.route("/api/strategies")
def list_strategies():
    items = Strategy.query.order_by(Strategy.created_at.desc()).all()
    return jsonify([{
        "id": s.id, "name": s.name, "stock_code": s.stock_code,
        "stock_name": s.stock_name, "exchange": s.exchange or "",
        "strategy_type": s.strategy_type,
        "params": s.params, "is_active": s.is_active, "mode": s.mode,
    } for s in items])

@bp.route("/api/strategies", methods=["POST"])
def create_strategy():
    d = request.get_json()
    s = Strategy(
        name=d["name"], stock_code=d["stock_code"],
        stock_name=d.get("stock_name", ""),
        exchange=d.get("exchange", ""),
        strategy_type=d["strategy_type"],
        params=d.get("params", {}),
        is_active=d.get("is_active", True),
        mode=d.get("mode", "paper"),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id, "message": "전략 등록 완료"})

@bp.route("/api/strategies/<int:sid>", methods=["PUT"])
def update_strategy(sid):
    s = Strategy.query.get_or_404(sid)
    d = request.get_json()
    for field in ("name", "stock_code", "stock_name", "exchange", "strategy_type", "params", "is_active", "mode"):
        if field in d:
            setattr(s, field, d[field])
    db.session.commit()
    return jsonify({"message": "업데이트 완료"})

@bp.route("/api/strategies/<int:sid>", methods=["DELETE"])
def delete_strategy(sid):
    s = Strategy.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "삭제 완료"})

@bp.route("/api/strategies/<int:sid>/toggle", methods=["POST"])
def toggle_strategy(sid):
    s = Strategy.query.get_or_404(sid)
    s.is_active = not s.is_active
    db.session.commit()
    return jsonify({"is_active": s.is_active})


@bp.route("/api/strategies/<int:sid>/chart")
def strategy_chart_data(sid):
    """전략의 종목 일봉/주봉/월봉 + 기술적 지표를 pandas로 계산하여 반환"""
    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta

    s = Strategy.query.get_or_404(sid)
    period = request.args.get("period", "month")  # day, month, year, 5year, 10year

    today = date.today()
    period_map = {
        "day":    {"period_code": "D", "count": 30,   "start": today - timedelta(days=60)},
        "month":  {"period_code": "D", "count": 60,   "start": today - relativedelta(months=3)},
        "year":   {"period_code": "D", "count": 250,  "start": today - relativedelta(years=1, months=2)},
        "5year":  {"period_code": "W", "count": 260,  "start": today - relativedelta(years=5, months=3)},
        "10year": {"period_code": "M", "count": 130,  "start": today - relativedelta(years=10, months=6)},
    }
    cfg = period_map.get(period, period_map["month"])

    try:
        if s.is_overseas:
            overseas_period = {"D": "0", "W": "1", "M": "2"}.get(cfg["period_code"], "0")
            raw = get_overseas_daily_ohlcv(s.stock_code, s.exchange, s.mode,
                                           count=cfg["count"],
                                           period_code=overseas_period)
        else:
            raw = get_daily_ohlcv(s.stock_code, s.mode,
                                  count=cfg["count"],
                                  period_code=cfg["period_code"],
                                  start_date=cfg["start"].strftime("%Y%m%d"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not raw:
        return jsonify({"error": "데이터 없음"}), 404

    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.sort_values("date").reset_index(drop=True)

    # 이동평균선
    params = s.params if isinstance(s.params, dict) else {}
    short_p = params.get("short_period", 5)
    long_p = params.get("long_period", 20)
    df["ma_short"] = df["close"].rolling(window=short_p).mean()
    df["ma_long"] = df["close"].rolling(window=long_p).mean()
    df["ma60"] = df["close"].rolling(window=60).mean()

    # RSI
    rsi_period = params.get("rsi_period", 14)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(window=rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=rsi_period).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    fast = params.get("macd_fast", 12)
    slow = params.get("macd_slow", 26)
    signal_p = params.get("macd_signal", 9)
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal_p, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # 거래량 이동평균
    df["vol_ma20"] = df["volume"].rolling(window=20).mean()

    df = df.fillna(0)

    # JSON 직렬화
    is_overseas = s.is_overseas
    candles = []
    for _, r in df.iterrows():
        o, h, l, c = r["open"], r["high"], r["low"], r["close"]
        if not is_overseas:
            o, h, l, c = int(o), int(h), int(l), int(c)
        else:
            o, h, l, c = round(float(o), 2), round(float(h), 2), round(float(l), 2), round(float(c), 2)
        candles.append({
            "time": r["date"].strftime("%Y-%m-%d"),
            "open": o, "high": h, "low": l, "close": c,
            "volume": int(r["volume"]),
            "ma_short": round(r["ma_short"], 1),
            "ma_long": round(r["ma_long"], 1),
            "ma60": round(r["ma60"], 1),
            "rsi": round(r["rsi"], 2),
            "macd": round(r["macd"], 2),
            "macd_signal": round(r["macd_signal"], 2),
            "macd_hist": round(r["macd_hist"], 2),
            "vol_ma20": round(r["vol_ma20"], 1),
        })

    return jsonify({
        "stock_code": s.stock_code,
        "stock_name": s.stock_name,
        "strategy_type": s.strategy_type,
        "params": params,
        "period": period,
        "period_code": cfg["period_code"],
        "candles": candles,
    })


def _search_naver_news(query, date_str, max_results=3, day_range=1):
    """네이버 뉴스 검색 - 국내 주식 뉴스"""
    import requests as req
    from bs4 import BeautifulSoup
    from datetime import datetime as dt, timedelta
    from urllib.parse import quote
    try:
        target = dt.strptime(date_str, "%Y-%m-%d").date()
        ds = (target - timedelta(days=day_range)).strftime("%Y.%m.%d")
        de = (target + timedelta(days=day_range)).strftime("%Y.%m.%d")
        url = f"https://search.naver.com/search.naver?where=news&query={quote(query)}&sort=1&ds={ds}&de={de}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        resp = req.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        titles = []
        for a in soup.select("a.news_tit")[:max_results]:
            titles.append(a.get_text(strip=True))
        if not titles:
            seen = set()
            for a in soup.find_all("a"):
                cls = " ".join(a.get("class", []))
                if "fender-ui" not in cls:
                    continue
                text = a.get_text(strip=True)
                if 15 < len(text) < 80 and text not in seen:
                    seen.add(text)
                    titles.append(text)
                    if len(titles) >= max_results:
                        break
        return titles
    except Exception:
        return []


def _search_yahoo_news(query, date_str, max_results=3, day_range=1):
    """Yahoo(Bing) 뉴스 검색 - 해외 주식 뉴스"""
    import requests as req
    from bs4 import BeautifulSoup
    from datetime import datetime as dt, timedelta
    from urllib.parse import quote
    try:
        target = dt.strptime(date_str, "%Y-%m-%d").date()
        ds = (target - timedelta(days=day_range)).strftime("%Y-%m-%d")
        de = (target + timedelta(days=day_range)).strftime("%Y-%m-%d")
        # Bing News 한국어 날짜 필터 검색
        date_filter = f"ex1%3a%22ez5_{ds}..{de}%22"
        url = f"https://www.bing.com/news/search?q={quote(query)}&qft={date_filter}&setlang=ko&cc=KR&form=PTFNR"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        resp = req.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        titles = []
        # Bing News 제목 셀렉터
        for a in soup.select("a.title")[:max_results]:
            text = a.get_text(strip=True)
            if text:
                titles.append(text)
        # 대체 셀렉터
        if not titles:
            for a in soup.find_all("a"):
                text = a.get_text(strip=True)
                if len(text) > 20 and any(k.lower() in text.lower() for k in query.split()[:2]):
                    titles.append(text[:80])
                    if len(titles) >= max_results:
                        break
        return titles
    except Exception:
        return []


# 뉴스 캐시 (메모리 기반, 서버 재시작 시 초기화)
_news_cache = {}

@bp.route("/api/strategies/<int:sid>/events")
def strategy_events(sid):
    """급등/급락(±3%) 구간을 감지하고 관련 뉴스 검색"""
    s = Strategy.query.get_or_404(sid)
    period = request.args.get("period", "month")

    # 기간별 기본 threshold: 장기일수록 큰 변동만 표시
    default_thresholds = {
        "day": 3.0, "month": 3.0, "year": 4.0, "5year": 6.0, "10year": 8.0,
    }
    threshold = float(request.args.get("threshold", default_thresholds.get(period, 3.0)))
    max_events = {"day": 20, "month": 30, "year": 30, "5year": 30, "10year": 30}.get(period, 30)

    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta
    today = date.today()
    period_start = {
        "day": today - timedelta(days=60),
        "month": today - relativedelta(months=3),
        "year": today - relativedelta(years=1, months=2),
        "5year": today - relativedelta(years=5, months=3),
        "10year": today - relativedelta(years=10, months=6),
    }.get(period, today - relativedelta(months=3))

    try:
        if s.is_overseas:
            import yfinance as yf
            ticker = yf.Ticker(s.stock_code)
            hist = ticker.history(start=period_start.strftime("%Y-%m-%d"),
                                 end=(today + timedelta(days=1)).strftime("%Y-%m-%d"))
            if hist.empty:
                return jsonify({"events": []})
            # 5year/10year는 주봉/월봉으로 리샘플링 (차트와 동일)
            resample_map = {"5year": "W", "10year": "ME"}
            if period in resample_map:
                hist = hist.resample(resample_map[period]).agg({
                    "Open": "first", "High": "max", "Low": "min",
                    "Close": "last", "Volume": "sum"
                }).dropna()
            hist = hist.reset_index()
            hist["change_pct"] = hist["Close"].pct_change() * 100

            # 1단계: threshold 넘는 이벤트 후보 수집 (뉴스 검색 없이)
            candidates = []
            for _, row in hist.iterrows():
                chg = row.get("change_pct", 0)
                if pd.isna(chg) or abs(chg) < threshold:
                    continue
                d = row["Date"]
                date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
                candidates.append({
                    "date_str": date_str,
                    "chg": float(chg),
                    "close": round(float(row["Close"]), 2),
                })

            # 2단계: 변동폭 큰 순으로 상위 max_events개만 선택
            candidates.sort(key=lambda x: abs(x["chg"]), reverse=True)
            candidates = candidates[:max_events]
            candidates.sort(key=lambda x: x["date_str"])  # 시간순 정렬

            # 3단계: 선택된 이벤트에 대해서만 뉴스 검색 (해외: Yahoo/Bing)
            day_range = {"day": 1, "month": 1, "year": 3, "5year": 7, "10year": 14}.get(period, 1)
            events = []
            for c in candidates:
                date_str = c["date_str"]
                chg = c["chg"]
                cache_key = f"{s.stock_code}_{date_str}"
                if cache_key not in _news_cache:
                    query = f"{s.stock_code} {s.stock_name} 주가" if s.stock_name else f"{s.stock_code} 주가"
                    _news_cache[cache_key] = _search_yahoo_news(query, date_str, day_range=day_range)
                    if not _news_cache[cache_key]:
                        _news_cache[cache_key] = _search_yahoo_news(f"{s.stock_code} 주가", date_str, day_range=day_range)

                news = _news_cache[cache_key]
                reason = " | ".join(news) if news else f"{'급등' if chg > 0 else '급락'} {chg:+.1f}%"
                events.append({
                    "time": date_str,
                    "change_pct": round(chg, 2),
                    "direction": "up" if chg > 0 else "down",
                    "reason": reason,
                    "news": news,
                    "price": c["close"],
                })
        else:
            from pykrx import stock as pykrx_stock
            start_str = period_start.strftime("%Y%m%d")
            end_str = today.strftime("%Y%m%d")
            df = pykrx_stock.get_market_ohlcv_by_date(start_str, end_str, s.stock_code)
            if df.empty:
                return jsonify({"events": []})
            # 5year/10year는 주봉/월봉으로 리샘플링
            resample_map = {"5year": "W", "10year": "ME"}
            if period in resample_map:
                df.index = pd.to_datetime(df.index)
                cols = df.columns.tolist()
                close_c = "종가" if "종가" in cols else "Close"
                open_c = "시가" if "시가" in cols else "Open"
                high_c = "고가" if "고가" in cols else "High"
                low_c = "저가" if "저가" in cols else "Low"
                vol_c = "거래량" if "거래량" in cols else "Volume"
                df = df.resample(resample_map[period]).agg({
                    open_c: "first", high_c: "max", low_c: "min",
                    close_c: "last", vol_c: "sum"
                }).dropna()
            df = df.reset_index()
            df.columns = [c.strip() for c in df.columns]
            close_col = "종가" if "종가" in df.columns else "Close"
            date_col = "날짜" if "날짜" in df.columns else df.columns[0]
            df["change_pct"] = df[close_col].pct_change() * 100

            # 1단계: threshold 넘는 이벤트 후보 수집
            candidates = []
            for _, row in df.iterrows():
                chg = row.get("change_pct", 0)
                if pd.isna(chg) or abs(chg) < threshold:
                    continue
                d = row[date_col]
                date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
                vol = row.get("거래량", row.get("Volume", 0))
                candidates.append({
                    "date_str": date_str,
                    "chg": float(chg),
                    "close": int(row[close_col]),
                    "vol": vol,
                })

            # 2단계: 변동폭 큰 순으로 상위 max_events개만 선택
            candidates.sort(key=lambda x: abs(x["chg"]), reverse=True)
            candidates = candidates[:max_events]
            candidates.sort(key=lambda x: x["date_str"])

            # 3단계: 선택된 이벤트에 대해서만 뉴스 검색 (국내: 네이버)
            day_range = {"day": 1, "month": 1, "year": 3, "5year": 7, "10year": 14}.get(period, 1)
            events = []
            for c in candidates:
                date_str = c["date_str"]
                chg = c["chg"]
                cache_key = f"{s.stock_code}_{date_str}"
                if cache_key not in _news_cache:
                    query = s.stock_name if s.stock_name else s.stock_code
                    _news_cache[cache_key] = _search_naver_news(query, date_str, day_range=day_range)

                news = _news_cache[cache_key]
                if news:
                    reason = " | ".join(news)
                else:
                    reason = f"{'급등' if chg > 0 else '급락'} {chg:+.1f}% (거래량: {int(c['vol']):,})"
                events.append({
                    "time": date_str,
                    "change_pct": round(chg, 2),
                    "direction": "up" if chg > 0 else "down",
                    "reason": reason,
                    "news": news,
                    "price": c["close"],
                })
        return jsonify({"events": events})
    except Exception as e:
        return jsonify({"error": str(e), "events": []}), 500


@bp.route("/api/strategies/<int:sid>/backtest")
def backtest_strategy(sid):
    """전략 백테스팅: 과거 데이터로 매매 시뮬레이션"""
    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta

    s = Strategy.query.get_or_404(sid)
    period = request.args.get("period", "year")
    try:
        raw_capital = request.args.get("capital", "10000000")
        initial_capital = float(raw_capital.replace(",", "").strip())
        if initial_capital <= 0:
            return jsonify({"error": "자본금은 0보다 커야 합니다"}), 400
    except (ValueError, AttributeError):
        return jsonify({"error": "잘못된 자본금 형식입니다"}), 400
    commission_rate = 0.00015  # 0.015%

    today = date.today()
    period_map = {
        "3month": today - relativedelta(months=3),
        "6month": today - relativedelta(months=6),
        "year":   today - relativedelta(years=1),
        "3year":  today - relativedelta(years=3),
        "5year":  today - relativedelta(years=5),
    }
    start_date = period_map.get(period, period_map["year"])

    # OHLCV 데이터 가져오기
    try:
        if s.is_overseas:
            import yfinance as yf
            ticker = yf.Ticker(s.stock_code)
            hist = ticker.history(start=start_date.strftime("%Y-%m-%d"),
                                  end=(today + timedelta(days=1)).strftime("%Y-%m-%d"))
            if hist.empty:
                return jsonify({"error": "데이터 없음"}), 404
            hist = hist.reset_index()
            ohlcv_list = []
            for _, row in hist.iterrows():
                ohlcv_list.append({
                    "date": row["Date"].strftime("%Y%m%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
        else:
            from pykrx import stock as pykrx_stock
            start_str = start_date.strftime("%Y%m%d")
            end_str = today.strftime("%Y%m%d")
            df = pykrx_stock.get_market_ohlcv_by_date(start_str, end_str, s.stock_code)
            if df.empty:
                return jsonify({"error": "데이터 없음"}), 404
            df = df.reset_index()
            df.columns = [c.strip() for c in df.columns]
            date_col = "날짜" if "날짜" in df.columns else df.columns[0]
            open_col = "시가" if "시가" in df.columns else "Open"
            high_col = "고가" if "고가" in df.columns else "High"
            low_col = "저가" if "저가" in df.columns else "Low"
            close_col = "종가" if "종가" in df.columns else "Close"
            vol_col = "거래량" if "거래량" in df.columns else "Volume"
            ohlcv_list = []
            for _, row in df.iterrows():
                d = row[date_col]
                ohlcv_list.append({
                    "date": d.strftime("%Y%m%d") if hasattr(d, "strftime") else str(d)[:10].replace("-", ""),
                    "open": int(row[open_col]),
                    "high": int(row[high_col]),
                    "low": int(row[low_col]),
                    "close": int(row[close_col]),
                    "volume": int(row[vol_col]),
                })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if len(ohlcv_list) < 30:
        return jsonify({"error": "데이터가 부족합니다 (최소 30일 필요)"}), 400

    # 전략 엔진 생성
    from strategies.runner import STRATEGY_MAP
    cls = STRATEGY_MAP.get(s.strategy_type)
    if cls is None:
        return jsonify({"error": f"지원하지 않는 전략 유형: {s.strategy_type}"}), 400
    engine = cls(s.stock_code, s.params or {})

    # 시뮬레이션
    cash = initial_capital
    qty = engine.get_quantity()
    holding = 0
    avg_price = 0.0
    trades = []
    equity_curve = []
    win_count = 0
    loss_count = 0
    max_equity = initial_capital
    max_drawdown = 0.0
    lookback = max(60, int((s.params or {}).get("long_period", 20)) + 5)

    for i in range(lookback, len(ohlcv_list)):
        window = ohlcv_list[max(0, i - 100):i + 1]
        bar = ohlcv_list[i]
        price = bar["close"]
        bar_date = bar["date"]
        date_str = f"{bar_date[:4]}-{bar_date[4:6]}-{bar_date[6:8]}"

        current = {
            "price": price,
            "change_rate": ((price - ohlcv_list[i - 1]["close"]) / ohlcv_list[i - 1]["close"] * 100)
                           if i > 0 else 0,
            "volume": bar["volume"],
            "high": bar["high"],
            "low": bar["low"],
            "open": bar["open"],
        }

        # 보유 중: 손절/익절 체크
        if holding > 0:
            if engine.check_stop_loss(avg_price, price):
                sell_value = price * holding
                commission = sell_value * commission_rate
                cash += sell_value - commission
                pnl = (price - avg_price) * holding - commission
                trades.append({
                    "time": date_str, "type": "sell", "price": price,
                    "qty": holding, "reason": "손절",
                    "pnl": round(pnl, 2),
                })
                if pnl >= 0:
                    win_count += 1
                else:
                    loss_count += 1
                holding = 0
                avg_price = 0
            elif engine.check_take_profit(avg_price, price):
                sell_value = price * holding
                commission = sell_value * commission_rate
                cash += sell_value - commission
                pnl = (price - avg_price) * holding - commission
                trades.append({
                    "time": date_str, "type": "sell", "price": price,
                    "qty": holding, "reason": "익절",
                    "pnl": round(pnl, 2),
                })
                win_count += 1
                holding = 0
                avg_price = 0
            elif engine.should_sell(window, current):
                sell_value = price * holding
                commission = sell_value * commission_rate
                cash += sell_value - commission
                pnl = (price - avg_price) * holding - commission
                trades.append({
                    "time": date_str, "type": "sell", "price": price,
                    "qty": holding, "reason": "시그널",
                    "pnl": round(pnl, 2),
                })
                if pnl >= 0:
                    win_count += 1
                else:
                    loss_count += 1
                holding = 0
                avg_price = 0

        # 미보유: 매수 체크
        elif holding == 0 and engine.should_buy(window, current):
            buy_cost = price * qty
            commission = buy_cost * commission_rate
            if cash >= buy_cost + commission:
                cash -= buy_cost + commission
                holding = qty
                avg_price = price
                trades.append({
                    "time": date_str, "type": "buy", "price": price,
                    "qty": qty, "reason": "시그널",
                })

        # 자산 기록
        equity = cash + (holding * price if holding > 0 else 0)
        equity_curve.append({"time": date_str, "value": round(equity, 2)})
        if equity > max_equity:
            max_equity = equity
        dd = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # 마지막 보유분 청산 (평가용)
    final_price = ohlcv_list[-1]["close"]
    final_equity = cash + (holding * final_price if holding > 0 else 0)
    total_return = (final_equity - initial_capital) / initial_capital * 100
    total_trades = len([t for t in trades if t["type"] == "sell"])

    # 벤치마크 (단순 보유)
    buy_hold_start = ohlcv_list[lookback]["close"]
    buy_hold_end = ohlcv_list[-1]["close"]
    buy_hold_qty = int(initial_capital / buy_hold_start) if buy_hold_start > 0 else 0
    buy_hold_return = ((buy_hold_end - buy_hold_start) / buy_hold_start * 100) if buy_hold_start > 0 else 0

    # 벤치마크 자산곡선
    buy_hold_curve = []
    for i in range(lookback, len(ohlcv_list)):
        bar = ohlcv_list[i]
        date_str = f"{bar['date'][:4]}-{bar['date'][4:6]}-{bar['date'][6:8]}"
        bh_equity = buy_hold_qty * bar["close"] + (initial_capital - buy_hold_qty * buy_hold_start)
        buy_hold_curve.append({"time": date_str, "value": round(bh_equity, 2)})

    return jsonify({
        "stock_code": s.stock_code,
        "stock_name": s.stock_name,
        "strategy_type": s.strategy_type,
        "period": period,
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return": round(total_return, 2),
        "buy_hold_return": round(buy_hold_return, 2),
        "total_trades": total_trades,
        "win_rate": round(win_count / (win_count + loss_count) * 100, 1) if (win_count + loss_count) > 0 else 0,
        "max_drawdown": round(max_drawdown, 2),
        "trades": trades,
        "equity_curve": equity_curve,
        "buy_hold_curve": buy_hold_curve,
    })


@bp.route("/api/strategies/<int:sid>/ai-analyze")
def ai_analyze(sid):
    """전략 종목에 대한 AI 분석 수행 (수동 테스트용)"""
    s = Strategy.query.get_or_404(sid)
    try:
        if s.is_overseas:
            ohlcv = get_overseas_daily_ohlcv(s.stock_code, s.exchange, s.mode, count=100)
            current = get_overseas_current_price(s.stock_code, s.exchange, s.mode)
        else:
            ohlcv = get_daily_ohlcv(s.stock_code, s.mode, count=100)
            current = get_current_price(s.stock_code, s.mode)
        result = analyze_stock(ohlcv, current, s.params or {})

        # AuctionAlert 저장 → alert_id 부여 → 매수/매도 버튼 활성화
        qty = (s.params or {}).get("buy_qty", 1)
        alert = AuctionAlert(
            strategy_id=s.id,
            stock_code=s.stock_code,
            stock_name=s.stock_name,
            suggested_action=result.get("action", "hold"),
            suggested_price=current["price"],
            suggested_qty=qty,
            ai_confidence=result.get("confidence", 0),
            ai_score=result.get("total_score", 0),
            ai_summary=result.get("summary", ""),
            ai_factors=result.get("factors", []),
            expires_at=datetime.now() + timedelta(minutes=10),
        )
        db.session.add(alert)
        db.session.commit()

        result["id"] = alert.id
        result["stock_code"] = s.stock_code
        result["stock_name"] = s.stock_name
        result["price"] = current["price"]
        result["change_rate"] = current["change_rate"]
        result["suggested_qty"] = qty
        result["expires_at"] = alert.expires_at.isoformat()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
