from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Semester, Course, GRADE_POINTS
from app.predict import predict_next_gpa, predict_future_cgpa

main_bp = Blueprint("main", __name__)


def compute_cgpa(semesters):
    total_points = sum(c.grade_points() * c.credit_units for s in semesters for c in s.courses)
    total_units = sum(c.credit_units for s in semesters for c in s.courses)
    return round(total_points / total_units, 2) if total_units else 0.0


@main_bp.route("/")
def index():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    semesters = current_user.semesters  # ordered by order_index
    cgpa = compute_cgpa(semesters)
    semester_gpas = [s.gpa() for s in semesters if s.courses]

    prediction = predict_next_gpa(semester_gpas)

    future_cgpa = None
    if prediction["has_prediction"] and semesters:
        history = [{"gpa": s.gpa(), "units": s.total_units()} for s in semesters if s.courses]
        avg_units = round(sum(h["units"] for h in history) / len(history)) if history else 15
        future_cgpa = predict_future_cgpa(
            history, prediction["blended_prediction"], avg_units, future_semesters=1
        )

    total_units = sum(s.total_units() for s in semesters)

    return render_template(
        "dashboard.html",
        semesters=semesters,
        cgpa=cgpa,
        total_units=total_units,
        prediction=prediction,
        future_cgpa=future_cgpa,
        grade_points=GRADE_POINTS,
    )


@main_bp.route("/api/chart-data")
@login_required
def chart_data():
    semesters = current_user.semesters
    labels = [s.name for s in semesters if s.courses]
    gpas = [s.gpa() for s in semesters if s.courses]

    cumulative = []
    running_points, running_units = 0.0, 0
    for s in semesters:
        if not s.courses:
            continue
        running_points += sum(c.grade_points() * c.credit_units for c in s.courses)
        running_units += s.total_units()
        cumulative.append(round(running_points / running_units, 2) if running_units else 0)

    prediction = predict_next_gpa(gpas)
    predicted_point = prediction["blended_prediction"] if prediction["has_prediction"] else None

    return jsonify({
        "labels": labels,
        "gpas": gpas,
        "cumulative": cumulative,
        "predicted_next_gpa": predicted_point,
    })


@main_bp.route("/semesters/add", methods=["POST"])
@login_required
def add_semester():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Semester name is required.", "danger")
        return redirect(url_for("main.dashboard"))

    max_order = max([s.order_index for s in current_user.semesters], default=0)
    semester = Semester(name=name, user_id=current_user.id, order_index=max_order + 1)
    db.session.add(semester)
    db.session.commit()
    flash(f"Semester '{name}' added.", "success")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/semesters/<int:semester_id>/delete", methods=["POST"])
@login_required
def delete_semester(semester_id):
    semester = Semester.query.filter_by(id=semester_id, user_id=current_user.id).first_or_404()
    db.session.delete(semester)
    db.session.commit()
    flash("Semester deleted.", "info")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/semesters/<int:semester_id>")
@login_required
def semester_detail(semester_id):
    semester = Semester.query.filter_by(id=semester_id, user_id=current_user.id).first_or_404()
    return render_template("semester_detail.html", semester=semester, grade_points=GRADE_POINTS)


@main_bp.route("/semesters/<int:semester_id>/courses/add", methods=["POST"])
@login_required
def add_course(semester_id):
    semester = Semester.query.filter_by(id=semester_id, user_id=current_user.id).first_or_404()

    title = request.form.get("title", "").strip()
    grade = request.form.get("grade", "").strip().upper()
    try:
        credit_units = int(request.form.get("credit_units", 0))
    except ValueError:
        credit_units = 0

    if not title or grade not in GRADE_POINTS or credit_units <= 0:
        flash("Please provide a valid course title, grade, and credit units.", "danger")
        return redirect(url_for("main.semester_detail", semester_id=semester_id))

    course = Course(title=title, grade=grade, credit_units=credit_units, semester_id=semester.id)
    db.session.add(course)
    db.session.commit()
    flash(f"Course '{title}' added.", "success")
    return redirect(url_for("main.semester_detail", semester_id=semester_id))


@main_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    semester = Semester.query.filter_by(id=course.semester_id, user_id=current_user.id).first_or_404()
    semester_id = semester.id
    db.session.delete(course)
    db.session.commit()
    flash("Course removed.", "info")
    return redirect(url_for("main.semester_detail", semester_id=semester_id))
