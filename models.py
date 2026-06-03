from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def _now_kst():
    return datetime.now(KST).replace(tzinfo=None)
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from db import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(50), default="")
    phone = db.Column(db.String(11), default="")
    email = db.Column(db.String(120), default="")
    birth_date = db.Column(db.String(10), default="")
    remember_token = db.Column(db.String(256), default="")
    login_method = db.Column(db.String(20), default="password")  # password|webauthn
    webauthn_credentials = db.Column(db.JSON, default=[])
    created_at = db.Column(db.DateTime, default=_now_kst)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Strategy(db.Model):
    __tablename__ = "strategies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock_code = db.Column(db.String(10), nullable=False)
    stock_name = db.Column(db.String(50), default="")
    exchange = db.Column(db.String(10), default="")  # 빈값=국내, NAS/NYS/AMS/HKS/TSE 등=해외
    strategy_type = db.Column(db.String(20), nullable=False)  # ma|rsi_macd|condition|ml
    params = db.Column(db.JSON, default={})
    is_active = db.Column(db.Boolean, default=True)
    mode = db.Column(db.String(10), default="paper")  # paper|real
    created_at = db.Column(db.DateTime, default=_now_kst)

    @property
    def is_overseas(self):
        return bool(self.exchange)

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey("strategies.id"), nullable=True)
    stock_code = db.Column(db.String(10), nullable=False)
    order_type = db.Column(db.String(4), nullable=False)   # buy|sell
    price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="pending")   # pending|submitted|filled|cancelled
    trigger = db.Column(db.String(20), default="auto")     # auto|auction_manual
    mode = db.Column(db.String(10), default="paper")
    kis_order_no = db.Column(db.String(50), default="")
    created_at = db.Column(db.DateTime, default=_now_kst)

class AuctionAlert(db.Model):
    __tablename__ = "auction_alerts"
    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey("strategies.id"), nullable=True)
    stock_code = db.Column(db.String(10), nullable=False)
    stock_name = db.Column(db.String(50), default="")
    suggested_action = db.Column(db.String(4))   # buy|sell|hold
    suggested_price = db.Column(db.Float, default=0)
    suggested_qty = db.Column(db.Integer, default=0)
    ai_confidence = db.Column(db.Integer, default=0)          # 0~100
    ai_score = db.Column(db.Float, default=0)                 # -100~100
    ai_summary = db.Column(db.Text, default="")               # AI 종합 요약
    ai_factors = db.Column(db.JSON, default=[])               # 팩터별 분석 상세
    user_decision = db.Column(db.String(4), nullable=True)    # buy|sell|pass|None
    decided_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=_now_kst)

class PortfolioSnapshot(db.Model):
    __tablename__ = "portfolio_snapshots"
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(10))
    stock_code = db.Column(db.String(10))
    quantity = db.Column(db.Integer, default=0)
    avg_price = db.Column(db.Float, default=0)
    current_price = db.Column(db.Float, default=0)
    snapped_at = db.Column(db.DateTime, default=_now_kst)

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100), default="새 대화")
    created_at = db.Column(db.DateTime, default=_now_kst)
    updated_at = db.Column(db.DateTime, default=_now_kst, onupdate=_now_kst)
    messages = db.relationship("ChatMessage", backref="session", lazy=True, cascade="all, delete-orphan")

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # user|bot
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_now_kst)

class EsgScore(db.Model):
    """종목별 ESG 등급"""
    __tablename__ = "esg_scores"
    id = db.Column(db.Integer, primary_key=True)
    stock_code = db.Column(db.String(10), unique=True, nullable=False)
    stock_name = db.Column(db.String(50), default="")
    total_grade = db.Column(db.String(5), default="")     # S, A+, A, B+, B, C, D
    env_grade = db.Column(db.String(5), default="")       # 환경
    social_grade = db.Column(db.String(5), default="")    # 사회
    gov_grade = db.Column(db.String(5), default="")       # 지배구조
    score = db.Column(db.Integer, default=0)              # 0~100 점수화
    data_year = db.Column(db.Integer, default=0)          # 평가년도
    updated_at = db.Column(db.DateTime, default=_now_kst)


class AuditLog(db.Model):
    """주문 감사 로그"""
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    action = db.Column(db.String(20), nullable=False)     # buy|sell|blocked|esg_filtered
    stock_code = db.Column(db.String(10), default="")
    stock_name = db.Column(db.String(50), default="")
    price = db.Column(db.Float, default=0)
    quantity = db.Column(db.Integer, default=0)
    mode = db.Column(db.String(10), default="paper")
    reason = db.Column(db.Text, default="")               # 판단 근거
    ai_score = db.Column(db.Float, nullable=True)         # AI 점수
    ai_summary = db.Column(db.Text, default="")           # AI 요약
    esg_grade = db.Column(db.String(5), default="")       # ESG 등급
    user = db.Column(db.String(50), default="")           # 실행자
    created_at = db.Column(db.DateTime, default=_now_kst)


class InvestLimit(db.Model):
    """투자 한도 설정"""
    __tablename__ = "invest_limits"
    id = db.Column(db.Integer, primary_key=True)
    daily_limit = db.Column(db.Float, default=0)          # 일일 한도 (0=무제한)
    monthly_limit = db.Column(db.Float, default=0)        # 월간 한도 (0=무제한)
    per_order_limit = db.Column(db.Float, default=0)      # 건당 한도 (0=무제한)
    esg_min_grade = db.Column(db.String(5), default="")   # ESG 최소 등급 필터 (빈값=미적용)
    updated_at = db.Column(db.DateTime, default=_now_kst)


class KisToken(db.Model):
    __tablename__ = "kis_tokens"
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(10), unique=True)  # paper|real
    access_token = db.Column(db.Text, default="")
    expires_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=_now_kst)
