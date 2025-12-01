import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # =========================================================
    # 1) STORAGE 경로 (Render / Local 자동 인식)
    # =========================================================
    if os.path.exists("/var/data"):
        STORAGE_ROOT = "/var/data"   # Render
    else:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        STORAGE_ROOT = os.path.join(BASE_DIR, "..", "instance")  # Local

    os.makedirs(STORAGE_ROOT, exist_ok=True)
    app.config["STORAGE_ROOT"] = STORAGE_ROOT

    # =========================================================
    # 2) 내부에서 쓰는 폴더 정의
    # =========================================================
    app.config["UPLOAD_FOLDER"] = os.path.join(STORAGE_ROOT, "uploads")
    app.config["PREOP_FOLDER"] = os.path.join(STORAGE_ROOT, "preop")
    app.config["FORMS_FOLDER"] = os.path.join(STORAGE_ROOT, "forms")
    app.config["EXCEL_OUTPUT"] = os.path.join(STORAGE_ROOT, "excel_output")
    app.config["NATEON_WEBHOOK_URL"] = os.environ.get("NATEON_WEBHOOK_URL")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PREOP_FOLDER"], exist_ok=True)
    os.makedirs(app.config["FORMS_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXCEL_OUTPUT"], exist_ok=True)

    # =========================================================
    # 3) SECRET_KEY + DB 설정
    # =========================================================
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key")

    db_path = os.path.join(STORAGE_ROOT, "database.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    # =========================================================
    # 4) Blueprint 등록
    # =========================================================
    from app.preop import preop_bp
    app.register_blueprint(preop_bp)

    from app.admin_preop import admin_preop_bp
    app.register_blueprint(admin_preop_bp)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # =========================================================
    # 5) DB 테이블 생성 + 기본 관리자 계정 생성
    # =========================================================
    with app.app_context():
        db.create_all()   # 🔥 테이블 자동 생성
        from app.admin_init import create_default_admin
        create_default_admin()   # 🔥 테이블 생성 후 관리자 생성

    return app
