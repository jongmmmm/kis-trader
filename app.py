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

    from routers import dashboard_bp, strategies_bp, orders_bp, auction_bp, settings_bp, auth_bp, chat_bp, esg_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(strategies_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(auction_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(esg_bp)

    from scheduler import init_scheduler
    init_scheduler(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request as req, jsonify as jf, redirect
        if req.path.startswith('/api/') or req.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jf({"authenticated": False, "msg": "로그인이 필요합니다."}), 401
        return redirect('/login')

    # 파일 다운로드
    @app.route('/download/<path:filename>')
    def download_file(filename):
        from flask import send_from_directory, abort
        import os as _os
        download_dir = _os.path.expanduser('~/자료구조')
        fpath = _os.path.join(download_dir, filename)
        if not _os.path.exists(fpath):
            abort(404)
        return send_from_directory(download_dir, filename, as_attachment=True)

    # Serve React SPA build
    import os
    frontend_dist = os.path.join(os.path.dirname(__file__), 'frontend', 'dist')

    @app.route('/react/', defaults={'path': ''})
    @app.route('/react/<path:path>')
    def serve_react(path):
        from flask import send_from_directory
        if path and os.path.exists(os.path.join(frontend_dist, path)):
            return send_from_directory(frontend_dist, path)
        index_path = os.path.join(frontend_dist, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(frontend_dist, 'index.html')
        return "React build not found. Run 'npm run build' in frontend/", 404

    return app
