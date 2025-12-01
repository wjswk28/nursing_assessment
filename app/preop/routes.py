from flask import render_template, request, redirect, url_for, flash, current_app
from app.preop import preop_bp
from app.models import PreOpPatient, PreOpAssessment
from app import db
from datetime import datetime
import os
from zoneinfo import ZoneInfo


# ======================================
# 시작 화면
# =====================================
@preop_bp.route("/start/<token>")
def start(token):
    patient = PreOpPatient.query.filter_by(token=token).first()

    if not patient:
        return "잘못된 접근입니다.", 404

    return render_template("preop/start.html", patient=patient)


@preop_bp.route("/form/<token>/step/<int:step>", methods=["GET", "POST"])
def form_step(token, step):
    patient = PreOpPatient.query.filter_by(token=token).first_or_404()

    # -----------------------------
    # 모든 step에서 기존 데이터 로딩
    # -----------------------------
    saved_answers = {
        a.question: a.answer
        for a in PreOpAssessment.query.filter_by(patient_id=patient.id, step=step).all()
    }

    # =============================
    # STEP 1 : 기본 정보 저장 + 로딩
    # =============================
    if step == 1:
        if request.method == "POST":
            name = request.form.get("name")
            surgery_date = request.form.get("surgery_date")

            errors = []

            # 이름 검증
            if name != patient.name:
                errors.append("이름이 등록된 정보와 일치하지 않습니다.")

            # 수술날짜 검증
            if surgery_date != patient.surgery_date:
                errors.append("수술 날짜가 등록된 정보와 일치하지 않습니다.")

            # 오류 처리
            if errors:
                flash(" / ".join(errors), "error")
                return render_template("preop/step_1.html",
                                    patient=patient,
                                    step=step,
                                    saved={})

            # 저장 전 기존 데이터 삭제
            PreOpAssessment.query.filter_by(patient_id=patient.id, step=1).delete()

            # 저장 (질문/답변 형식으로 저장됨)
            db.session.add_all([
                PreOpAssessment(patient_id=patient.id, step=1, question="name", answer=name),
                PreOpAssessment(patient_id=patient.id, step=1, question="surgery_date", answer=surgery_date),
            ])
            db.session.commit()

            return redirect(url_for("preop.form_step", token=token, step=2))

        # GET 요청 시 기존 값 표시
        return render_template("preop/step_1.html",
                            patient=patient,
                            step=step,
                            saved=saved_answers)

    # =============================
    # STEP 2 : 키/몸무게/증상/경위
    # =============================
    if step == 2:
        if request.method == "POST":
            PreOpAssessment.query.filter_by(patient_id=patient.id, step=2).delete()

            fields = ["height", "weight", "chief_complaint", "injury_cause"]

            for f in fields:
                value = request.form.get(f, "")
                db.session.add(
                    PreOpAssessment(
                        patient_id=patient.id,
                        step=2,
                        question=f,
                        answer=value
                    )
                )

            db.session.commit()
            return redirect(url_for("preop.form_step", token=token, step=3))

        return render_template("preop/step_2.html",
                               patient=patient,
                               step=step,
                               saved=saved_answers)

    # =============================
    # STEP 4 : 복용약 + 과거 수술 + 이미지
    # =============================
    if step == 4:
        if request.method == "POST":

            # 기존 step4 데이터 삭제
            PreOpAssessment.query.filter_by(patient_id=patient.id, step=4).delete()

            # 복용약
            oral_med = request.form.get("oral_med", "")
            oral_desc = request.form.get("oral_med_desc", "")

            db.session.add(PreOpAssessment(patient_id=patient.id, step=4,
                                        question="oral_med", answer=oral_med))
            db.session.add(PreOpAssessment(patient_id=patient.id, step=4,
                                        question="oral_med_desc", answer=oral_desc))

            # 복용약 이미지
            oral_img = request.files.get("oral_med_image")
            if oral_img and oral_img.filename:
                filename = f"oral_{patient.id}_{step}_{oral_img.filename}"
                filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                oral_img.save(filepath)

                db.session.add(PreOpAssessment(patient_id=patient.id, step=4,
                                            question="oral_med_image", answer=filename))

            # 과거 수술 여부
            sh = request.form.get("surgery_history", "")
            db.session.add(PreOpAssessment(
                patient_id=patient.id, step=4,
                question="surgery_history", answer=sh
            ))

            # 여러 개의 수술 입력값들 -> 배열로 받기
            sh_desc_list = request.form.getlist("surgery_history_desc[]")
            combined = "|".join(sh_desc_list)

            db.session.add(PreOpAssessment(
                patient_id=patient.id, step=4,
                question="surgery_history_desc", answer=combined
            ))

            db.session.commit()

            return redirect(url_for("preop.form_step", token=token, step=5))

        # -------------------------
        # 🔥 GET 요청 시 데이터 복원 추가 (중요한 부분)
        # -------------------------
        # 수술기록 문자열 불러오기
        sh_combined = saved_answers.get("surgery_history_desc", "")
        saved_list = sh_combined.split("|") if sh_combined else []

        # saved_answers 에 리스트를 추가해야 step_4.html 에서 사용 가능
        saved_answers["surgery_history_desc_list"] = saved_list

        return render_template("preop/step_4.html",
                            patient=patient,
                            step=step,
                            saved=saved_answers)


    # =============================
    # STEP 3, 5, 6, 7 ... 자동 저장
    # =============================
    if request.method == "POST":

        PreOpAssessment.query.filter_by(patient_id=patient.id, step=step).delete()

        for key, value in request.form.items():
            db.session.add(
                PreOpAssessment(
                    patient_id=patient.id,
                    step=step,
                    question=key,
                    answer=value
                )
            )

        db.session.commit()

        # ⭐ Step9이면 종료로 이동
        if step == 9:
            patient.submitted = True
            patient.completed_at = datetime.utcnow()
            db.session.commit()

            # ⭐ 네이트온 메시지 전송
            from app.preop.utils import send_nateon_message

            msg = (
                f"[수술 전 문진 제출 완료]\n"
                f"이름: {patient.name}\n"
                f"등록번호: {patient.patient_id}\n"
                f"수술일: {patient.surgery_date}\n"
                f"주치의: {patient.doctor_name}\n"
                f"제출시간: {datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M')}"
            )
            send_nateon_message(msg)

            return redirect(url_for("preop.preop_complete", token=token))


        # ⭐ Step1~8은 다음 스텝으로 이동
        return redirect(url_for("preop.form_step", token=token, step=step + 1))

    return render_template(f"preop/step_{step}.html",
                           patient=patient,
                           step=step,
                           saved=saved_answers)
 
 
# ======================================
# 제출 완료
# ======================================   


@preop_bp.route("/complete/<string:token>")
def preop_complete(token):
    form = PreOpPatient.query.filter_by(token=token).first_or_404()

    return render_template("preop/complete.html", form=form)
