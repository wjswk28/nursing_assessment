from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.admin_preop import admin_preop_bp
from app.models import PreOpPatient, PreOpAssessment
from app import db
from datetime import datetime, date     # ← date 추가
import uuid



"""
# ===========================================
# 관리자용: 환자 등록
# ===========================================
@admin_preop_bp.route("/create", methods=["GET", "POST"])
@login_required
def preop_create():

    if not (current_user.is_admin or current_user.is_superadmin):
        return "권한이 없습니다.", 403

    if request.method == "POST":
        name = request.form.get("name")
        patient_id = request.form.get("patient_id")
        birth_date = request.form.get("birth_date")
        phone = request.form.get("phone")
        doctor_name = request.form.get("doctor_name")
        surgery_date = request.form.get("surgery_date")

        # New fields
        gender = request.form.get("gender")
        surgery_name = request.form.get("surgery_name")

        patient = PreOpPatient(
            name=name,
            patient_id=patient_id,
            birth_date=birth_date,
            phone=phone,
            doctor_name=doctor_name,
            surgery_date=surgery_date,
            gender=gender,               # ← 추가
            surgery_name=surgery_name,   # ← 추가
            token=uuid.uuid4().hex
        )

        db.session.add(patient)
        db.session.commit()

        flash("환자가 등록되었습니다.", "success")
        return redirect(url_for("admin_preop.preop_list"))

    return render_template("admin_preop/create.html")"""

# ===========================================
# 관리자용: 엑셀 기반 환자 등록 페이지
# ===========================================
@admin_preop_bp.route("/create_excel", methods=["GET"])
@login_required
def preop_create_excel():

    if not (current_user.is_admin or current_user.is_superadmin):
        return "권한이 없습니다.", 403

    return render_template("admin_preop/create_to_excel.html")


# ===========================================
# 관리자용: 환자 리스트
# ===========================================
from sqlalchemy import or_

@admin_preop_bp.route("/list")
@login_required
def preop_list():

    if not (current_user.is_admin or current_user.is_superadmin):
        return "권한이 없습니다.", 403

    # ------------------------
    # 🔍 검색어 받기
    # ------------------------
    q = request.args.get("q", "").strip()

    query = PreOpPatient.query

    if q:
        query = query.filter(
            or_(
                PreOpPatient.name.like(f"%{q}%"),
                PreOpPatient.patient_id.like(f"%{q}%"),
                PreOpPatient.phone.like(f"%{q}%"),
                PreOpPatient.doctor_name.like(f"%{q}%"),
                PreOpPatient.surgery_name.like(f"%{q}%"),
                PreOpPatient.surgery_date.like(f"%{q}%"),
            )
        )

    # ------------------------
    # 정렬
    # ------------------------
    query = query.order_by(PreOpPatient.surgery_date.desc())

    # ------------------------
    # 페이지네이션
    # ------------------------
    page = request.args.get("page", 1, type=int)
    per_page = 10

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    patients = pagination.items

    return render_template(
        "admin_preop/list.html",
        patients=patients,
        pagination=pagination,
        q=q
    )



# ===========================================
# 관리자용: 환자 상세 보기
# ===========================================
@admin_preop_bp.route("/view/<int:patient_id>")
@login_required
def preop_view(patient_id):

    if not (current_user.is_admin or current_user.is_superadmin):
        return "권한이 없습니다.", 403

    patient = PreOpPatient.query.get_or_404(patient_id)

    rows = PreOpAssessment.query.filter_by(
        patient_id=patient.id
    ).order_by(PreOpAssessment.step).all()

    saved_data = {}

    for r in rows:
        if r.step not in saved_data:
            saved_data[r.step] = {}
        saved_data[r.step][r.question] = r.answer

    return render_template(
        "admin_preop/view.html",
        patient=patient,
        saved_data=saved_data
    )


# ===========================================
# 관리자용: 환자 정보 수정
# ===========================================   
@admin_preop_bp.route("/edit/<int:patient_id>", methods=["GET", "POST"])
def preop_edit(patient_id):

    patient = PreOpPatient.query.get_or_404(patient_id)

    if request.method == "POST":
        patient.name = request.form.get("name")
        patient.patient_id = request.form.get("patient_id")
        patient.birth_date = request.form.get("birth_date")
        patient.phone = request.form.get("phone")
        patient.doctor_name = request.form.get("doctor_name")
        patient.surgery_date = request.form.get("surgery_date")

        # New fields
        patient.gender = request.form.get("gender")
        patient.surgery_name = request.form.get("surgery_name")

        db.session.commit()
        flash("환자 정보가 수정되었습니다.", "success")
        return redirect(url_for("admin_preop.preop_list"))

    return render_template("admin_preop/edit.html", patient=patient)

@admin_preop_bp.route("/find_from_excel", methods=["POST"])
@login_required
def find_from_excel():
    import pandas as pd
    import re
    from werkzeug.utils import secure_filename
    import os

    excel_file = request.files.get("excel_file")
    patient_id = request.form.get("patient_id", "").strip()

    if not excel_file or not patient_id:
        return jsonify({"status": "error", "message": "파일 또는 등록번호가 없습니다."})

    # 파일 저장
    filename = secure_filename(excel_file.filename)
    temp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    excel_file.save(temp_path)

    # 엑셀 읽기 (header 유무 상관없이 처리)
    try:
        df = pd.read_excel(temp_path, header=None, dtype=str)
    except Exception as e:
        return jsonify({"status": "error", "message": f'엑셀 파일을 읽을 수 없습니다: {str(e)}'})

    # 🔥 모든 셀 앞뒤 공백 제거
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # ============================================================
    # 1) 등록번호(9자리 숫자)만 들어있는 열 자동 탐색
    # ============================================================
    pid_col = None
    def normalize_pid(v):
        v = str(v).strip()
        v = re.sub(r"\D", "", v)   # 숫자만 남기기
        return v.zfill(9)          # 9자리로 앞 0 채움

    # 엑셀 탐색 부분에서 패턴 탐색 대신 이렇게
    for col in df.columns:
        if df[col].apply(lambda x: normalize_pid(x) == normalize_pid(patient_id)).any():
            pid_col = col
            break

    if pid_col is None:
        return jsonify({"status": "error", "message": "등록번호(9자리)를 포함한 열을 찾을 수 없습니다."})

    # ============================================================
    # 2) 등록번호로 행 검색
    # ============================================================
    df[pid_col] = df[pid_col].astype(str).str.strip()
    row = df[df[pid_col] == patient_id]

    if row.empty:
        return jsonify({"status": "error", "message": f"[{patient_id}] 등록번호를 찾을 수 없습니다."})

    r = row.iloc[0]
    print("🔍 READ ROW:", r.to_dict())

    # 안전 문자열 처리
    def safe(v):
        return "" if pd.isna(v) else str(v).strip()

    # 🔥 날짜만 뽑아내는 함수
    def extract_date(v):
        v = safe(v)
        m = re.search(r"\d{4}-\d{2}-\d{2}", v)
        return m.group(0) if m else ""
    
    def extract_age(v):
        v = safe(v)
        m = re.search(r"\d+", v)
        return m.group(0) if m else ""

    # index는 행의 실제 길이에 따라 보정
    def get_col(idx):
        try:
            return safe(r[idx])
        except:
            return ""

    # ============================================================
    # 3) 나머지 값 매핑 (너가 제공한 엑셀 구조 기준)
    # ============================================================
    patient_data = {
        "surgery_date": extract_date(get_col(5)),
        "patient_id": safe(patient_id),
        "name": get_col(8),
        "gender": get_col(9),
        "age": extract_age(get_col(10)),
        "surgery_name": get_col(12),
        "doctor_name": get_col(13),
        "phone": get_col(30),
    }

    return jsonify({"status": "success", "patient": patient_data})

# ===========================================
# 🔥 NEW: O열이 "Gen"인 환자 전체를 반환
# ===========================================
@admin_preop_bp.route("/find_from_excel_multi", methods=["POST"])
@login_required
def find_from_excel_multi():
    import pandas as pd
    import re
    from werkzeug.utils import secure_filename
    import os

    excel_file = request.files.get("excel_file")

    if not excel_file:
        return jsonify({"status": "error", "message": "엑셀 파일이 없습니다."})

    # 파일 저장
    filename = secure_filename(excel_file.filename)
    temp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    excel_file.save(temp_path)

    # 엑셀 읽기
    try:
        df = pd.read_excel(temp_path, header=None, dtype=str)
    except Exception as e:
        return jsonify({"status": "error", "message": f"엑셀 파일을 읽을 수 없습니다: {str(e)}"})

    # 셀 공백 제거
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # 🔥 O열(인덱스 14)의 값이 "Gen"인 행 필터링
    GEN_COL = 14   # 0-based index = 15번째 열(O열)
    if GEN_COL not in df.columns:
        return jsonify({"status": "error", "message": "엑셀에서 O열(Gen 판별 열)을 찾을 수 없습니다."})

    filtered = df[df[GEN_COL] == "Gen"]

    if filtered.empty:
        return jsonify({"status": "error", "message": "Gen 환자를 찾을 수 없습니다."})

    # 안전하게 값 추출
    def safe(v):
        return "" if pd.isna(v) else str(v).strip()

    # 나이 추출
    def extract_age(v):
        v = safe(v)
        m = re.search(r"\d+", v)
        return m.group(0) if m else ""

    # 날짜 추출
    def extract_date(v):
        v = safe(v)
        m = re.search(r"\d{4}-\d{2}-\d{2}", v)
        return m.group(0) if m else ""

    patients = []

    # 🔥 각 행에서 필요한 정보 추출
    for _, r in filtered.iterrows():

        def get(idx):
            try:
                return safe(r[idx])
            except:
                return ""

        patient_data = {
            "surgery_date": extract_date(get(5)),   # F열
            "patient_id": get(7),                   # H열
            "name": get(8),                         # I열
            "gender": get(9),                       # J열
            "age": extract_age(get(10)),            # K열
            "surgery_name": get(12),                # M열
            "doctor_name": get(13),                 # N열
            "phone": get(30),                       # AE열
        }

        # 최소한의 값(name, patient_id) 체크
        if patient_data["name"] and patient_data["patient_id"]:
            patients.append(patient_data)

    return jsonify({"status": "success", "patients": patients})

@admin_preop_bp.route("/create_excel_submit", methods=["POST"])
@login_required
def preop_create_excel_submit():
    if not (current_user.is_admin or current_user.is_superadmin):
        return "권한이 없습니다.", 403

    import json
    import uuid

    json_data = request.form.get("jsonPatients", "")

    # ===========================================
    # 🔥 CASE 1) 엑셀 일괄 등록 (jsonPatients 존재)
    # ===========================================
    if json_data:
        try:
            patients = json.loads(json_data)
        except:
            flash("엑셀 데이터 파싱 오류!", "danger")
            return redirect(url_for("admin_preop.preop_create_excel_full"))

        if not isinstance(patients, list) or len(patients) == 0:
            flash("엑셀에서 가져온 환자가 없습니다.", "warning")
            return redirect(url_for("admin_preop.preop_create_excel_full"))

        created_count = 0
        for p in patients:
            try:
                patient = PreOpPatient(
                    name=p.get("name", ""),
                    patient_id=p.get("patient_id", ""),
                    age=p.get("age", ""),
                    phone=p.get("phone", ""),
                    doctor_name=p.get("doctor_name", ""),
                    surgery_date=p.get("surgery_date", ""),
                    gender=p.get("gender", ""),
                    surgery_name=p.get("surgery_name", ""),
                    token=uuid.uuid4().hex
                )
                db.session.add(patient)
                created_count += 1
            except Exception as e:
                print("❌ 등록 오류:", e)
                continue

        db.session.commit()
        flash(f"{created_count}명의 환자를 등록했습니다!", "success")
        return redirect(url_for("admin_preop.preop_list"))

    # ===========================================
    # 🔥 CASE 2) 수동 개별 등록 (jsonPatients 없음)
    # ===========================================
    name = request.form.get("name", "").strip()
    patient_id = request.form.get("patient_id", "").strip()
    age = request.form.get("age", "").strip()
    phone = request.form.get("phone", "").strip()
    doctor_name = request.form.get("doctor_name", "").strip()
    surgery_date = request.form.get("surgery_date", "").strip()
    gender = request.form.get("gender", "").strip()
    surgery_name = request.form.get("surgery_name", "").strip()

    # 필수값 확인
    if not (name and patient_id and surgery_date):
        flash("필수 항목이 누락되었습니다.", "danger")
        return redirect(url_for("admin_preop.preop_create_excel_full"))

    patient = PreOpPatient(
        name=name,
        patient_id=patient_id,
        age=age,
        phone=phone,
        doctor_name=doctor_name,
        surgery_date=surgery_date,
        gender=gender,
        surgery_name=surgery_name,
        token=uuid.uuid4().hex
    )

    db.session.add(patient)
    db.session.commit()

    flash(f"환자 [{name}] 이(가) 등록되었습니다!", "success")
    return redirect(url_for("admin_preop.preop_list"))


@admin_preop_bp.route("/create_excel_full")
@login_required
def preop_create_excel_full():
    return render_template("admin_preop/create_excel_full.html")

# ===========================================
# 관리자용: 환자 삭제
# ===========================================
@admin_preop_bp.route("/delete/<int:patient_id>", methods=["DELETE"])
@login_required
def preop_delete(patient_id):

    if not (current_user.is_admin or current_user.is_superadmin):
        return jsonify({"status": "error", "message": "권한이 없습니다."}), 403

    patient = PreOpPatient.query.get_or_404(patient_id)

    # 삭제
    db.session.delete(patient)
    db.session.commit()

    return jsonify({"status": "success", "message": "삭제되었습니다."})



