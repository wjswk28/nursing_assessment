# app/admin_init.py

from app.models import User
from app import db

def create_default_admin():
    """관리자 계정을 자동 생성 (이미 있으면 패스)"""

    admin_username = "gokys2050"
    admin_password = "goys2015"

    # 이미 관리자 계정이 있는지 확인
    existing = User.query.filter_by(username=admin_username).first()
    if existing:
        print("ℹ️ 기본 관리자 계정이 이미 존재합니다.")
        return

    # 관리자 계정 생성
    admin = User(
        username=admin_username,
        password=admin_password,   # 필요하면 해싱 적용 가능
        name="관리자",
        department="관리자",
        is_admin=True,
        is_superadmin=True
    )

    db.session.add(admin)
    db.session.commit()

    print("🔥 기본 관리자 계정 생성 완료:", admin_username)
