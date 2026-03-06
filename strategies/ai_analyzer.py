"""
RAG 기반 AI 종목 분석기
- 일봉 OHLCV, 현재가, 기술적 지표를 종합 분석
- 각 팩터별 점수(-100 ~ +100)를 산출하고 가중 합산
- 최종 매수/매도/관망 추천 + 신뢰도 + 근거 텍스트 생성
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def analyze_stock(ohlcv: list, current: dict, params: dict = None) -> dict:
    """
    종합 AI 분석 수행.

    Returns:
        {
            "action": "buy" | "sell" | "hold",
            "confidence": 0~100,
            "total_score": -100~100,
            "factors": [{"name": ..., "score": ..., "weight": ..., "reason": ...}, ...],
            "summary": "종합 판단 텍스트",
        }
    """
    if not ohlcv or len(ohlcv) < 10:
        return _default_result("데이터 부족 (최소 10일 필요)")

    params = params or {}
    df = pd.DataFrame(ohlcv)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.sort_values("date").reset_index(drop=True)

    price = current.get("price", df["close"].iloc[-1])
    change_rate = current.get("change_rate", 0)

    factors = []

    # 1. 이동평균 추세 분석
    factors.append(_analyze_ma_trend(df, price, params))

    # 2. RSI 분석
    factors.append(_analyze_rsi(df, params))

    # 3. MACD 분석
    factors.append(_analyze_macd(df, params))

    # 4. 거래량 분석
    factors.append(_analyze_volume(df, current))

    # 5. 가격 모멘텀
    factors.append(_analyze_momentum(df, price))

    # 6. 변동성 분석
    factors.append(_analyze_volatility(df))

    # 7. 캔들 패턴 분석
    factors.append(_analyze_candle_pattern(df))

    # 8. 당일 등락 분석
    factors.append(_analyze_intraday(current, change_rate))

    # 가중 합산
    total_weighted = sum(f["score"] * f["weight"] for f in factors)
    total_weight = sum(f["weight"] for f in factors)
    total_score = total_weighted / total_weight if total_weight > 0 else 0

    # 신뢰도 계산 (팩터 간 일치도)
    signs = [1 if f["score"] > 10 else (-1 if f["score"] < -10 else 0) for f in factors]
    agreement = abs(sum(signs)) / len(signs) if signs else 0
    confidence = min(95, int(abs(total_score) * 0.7 + agreement * 30))

    # 최종 판단
    if total_score >= 20:
        action = "buy"
    elif total_score <= -20:
        action = "sell"
    else:
        action = "hold"

    # 요약 텍스트 생성
    summary = _generate_summary(action, confidence, total_score, factors, price, change_rate)

    return {
        "action": action,
        "confidence": confidence,
        "total_score": round(total_score, 1),
        "factors": factors,
        "summary": summary,
    }


def _default_result(reason: str) -> dict:
    return {
        "action": "hold",
        "confidence": 0,
        "total_score": 0,
        "factors": [],
        "summary": reason,
    }


# ──────────── 팩터 분석 함수들 ────────────

def _analyze_ma_trend(df, price, params):
    """이동평균선 배열/정배열 분석"""
    short_p = params.get("short_period", 5)
    long_p = params.get("long_period", 20)

    ma5 = df["close"].rolling(short_p).mean()
    ma20 = df["close"].rolling(long_p).mean()
    ma60 = df["close"].rolling(60).mean()

    score = 0
    reasons = []

    if len(ma5.dropna()) > 0 and len(ma20.dropna()) > 0:
        cur_ma5 = ma5.iloc[-1]
        cur_ma20 = ma20.iloc[-1]
        prev_ma5 = ma5.iloc[-2] if len(ma5) > 1 else cur_ma5
        prev_ma20 = ma20.iloc[-2] if len(ma20) > 1 else cur_ma20

        # 골든크로스 / 데드크로스 감지
        if prev_ma5 <= prev_ma20 and cur_ma5 > cur_ma20:
            score += 40
            reasons.append("골든크로스 발생")
        elif prev_ma5 >= prev_ma20 and cur_ma5 < cur_ma20:
            score -= 40
            reasons.append("데드크로스 발생")

        # 현재가 vs 이동평균 위치
        if price > cur_ma5 > cur_ma20:
            score += 25
            reasons.append("정배열 (가격>단기>장기)")
        elif price < cur_ma5 < cur_ma20:
            score -= 25
            reasons.append("역배열 (가격<단기<장기)")

        # 60일선 위/아래
        if len(ma60.dropna()) > 0:
            cur_ma60 = ma60.iloc[-1]
            if price > cur_ma60:
                score += 10
                reasons.append("60일선 위")
            else:
                score -= 10
                reasons.append("60일선 아래")

    score = max(-100, min(100, score))
    return {"name": "이동평균 추세", "score": score, "weight": 0.20,
            "reason": " / ".join(reasons) if reasons else "중립"}


def _analyze_rsi(df, params):
    """RSI 과매수/과매도 분석"""
    period = params.get("rsi_period", 14)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    score = 0
    reasons = []

    if len(rsi.dropna()) > 0:
        cur_rsi = rsi.iloc[-1]
        if cur_rsi <= 20:
            score = 60
            reasons.append(f"RSI {cur_rsi:.0f} 극도 과매도")
        elif cur_rsi <= 30:
            score = 35
            reasons.append(f"RSI {cur_rsi:.0f} 과매도 진입")
        elif cur_rsi >= 80:
            score = -60
            reasons.append(f"RSI {cur_rsi:.0f} 극도 과매수")
        elif cur_rsi >= 70:
            score = -35
            reasons.append(f"RSI {cur_rsi:.0f} 과매수 진입")
        elif 40 <= cur_rsi <= 60:
            score = 5
            reasons.append(f"RSI {cur_rsi:.0f} 중립 구간")
        else:
            reasons.append(f"RSI {cur_rsi:.0f}")

        # RSI 추세 (상승 전환 / 하락 전환)
        if len(rsi.dropna()) >= 3:
            rsi_recent = rsi.dropna().tail(3)
            if rsi_recent.iloc[-1] > rsi_recent.iloc[-2] > rsi_recent.iloc[-3]:
                score += 10
                reasons.append("RSI 상승 전환")
            elif rsi_recent.iloc[-1] < rsi_recent.iloc[-2] < rsi_recent.iloc[-3]:
                score -= 10
                reasons.append("RSI 하락 전환")

    score = max(-100, min(100, score))
    return {"name": "RSI", "score": score, "weight": 0.15,
            "reason": " / ".join(reasons) if reasons else "분석 불가"}


def _analyze_macd(df, params):
    """MACD 신호 분석"""
    fast = params.get("macd_fast", 12)
    slow = params.get("macd_slow", 26)
    sig_p = params.get("macd_signal", 9)

    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=sig_p, adjust=False).mean()
    hist = macd - signal

    score = 0
    reasons = []

    if len(hist.dropna()) >= 2:
        cur_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2]
        cur_macd = macd.iloc[-1]

        # 히스토그램 전환
        if prev_hist <= 0 and cur_hist > 0:
            score += 40
            reasons.append("MACD 히스토그램 양전환")
        elif prev_hist >= 0 and cur_hist < 0:
            score -= 40
            reasons.append("MACD 히스토그램 음전환")

        # MACD 방향
        if cur_macd > 0 and cur_hist > 0:
            score += 15
            reasons.append("MACD 양(+) 강세")
        elif cur_macd < 0 and cur_hist < 0:
            score -= 15
            reasons.append("MACD 음(-) 약세")

        # 히스토그램 확대/축소
        if abs(cur_hist) > abs(prev_hist):
            if cur_hist > 0:
                score += 10
                reasons.append("매수세 확대")
            else:
                score -= 10
                reasons.append("매도세 확대")

    score = max(-100, min(100, score))
    return {"name": "MACD", "score": score, "weight": 0.15,
            "reason": " / ".join(reasons) if reasons else "분석 불가"}


def _analyze_volume(df, current):
    """거래량 이상 신호 분석"""
    vol_ma20 = df["volume"].rolling(20).mean()
    score = 0
    reasons = []

    if len(vol_ma20.dropna()) > 0:
        cur_vol = current.get("volume", df["volume"].iloc[-1])
        avg_vol = vol_ma20.iloc[-1]

        if avg_vol > 0:
            vol_ratio = cur_vol / avg_vol

            if vol_ratio >= 3.0:
                # 거래량 폭발 - 방향에 따라 판단
                change = current.get("change_rate", 0)
                if change > 0:
                    score = 45
                    reasons.append(f"거래량 폭발 ({vol_ratio:.1f}배) + 상승")
                else:
                    score = -30
                    reasons.append(f"거래량 폭발 ({vol_ratio:.1f}배) + 하락 (투매 가능성)")
            elif vol_ratio >= 1.5:
                score = 15
                reasons.append(f"평균 대비 거래량 증가 ({vol_ratio:.1f}배)")
            elif vol_ratio <= 0.5:
                score = -10
                reasons.append(f"거래량 부진 ({vol_ratio:.1f}배)")
            else:
                reasons.append(f"거래량 보통 ({vol_ratio:.1f}배)")

    score = max(-100, min(100, score))
    return {"name": "거래량", "score": score, "weight": 0.15,
            "reason": " / ".join(reasons) if reasons else "분석 불가"}


def _analyze_momentum(df, price):
    """가격 모멘텀 (단기/중기 수익률)"""
    score = 0
    reasons = []

    closes = df["close"]
    if len(closes) >= 5:
        ret_5d = (price - closes.iloc[-5]) / closes.iloc[-5] * 100
        if ret_5d > 5:
            score += 20
            reasons.append(f"5일 수익률 +{ret_5d:.1f}% (강세)")
        elif ret_5d < -5:
            score -= 15
            reasons.append(f"5일 수익률 {ret_5d:.1f}% (약세)")
        else:
            reasons.append(f"5일 수익률 {ret_5d:+.1f}%")

    if len(closes) >= 20:
        ret_20d = (price - closes.iloc[-20]) / closes.iloc[-20] * 100
        if ret_20d > 10:
            score += 15
            reasons.append(f"20일 수익률 +{ret_20d:.1f}%")
        elif ret_20d < -10:
            score -= 20
            reasons.append(f"20일 수익률 {ret_20d:.1f}%")

        # 과열 경고
        if ret_5d > 10 and ret_20d > 15:
            score -= 20
            reasons.append("단기 과열 주의")
        # 반등 가능성
        elif ret_5d > 0 and ret_20d < -10:
            score += 15
            reasons.append("저점 반등 신호")

    score = max(-100, min(100, score))
    return {"name": "모멘텀", "score": score, "weight": 0.10,
            "reason": " / ".join(reasons) if reasons else "분석 불가"}


def _analyze_volatility(df):
    """변동성 분석 (ATR 기반)"""
    score = 0
    reasons = []

    if len(df) >= 14:
        high_low = df["high"] - df["low"]
        atr = high_low.rolling(14).mean()
        cur_atr = atr.iloc[-1]
        avg_price = df["close"].iloc[-1]

        if avg_price > 0:
            atr_pct = cur_atr / avg_price * 100

            if atr_pct > 5:
                score = -20
                reasons.append(f"고변동 (ATR {atr_pct:.1f}%) - 리스크 높음")
            elif atr_pct > 3:
                score = -5
                reasons.append(f"변동성 주의 (ATR {atr_pct:.1f}%)")
            elif atr_pct < 1.5:
                score = 5
                reasons.append(f"안정적 (ATR {atr_pct:.1f}%)")
            else:
                reasons.append(f"보통 변동성 (ATR {atr_pct:.1f}%)")

        # 변동성 추세
        if len(atr.dropna()) >= 5:
            recent_atr = atr.dropna().tail(5)
            if recent_atr.iloc[-1] > recent_atr.iloc[0] * 1.3:
                score -= 10
                reasons.append("변동성 확대 중")
            elif recent_atr.iloc[-1] < recent_atr.iloc[0] * 0.7:
                score += 5
                reasons.append("변동성 축소 중")

    score = max(-100, min(100, score))
    return {"name": "변동성", "score": score, "weight": 0.10,
            "reason": " / ".join(reasons) if reasons else "분석 불가"}


def _analyze_candle_pattern(df):
    """최근 캔들 패턴 분석"""
    score = 0
    reasons = []

    if len(df) >= 3:
        last = df.iloc[-1]
        prev = df.iloc[-2]

        body = last["close"] - last["open"]
        body_size = abs(body)
        total_range = last["high"] - last["low"]

        if total_range > 0:
            body_ratio = body_size / total_range

            # 양봉/음봉 판단
            if body > 0:
                # 망치형 (하락 후 긴 아래꼬리)
                lower_wick = last["open"] - last["low"]
                if lower_wick > body_size * 2 and prev["close"] < prev["open"]:
                    score += 30
                    reasons.append("망치형 캔들 (반등 신호)")
                elif body_ratio > 0.7:
                    score += 15
                    reasons.append("강한 양봉")
            else:
                # 교수형 (상승 후 긴 위꼬리)
                upper_wick = last["high"] - last["open"]
                if upper_wick > body_size * 2 and prev["close"] > prev["open"]:
                    score -= 30
                    reasons.append("교수형 캔들 (하락 신호)")
                elif body_ratio > 0.7:
                    score -= 15
                    reasons.append("강한 음봉")

            # 도지 (몸통 매우 작음)
            if body_ratio < 0.1 and total_range > 0:
                score = 0
                reasons.append("도지 캔들 (추세 전환 가능)")

        # 3일 연속 상승/하락
        if len(df) >= 4:
            last3 = df.tail(3)
            if all(last3["close"].values[i] > last3["open"].values[i] for i in range(3)):
                score += 15
                reasons.append("3일 연속 양봉")
            elif all(last3["close"].values[i] < last3["open"].values[i] for i in range(3)):
                score -= 15
                reasons.append("3일 연속 음봉")

    score = max(-100, min(100, score))
    return {"name": "캔들 패턴", "score": score, "weight": 0.08,
            "reason": " / ".join(reasons) if reasons else "특이 패턴 없음"}


def _analyze_intraday(current, change_rate):
    """당일 장중 등락 분석"""
    score = 0
    reasons = []

    if change_rate > 5:
        score = -20
        reasons.append(f"당일 +{change_rate:.1f}% 급등 (추격매수 위험)")
    elif change_rate > 2:
        score = 10
        reasons.append(f"당일 +{change_rate:.1f}% 상승세")
    elif change_rate < -5:
        score = 15
        reasons.append(f"당일 {change_rate:.1f}% 급락 (반등 가능)")
    elif change_rate < -2:
        score = -15
        reasons.append(f"당일 {change_rate:.1f}% 하락세")
    else:
        reasons.append(f"당일 {change_rate:+.1f}% 보합")

    # 고가 대비 위치
    high = current.get("high", 0)
    low = current.get("low", 0)
    price = current.get("price", 0)
    if high > low > 0:
        position = (price - low) / (high - low)
        if position > 0.9:
            score += 10
            reasons.append("장중 고점 부근")
        elif position < 0.1:
            score -= 10
            reasons.append("장중 저점 부근")

    score = max(-100, min(100, score))
    return {"name": "당일 등락", "score": score, "weight": 0.07,
            "reason": " / ".join(reasons) if reasons else "보합"}


# ──────────── 요약 생성 ────────────

def _generate_summary(action, confidence, total_score, factors, price, change_rate):
    """분석 결과를 자연어 요약 텍스트로 생성"""
    action_text = {"buy": "매수", "sell": "매도", "hold": "관망"}.get(action, "관망")
    conf_text = "높음" if confidence >= 70 else ("보통" if confidence >= 40 else "낮음")

    # 주요 근거 추출 (가중 점수 상위 3개)
    sorted_factors = sorted(factors, key=lambda f: abs(f["score"] * f["weight"]), reverse=True)
    top_reasons = [f["reason"] for f in sorted_factors[:3] if f["reason"] != "중립"]

    bullish = [f for f in factors if f["score"] > 10]
    bearish = [f for f in factors if f["score"] < -10]

    lines = []
    lines.append(f"AI 종합 판단: {action_text} (신뢰도 {confidence}% / 점수 {total_score:+.0f})")
    lines.append(f"현재가 {price:,}원 ({change_rate:+.1f}%)")

    if bullish:
        lines.append(f"긍정 요인 {len(bullish)}개: " + ", ".join(f["name"] for f in bullish))
    if bearish:
        lines.append(f"부정 요인 {len(bearish)}개: " + ", ".join(f["name"] for f in bearish))

    if top_reasons:
        lines.append("핵심 근거: " + " | ".join(top_reasons))

    if action == "buy":
        lines.append("장 마감 전 매수 포지션을 권장합니다.")
    elif action == "sell":
        lines.append("장 마감 전 매도(익절/손절)를 권장합니다.")
    else:
        lines.append("뚜렷한 방향성이 없어 관망을 권장합니다.")

    return "\n".join(lines)
