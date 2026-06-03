import json
import queue
import threading
from datetime import datetime
from flask import Blueprint, jsonify, request, Response, stream_with_context
from db import db
from models import AuctionAlert, Order

bp = Blueprint("auction", __name__, url_prefix="/api/auction")

_sse_clients: list = []
_lock = threading.Lock()


def broadcast_auction(alert_id: int):
    alert = AuctionAlert.query.get(alert_id)
    if not alert:
        return
    msg = json.dumps({
        "id": alert.id,
        "stock_code": alert.stock_code,
        "stock_name": alert.stock_name,
        "suggested_action": alert.suggested_action,
        "suggested_price": alert.suggested_price,
        "suggested_qty": alert.suggested_qty,
        "ai_confidence": alert.ai_confidence or 0,
        "ai_score": alert.ai_score or 0,
        "ai_summary": alert.ai_summary or "",
        "ai_factors": alert.ai_factors or [],
        "expires_at": alert.expires_at.isoformat(),
    })
    with _lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


@bp.route("/stream")
def stream():
    q = queue.Queue(maxsize=20)
    with _lock:
        _sse_clients.append(q)

    def generate():
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        except GeneratorExit:
            with _lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@bp.route("/pending")
def pending():
    now = datetime.now()  # KST naive — consistent with expires_at
    alerts = AuctionAlert.query.filter_by(user_decision=None).filter(
        AuctionAlert.expires_at >= now
    ).order_by(AuctionAlert.created_at.desc()).all()
    return jsonify([{
        "id": a.id, "stock_code": a.stock_code, "stock_name": a.stock_name,
        "suggested_action": a.suggested_action, "suggested_price": a.suggested_price,
        "suggested_qty": a.suggested_qty,
        "ai_confidence": a.ai_confidence or 0,
        "ai_score": a.ai_score or 0,
        "ai_summary": a.ai_summary or "",
        "ai_factors": a.ai_factors or [],
        "expires_at": a.expires_at.isoformat(),
    } for a in alerts])


@bp.route("/decide/<int:alert_id>", methods=["POST"])
def decide(alert_id: int):
    data = request.get_json()
    decision = data.get("decision")
    if decision not in ("buy", "sell", "pass"):
        return jsonify({"error": "decision must be buy/sell/pass"}), 400

    alert = AuctionAlert.query.get_or_404(alert_id)
    if alert.user_decision is not None:
        return jsonify({"error": "already decided"}), 400

    alert.user_decision = decision
    alert.decided_at = datetime.now()  # KST naive
    db.session.commit()

    if decision in ("buy", "sell"):
        from kis_api import place_order
        from models import Strategy
        from routers.esg import _check_invest_limit, create_audit_log
        from esg_data import get_esg

        strat = Strategy.query.get(alert.strategy_id)
        mode = strat.mode if strat else "paper"

        # 사용자가 설정한 가격/수량 우선, 없으면 AI 추천값
        order_price = data.get("price", alert.suggested_price)
        order_qty = data.get("quantity", alert.suggested_qty)
        order_price = int(order_price) if order_price else int(alert.suggested_price)
        order_qty = int(order_qty) if order_qty else alert.suggested_qty

        # 투자 한도 + ESG 필터 체크 (매수만)
        if decision == "buy":
            limit_check = _check_invest_limit(order_price * order_qty, alert.stock_code)
            if not limit_check["allowed"]:
                esg = get_esg(alert.stock_code)
                create_audit_log(
                    action="blocked", stock_code=alert.stock_code,
                    stock_name=alert.stock_name, price=order_price,
                    quantity=order_qty, mode=mode,
                    reason=limit_check["reason"],
                    ai_score=alert.ai_score, ai_summary=alert.ai_summary,
                    esg_grade=esg.get("total_grade", ""),
                )
                return jsonify({"message": f"주문 차단: {limit_check['reason']}"}), 400

        result = place_order(alert.stock_code, decision,
                             order_price, order_qty, mode)
        order = Order(
            strategy_id=alert.strategy_id,
            stock_code=alert.stock_code,
            order_type=decision,
            price=order_price,
            quantity=order_qty,
            status="submitted" if result["success"] else "pending",
            trigger="auction_manual",
            mode=mode,
            kis_order_no=result.get("order_no", ""),
        )
        db.session.add(order)
        db.session.commit()

        # 감사 로그 기록
        esg = get_esg(alert.stock_code)
        create_audit_log(
            order=order, action=decision,
            stock_code=alert.stock_code, stock_name=alert.stock_name,
            price=order_price, quantity=order_qty, mode=mode,
            reason=f"AI 분석 기반 {decision} (점수: {alert.ai_score})",
            ai_score=alert.ai_score, ai_summary=alert.ai_summary,
            esg_grade=esg.get("total_grade", ""),
        )

        price_text = "시장가" if order_price == 0 else f"{order_price:,}원"
        label = "매수" if decision == "buy" else "매도"
        return jsonify({"message": f"{label} 주문 완료! {alert.stock_code} {order_qty}주 × {price_text}"})

    return jsonify({"message": f"{decision} 처리 완료"})
