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

    # 🔍 검색어 & 날짜 파라미터
    q = request.args.get("q", "").strip()
    date_str = request.args.get("date", "").strip()

    # 기본값: 오늘 날짜 (YYYY-MM-DD)
    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")

    # 기본 쿼리: 선택된 날짜 환자만
    query = PreOpPatient.query.filter(
        PreOpPatient.surgery_date == date_str
    )

    # 검색어가 있으면, 선택된 날짜 안에서 추가 필터
    if q:
        query = query.filter(
            or_(
                PreOpPatient.name.like(f"%{q}%"),
                PreOpPatient.patient_id.like(f"%{q}%"),
                PreOpPatient.phone.like(f"%{q}%"),
                PreOpPatient.doctor_name.like(f"%{q}%"),
                PreOpPatient.surgery_name.like(f"%{q}%"),
            )
        )

    # 정렬
    query = query.order_by(PreOpPatient.surgery_date.asc(), PreOpPatient.name.asc())

    # 페이지네이션
    page = request.args.get("page", 1, type=int)
    per_page = 10

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    patients = pagination.items

    return render_template(
        "admin_preop/list.html",
        patients=patients,
        pagination=pagination,
        q=q,
        selected_date=date_str,   # 🔵 템플릿으로 날짜 전달
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
    input_pid = request.form.get("patient_id", "").strip()

    if not excel_file or not input_pid:
        return jsonify({"status": "error", "message": "파일 또는 등록번호가 없습니다."})

    # ==============================
    # 🔹 등록번호 정규화 함수
    #    - 숫자만 남기고
    #    - 앞의 0 제거
    #    - 모두 0 또는 비면 "0"
    # ==============================
    def normalize_pid(v):
        if v is None:
            return ""
        s = str(v).strip()
        s = re.sub(r"\D", "", s)   # 숫자만 남기기
        s = s.lstrip("0")          # 앞의 0 제거
        return s or "0"

    # 화면에 보여줄 때 9자리 0패딩용
    def format_pid9(v):
        return normalize_pid(v).zfill(9)

    # ------------------------------
    # 1) 파일 임시 저장
    # ------------------------------
    filename = secure_filename(excel_file.filename)
    temp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    excel_file.save(temp_path)

    # ------------------------------
    # 2) 엑셀 읽기
    # ------------------------------
    try:
        # 전부 문자열로 읽기
        df = pd.read_excel(temp_path, header=None, dtype=str)
    except Exception as e:
        return jsonify({"status": "error", "message": f"엑셀 파일을 읽을 수 없습니다: {str(e)}"})

    # 🔥 모든 셀 앞뒤 공백 제거
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # ------------------------------
    # 3) 등록번호 열 찾기 (정규화해서 비교)
    # ------------------------------
    search_key = normalize_pid(input_pid)
    pid_col = None

    for col in df.columns:
        if df[col].apply(lambda x: normalize_pid(x) == search_key).any():
            pid_col = col
            break

    if pid_col is None:
        return jsonify({"status": "error", "message": "등록번호를 포함한 열을 찾을 수 없습니다."})

    # ------------------------------
    # 4) 등록번호로 행 찾기 (정규화 기준)
    # ------------------------------
    df["_norm_pid"] = df[pid_col].apply(normalize_pid)
    row = df[df["_norm_pid"] == search_key]

    if row.empty:
        return jsonify({"status": "error", "message": f"[{input_pid}] 등록번호를 찾을 수 없습니다."})

    r = row.iloc[0]
    print("🔍 READ ROW:", r.to_dict())

    # 안전 문자열 처리
    def safe(v):
        return "" if pd.isna(v) else str(v).strip()

    # 🔥 날짜만 뽑아내는 함수 (YYYY-MM-DD)
    def extract_date(v):
        v = safe(v)
        m = re.search(r"\d{4}-\d{2}-\d{2}", v)
        return m.group(0) if m else ""
    
    # 🔥 나이만 숫자로 뽑기
    def extract_age(v):
        v = safe(v)
        m = re.search(r"\d+", v)
        return m.group(0) if m else ""

    # index는 행의 실제 길이에 따라 보정
    def get_col(idx):
        try:
            return safe(r[idx])
        except Exception:
            return ""

    # ------------------------------
    # 5) 나머지 값 매핑 (엑셀 구조 그대로)
    #    ※ 인덱스는 기존 코드 유지
    # ------------------------------
    patient_data = {
        "surgery_date": extract_date(get_col(5)),
        # 🔵 엑셀에 있는 원본 값에서 9자리로 포맷
        "patient_id": format_pid9(r[pid_col]),
        "name": get_col(8),
        "gender": get_col(9),
        "age": extract_age(get_col(10)),
        "surgery_name": get_col(12),
        "doctor_name": get_col(13),
        "phone": get_col(30),
    }

    return jsonify({"status": "success", "patient": patient_data})

@admin_preop_bp.route("/create_excel_submit", methods=["POST"])
@login_required
def preop_create_excel_submit():
    if not (current_user.is_admin or current_user.is_superadmin):
        return "권한이 없습니다.", 403

    surgery_date = request.form.get("surgery_date")
    patient_id = request.form.get("patient_id")
    name = request.form.get("name")
    gender = request.form.get("gender")
    age = request.form.get("age")
    surgery_name = request.form.get("surgery_name")
    doctor_name = request.form.get("doctor_name")
    phone = request.form.get("phone")

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

    flash("환자가 등록되었습니다!", "success")
    return redirect(url_for("admin_preop.preop_list"))
@admin_preop_bp.route("/parse_excel_gen", methods=["POST"])
@login_required
def parse_excel_gen():
    """엑셀에서 15번 열이 'Gen'인 행들만 파싱해서 미리보기용 JSON으로 반환"""
    if not (current_user.is_admin or current_user.is_superadmin):
        return jsonify({"status": "error", "message": "권한이 없습니다."}), 403

    import pandas as pd
    import re
    from werkzeug.utils import secure_filename
    import os

    excel_file = request.files.get("excel_file")
    if not excel_file:
        return jsonify({"status": "error", "message": "엑셀 파일이 필요합니다."})

    # 1) 파일 저장
    filename = secure_filename(excel_file.filename)
    temp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    excel_file.save(temp_path)

    # 2) 엑셀 읽기
    try:
        df = pd.read_excel(temp_path, header=None, dtype=str)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"엑셀 파일을 읽을 수 없습니다: {e}"
        })

    # 공백 제거
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # 유틸 함수들
    def safe(v):
        return "" if pd.isna(v) else str(v).strip()

    def extract_date(v):
        v = safe(v)
        m = re.search(r"\d{4}-\d{2}-\d{2}", v)
        return m.group(0) if m else ""

    def extract_age(v):
        v = safe(v)
        m = re.search(r"\d+", v)
        return m.group(0) if m else ""

    def normalize_pid(v):
        if v is None:
            return ""
        s = re.sub(r"\D", "", str(v))
        s = s.lstrip("0")
        return s or "0"

    def pid9(v):
        return normalize_pid(v).zfill(9)

    # 🔵 15번 열(인덱스 14)이 "Gen" 인 행만 선택
    try:
        gen_rows = df[df[14].apply(lambda x: safe(x) == "Gen")]
    except KeyError:
        return jsonify({
            "status": "error",
            "message": "엑셀에 15번째 열(Gen 열)이 없습니다. 열 위치를 확인해주세요."
        })

    if gen_rows.empty:
        return jsonify({
            "status": "error",
            "message": '15번 열이 "Gen"인 환자를 찾을 수 없습니다.'
        })

    patients = []

    # 행들을 미리보기용 dict 리스트로 변환
    for _, r in gen_rows.iterrows():
        surgery_date = extract_date(r[5])   # 6번째 열: 수술 날짜
        patient_id   = pid9(r[7])           # 8번째 열(H): 등록번호
        name         = safe(r[8])           # 9번째 열(I): 이름
        gender       = safe(r[9])           # 10번째 열(J): 성별
        age          = extract_age(r[10])   # 11번째 열(K): 나이
        surgery_name = safe(r[12])          # 13번째 열(M): 수술명
        doctor_name  = safe(r[13])          # 14번째 열(N): 주치의
        phone        = safe(r[30])          # 31번째 열(AF): 전화번호

        if not patient_id or not name:
            continue

        patients.append({
            "surgery_date": surgery_date,
            "patient_id":   patient_id,
            "name":         name,
            "gender":       gender,
            "age":          age,
            "surgery_name": surgery_name,
            "doctor_name":  doctor_name,
            "phone":        phone,
        })

    return jsonify({"status": "success", "patients": patients})

@admin_preop_bp.route("/create_excel_multi", methods=["POST"])
@login_required
def preop_create_excel_multi():
    """엑셀에서 15번 열이 'Gen' 인 행들을 모두 PreOpPatient로 일괄 등록"""
    if not (current_user.is_admin or current_user.is_superadmin):
        return jsonify({"status": "error", "message": "권한이 없습니다."}), 403

    import pandas as pd
    import re
    from werkzeug.utils import secure_filename
    import os

    excel_file = request.files.get("excel_file")
    if not excel_file:
        return jsonify({"status": "error", "message": "엑셀 파일이 필요합니다."})

    # 1) 파일 저장
    filename = secure_filename(excel_file.filename)
    temp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    excel_file.save(temp_path)

    # 2) 엑셀 읽기
    try:
        df = pd.read_excel(temp_path, header=None, dtype=str)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"엑셀 파일을 읽을 수 없습니다: {e}"
        })

    # 공백 제거
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # 유틸 함수들
    def safe(v):
        return "" if pd.isna(v) else str(v).strip()

    def extract_date(v):
        v = safe(v)
        m = re.search(r"\d{4}-\d{2}-\d{2}", v)
        return m.group(0) if m else ""

    def extract_age(v):
        v = safe(v)
        m = re.search(r"\d+", v)
        return m.group(0) if m else ""

    def normalize_pid(v):
        if v is None:
            return ""
        s = re.sub(r"\D", "", str(v))
        s = s.lstrip("0")
        return s or "0"

    def pid9(v):
        return normalize_pid(v).zfill(9)

    # 3) 🔵 15번 열이 "Gen" 인 행만 선택 (15번 열 → 인덱스 14)
    gen_rows = df[df[14].apply(lambda x: safe(x) == "Gen")]

    # 만약 첫 행이 헤더이면서 "Gen" 이라면, 아래 한 줄로 헤더를 제외할 수 있음
    # gen_rows = gen_rows[gen_rows.index > 0]

    if gen_rows.empty:
        return jsonify({
            "status": "error",
            "message": '15번 열이 "Gen"인 환자를 찾을 수 없습니다.'
        })

    count = 0

    # 4) 각 행을 PreOpPatient 로 저장
    for _, r in gen_rows.iterrows():
        surgery_date = extract_date(r[5])   # 6번째 열: 수술 날짜
        patient_id   = pid9(r[7])           # 8번째 열(H): 등록번호
        name         = safe(r[8])           # 9번째 열(I): 이름
        gender       = safe(r[9])           # 10번째 열(J): 성별
        age          = extract_age(r[10])   # 11번째 열(K): 나이
        surgery_name = safe(r[12])          # 13번째 열(M): 수술명
        doctor_name  = safe(r[13])          # 14번째 열(N): 주치의
        phone        = safe(r[30])          # 31번째 열(AF): 전화번호

        if not patient_id or not name:
            continue

        # 중복 방지: 같은 수술일 + 등록번호가 이미 있으면 건너뜀
        existing = PreOpPatient.query.filter_by(
            patient_id=patient_id,
            surgery_date=surgery_date,
        ).first()
        if existing:
            continue

        patient = PreOpPatient(
            name=name,
            patient_id=patient_id,
            age=age,
            phone=phone,
            doctor_name=doctor_name,
            surgery_date=surgery_date,
            gender=gender,
            surgery_name=surgery_name,
            token=uuid.uuid4().hex,
        )
        db.session.add(patient)
        count += 1

    db.session.commit()

    return jsonify({
        "status": "success",
        "count": count,
        "redirect_url": url_for("admin_preop.preop_list"),
    })

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



