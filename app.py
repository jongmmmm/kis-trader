from flask import Flask
from flask_login import LoginManager
from config import Config
from db import db

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["CURRENT_MODE"] = "paper"
    app.config["REMEMBER_COOKIE_DURATION"] = 60 * 60 * 24 * 30  # 30일

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    with app.app_context():
        import models  # noqa: F401 — 모든 모델 로드 후 테이블 생성
        db.create_all()

    from routers import dashboard_bp, strategies_bp, orders_bp, auction_bp, settings_bp, auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(strategies_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(auction_bp)
    app.register_blueprint(settings_bp)

    from scheduler import init_scheduler
    init_scheduler(app)

    return app
