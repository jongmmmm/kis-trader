"""ESG 등급 조회 + 투자 한도 + 감사 로그 API"""

from flask import Blueprint, jsonify, request
from db import db
from models import EsgScore, AuditLog, InvestLimit, Order, _now_kst
from esg_data import get_esg, check_esg_filter, ESG_DATABASE
from datetime import datetime, timedelta

bp = Blueprint("esg", __name__)


# ═══════════════════════════════════════════════
# ESG 등급 조회
# ═══════════════════════════════════════════════

@bp.route("/api/esg/<stock_code>")
def esg_score(stock_code):
    """종목 ESG 등급 조회"""
    return jsonify(get_esg(stock_code))


@bp.route("/api/esg/check-filter", methods=["POST"])
def esg_check():
    """ESG 필터 체크"""
    data = request.get_json()
    stock_code = data.get("stock_code", "")
    min_grade = data.get("min_grade", "")
    return jsonify(check_esg_filter(stock_code, min_grade))


@bp.route("/api/esg/list")
def esg_list():
    """ESG 데이터 보유 종목 전체 조회"""
    results = []
    for code in ESG_DATABASE:
        results.append(get_esg(code))
    results.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(results)


# ═══════════════════════════════════════════════
# 투자 한도 설정
# ═══════════════════════════════════════════════

@bp.route("/api/invest-limit", methods=["GET"])
def get_limit():
    """현재 투자 한도 조회"""
    limit = InvestLimit.query.first()
    if not limit:
        return jsonify({"daily_limit": 0, "monthly_limit": 0, "per_order_limit": 0, "esg_min_grade": ""})
    return jsonify({
        "daily_limit": limit.daily_limit,
        "monthly_limit": limit.monthly_limit,
        "per_order_limit": limit.per_order_limit,
        "esg_min_grade": limit.esg_min_grade,
    })


@bp.route("/api/invest-limit", methods=["POST"])
def set_limit():
    """투자 한도 설정"""
    data = request.get_json()
    limit = InvestLimit.query.first()
    if not limit:
        limit = InvestLimit()
        db.session.add(limit)
    limit.daily_limit = float(data.get("daily_limit", 0))
    limit.monthly_limit = float(data.get("monthly_limit", 0))
    limit.per_order_limit = float(data.get("per_order_limit", 0))
    limit.esg_min_grade = data.get("esg_min_grade", "")
    limit.updated_at = _now_kst()
    db.session.commit()
    return jsonify({"message": "투자 한도가 설정되었습니다."})


@bp.route("/api/invest-limit/check", methods=["POST"])
def check_limit():
    """주문 전 한도 체크"""
    data = request.get_json()
    order_amount = float(data.get("amount", 0))
    stock_code = data.get("stock_code", "")
    result = _check_invest_limit(order_amount, stock_code)
    return jsonify(result)


def _check_invest_limit(order_amount: float, stock_code: str = "") -> dict:
    """투자 한도 + ESG 필터 통합 체크"""
    limit = InvestLimit.query.first()
    if not limit:
        return {"allowed": True, "reason": "한도 미설정"}

    # 건당 한도
    if limit.per_order_limit > 0 and order_amount > limit.per_order_limit:
        return {"allowed": False, "reason": f"건당 한도 초과 ({order_amount:,.0f} > {limit.per_order_limit:,.0f}원)"}

    # 일일 한도
    if limit.daily_limit > 0:
        now = _now_kst()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_total = db.session.query(db.func.sum(Order.price * Order.quantity)).filter(
            Order.order_type == "buy",
            Order.created_at >= today_start,
        ).scalar() or 0
        if daily_total + order_amount > limit.daily_limit:
            return {"allowed": False, "reason": f"일일 한도 초과 (오늘 {daily_total:,.0f} + {order_amount:,.0f} > {limit.daily_limit:,.0f}원)"}

    # 월간 한도
    if limit.monthly_limit > 0:
        now = _now_kst()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_total = db.session.query(db.func.sum(Order.price * Order.quantity)).filter(
            Order.order_type == "buy",
            Order.created_at >= month_start,
        ).scalar() or 0
        if monthly_total + order_amount > limit.monthly_limit:
            return {"allowed": False, "reason": f"월간 한도 초과 (이번달 {monthly_total:,.0f} + {order_amount:,.0f} > {limit.monthly_limit:,.0f}원)"}

    # ESG 필터
    if limit.esg_min_grade and stock_code:
        esg_result = check_esg_filter(stock_code, limit.esg_min_grade)
        if not esg_result["passed"]:
            return {"allowed": False, "reason": f"ESG 필터 차단: {esg_result['reason']}"}

    return {"allowed": True, "reason": "한도 내 주문 가능"}


def create_audit_log(order=None, **kwargs):
    """감사 로그 생성"""
    log = AuditLog(
        order_id=order.id if order else kwargs.get("order_id"),
        action=kwargs.get("action", ""),
        stock_code=kwargs.get("stock_code", ""),
        stock_name=kwargs.get("stock_name", ""),
        price=kwargs.get("price", 0),
        quantity=kwargs.get("quantity", 0),
        mode=kwargs.get("mode", "paper"),
        reason=kwargs.get("reason", ""),
        ai_score=kwargs.get("ai_score"),
        ai_summary=kwargs.get("ai_summary", ""),
        esg_grade=kwargs.get("esg_grade", ""),
        user=kwargs.get("user", "system"),
    )
    db.session.add(log)
    db.session.commit()
    return log


# ═══════════════════════════════════════════════
# 감사 로그 조회
# ═══════════════════════════════════════════════

@bp.route("/api/audit-logs")
def list_audit_logs():
    """감사 로그 조회"""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify([{
        "id": l.id,
        "action": l.action,
        "stock_code": l.stock_code,
        "stock_name": l.stock_name,
        "price": l.price,
        "quantity": l.quantity,
        "mode": l.mode,
        "reason": l.reason,
        "ai_score": l.ai_score,
        "ai_summary": l.ai_summary,
        "esg_grade": l.esg_grade,
        "user": l.user,
        "created_at": l.created_at.isoformat(),
    } for l in logs])
