from sqlalchemy import text
from app import create_app, db

app = create_app()

with app.app_context():
    cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(preop_patients)")).all()]

    if "sms_sent" not in cols:
        db.session.execute(text("ALTER TABLE preop_patients ADD COLUMN sms_sent INTEGER DEFAULT 0"))
        print("✅ added sms_sent")

    if "sms_sent_at" not in cols:
        db.session.execute(text("ALTER TABLE preop_patients ADD COLUMN sms_sent_at TEXT"))
        print("✅ added sms_sent_at")

    db.session.commit()
    print("✅ migration done")
