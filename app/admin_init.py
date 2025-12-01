from app.models import User
from app import db

def create_default_admin():
    admin_username = "gokys2050"
    admin_password = "goys2015"

    # 이미 관리자 계정이 있으면 건너뛰기
    existing = User.query.filter_by(username=admin_username).first()
    if existing:
        print("ℹ️ 기본 관리자 계정이 이미 존재합니다.")
        return

    # User 생성 (password 없이 생성)
    admin = User(
        username=admin_username,
        name="관리자",
        is_admin=True,
        is_superadmin=True
    )

    # 여기에서 비밀번호 해싱 적용
    admin.set_password(admin_password)

    db.session.add(admin)
    db.session.commit()

    print("🔥 기본 관리자 계정 생성 완료:", admin_username)
