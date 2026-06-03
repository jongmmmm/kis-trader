from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from models import ChatSession, ChatMessage
from db import db
import json

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat/sessions", methods=["GET"])
@login_required
def get_sessions():
    sessions = ChatSession.query.filter_by(user_id=current_user.id)\
        .order_by(ChatSession.updated_at.desc()).all()
    return jsonify([{
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    } for s in sessions])


@chat_bp.route("/api/chat/sessions", methods=["POST"])
@login_required
def create_session():
    s = ChatSession(user_id=current_user.id, title="새 대화")
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()})


@chat_bp.route("/api/chat/sessions/<int:sid>", methods=["DELETE"])
@login_required
def delete_session(sid):
    s = ChatSession.query.filter_by(id=sid, user_id=current_user.id).first()
    if not s:
        return jsonify({"error": "not found"}), 404
    db.session.delete(s)
    db.session.commit()
    return jsonify({"ok": True})


@chat_bp.route("/api/chat/sessions/<int:sid>/messages", methods=["GET"])
@login_required
def get_messages(sid):
    s = ChatSession.query.filter_by(id=sid, user_id=current_user.id).first()
    if not s:
        return jsonify({"error": "not found"}), 404
    msgs = ChatMessage.query.filter_by(session_id=sid)\
        .order_by(ChatMessage.created_at.asc()).all()
    return jsonify([{
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    } for m in msgs])


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    question = data.get("message", "").strip()
    session_id = data.get("session_id")
    if not question:
        return jsonify({"error": "메시지를 입력해주세요."}), 400

    # 세션이 없으면 새로 생성
    if not session_id:
        s = ChatSession(user_id=current_user.id, title=question[:30])
        db.session.add(s)
        db.session.commit()
        session_id = s.id
    else:
        s = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not s:
            return jsonify({"error": "session not found"}), 404

    # 사용자 메시지 저장
    user_msg = ChatMessage(session_id=session_id, role="user", content=question)
    db.session.add(user_msg)

    from chatbot.engine import ask
    answer = ask(question)

    # 봇 응답 저장
    bot_msg = ChatMessage(session_id=session_id, role="bot", content=answer)
    db.session.add(bot_msg)

    # 첫 메시지면 제목 업데이트
    s = ChatSession.query.get(session_id)
    if s and s.title == "새 대화":
        s.title = question[:30]

    db.session.commit()

    return jsonify({
        "answer": answer,
        "session_id": session_id,
    })
