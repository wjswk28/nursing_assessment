from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    name = db.Column(db.String(50))
    is_admin = db.Column(db.Boolean, default=False)
    is_superadmin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PreOpPatient(db.Model):
    __tablename__ = "preop_patients"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), nullable=False)
    patient_id = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    sms_sent = db.Column(db.Boolean, default=False)   # 문자 전송 여부
    sms_sent_at = db.Column(db.DateTime, nullable=True)  # 마지막 전송 시각
    gender = db.Column(db.String(1))
    surgery_name = db.Column(db.String(200))
    doctor_name = db.Column(db.String(50), nullable=False)
    surgery_date = db.Column(db.String(10), nullable=False)

    submitted = db.Column(db.Boolean, default=False)

    token = db.Column(db.String(100), unique=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    age = db.Column(db.String(5))

    # 🔥 올바른 cascade 관계 (정답)
    assessments = db.relationship(
        "PreOpAssessment",
        cascade="all, delete-orphan",
        backref=db.backref("patient", passive_deletes=True)
    )


class PreOpAssessment(db.Model):
    __tablename__ = "preop_assessments"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("preop_patients.id", ondelete="CASCADE"),
        nullable=False
    )

    step = db.Column(db.Integer, nullable=False)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
