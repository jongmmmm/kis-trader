import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from db import db
from models import Strategy
from kis_api import get_daily_ohlcv, get_current_price
from strategies.ai_analyzer import analyze_stock

bp = Blueprint("strategies", __name__, url_prefix="/strategies")

@bp.route("/")
def index():
    return render_template("strategies.html")

@bp.route("/api/strategies")
def list_strategies():
    items = Strategy.query.order_by(Strategy.created_at.desc()).all()
    return jsonify([{
        "id": s.id, "name": s.name, "stock_code": s.stock_code,
        "stock_name": s.stock_name, "strategy_type": s.strategy_type,
        "params": s.params, "is_active": s.is_active, "mode": s.mode,
    } for s in items])

@bp.route("/api/strategies", methods=["POST"])
def create_strategy():
    d = request.get_json()
    s = Strategy(
        name=d["name"], stock_code=d["stock_code"],
        stock_name=d.get("stock_name", ""),
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
    for field in ("name", "stock_code", "stock_name", "strategy_type", "params", "is_active", "mode"):
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
    candles = []
    for _, r in df.iterrows():
        candles.append({
            "time": r["date"].strftime("%Y-%m-%d"),
            "open": int(r["open"]), "high": int(r["high"]),
            "low": int(r["low"]), "close": int(r["close"]),
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


@bp.route("/api/strategies/<int:sid>/ai-analyze")
def ai_analyze(sid):
    """전략 종목에 대한 AI 분석 수행 (수동 테스트용)"""
    s = Strategy.query.get_or_404(sid)
    try:
        ohlcv = get_daily_ohlcv(s.stock_code, s.mode, count=100)
        current = get_current_price(s.stock_code, s.mode)
        result = analyze_stock(ohlcv, current, s.params or {})
        result["stock_code"] = s.stock_code
        result["stock_name"] = s.stock_name
        result["price"] = current["price"]
        result["change_rate"] = current["change_rate"]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
