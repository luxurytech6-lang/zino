from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Standard 5.0 grading scale (edit here if your institution uses a 4.0 scale)
GRADE_POINTS = {
    "A": 5.0,
    "B": 4.0,
    "C": 3.0,
    "D": 2.0,
    "E": 1.0,
    "F": 0.0,
}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    semesters = db.relationship(
        "Semester", backref="user", lazy=True, cascade="all, delete-orphan",
        order_by="Semester.order_index"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Semester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)  # e.g. "100 Level - First Semester"
    order_index = db.Column(db.Integer, nullable=False, default=0)  # chronological order for regression
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship(
        "Course", backref="semester", lazy=True, cascade="all, delete-orphan"
    )

    def gpa(self):
        total_points = sum(c.grade_points() * c.credit_units for c in self.courses)
        total_units = sum(c.credit_units for c in self.courses)
        return round(total_points / total_units, 2) if total_units else 0.0

    def total_units(self):
        return sum(c.credit_units for c in self.courses)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semester.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    credit_units = db.Column(db.Integer, nullable=False, default=3)
    grade = db.Column(db.String(2), nullable=False)  # A, B, C, D, E, F

    def grade_points(self):
        return GRADE_POINTS.get(self.grade.upper(), 0.0)
